"""Reverse interest queries and workspace-wide aggregation.

# Subsystem: docs/subsystems/cross_repo_operations - Reverse reading of interest edges
# Chunk: docs/chunks/federation_reverse_interest - Inbound edge enumeration

An `external.yaml` pointer is a directed edge: the tree holding it records that it
reads an artifact owned by another tree. Every existing operation follows that
edge *forwards* (resolve the pointer, fetch the content). This module reads the
edges backwards, which is the query the graph-shaped ownership model owes its
users: with promotion, everything important is visible at the workspace root;
with ownership left where the enforcing code lives, it is not - unless tooling
aggregates. That is the cost this module pays.

Two primitives, both CLI-free so validation can reuse them:

- :func:`scan_interest_edges` walks every member tree once and returns every
  pointer it found, resolved where possible and flagged where not. Indexes on the
  result answer "who consumes X?" without re-walking, so one scan serves a
  whole-workspace audit.
- :func:`iter_member_trees` is the iteration surface for aggregated listings.

Two rules the rest of the module rests on:

**Peer matching is by resolved path, never by member name.** A pointer targets
artifact X iff `Workspace.resolve(ref.tree)/docs/<type>/<id>` *is* X's directory
- the same authority :func:`external_resolve.resolve_peer_pointer` uses when it
follows the edge forwards. Comparing member-name strings instead would miss a
tree registered under a second name and would silently conflate two names that
map to one path. Reverse and forward resolution must agree, or the report is a
different kind of lie than the one this narrative set out to kill.

**Cross-repo pointers are matched by artifact id, and never mixed in with peers.**
`why:` is legal on `repo:` pointers too, and in the monorepo that motivated this
work most pointers are `repo:` pointers at a hub repo, so hiding them would
answer "who consumes this?" wrongly. But nothing inside the workspace can verify
what a repository contains: an id match is a strong hint, not a resolution.
:class:`ConsumerReport` therefore keeps the certain answers and the heuristic
ones in separate lists, and callers are expected to keep them visibly apart.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from external_refs import (
    ARTIFACT_DIR_NAME,
    is_external_artifact,
    load_external_ref,
)
from models import ArtifactType, ExternalArtifactRef
from models.workspace import WorkspaceMember
from workspace import Workspace


# Chunk: docs/chunks/federation_reverse_interest - A reported row stays one row
def summarize_pointer_error(error: BaseException) -> str:
    """Render why a pointer could not be read as a single line.

    Every consumer of this text tabulates it - a listing row, a report line - so a
    raw multi-line `ValidationError` (three lines and a docs URL per problem)
    would break the shape of the output that carries it. This is the same
    constraint `ExternalArtifactRef.why` is validated against, applied to error
    text: field paths and messages joined the way `workspace.load_manifest`
    already reports manifest defects.
    """
    if isinstance(error, ValidationError):
        return "; ".join(
            f"{'.'.join(str(part) for part in item['loc']) or 'external.yaml'}: "
            f"{item['msg']}"
            for item in error.errors()
        )
    return " ".join(str(error).split())


def _relative_to_root(root: Path, path: Path) -> str:
    """Render `path` relative to the workspace root, as a POSIX path.

    Falls back to the absolute path when the two are unrelated, so a report never
    fails on an odd layout (a member reached through a symlink, say).
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# Chunk: docs/chunks/federation_reverse_interest - One inbound pointer, resolved or not
@dataclass(frozen=True)
class InterestEdge:
    """One `external.yaml` pointer, read as an inbound edge on its target.

    `target_dir` is the artifact directory the pointer resolves to, and is None
    for a pointer that cannot be resolved inside this workspace: either a `tree:`
    naming an unregistered member (then `unresolved_reason` says so) or a `repo:`
    pointer, whose target lives in another repository by definition.
    """

    member: str
    member_path: Path
    pointer_dir: Path
    pointer_rel: str
    ref: ExternalArtifactRef
    # The artifact type of the directory the pointer *lives* in. Normally equal to
    # `ref.artifact_type`, but a hand-written pointer can disagree with its own
    # location, and preserving the disagreement is what lets a validator report it.
    # Addressing always uses `ref.artifact_type`: that is what the pointer says
    # about its target.
    pointer_type: ArtifactType | None = None
    target_dir: Path | None = None
    unresolved_reason: str | None = None

    @property
    def is_peer(self) -> bool:
        """True when this edge addresses another tree in the same workspace."""
        return self.ref.is_peer

    @property
    def why(self) -> str | None:
        """The interest note, if the pointer records one."""
        return self.ref.why

    @property
    def target_display(self) -> str:
        """The pointer's target, formatted for human output."""
        return self.ref.target_display

    @property
    def flavor(self) -> str:
        """"peer" or "repo" - which addressing flavor this edge uses."""
        return "peer" if self.is_peer else "repo"

    # Chunk: docs/chunks/federation_reverse_interest - Rows that are working addresses
    @property
    def qualified_pointer(self) -> str:
        """The pointer's own location as a qualified reference.

        `<member>::docs/<type>/<name>` - the grammar inline backreferences accept,
        so a reported row can be pasted into a comment and still resolve.

        The type comes from the directory the pointer *lives* in, not from
        `ref.artifact_type`: the two can disagree in a hand-written pointer, and
        this string is an address of the pointer itself. Matching against a target
        uses `ref.artifact_type`, which is what the pointer says about its target.
        """
        return f"{self.member}::docs/{self.pointer_dir.parent.name}/{self.pointer_dir.name}"


# Chunk: docs/chunks/federation_reverse_interest - Unreadable pointers are reported, not fatal
@dataclass(frozen=True)
class MalformedPointer:
    """An `external.yaml` that exists but could not be understood.

    Collected rather than raised: a single bad file in one of 29 trees must not
    take down a workspace-wide query, and a pointer nobody can read is itself a
    finding worth printing.
    """

    member: str
    pointer_dir: Path
    pointer_rel: str
    message: str


# Chunk: docs/chunks/federation_reverse_interest - One scan, many questions
@dataclass(frozen=True)
class InterestScan:
    """Every pointer found in a workspace, with lookup indexes over them.

    The indexes are built once at construction, so a caller asking about many
    artifacts against one scan (a whole-workspace audit, say) pays for the walk
    and the indexing once rather than per question.
    """

    workspace: Workspace
    edges: list[InterestEdge] = field(default_factory=list)
    malformed: list[MalformedPointer] = field(default_factory=list)
    _by_target: dict[tuple[ArtifactType, Path], list[InterestEdge]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _by_artifact_id: dict[tuple[ArtifactType, str], list[InterestEdge]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        by_target: dict[tuple[ArtifactType, Path], list[InterestEdge]] = defaultdict(list)
        by_artifact_id: dict[tuple[ArtifactType, str], list[InterestEdge]] = defaultdict(list)
        for edge in self.edges:
            if edge.target_dir is not None:
                by_target[(edge.ref.artifact_type, edge.target_dir)].append(edge)
            by_artifact_id[(edge.ref.artifact_type, edge.ref.artifact_id)].append(edge)
        self._by_target.update(by_target)
        self._by_artifact_id.update(by_artifact_id)

    def by_target(self) -> dict[tuple[ArtifactType, Path], list[InterestEdge]]:
        """Resolved peer edges, keyed by (type, resolved target directory).

        The authoritative index: a key here is an address, so a hit means the
        pointer resolves to exactly that artifact.
        """
        return self._by_target

    def by_artifact_id(self) -> dict[tuple[ArtifactType, str], list[InterestEdge]]:
        """All edges, keyed by (type, target artifact id).

        Weaker than :meth:`by_target` - an id is not an address - but it is the
        only key a `repo:` pointer offers, and it is what a validator needs when
        it asks "does a pointer at this name already exist anywhere?".
        """
        return self._by_artifact_id


# Chunk: docs/chunks/federation_reverse_interest - The answer to "who consumes this?"
@dataclass(frozen=True)
class ConsumerReport:
    """Who reads one artifact, split by how certain the answer is.

    `peers` resolved to this exact artifact directory. `cross_repo` merely name an
    artifact with the same id in some other repository; they are reported because
    the interest is real, and kept separate because the match is not verified.
    """

    artifact_type: ArtifactType
    artifact_id: str
    owner_root: Path
    # The member that *is* the owning tree, or None when the owning tree is not
    # itself registered. Deliberately not "the innermost member containing it": an
    # enclosing member does not own this artifact, and nothing can point at an
    # unregistered tree, so conflating the two would turn an unanswerable question
    # into a confident "no consumers".
    owner_member: WorkspaceMember | None
    target_dir: Path
    target_exists: bool
    peers: list[InterestEdge] = field(default_factory=list)
    cross_repo: list[InterestEdge] = field(default_factory=list)
    malformed: list[MalformedPointer] = field(default_factory=list)

    @property
    def has_consumers(self) -> bool:
        """True when any tree in the workspace records interest in this artifact."""
        return bool(self.peers or self.cross_repo)


# Chunk: docs/chunks/federation_reverse_interest - Iteration surface for aggregated listings
def iter_member_trees(workspace: Workspace) -> Iterator[tuple[WorkspaceMember, Path]]:
    """Yield each member with the absolute path of its tree root.

    Members are yielded in declaration order, deduplicated by resolved path: a
    tree registered under two names is one tree on disk, and listing it twice
    would report its artifacts twice. Members whose path does not exist are still
    yielded - a registered tree that has vanished is a finding, and hiding it here
    would make the caller's report quietly incomplete.
    """
    seen: set[Path] = set()
    for member in workspace.members:
        path = workspace.member_path(member)
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        yield member, path


# Chunk: docs/chunks/federation_reverse_interest - Pointer enumeration within one tree
def iter_pointers(tree_root: Path) -> Iterator[tuple[ArtifactType, Path]]:
    """Yield every pointer artifact directory in one tree, with its type.

    A pointer is an artifact directory holding `external.yaml` and no main
    document - the definition :func:`external_refs.is_external_artifact` already
    enforces everywhere else.
    """
    for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
        artifacts_dir = tree_root / "docs" / dir_name
        if not artifacts_dir.is_dir():
            continue
        for artifact_dir in sorted(artifacts_dir.iterdir()):
            if not artifact_dir.is_dir():
                continue
            if is_external_artifact(artifact_dir, artifact_type):
                yield artifact_type, artifact_dir


# Chunk: docs/chunks/federation_reverse_interest - The single workspace-wide walk
def scan_interest_edges(workspace: Workspace) -> InterestScan:
    """Read every pointer in every member tree as an inbound edge.

    Peer pointers are resolved through the manifest here, once, so that callers
    can match on target identity rather than on member-name strings.

    Args:
        workspace: The loaded workspace to walk.

    Returns:
        An :class:`InterestScan` holding the edges and any unreadable pointers.
    """
    root = workspace.root
    edges: list[InterestEdge] = []
    malformed: list[MalformedPointer] = []

    for member, member_path in iter_member_trees(workspace):
        if not member_path.is_dir():
            continue
        for artifact_type, pointer_dir in iter_pointers(member_path):
            pointer_rel = _relative_to_root(root, pointer_dir)
            try:
                ref = load_external_ref(pointer_dir)
            except Exception as exc:  # pydantic ValidationError, YAML errors, IO
                malformed.append(
                    MalformedPointer(
                        member=member.name,
                        pointer_dir=pointer_dir,
                        pointer_rel=pointer_rel,
                        message=summarize_pointer_error(exc),
                    )
                )
                continue

            target_dir: Path | None = None
            unresolved_reason: str | None = None
            if ref.is_peer:
                try:
                    target_root = workspace.resolve(ref.tree)
                except KeyError:
                    unresolved_reason = (
                        f"tree '{ref.tree}' is not registered in "
                        f"{workspace.manifest_path}"
                    )
                else:
                    target_dir = (
                        target_root
                        / "docs"
                        / ARTIFACT_DIR_NAME[ref.artifact_type]
                        / ref.artifact_id
                    ).resolve()

            edges.append(
                InterestEdge(
                    member=member.name,
                    member_path=member_path,
                    pointer_dir=pointer_dir,
                    pointer_rel=pointer_rel,
                    ref=ref,
                    pointer_type=artifact_type,
                    target_dir=target_dir,
                    unresolved_reason=unresolved_reason,
                )
            )

    return InterestScan(workspace=workspace, edges=edges, malformed=malformed)


# Chunk: docs/chunks/federation_reverse_interest - Reverse lookup for one artifact
def find_consumers(
    workspace: Workspace,
    artifact_type: ArtifactType,
    artifact_id: str,
    owner_root: Path,
    scan: InterestScan | None = None,
) -> ConsumerReport:
    """Find every tree in the workspace recording interest in one artifact.

    The artifact need not exist: pointers at an artifact that was renamed or
    deleted are precisely what a reverse query is for, and `target_exists` on the
    result reports that condition instead of suppressing the answer.

    Args:
        workspace: The loaded workspace to search.
        artifact_type: The target artifact's type.
        artifact_id: The target artifact's directory name in its owning tree.
        owner_root: Root of the tree that owns the artifact.
        scan: An existing scan to reuse. Pass one when asking about many
            artifacts so the walk happens once.

    Returns:
        A :class:`ConsumerReport`, with peer and cross-repo interest separated.
    """
    scan = scan if scan is not None else scan_interest_edges(workspace)

    target_dir = owner_root / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
    resolved_target = target_dir.resolve()

    peers = scan.by_target().get((artifact_type, resolved_target), [])
    cross_repo = [
        edge
        for edge in scan.by_artifact_id().get((artifact_type, artifact_id), [])
        if not edge.is_peer
    ]

    enclosing = workspace.find_member_for_path(owner_root)
    owner_member = (
        enclosing
        if enclosing is not None
        and workspace.member_path(enclosing).resolve() == owner_root.resolve()
        else None
    )

    return ConsumerReport(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        owner_root=owner_root,
        owner_member=owner_member,
        target_dir=target_dir,
        target_exists=target_dir.is_dir(),
        peers=list(peers),
        cross_repo=cross_repo,
        malformed=list(scan.malformed),
    )


__all__ = [
    "ConsumerReport",
    "InterestEdge",
    "InterestScan",
    "MalformedPointer",
    "find_consumers",
    "iter_member_trees",
    "iter_pointers",
    "scan_interest_edges",
    "summarize_pointer_error",
]
