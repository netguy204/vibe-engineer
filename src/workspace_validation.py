"""Workspace-wide reference validation: every defect, with a fix class.

# Chunk: docs/chunks/federation_global_validator - Workspace reference validator

This module answers one question for a whole repository of VE trees: does every
reference resolve, and if not, *what kind* of fix does it need? It is the engine
behind `ve workspace validate` and the CI gate that makes referential integrity
dischargeable at monorepo scale.

It adds no grammar and no new resolution rule. Four authorities already exist,
and this module only joins them:

- what a reference *is* — ``backreferences.scan_backreferences`` and
  ``QualifierKind`` (``federation_qualified_refs``);
- which trees exist — the ``.ve-workspace.yaml`` manifest (``workspace``);
- which tree *governs a file* — ``project.find_enclosing_tree``
  (``federation_tree_discovery``);
- whether a pointer resolves — ``external_resolve.resolve_peer_pointer``
  (``federation_peer_refs``).

Governing trees vs member trees
-------------------------------

Three tree predicates exist in the codebase, and reconciling them is this
module's call. The semantics adopted here:

- A **governing tree** requires ``docs/trunk/``. Only a governing tree can
  answer "what does a *bare* reference in this file mean?" That is
  ``project.find_enclosing_tree``, imported below as ``find_governing_tree``:
  the nearest enclosing tree of the *file*, never the working directory, never
  the repository root.
- A **member tree** only has to be registered in the manifest. Every member is
  a legitimate *target* of a ``member::`` qualifier or a ``tree:`` pointer —
  including a pointer-only tree that holds nothing but ``external.yaml``
  interest edges. This matches ``resolve_peer_pointer``, which deliberately
  gates on registration rather than on a tree predicate, and
  ``workspace.is_ve_tree``, the permissive predicate imported here as
  ``is_member_tree``.

The consequence, stated as a rule: **pointer-only trees are addressable but not
governing.** A bare reference in a file inside a pointer-only tree has no
governing tree of its own, and is reported as ``unresolvable-bare`` or
``misrouted-bare`` — correctly, because it is unaddressed, and the fix is to
qualify it.

Known duplication, not resolved here: ``project.is_ve_tree`` (all of
``project.TREE_MARKERS``, today exactly ``docs/trunk/``) and
``workspace.has_trunk`` are the same test under two names. They agree, so
nothing is broken; unifying them touches two modules for no behavioral gain and
is left as a follow-up.

Two limits this validator states rather than hides
--------------------------------------------------

1. **Own-line comments only.** The shared grammar accepts a backreference at
   any indentation, so references inside classes and functions are scanned like
   any other. What it will not do is find one trailing after code on the same
   line: a grammar loose enough to match that is loose enough to match prose
   *about* references. A clean report means "every own-line reference
   resolves", and the CLI says so.
2. **``org/repo`` targets are unverified.** Resolving them needs network access
   or a warm repo cache, so they are collected in ``ValidationReport.unverified``
   and never reported as defects. A gate whose verdict depends on whether a
   cache happened to be warm is not a gate. ``member::`` targets are the
   deliberate contrast: they live in this same working copy, so they resolve
   through the manifest and *are* verified — in comments and in frontmatter
   declared-path fields alike (``federation_member_refs``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from backreferences import ParsedBackreference, QualifierKind, scan_backreferences
from external_refs import (
    ARTIFACT_DIR_NAME,
    ARTIFACT_MAIN_FILE,
    is_external_artifact,
    load_external_ref,
)
from external_resolve import resolve_peer_pointer
from frontmatter import parse_frontmatter
from models import ArtifactType, ChunkFrontmatter, ChunkStatus, SubsystemFrontmatter

# Chunk: docs/chunks/federation_member_refs - Shared qualifier shape rule
from models.shared import classify_qualifier_shape
from project import find_enclosing_tree as find_governing_tree
from source_files import enumerate_source_files
from symbols import expand_glob, is_glob_pattern, name_is_reexport_only
from task import TaskChunkError
from workspace import (
    Workspace,
    is_ve_tree as is_member_tree,
    load_workspace,
    scan_for_trees,
    validate_member_paths,
)

# Artifact types whose main document carries a `code_references` field. Chunks
# and subsystems are the only two schemas that have one, so there is nothing to
# read for narratives or investigations.
_FRONTMATTER_MODELS: dict[ArtifactType, type] = {
    ArtifactType.CHUNK: ChunkFrontmatter,
    ArtifactType.SUBSYSTEM: SubsystemFrontmatter,
}


# Chunk: docs/chunks/federation_global_validator - Machine-readable fix classes
class FixClass(StrEnum):
    """What kind of fix a defect needs.

    Declaration order is report order: the two bare-reference classes come
    first because they are the case study's silent failures, and the
    frontmatter class comes last because it is the least likely to hide a
    routing mistake.

    The `federation_validate_fix_skill` loop dispatches on these values, so they
    are part of this module's contract with that skill.
    """

    UNRESOLVABLE_BARE = "unresolvable-bare"
    MISROUTED_BARE = "misrouted-bare"
    UNKNOWN_QUALIFIER = "unknown-qualifier"
    MISSING_TARGET = "missing-target"
    MALFORMED_QUALIFIER = "malformed-qualifier"
    UNRESOLVABLE_FRONTMATTER = "unresolvable-frontmatter"


# Chunk: docs/chunks/federation_global_validator - Candidate target for a misrouted reference
@dataclass(frozen=True)
class CandidateTarget:
    """A tree that does contain the artifact a failing reference names.

    Carries the member name *and* the path because they answer different
    questions: the member name is the qualifier to write, and its absence means
    the tree must be registered with `ve workspace add` before the reference can
    be qualified against it at all.
    """

    member: str | None
    path: str

    @property
    def qualifier(self) -> str | None:
        """The qualifier prefix to write, or None if the tree is unregistered."""
        return f"{self.member}::" if self.member else None

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {"member": self.member, "path": self.path, "qualifier": self.qualifier}


# Chunk: docs/chunks/federation_global_validator - One reported defect
@dataclass(frozen=True)
class ValidationDefect:
    """A single reference that does not resolve, and how to fix it."""

    fix_class: FixClass
    path: str  # workspace-root-relative POSIX path
    line: int | None  # 1-indexed, None when the defect has no single line
    reference: str  # the reference as written
    message: str
    candidates: tuple[CandidateTarget, ...] = ()
    member: str | None = None  # the member owning `path`, when there is one

    @property
    def location(self) -> str:
        """`path:line`, or just `path` when there is no line."""
        return self.path if self.line is None else f"{self.path}:{self.line}"

    @property
    def sort_key(self) -> tuple:
        """Deterministic ordering within a fix class."""
        return (self.path, self.line if self.line is not None else 0, self.reference)

    def to_dict(self) -> dict:
        """JSON-serializable form, as consumed by the validate-fix skill."""
        return {
            "fix_class": self.fix_class.value,
            "path": self.path,
            "line": self.line,
            "location": self.location,
            "reference": self.reference,
            "message": self.message,
            "member": self.member,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


# Chunk: docs/chunks/federation_global_validator - References that cannot be checked offline
@dataclass(frozen=True)
class UnverifiedReference:
    """A reference this validator deliberately does not resolve.

    Reported so a clean run is never mistaken for total coverage.
    """

    path: str
    line: int | None
    reference: str
    reason: str

    def to_dict(self) -> dict:
        """JSON-serializable form."""
        return {
            "path": self.path,
            "line": self.line,
            "reference": self.reference,
            "reason": self.reason,
        }


# Chunk: docs/chunks/federation_global_validator - Per-tree artifact index
@dataclass(frozen=True)
class TreeIndex:
    """The artifact ids present in one tree, by artifact type.

    Presence is directory existence, so an `external.yaml` pointer stub counts
    as a target — matching `integrity.py`, which already treats external chunks
    as valid backreference targets. A pointer is a real local address; where its
    *content* lives is the pointer's business.
    """

    root: Path
    artifacts: dict[ArtifactType, frozenset[str]]

    def has(self, artifact_type: ArtifactType, artifact_id: str) -> bool:
        """Return True if this tree holds an artifact of that type and id."""
        return artifact_id in self.artifacts.get(artifact_type, frozenset())


# Chunk: docs/chunks/federation_global_validator - Tree indexing
def index_tree(root: Path) -> TreeIndex:
    """Index every artifact directory in the tree rooted at `root`."""
    artifacts: dict[ArtifactType, frozenset[str]] = {}
    for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
        directory = root / "docs" / dir_name
        if not directory.is_dir():
            artifacts[artifact_type] = frozenset()
            continue
        artifacts[artifact_type] = frozenset(
            entry.name for entry in directory.iterdir() if entry.is_dir()
        )
    return TreeIndex(root=root, artifacts=artifacts)


# Chunk: docs/chunks/federation_global_validator - The whole-workspace report
@dataclass(frozen=True)
class ValidationReport:
    """Everything one validation run found.

    `ok` is the CI verdict: it is False when there is any defect *or* any
    manifest error, because a member whose tree is missing makes every qualified
    reference to it unresolvable. Unregistered governing trees are a note rather
    than a verdict — references inside them still resolve, so failing on them
    would report a defect where none exists.
    """

    workspace_root: Path
    defects: tuple[ValidationDefect, ...] = ()
    unverified: tuple[UnverifiedReference, ...] = ()
    manifest_errors: tuple[str, ...] = ()
    unregistered_trees: tuple[str, ...] = ()
    members: tuple[str, ...] = ()
    files_scanned: int = 0
    references_checked: int = 0
    artifacts_scanned: int = 0
    pointers_checked: int = 0
    # Chunk: docs/chunks/crossref_unchecked_anchors - Symbol-anchor coverage counts
    symbol_anchors_checked: int = 0
    symbol_anchors_unchecked: int = 0

    @property
    def ok(self) -> bool:
        """True when nothing gates: no defects and no manifest errors."""
        return not self.defects and not self.manifest_errors

    def by_fix_class(self) -> dict[FixClass, list[ValidationDefect]]:
        """Defects grouped by fix class, in `FixClass` declaration order.

        Only non-empty groups appear, so callers can iterate the result as the
        report's sections.
        """
        grouped: dict[FixClass, list[ValidationDefect]] = {}
        for fix_class in FixClass:
            matching = [d for d in self.defects if d.fix_class is fix_class]
            if matching:
                grouped[fix_class] = matching
        return grouped

    def to_dict(self) -> dict:
        """JSON-serializable form, as consumed by the validate-fix skill."""
        return {
            "workspace_root": str(self.workspace_root),
            "ok": self.ok,
            "members": list(self.members),
            "defects": [defect.to_dict() for defect in self.defects],
            "unverified": [ref.to_dict() for ref in self.unverified],
            "manifest_errors": list(self.manifest_errors),
            "unregistered_trees": list(self.unregistered_trees),
            "counts": {
                "files_scanned": self.files_scanned,
                "references_checked": self.references_checked,
                "artifacts_scanned": self.artifacts_scanned,
                "pointers_checked": self.pointers_checked,
                "symbol_anchors_checked": self.symbol_anchors_checked,
                "symbol_anchors_unchecked": self.symbol_anchors_unchecked,
                "defects": len(self.defects),
                "unverified": len(self.unverified),
            },
        }


# Chunk: docs/chunks/federation_global_validator - Deduplicated workspace file enumeration
def enumerate_workspace_files(workspace: Workspace) -> list[Path]:
    """Every source file in the workspace, each appearing once.

    The union of the workspace root and each member is taken on purpose. The
    root scan is what makes files in packages with *no docs tree at all*
    first-class — the case study's `backend-api-lib` is a direct consumer of
    cross-tree vocabulary, and skipping it would make its references permanently
    unfixable. The per-member scans guarantee full member coverage even when a
    member sits somewhere the root scan would not reach it.

    Deduplication on the resolved path is what keeps nested members from being
    scanned twice, so every file is read exactly once.
    """
    seen: set[Path] = set()
    roots = [workspace.root, *(workspace.member_path(m) for m in workspace.members)]
    for root in roots:
        if not root.is_dir():
            continue
        for path in enumerate_source_files(root):
            seen.add(path.resolve())
    return sorted(seen)


def _find_line(content: str, needle: str) -> int | None:
    """1-indexed line number of the first line containing `needle`."""
    for line_number, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            return line_number
    return None


# Chunk: docs/chunks/crossref_defect_line_anchor - Anchor findings on the owning field's entry
def _find_field_entry_line(content: str, field_name: str, needle: str) -> int | None:
    """1-indexed line of the first line containing `needle` *inside* one
    frontmatter field's block.

    A whole-document search cannot anchor a `code_references` defect: the same
    path routinely appears earlier in `code_paths`, so the first textual
    occurrence points a fix loop at the wrong entry. This scanner confines the
    search to the lines that belong to `field_name`'s YAML block — the lines
    after the top-level `field_name:` key that are indented or are list items
    (both the zero-indent `- ref:` style `ve` emits and the indented
    `  - ref:` style hand-written frontmatter uses), stopping at the next
    top-level key or the closing `---` fence.

    Frontmatter shapes this scanner cannot follow (e.g. flow-style lists) fall
    back to the whole-document first occurrence: a degraded anchor beats a
    lost one.
    """
    in_block = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not in_block:
            if line.startswith(f"{field_name}:"):
                in_block = True
            continue
        is_list_item = line.startswith("- ") or line.rstrip() == "-"
        if not (line[:1].isspace() or is_list_item):
            break  # next top-level key, or the closing --- fence
        if needle in line:
            return line_number
    return _find_line(content, needle)


# Chunk: docs/chunks/federation_global_validator - Conservative symbol existence check
# Chunk: docs/chunks/crossref_reexport_absence - Re-export-only mentions are absent
# Chunk: docs/chunks/crossref_unchecked_anchors - Non-identifier anchors are UNCHECKED, not passed
def _symbol_is_absent(
    content: str, symbol_path: str, *, is_python: bool = False
) -> tuple[str, str, str] | None:
    """Return (disposition, name, reason clause), or None if the symbol may exist.

    The disposition is ``"absent"`` (the anchor provably does not resolve — a
    gating defect) or ``"unchecked"`` (the anchor cannot be checked at all —
    reported, never gating). ``None`` means the check ran and the symbol may
    exist.

    "Cheaply checkable" read conservatively: only the last `::` component is
    considered, and absence is only claimed when the name appears *nowhere* in
    the file as a whole word — or, for Python files, appears *only* inside
    import/`__all__` re-export statements, where the name is bound but its
    definition lives in another file (the `# noqa: F401` field case). A name
    mentioned in a call, a string, or a dynamic definition keeps the validator
    quiet, and unparseable Python falls back to the whole-word scan. Absences
    are gating errors, so a false positive costs far more than a missed rename.

    A leaf that is not an identifier (dotted/bracketed anchors such as
    ``jobs.Checks.steps[Seed workspace .venv]`` for YAML workflows) is the
    same undecidable signal that makes ``name_is_reexport_only`` return
    ``None``: whole-word ``\\b`` semantics around dots and brackets are
    meaningless, so instead of silently passing, the anchor is reported
    ``"unchecked"`` — zero coverage, stated.

    The reason clause distinguishes the dispositions so the report can point
    at the right fix: a vanished name was probably renamed or removed; a
    re-export-only name needs the reference repointed at the defining file;
    an unchecked anchor is one the operator must verify by other means.
    """
    name = symbol_path.split("::")[-1].strip()
    if not name or not name.isidentifier():
        return (
            "unchecked",
            name,
            "is not a checkable identifier; only plain identifier names "
            "are symbol-checked",
        )
    if not re.search(rf"\b{re.escape(name)}\b", content):
        return (
            "absent",
            name,
            "appears nowhere in it; the symbol was probably renamed or removed",
        )
    if is_python and name_is_reexport_only(content, name):
        return (
            "absent",
            name,
            "appears only in import/__all__ re-export statements; "
            "the definition lives in another file",
        )
    return None


# Chunk: docs/chunks/federation_global_validator - Workspace-wide validation
class _Validator:
    """One validation run over one workspace.

    A class rather than a chain of functions because every check needs the same
    derived structures — the member indexes, the indexes of trees no member
    registers, the tree-root-to-member map, and the governing-tree cache — and
    threading four of those through every check would obscure the checks
    themselves.
    """

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.root = workspace.root.resolve()
        self.defects: list[ValidationDefect] = []
        self.unverified: list[UnverifiedReference] = []
        self.files_scanned = 0
        self.references_checked = 0
        self.artifacts_scanned = 0
        self.pointers_checked = 0
        # Chunk: docs/chunks/crossref_unchecked_anchors - Symbol-anchor coverage counters
        self.symbol_anchors_checked = 0
        self.symbol_anchors_unchecked = 0

        # Member indexes in manifest order, so candidate lists are deterministic
        # and read the way the operator wrote the manifest.
        self.member_indexes: dict[str, TreeIndex] = {}
        self.member_roots: dict[str, Path] = {}
        for member in workspace.members:
            path = workspace.member_path(member)
            self.member_roots[member.name] = path
            if path.is_dir() and is_member_tree(path):
                self.member_indexes[member.name] = index_tree(path)

        self.member_by_root: dict[Path, str] = {
            path.resolve(): name
            for name, path in self.member_roots.items()
            if path.is_dir()
        }
        # Governing trees that no member registers. Discovered up front with the
        # same bootstrap scan `ve workspace init --scan` uses, because a tree has
        # to be a *candidate* even when it holds no source files of its own —
        # otherwise a misrouted reference whose only possible target is an
        # unregistered tree would be reported as unresolvable, hiding the fix.
        self.extra_indexes: dict[Path, TreeIndex] = {}
        for rel_path in scan_for_trees(self.root):
            tree_root = (self.root if rel_path == "." else self.root / rel_path).resolve()
            if tree_root not in self.member_by_root:
                self.extra_indexes[tree_root] = index_tree(tree_root)

        self.governing_cache: dict[Path, Path | None] = {}

    # -- helpers ----------------------------------------------------------

    def relative(self, path: Path) -> str:
        """Workspace-root-relative POSIX path, for reporting."""
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def member_for(self, path: Path) -> str | None:
        """Name of the member owning `path` (longest prefix), if any."""
        member = self.workspace.find_member_for_path(path)
        return member.name if member else None

    def governing_tree(self, file_path: Path) -> Path | None:
        """The tree that governs bare references in `file_path`.

        Cached per directory: sibling files always share the answer, and the
        walk is the most repeated filesystem work in a large workspace.
        """
        directory = file_path.parent
        if directory not in self.governing_cache:
            self.governing_cache[directory] = find_governing_tree(directory)
        return self.governing_cache[directory]

    def index_for_tree(self, root: Path) -> TreeIndex:
        """Index for an arbitrary tree root, registered or not."""
        resolved = root.resolve()
        name = self.member_by_root.get(resolved)
        if name is not None and name in self.member_indexes:
            return self.member_indexes[name]
        if resolved not in self.extra_indexes:
            self.extra_indexes[resolved] = index_tree(resolved)
        return self.extra_indexes[resolved]

    def candidates_for(
        self,
        artifact_type: ArtifactType,
        artifact_id: str,
        exclude: tuple[Path, ...] = (),
    ) -> tuple[CandidateTarget, ...]:
        """Trees that do hold the artifact a failing reference names.

        Keyed on (type, id) rather than on a parsed comment so pointers get
        candidates too: knowing that a stale `tree:` pointer's target moved to
        another member is the difference between a mechanical retarget and an
        escalation.

        `exclude` takes several trees because more than one can be a *trivial*
        answer. For a pointer, both the tree it names and the tree it lives in
        must go: the pointing tree holds a directory with the artifact's name —
        the pointer itself — and offering that back as a candidate would tell
        the fix loop to retarget a pointer at itself.

        Members come first in manifest order, then trees no member registers,
        sorted by path — so a report is stable across runs and diffable between
        them.
        """
        excluded = {path.resolve() for path in exclude}
        found: list[CandidateTarget] = []

        for name, index in self.member_indexes.items():
            if index.root.resolve() in excluded:
                continue
            if index.has(artifact_type, artifact_id):
                found.append(CandidateTarget(member=name, path=self.relative(index.root)))

        for tree_root in sorted(self.extra_indexes):
            if tree_root in excluded or tree_root in self.member_by_root:
                continue
            if self.extra_indexes[tree_root].has(artifact_type, artifact_id):
                found.append(CandidateTarget(member=None, path=self.relative(tree_root)))

        return tuple(found)

    def candidates_for_reference(
        self, reference: ParsedBackreference, exclude: Path | None = None
    ) -> tuple[CandidateTarget, ...]:
        """Candidate targets for one parsed backreference.

        A backreference has at most one trivial answer — the tree it already
        failed in — so this takes a single optional path.
        """
        return self.candidates_for(
            reference.artifact_type,
            reference.artifact_id,
            exclude=() if exclude is None else (exclude,),
        )

    def report_defect(self, **kwargs) -> None:
        """Record one defect."""
        self.defects.append(ValidationDefect(**kwargs))

    # -- source file references -------------------------------------------

    def check_files(self) -> None:
        """Scan every source file in the workspace for defective references."""
        for file_path in enumerate_workspace_files(self.workspace):
            try:
                content = file_path.read_text()
            except (OSError, UnicodeDecodeError):
                continue
            self.files_scanned += 1
            references = scan_backreferences(content)
            if not references:
                continue
            # The governing tree is a property of the file, so it is resolved
            # once even when the file carries references into several trees --
            # the case-study file did exactly that.
            governing = self.governing_tree(file_path)
            if governing is not None:
                self.index_for_tree(governing)  # ensure it is a candidate source
            rel_path = self.relative(file_path)
            owner = self.member_for(file_path)
            for reference in references:
                self.references_checked += 1
                self.check_reference(reference, rel_path, governing, owner)

    def check_reference(
        self,
        reference: ParsedBackreference,
        rel_path: str,
        governing: Path | None,
        owner: str | None,
    ) -> None:
        """Classify one parsed backreference."""
        if reference.qualifier_kind is QualifierKind.MALFORMED:
            self.report_defect(
                fix_class=FixClass.MALFORMED_QUALIFIER,
                path=rel_path,
                line=reference.line_number,
                reference=reference.reference,
                message=(
                    f"{reference.malformed_reason}. Normalize it to "
                    f"'<member>::{reference.artifact_path}'"
                ),
                candidates=self.candidates_for_reference(reference),
                member=owner,
            )
            return

        if reference.qualifier_kind is QualifierKind.REPO:
            self.unverified.append(
                UnverifiedReference(
                    path=rel_path,
                    line=reference.line_number,
                    reference=reference.reference,
                    reason=(
                        f"target lives in repository '{reference.qualifier}'; "
                        f"cross-repository targets are not resolved offline"
                    ),
                )
            )
            return

        if reference.qualifier_kind is QualifierKind.MEMBER:
            self.check_member_reference(reference, rel_path, owner)
            return

        self.check_bare_reference(reference, rel_path, governing, owner)

    def check_member_reference(
        self, reference: ParsedBackreference, rel_path: str, owner: str | None
    ) -> None:
        """Classify a `<member>::docs/...` reference."""
        name = reference.qualifier or ""
        known = ", ".join(self.workspace.manifest.names()) or "(none)"

        if name not in self.member_roots:
            self.report_defect(
                fix_class=FixClass.UNKNOWN_QUALIFIER,
                path=rel_path,
                line=reference.line_number,
                reference=reference.reference,
                message=(
                    f"'{name}' is not a workspace member. Registered members: "
                    f"{known}. Register the tree with `ve workspace add {name} "
                    f"<path>`, or correct the qualifier"
                ),
                candidates=self.candidates_for_reference(reference),
                member=owner,
            )
            return

        index = self.member_indexes.get(name)
        if index is None:
            self.report_defect(
                fix_class=FixClass.UNKNOWN_QUALIFIER,
                path=rel_path,
                line=reference.line_number,
                reference=reference.reference,
                message=(
                    f"member '{name}' is registered at "
                    f"'{self.relative(self.member_roots[name])}' but no VE tree "
                    f"exists there, so the qualifier resolves to nothing"
                ),
                candidates=self.candidates_for_reference(reference),
                member=owner,
            )
            return

        if not index.has(reference.artifact_type, reference.artifact_id):
            self.report_defect(
                fix_class=FixClass.MISSING_TARGET,
                path=rel_path,
                line=reference.line_number,
                reference=reference.reference,
                message=(
                    f"tree '{name}' has no {reference.artifact_type.value} "
                    f"'{reference.artifact_id}' (looked for "
                    f"{self.relative(index.root)}/{reference.artifact_path})"
                ),
                candidates=self.candidates_for_reference(reference, exclude=index.root),
                member=owner,
            )

    def check_bare_reference(
        self,
        reference: ParsedBackreference,
        rel_path: str,
        governing: Path | None,
        owner: str | None,
    ) -> None:
        """Classify a bare reference against the file's governing tree."""
        if governing is not None:
            if self.index_for_tree(governing).has(
                reference.artifact_type, reference.artifact_id
            ):
                return
            context = (
                f"does not resolve in '{self.relative(governing)}' (the nearest "
                f"enclosing tree of this file)"
            )
        else:
            context = (
                "has no governing tree (nothing at or above this file inside the "
                "workspace holds a docs/trunk/), so a bare reference here addresses "
                "no tree"
            )

        candidates = self.candidates_for_reference(reference, exclude=governing)
        if candidates:
            options = ", ".join(
                candidate.qualifier + reference.artifact_path
                if candidate.qualifier
                else f"{candidate.path} (unregistered: `ve workspace add` it first)"
                for candidate in candidates
            )
            self.report_defect(
                fix_class=FixClass.MISROUTED_BARE,
                path=rel_path,
                line=reference.line_number,
                reference=reference.reference,
                message=f"{context}. It resolves elsewhere — qualify it as: {options}",
                candidates=candidates,
                member=owner,
            )
            return

        self.report_defect(
            fix_class=FixClass.UNRESOLVABLE_BARE,
            path=rel_path,
            line=reference.line_number,
            reference=reference.reference,
            message=(
                f"{context}. No tree in this workspace holds "
                f"{reference.artifact_type.value} '{reference.artifact_id}' either, so "
                f"it may never have resolved anywhere — decide what it meant rather "
                f"than deleting it"
            ),
            member=owner,
        )

    # -- artifacts: pointers and frontmatter -------------------------------

    def check_artifacts(self) -> None:
        """Validate pointers and frontmatter in every registered member tree.

        Manifest-scoped on purpose: source files are scanned workspace-wide
        because a bad reference can live in any file, but the manifest is what
        declares which *trees* this workspace governs.
        """
        for name, index in self.member_indexes.items():
            for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
                directory = index.root / "docs" / dir_name
                if not directory.is_dir():
                    continue
                for artifact_dir in sorted(
                    entry for entry in directory.iterdir() if entry.is_dir()
                ):
                    self.check_artifact(name, artifact_type, artifact_dir)

    def check_artifact(
        self, member: str, artifact_type: ArtifactType, artifact_dir: Path
    ) -> None:
        """Validate one artifact directory: a pointer, or a local document."""
        if is_external_artifact(artifact_dir, artifact_type):
            self.check_pointer(member, artifact_type, artifact_dir)
            return
        self.artifacts_scanned += 1
        self.check_code_references(member, artifact_type, artifact_dir)

    def check_pointer(
        self, member: str, artifact_type: ArtifactType, artifact_dir: Path
    ) -> None:
        """Validate one `external.yaml` pointer.

        `resolve_peer_pointer` is the authority for whether a peer pointer
        resolves; only the manifest lookup is repeated here, because that is the
        single place where two fix classes genuinely diverge (an unknown tree
        needs registering, a missing artifact needs a target).
        """
        self.pointers_checked += 1
        pointer_file = artifact_dir / "external.yaml"
        rel_path = self.relative(pointer_file)
        content = pointer_file.read_text() if pointer_file.is_file() else ""
        pointing_root = self.member_indexes[member].root

        try:
            ref = load_external_ref(artifact_dir)
        except Exception as exc:
            self.report_defect(
                fix_class=FixClass.MISSING_TARGET,
                path=rel_path,
                line=None,
                reference=self.relative(artifact_dir),
                message=f"pointer cannot be read, so it resolves to nothing: {exc}",
                member=member,
            )
            return

        target = f"docs/{ARTIFACT_DIR_NAME[artifact_type]}/{ref.artifact_id}"

        if not ref.is_peer:
            self.unverified.append(
                UnverifiedReference(
                    path=rel_path,
                    line=_find_line(content, "repo:"),
                    reference=f"{ref.target_display} {target}",
                    reason=(
                        f"pointer targets repository '{ref.repo}'; cross-repository "
                        f"targets are not resolved offline"
                    ),
                )
            )
            return

        reference = f"tree:{ref.tree} {target}"
        if ref.tree not in self.member_roots:
            known = ", ".join(self.workspace.manifest.names()) or "(none)"
            self.report_defect(
                fix_class=FixClass.UNKNOWN_QUALIFIER,
                path=rel_path,
                line=_find_line(content, "tree:"),
                reference=reference,
                message=(
                    f"pointer targets tree '{ref.tree}', which is not a workspace "
                    f"member. Registered members: {known}. Register it with "
                    f"`ve workspace add {ref.tree} <path>`"
                ),
                candidates=self.candidates_for(
                    artifact_type, ref.artifact_id, exclude=(pointing_root,)
                ),
                member=member,
            )
            return

        try:
            resolve_peer_pointer(artifact_dir, ref, artifact_type)
        except TaskChunkError as exc:
            self.report_defect(
                fix_class=FixClass.MISSING_TARGET,
                path=rel_path,
                line=_find_line(content, "artifact_id:"),
                reference=reference,
                message=str(exc),
                # A stale pointer whose target simply moved is a mechanical
                # retarget; without candidates the skill could only escalate.
                candidates=self.candidates_for(
                    artifact_type,
                    ref.artifact_id,
                    exclude=(self.member_roots[ref.tree], pointing_root),
                ),
                member=member,
            )

    # Chunk: docs/chunks/crossref_workspace_parity - Directory targets, code_paths, status gating
    # Chunk: docs/chunks/crossref_glob_refs - Glob file parts error only on empty expansion
    # Chunk: docs/chunks/federation_member_refs - Member-qualified file parts resolve and verify
    def check_code_references(
        self, member: str, artifact_type: ArtifactType, artifact_dir: Path
    ) -> None:
        """Validate `code_paths` and `code_references` in one artifact's frontmatter.

        Path-existence semantics deliberately mirror the single-tree check
        (``integrity.IntegrityValidator._validate_chunk_file_paths``) so the
        two validators cannot teach contradictory lessons:

        - ``Path.exists()``, not ``is_file()`` — "this chunk governs that
          package directory" is a legitimate reference.
        - Both declared-path fields are checked; ``code_paths`` must not rot
          invisibly in workspace mode.
        - File parts containing glob magic are patterns: they expand against
          the member root and are a defect only when the expansion is empty,
          so "this applies uniformly across N packages" does not require
          enumerating N paths. Symbol anchors on patterns are unverified,
          not silently passed.
        - Chunks are checked only in ACTIVE/COMPOSITE status. FUTURE and
          IMPLEMENTING chunks legitimately list files they expect to create,
          and HISTORICAL/SUPERSEDED chunks keep archaeological references to
          code that may be gone.
        - Qualified file parts follow federation addressing: ``member::path``
          resolves through the workspace manifest against the named member's
          root and is verified like a local path; ``org/repo::path`` is
          unverified (offline); a malformed qualifier is a defect, not a fake
          cross-repository unverified.

        Symbol-anchor checking is a workspace-mode extra on top of that shared
        contract, and applies only to file targets — a symbol cannot be looked
        up in a directory.
        """
        model = _FRONTMATTER_MODELS.get(artifact_type)
        if model is None:
            return
        main_file = artifact_dir / ARTIFACT_MAIN_FILE[artifact_type]
        frontmatter = parse_frontmatter(main_file, model)
        if frontmatter is None:
            return
        # Subsystems carry no code_paths field; chunks carry both.
        code_paths: list[str] = getattr(frontmatter, "code_paths", []) or []
        if not frontmatter.code_references and not code_paths:
            return
        if artifact_type is ArtifactType.CHUNK and frontmatter.status not in (
            ChunkStatus.ACTIVE,
            ChunkStatus.COMPOSITE,
        ):
            return

        content = main_file.read_text()
        rel_path = self.relative(main_file)
        member_root = self.member_indexes[member].root

        def resolve_path(reference: str, file_part: str, field_name: str) -> list[Path]:
            """Shared path resolution for both declared-path fields.

            Returns the existing target paths (one element for a concrete
            path, every match for a glob pattern), or an empty list after
            recording the unverified/defect disposition — so both fields get
            identical qualified-reference routing and existence semantics.

            # Chunk: docs/chunks/federation_member_refs - Member-qualified refs are verified
            A qualified file part is routed by the shared qualifier shape
            rule: `member::path` names a sibling tree of this same working
            copy, so it resolves through the workspace manifest and IS
            verified — existence, glob expansion, and symbol anchors all run
            against the named member's root. Only `org/repo::` targets stay
            unverified, because resolving another repository needs network
            access. Resolution gates on manifest registration plus the
            filesystem, matching `resolve_peer_pointer`; it does not require
            the member to be a governing tree, because a file target does
            not live under `docs/`.
            """
            target_root = member_root
            tree_name = member
            path_part = file_part
            if "::" in file_part:
                qualifier, _, remainder = file_part.partition("::")
                if not qualifier or "::" in remainder:
                    kind = "invalid"
                    reason: str | None = (
                        "qualifier cannot be empty before '::'"
                        if not qualifier
                        else f"'{file_part}' cannot contain multiple '::' delimiters"
                    )
                else:
                    kind, reason = classify_qualifier_shape(qualifier)
                if kind == "repo":
                    self.unverified.append(
                        UnverifiedReference(
                            path=rel_path,
                            # Chunk: docs/chunks/crossref_defect_line_anchor - Anchor on the owning field's entry
                            line=_find_field_entry_line(content, field_name, reference),
                            reference=reference,
                            reason=(
                                "code reference is qualified with another repository; "
                                "cross-repository targets are not resolved offline"
                            ),
                        )
                    )
                    return []
                if kind == "invalid":
                    self.report_defect(
                        fix_class=FixClass.MALFORMED_QUALIFIER,
                        path=rel_path,
                        line=_find_field_entry_line(content, field_name, reference),
                        reference=reference,
                        message=(
                            f"{field_name} entry has a malformed qualifier: "
                            f"{reason}. Qualify it as '<member>::<path>' or "
                            f"'<org>/<repo>::<path>'"
                        ),
                        member=member,
                    )
                    return []
                if qualifier not in self.member_roots:
                    known = ", ".join(self.workspace.manifest.names()) or "(none)"
                    self.report_defect(
                        fix_class=FixClass.UNKNOWN_QUALIFIER,
                        path=rel_path,
                        line=_find_field_entry_line(content, field_name, reference),
                        reference=reference,
                        message=(
                            f"'{qualifier}' is not a workspace member. Registered "
                            f"members: {known}. Register the tree with "
                            f"`ve workspace add {qualifier} <path>`, or correct "
                            f"the qualifier"
                        ),
                        member=member,
                    )
                    return []
                target_root = self.member_roots[qualifier]
                tree_name = qualifier
                path_part = remainder
            if is_glob_pattern(path_part):
                matches = expand_glob(target_root, path_part)
                if not matches:
                    self.report_defect(
                        fix_class=FixClass.UNRESOLVABLE_FRONTMATTER,
                        path=rel_path,
                        # Chunk: docs/chunks/crossref_defect_line_anchor - Anchor on the owning field's entry
                        line=_find_field_entry_line(content, field_name, reference),
                        reference=reference,
                        message=(
                            f"{field_name} glob pattern '{path_part}' matches "
                            f"nothing in tree '{tree_name}'"
                        ),
                        member=member,
                    )
                return matches
            target = target_root / path_part
            if not target.exists():
                self.report_defect(
                    fix_class=FixClass.UNRESOLVABLE_FRONTMATTER,
                    path=rel_path,
                    line=_find_field_entry_line(content, field_name, reference),
                    reference=reference,
                    message=(
                        f"{field_name} entry points at '{path_part}', which does "
                        f"not exist in tree '{tree_name}'"
                    ),
                    member=member,
                )
                return []
            return [target]

        for path in code_paths:
            resolve_path(path, path, "code_paths")

        # Chunk: docs/chunks/crossref_unchecked_anchors - Every uncheckable anchor is stated and counted
        for symbolic in frontmatter.code_references:
            ref = symbolic.ref
            file_part, _, symbol_path = ref.partition("#")
            targets = resolve_path(ref, file_part, "code_references")
            if not symbol_path:
                continue
            if "::" in file_part:
                qualifier = file_part.partition("::")[0]
                kind, _ = classify_qualifier_shape(qualifier) if qualifier else ("invalid", None)
                if kind != "member":
                    # org/repo refs are recorded unverified (cross-repo);
                    # their symbol anchor is part of what was not checked.
                    self.symbol_anchors_unchecked += 1
                    continue
                # member:: targets resolve against the named member's root and
                # are verified like local files — fall through to the check.
            if not targets:
                # The file part is already a gating defect (missing file or
                # empty glob); the anchor is neither checked nor counted —
                # the coverage count describes the checker's blind spots,
                # not its queue.
                continue
            if is_glob_pattern(file_part):
                # A symbol cannot be attributed to one file of a pattern's
                # expansion; report it as unverified rather than silently
                # passing or spuriously failing.
                self.symbol_anchors_unchecked += 1
                self.unverified.append(
                    UnverifiedReference(
                        path=rel_path,
                        line=_find_line(content, ref),
                        reference=ref,
                        reason=(
                            "symbol anchor on a glob pattern; symbols are not "
                            "checked across glob expansions"
                        ),
                    )
                )
                continue
            target = targets[0]
            if not target.is_file():
                self.symbol_anchors_unchecked += 1
                self.unverified.append(
                    UnverifiedReference(
                        path=rel_path,
                        line=_find_field_entry_line(content, "code_references", ref),
                        reference=ref,
                        reason=(
                            "symbol anchor on a directory; a symbol cannot "
                            "be looked up in a directory"
                        ),
                    )
                )
                continue
            try:
                target_content = target.read_text()
            except (OSError, UnicodeDecodeError):
                self.symbol_anchors_unchecked += 1
                self.unverified.append(
                    UnverifiedReference(
                        path=rel_path,
                        line=_find_field_entry_line(content, "code_references", ref),
                        reference=ref,
                        reason=(
                            f"'{file_part}' could not be read; the symbol "
                            "anchor is not checked"
                        ),
                    )
                )
                continue
            result = _symbol_is_absent(
                target_content, symbol_path, is_python=target.suffix == ".py"
            )
            if result is not None and result[0] == "unchecked":
                _, _, reason = result
                self.symbol_anchors_unchecked += 1
                self.unverified.append(
                    UnverifiedReference(
                        path=rel_path,
                        line=_find_field_entry_line(content, "code_references", ref),
                        reference=ref,
                        reason=f"symbol anchor '{symbol_path}' {reason}",
                    )
                )
                continue
            self.symbol_anchors_checked += 1
            if result is not None:
                _, missing, reason = result
                self.report_defect(
                    fix_class=FixClass.UNRESOLVABLE_FRONTMATTER,
                    path=rel_path,
                    line=_find_field_entry_line(content, "code_references", ref),
                    reference=ref,
                    message=(
                        f"'{file_part}' exists but the name '{missing}' {reason}"
                    ),
                    member=member,
                )

    # -- assembly ----------------------------------------------------------

    def unregistered_governing_trees(self) -> tuple[str, ...]:
        """Governing trees discovered during the walk that no member registers."""
        return tuple(
            sorted(
                self.relative(root)
                for root in self.extra_indexes
                if root not in self.member_by_root
            )
        )

    def run(self) -> ValidationReport:
        """Validate the workspace and assemble a deterministic report."""
        self.check_files()
        self.check_artifacts()

        # Deduplicate identical findings, then group by fix class and sort
        # within each group, so two runs of the same workspace are byte-stable.
        unique: dict[tuple, ValidationDefect] = {}
        for defect in self.defects:
            unique.setdefault(
                (defect.fix_class, defect.path, defect.line, defect.reference), defect
            )
        ordered: list[ValidationDefect] = []
        for fix_class in FixClass:
            ordered.extend(
                sorted(
                    (d for d in unique.values() if d.fix_class is fix_class),
                    key=lambda d: d.sort_key,
                )
            )

        return ValidationReport(
            workspace_root=self.root,
            defects=tuple(ordered),
            unverified=tuple(
                sorted(self.unverified, key=lambda r: (r.path, r.line or 0, r.reference))
            ),
            manifest_errors=tuple(validate_member_paths(self.workspace)),
            unregistered_trees=self.unregistered_governing_trees(),
            members=tuple(self.workspace.manifest.names()),
            files_scanned=self.files_scanned,
            references_checked=self.references_checked,
            artifacts_scanned=self.artifacts_scanned,
            pointers_checked=self.pointers_checked,
            symbol_anchors_checked=self.symbol_anchors_checked,
            symbol_anchors_unchecked=self.symbol_anchors_unchecked,
        )


# Chunk: docs/chunks/federation_global_validator - Validation entry points
def validate_workspace(workspace: Workspace) -> ValidationReport:
    """Validate every reference in `workspace` and report all defects.

    Args:
        workspace: The loaded workspace to validate.

    Returns:
        A deterministic :class:`ValidationReport`. Nothing raises for a
        defective workspace — defects are the product.
    """
    return _Validator(workspace).run()


def validate_workspace_at(start: Path) -> ValidationReport:
    """Find the workspace at or above `start` and validate it.

    Args:
        start: Any directory inside the workspace.

    Returns:
        A :class:`ValidationReport`.

    Raises:
        WorkspaceNotFoundError: If no manifest exists at or above `start`.
        WorkspaceManifestError: If the manifest is unusable.
    """
    return validate_workspace(load_workspace(start))


__all__ = [
    "CandidateTarget",
    "FixClass",
    "TreeIndex",
    "UnverifiedReference",
    "ValidationDefect",
    "ValidationReport",
    "enumerate_workspace_files",
    "index_tree",
    "validate_workspace",
    "validate_workspace_at",
]
