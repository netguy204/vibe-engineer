"""Scaffolding a package as a workspace member instead of a new namespace.

# Subsystem: docs/subsystems/cross_repo_operations - Intra-workspace addressing flavor
# Chunk: docs/chunks/federation_template_pointers - Pointer-only package scaffolding

A package scaffold is where a monorepo's documentation namespaces come from. The
case-study repository grew ~29 VE trees because its package template shipped a
literal `docs/trunk` + `docs/chunks` inside the generated package: every scaffolded
package minted another root-relative namespace *by construction*, which is why any
one-time cleanup regressed.

This module is the alternative a template can call. Its default output is a
**pointer-only tree**: `external.yaml` interest edges naming the artifacts the new
package consumes, plus registration in `.ve-workspace.yaml` — no `docs/trunk/`, and
no artifact directory that holds no pointer. Such a package is addressable
(`<member>::docs/...`) without becoming an addressing root, because membership
(`workspace.is_ve_tree`, permissive) and governance (`project.TREE_MARKERS`, strictly
`docs/trunk/`) are deliberately different predicates.

A full tree is the explicit opt-in (`full_tree=True`), for a package that will own
intent of its own. Both flavors register the package when a manifest is present and
skip registration cleanly when there is none, so single-repo use is unchanged.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from external_refs import ARTIFACT_DIR_NAME, create_peer_yaml, normalize_artifact_path
from models import ArtifactType
from models.workspace import validate_member_name
from project import Project, find_enclosing_tree
from template_system import render_template
from workspace import (
    WORKSPACE_MANIFEST_NAME,
    WorkspaceError,
    WorkspaceManifestError,
    WorkspaceNotFoundError,
    add_member,
    load_workspace,
    relativize_to_workspace,
    save_workspace,
    suggest_member_names,
)


# Chunk: docs/chunks/federation_template_pointers - Interest spec grammar
# `<member>::docs/<type>/<name>[: why]`. The `::` half is the qualified-reference
# grammar, so one string is copy-pasteable between a backreference comment, a
# scaffold flag, and a package template's variables.
INTEREST_SPEC_PATTERN = re.compile(
    r"^\s*(?P<member>[^\s:/]+)::(?P<artifact>[^\s:]+)"
    r"(?:\s*:\s*(?P<why>\S.*?))?\s*$"
)


class InterestSpecError(ValueError):
    """An interest spec does not match the grammar."""


class PackageScaffoldError(Exception):
    """A scaffold was executed with a request that does not validate."""


@dataclass(frozen=True)
class InterestSpec:
    """An interest edge as the operator wrote it, before resolution."""

    member: str
    artifact: str
    why: str | None


@dataclass(frozen=True)
class InterestEdge:
    """A resolved interest edge: which pointer to write, and at what."""

    member: str
    artifact_type: ArtifactType
    artifact_id: str
    why: str | None

    @property
    def local_path(self) -> str:
        """Where the pointer lands inside the scaffolded package."""
        return f"docs/{ARTIFACT_DIR_NAME[self.artifact_type]}/{self.artifact_id}"

    @property
    def qualified_ref(self) -> str:
        """The edge as a qualified reference an agent can follow."""
        return f"{self.member}::{self.local_path}"


@dataclass
class PackageScaffoldResult:
    """What a scaffold produced, in the terms the CLI reports."""

    path: Path
    name: str
    full_tree: bool
    created: list[str] = field(default_factory=list)
    interests: list[InterestEdge] = field(default_factory=list)
    registered: bool = False
    workspace_root: Path | None = None
    governing_tree: Path | None = None
    warnings: list[str] = field(default_factory=list)


# Chunk: docs/chunks/federation_template_pointers - Interest spec parsing
def parse_interest(spec: str) -> InterestSpec:
    """Parse an interest spec into its member, artifact, and `why:` note.

    Args:
        spec: `<member>::docs/<type>/<name>[: why]`. The artifact may also be
            given as `<type>/<name>` or, when it already exists in the member's
            tree, just `<name>`.

    Returns:
        The parsed spec (not yet resolved against a workspace).

    Raises:
        InterestSpecError: If the string does not match the grammar.
    """
    match = INTEREST_SPEC_PATTERN.match(spec)
    if match is not None:
        return InterestSpec(
            member=match.group("member"),
            artifact=match.group("artifact"),
            why=match.group("why"),
        )

    if "::" not in spec:
        raise InterestSpecError(
            f"interest '{spec}' is not qualified: an interest edge must name the "
            f"tree that owns the artifact, as '<member>::docs/<type>/<name>: why'. "
            f"A bare path would name an artifact in the new package, which owns "
            f"nothing yet."
        )

    member = spec.split("::", 1)[0].strip()
    if "/" in member:
        raise InterestSpecError(
            f"'{member}::' names another repository, not a workspace member. A peer "
            f"interest edge points at a tree in this same working copy; for an "
            f"artifact in another repository use `ve external create` instead."
        )

    raise InterestSpecError(
        f"interest '{spec}' does not parse. Expected "
        f"'<member>::docs/<type>/<name>: why this package depends on it'."
    )


def _relative(target: Path, start: Path) -> str:
    """Path to `target` as seen from `start`, for prose in a rendered file."""
    return Path(os.path.relpath(target, start=start)).as_posix()


# Chunk: docs/chunks/federation_template_pointers - Package scaffold
class PackageScaffold:
    """Scaffold a package as a workspace member.

    Validation is total before anything is written: a rejected scaffold leaves no
    half-created package behind, which matters because the failure modes it catches
    (an unknown member, a pointer at an artifact that never existed) are precisely
    the ones that are invisible afterwards.
    """

    def __init__(
        self,
        path: Path,
        name: str | None = None,
        interests: list[str] | tuple[str, ...] = (),
        full_tree: bool = False,
    ):
        """Create a scaffold request.

        Args:
            path: Directory of the new package (created if absent).
            name: Workspace member name; defaults to the directory's name.
            interests: Interest specs (see :func:`parse_interest`).
            full_tree: Create a full VE tree instead of a pointer-only one.
        """
        self.path = Path(path)
        self.requested_name = name
        self.interest_specs = list(interests)
        self.full_tree = full_tree

        self._workspace = None
        self._edges: list[InterestEdge] = []
        self._member_name: str | None = None
        self._relative_path: str | None = None
        self._warnings: list[str] = []
        self._validated = False

    # Chunk: docs/chunks/federation_template_pointers - Total validation before creation
    def validate(self) -> list[str]:
        """Check the request against the filesystem and the workspace manifest.

        Returns:
            One message per defect, empty if the request is executable.
        """
        errors: list[str] = []
        self._warnings = []
        self._edges = []
        self._workspace = None
        self._validated = False

        if self.path.exists() and not self.path.is_dir():
            return [f"'{self.path}' exists and is not a directory"]

        if (self.path / "docs" / "trunk").is_dir():
            return [
                f"'{self.path}' already holds a full VE tree (docs/trunk/). Record "
                f"further interest in it with `ve external point <member> "
                f"<artifact> --why ...`."
            ]

        if not self.interest_specs and not self.full_tree:
            return [
                "a pointer-only package needs at least one --interest "
                "'<member>::docs/<type>/<name>: why', naming intent it consumes. A "
                "package that consumes no documented intent needs no docs tree at "
                "all — an empty one is a new addressing root and nothing else. Pass "
                "--full-tree only if this package will own intent of its own."
            ]

        specs: list[InterestSpec] = []
        for raw in self.interest_specs:
            try:
                specs.append(parse_interest(raw))
            except InterestSpecError as exc:
                errors.append(str(exc))
        if errors:
            return errors

        try:
            self._workspace = load_workspace(self.path)
        except WorkspaceNotFoundError:
            self._workspace = None
        except WorkspaceManifestError as exc:
            return [str(exc)]

        if self._workspace is None:
            if specs:
                return [
                    f"interest edges name workspace members, and no "
                    f"{WORKSPACE_MANIFEST_NAME} was found at or above '{self.path}'. "
                    f"Run `ve workspace init` at the root of the repository holding "
                    f"your VE trees, then scaffold again."
                ]
            # A full tree outside a workspace is ordinary single-repo use.
            self._member_name = self.requested_name or self.path.name
            self._validated = True
            return []

        errors.extend(self._validate_membership())
        errors.extend(self._resolve_edges(specs))

        self._validated = not errors
        return errors

    def _validate_membership(self) -> list[str]:
        """Resolve the member name and path this package will be registered under."""
        errors: list[str] = []
        try:
            self._relative_path = relativize_to_workspace(
                self._workspace.root, str(self.path.absolute())
            )
        except WorkspaceManifestError as exc:
            return [str(exc)]

        already = next(
            (
                member
                for member in self._workspace.members
                if member.path == self._relative_path
            ),
            None,
        )
        if already is not None:
            return [
                f"'{self._relative_path}' is already registered as member "
                f"'{already.name}'. Scaffolding creates a member; to record another "
                f"dependency in an existing one run `ve external point <member> "
                f"<artifact> --why ...` from it."
            ]

        suggested = suggest_member_names([self._relative_path], root=self._workspace.root)
        self._member_name = self.requested_name or suggested[0][0]

        try:
            validate_member_name(self._member_name)
        except ValueError as exc:
            errors.append(str(exc))
            return errors

        existing = self._workspace.manifest.get(self._member_name)
        if existing is not None:
            errors.append(
                f"member '{self._member_name}' is already registered, pointing at "
                f"'{existing.path}'. Member names are what '<member>::' references "
                f"resolve against, so pass --name to give this package another one."
            )
        return errors

    # Chunk: docs/chunks/federation_template_pointers - Interest targets must already resolve
    def _resolve_edges(self, specs: list[InterestSpec]) -> list[str]:
        """Resolve each spec against the workspace, refusing unresolvable targets."""
        errors: list[str] = []

        for spec in specs:
            try:
                member_root = self._workspace.resolve(spec.member)
            except KeyError as exc:
                errors.append(exc.args[0])
                continue

            if member_root.absolute() == self.path.absolute():
                errors.append(
                    f"'{spec.member}' is this package, so the pointer would address "
                    f"the tree that already owns the artifact. Reference it with a "
                    f"bare path instead."
                )
                continue

            try:
                artifact_type, artifact_id = normalize_artifact_path(
                    spec.artifact, search_path=member_root
                )
            except ValueError as exc:
                errors.append(str(exc))
                continue

            target = member_root / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
            if not target.is_dir():
                errors.append(
                    f"{artifact_type.value} '{artifact_id}' does not exist in tree "
                    f"'{spec.member}' (looked for {target}). A pointer at an artifact "
                    f"that was never there can never resolve, and it leaves no "
                    f"deletion event behind for an audit to find — create the "
                    f"artifact first."
                )
                continue

            edge = InterestEdge(
                member=spec.member,
                artifact_type=artifact_type,
                artifact_id=artifact_id,
                why=spec.why,
            )
            if any(existing.local_path == edge.local_path for existing in self._edges):
                errors.append(
                    f"two interest edges would both be written to {edge.local_path}; "
                    f"point at each artifact once, then use `ve external point "
                    f"--name` if you need a second local name."
                )
                continue

            self._edges.append(edge)
            if edge.why is None:
                self._warnings.append(
                    f"interest edge {edge.qualified_ref} carries no 'why:' note, so a "
                    f"reverse interest query cannot say what this package depends on"
                )

        return errors

    # Chunk: docs/chunks/federation_template_pointers - Create pointers, then register
    def execute(self) -> PackageScaffoldResult:
        """Create the package and register it as a workspace member.

        Returns:
            The scaffold result, including warnings worth reporting.

        Raises:
            PackageScaffoldError: If the request does not validate.
        """
        if not self._validated:
            errors = self.validate()
            if errors:
                raise PackageScaffoldError("; ".join(errors))

        result = PackageScaffoldResult(
            path=self.path,
            name=self._member_name,
            full_tree=self.full_tree,
            workspace_root=self._workspace.root if self._workspace else None,
            governing_tree=find_enclosing_tree(self.path.parent),
            warnings=list(self._warnings),
        )

        self.path.mkdir(parents=True, exist_ok=True)

        if self.full_tree:
            # The advisory `ve init` prints about minting an addressing root is
            # exactly what --full-tree opted into, and this scaffold registers the
            # tree itself, so it would be noise here.
            init_result = Project(self.path).init(advise_on_workspace=False)
            result.created.extend(init_result.created)
            result.warnings.extend(init_result.warnings)

        for edge in self._edges:
            pointer = create_peer_yaml(
                project_path=self.path,
                short_name=edge.artifact_id,
                member=edge.member,
                external_artifact_id=edge.artifact_id,
                artifact_type=edge.artifact_type,
                why=edge.why,
            )
            result.created.append(pointer.relative_to(self.path).as_posix())
        result.interests = list(self._edges)

        if not self.full_tree:
            result.created.extend(self._render_agents_md(result))

        self._register(result)
        return result

    # Chunk: docs/chunks/federation_template_pointers - Registration via the library API
    def _register(self, result: PackageScaffoldResult) -> None:
        """Register the finished package in the workspace manifest.

        Reloads the manifest so registration validates against the tree that now
        exists on disk (`add_member` checks the filesystem facts) and so a manifest
        edited since validation is not clobbered.
        """
        if self._workspace is None:
            return

        try:
            workspace = load_workspace(self.path)
            save_workspace(add_member(workspace, result.name, self._relative_path))
            result.registered = True
        except WorkspaceError as exc:
            result.warnings.append(
                f"could not register member '{result.name}': {exc}. Register it with "
                f"`ve workspace add {result.name} {self._relative_path}`."
            )

    # Chunk: docs/chunks/agentskills_migration - AGENTS.md canonical, CLAUDE.md symlink
    def _render_agents_md(self, result: PackageScaffoldResult) -> list[str]:
        """Render agent instructions explaining where this package's docs live."""
        governing = result.governing_tree
        members = [member.name for member in self._workspace.members] if self._workspace else []
        example = (
            result.interests[0].qualified_ref
            if result.interests
            else f"{members[0] if members else '<member>'}::docs/subsystems/<name>"
        )

        rendered = render_template(
            "package",
            "AGENTS.md.jinja2",
            package_name=result.name,
            governing_tree_rel=_relative(governing, self.path) if governing else None,
            workspace_root_rel=(
                _relative(result.workspace_root, self.path) if result.workspace_root else None
            ),
            interests=[
                {
                    "qualified_ref": edge.qualified_ref,
                    "local_path": edge.local_path,
                    "member": edge.member,
                    "artifact_id": edge.artifact_id,
                    "why": edge.why,
                }
                for edge in result.interests
            ],
            example_ref=example,
            members=members,
        )

        agents_file = self.path / "AGENTS.md"
        agents_file.write_text(rendered)
        created = ["AGENTS.md"]

        claude_file = self.path / "CLAUDE.md"
        if not claude_file.exists() and not claude_file.is_symlink():
            claude_file.symlink_to("AGENTS.md")
            created.append("CLAUDE.md")

        return created


__all__ = [
    "INTEREST_SPEC_PATTERN",
    "InterestEdge",
    "InterestSpec",
    "InterestSpecError",
    "PackageScaffold",
    "PackageScaffoldError",
    "PackageScaffoldResult",
    "parse_interest",
]
