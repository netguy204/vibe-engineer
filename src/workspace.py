"""Workspace manifest discovery, loading, validation, and scan bootstrap.

# Chunk: docs/chunks/federation_workspace_manifest - Workspace manifest loader

A *workspace* is a repository containing multiple VE project trees, described by
a `.ve-workspace.yaml` manifest at the workspace root. This module is the
CLI-free half of that feature: it is imported by `ve workspace` commands, and is
meant to be imported equally by reference resolution and validation code that
needs to answer "which trees exist?" and "which tree owns this path?".

Two predicates for "is this a VE tree?" live here, deliberately differing in
strictness:

- :func:`is_ve_tree` (permissive) decides whether a directory may be *registered*
  as a member. Pointer-only trees — nothing but `external.yaml` interest edges —
  must qualify, or a workspace cannot describe scaffolded packages.
- :func:`has_trunk` (strict) decides whether :func:`scan_for_trees` *proposes* a
  directory during bootstrap. `docs/trunk/` is the strongest available signal of
  an intentional tree, and a bootstrap scan that proposed every pointer stub
  would bury the operator.

Scanning is a bootstrap aid, never the authority: it cannot name trees (names are
what `::` qualifiers resolve against) and cannot tell an intentional tree from an
accidental one, such as a scaffolding template that ships its own docs tree.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import yaml
from pydantic import ValidationError

from models.workspace import (
    WorkspaceManifest,
    WorkspaceMember,
    normalize_member_path,
    validate_member_name,
)

WORKSPACE_MANIFEST_NAME = ".ve-workspace.yaml"

# Artifact directories whose presence under docs/ marks a VE tree.
VE_ARTIFACT_DIRS = ("trunk", "chunks", "narratives", "investigations", "subsystems")

# Non-hidden directories a scan never descends into. Walking these on a large
# monorepo is slow enough to look broken, and a docs tree found inside one is a
# vendored or built copy, not a member of this workspace.
SCAN_SKIP_DIRS = frozenset(
    {
        "node_modules",
        "venv",
        "__pycache__",
        "site-packages",
        "dist",
        "build",
        "target",
    }
)


class WorkspaceError(Exception):
    """Base class for workspace manifest errors."""


class WorkspaceNotFoundError(WorkspaceError):
    """No `.ve-workspace.yaml` was found at or above the starting directory."""


class WorkspaceManifestError(WorkspaceError):
    """A `.ve-workspace.yaml` exists but could not be parsed or validated."""


# Chunk: docs/chunks/federation_workspace_manifest - Duplicate-key detection on load
class _UniqueKeyLoader(yaml.SafeLoader):
    """A SafeLoader that refuses duplicate mapping keys.

    `yaml.safe_load` silently keeps the last of two duplicate keys. For the
    manifest that would mean a repeated member name quietly resolving to one of
    two trees, which is exactly the class of silent misresolution the workspace
    exists to eliminate.
    """

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        # SafeConstructor.construct_yaml_map delegates to self.construct_mapping,
        # so overriding it here is enough to cover every mapping in the document.
        seen: set = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.MarkedYAMLError(
                    context="while parsing a mapping",
                    problem=f"duplicate key '{key}'",
                    problem_mark=key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


# Chunk: docs/chunks/federation_workspace_manifest - Permissive member tree predicate
def is_ve_tree(path: Path) -> bool:
    """Return True if `path` is the root of a VE tree.

    A VE tree has a `docs/` directory containing at least one artifact directory
    (`trunk/`, `chunks/`, `narratives/`, `investigations/`, `subsystems/`). This
    is permissive by design: pointer-only trees have `docs/chunks/` full of
    `external.yaml` stubs and no `docs/trunk/`, and they are legitimate members.
    """
    docs = path / "docs"
    if not docs.is_dir():
        return False
    return any((docs / name).is_dir() for name in VE_ARTIFACT_DIRS)


# Chunk: docs/chunks/federation_workspace_manifest - Strict scan predicate
def has_trunk(path: Path) -> bool:
    """Return True if `path` holds a `docs/trunk/` directory.

    The signal that a tree was created intentionally, used to decide what a
    bootstrap scan proposes.
    """
    return (path / "docs" / "trunk").is_dir()


# Chunk: docs/chunks/federation_workspace_manifest - Loaded workspace with resolution helpers
@dataclass(frozen=True)
class Workspace:
    """A workspace root plus its validated manifest."""

    root: Path
    manifest: WorkspaceManifest

    @property
    def manifest_path(self) -> Path:
        """Path to the `.ve-workspace.yaml` describing this workspace."""
        return self.root / WORKSPACE_MANIFEST_NAME

    @property
    def members(self) -> list[WorkspaceMember]:
        """Registered members, in declaration order."""
        return self.manifest.members

    def member_path(self, member: WorkspaceMember) -> Path:
        """Absolute path to a member's tree root."""
        if member.path == ".":
            return self.root
        return self.root / member.path

    def resolve(self, name: str) -> Path:
        """Resolve a member name to the absolute path of its tree root.

        Args:
            name: A registered member name.

        Returns:
            Absolute path to the member's tree root.

        Raises:
            KeyError: If no member with that name is registered. The message
                lists the registered names.
        """
        member = self.manifest.get(name)
        if member is None:
            known = ", ".join(self.manifest.names()) or "(none)"
            raise KeyError(
                f"'{name}' is not a member of the workspace at {self.root}. "
                f"Registered members: {known}"
            )
        return self.member_path(member)

    def member_paths(self) -> dict[str, Path]:
        """Mapping of member name to absolute tree root path."""
        return {member.name: self.member_path(member) for member in self.members}

    # Chunk: docs/chunks/federation_workspace_manifest - Longest-prefix nesting resolution
    def find_member_for_path(self, path: Path) -> WorkspaceMember | None:
        """Return the innermost member whose tree contains `path`.

        Nested members are legal — a library tree inside a platform tree is the
        point of a workspace — so containment alone is ambiguous. The
        disambiguating rule is longest prefix wins: the most deeply nested
        member that contains the path is the one that owns it.

        Args:
            path: A path (file or directory), absolute or relative to the root.

        Returns:
            The owning member, or None if the path lies outside every member.
        """
        try:
            absolute = (path if path.is_absolute() else self.root / path).resolve()
            root = self.root.resolve()
            relative = absolute.relative_to(root)
        except ValueError:
            return None

        candidate: WorkspaceMember | None = None
        candidate_depth = -1
        rel_parts = relative.parts
        for member in self.members:
            member_parts = () if member.path == "." else tuple(member.path.split("/"))
            if rel_parts[: len(member_parts)] != member_parts:
                continue
            depth = len(member_parts)
            if depth > candidate_depth:
                candidate = member
                candidate_depth = depth
        return candidate


# Chunk: docs/chunks/federation_workspace_manifest - Upward manifest discovery
def find_workspace_root(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.ve-workspace.yaml`.

    Args:
        start: Directory to start from (checked itself, then its ancestors).

    Returns:
        The directory containing the manifest, or None if there is none.
    """
    current = start if start.is_dir() else start.parent
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / WORKSPACE_MANIFEST_NAME).is_file():
            return candidate
    return None


# Chunk: docs/chunks/federation_workspace_manifest - Manifest parsing and shape validation
def load_manifest(manifest_path: Path) -> WorkspaceManifest:
    """Parse and shape-validate a manifest file.

    Args:
        manifest_path: Path to a `.ve-workspace.yaml`.

    Returns:
        The validated manifest.

    Raises:
        WorkspaceManifestError: If the file is unparseable or invalid.
    """
    try:
        raw = yaml.load(manifest_path.read_text(), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise WorkspaceManifestError(f"{manifest_path} is not valid YAML: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise WorkspaceManifestError(
            f"{manifest_path} must contain a mapping with a 'members' key"
        )

    try:
        return WorkspaceManifest.model_validate(raw)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise WorkspaceManifestError(f"{manifest_path} is invalid: {details}") from exc


# Chunk: docs/chunks/federation_workspace_manifest - Workspace loading entry point
def load_workspace(start: Path) -> Workspace:
    """Find and load the workspace at or above `start`.

    Args:
        start: Directory to start the upward search from.

    Returns:
        The loaded workspace.

    Raises:
        WorkspaceNotFoundError: If no manifest exists at or above `start`.
        WorkspaceManifestError: If the manifest is unparseable or invalid.
    """
    root = find_workspace_root(start)
    if root is None:
        raise WorkspaceNotFoundError(
            f"No {WORKSPACE_MANIFEST_NAME} found in {start} or any parent "
            f"directory. Run `ve workspace init` at the root of the repository "
            f"that contains your VE trees."
        )
    return Workspace(root=root, manifest=load_manifest(root / WORKSPACE_MANIFEST_NAME))


# Chunk: docs/chunks/federation_workspace_manifest - Manifest serialization
def write_manifest(root: Path, manifest: WorkspaceManifest) -> Path:
    """Write `manifest` to `root/.ve-workspace.yaml`.

    Args:
        root: The workspace root directory.
        manifest: The manifest to serialize.

    Returns:
        Path to the written file.
    """
    root.mkdir(parents=True, exist_ok=True)
    target = root / WORKSPACE_MANIFEST_NAME
    payload = yaml.safe_dump({"members": manifest.to_mapping()}, sort_keys=False)
    target.write_text(payload)
    return target


def save_workspace(workspace: Workspace) -> Path:
    """Persist a workspace's manifest back to disk."""
    return write_manifest(workspace.root, workspace.manifest)


# Chunk: docs/chunks/federation_workspace_manifest - Filesystem validation of members
def validate_member_paths(workspace: Workspace) -> list[str]:
    """Check that every member path exists and holds a VE tree.

    Args:
        workspace: The workspace to check.

    Returns:
        One human-readable message per defective member (empty if all valid).
    """
    errors: list[str] = []
    for member in workspace.members:
        path = workspace.member_path(member)
        if not path.exists():
            errors.append(
                f"member '{member.name}' points at '{member.path}', which does not exist"
            )
        elif not path.is_dir():
            errors.append(
                f"member '{member.name}' points at '{member.path}', which is not a directory"
            )
        elif not is_ve_tree(path):
            errors.append(
                f"member '{member.name}' points at '{member.path}', which contains no "
                f"VE tree (expected docs/ with one of: "
                f"{', '.join(VE_ARTIFACT_DIRS)})"
            )
    return errors


# Chunk: docs/chunks/federation_workspace_manifest - Scan pruning of non-member directories
def _should_skip_dir(name: str) -> bool:
    """Return True if a scan must not descend into a directory with this name.

    Hidden directories are skipped wholesale. A VE tree inside one is never an
    intentional workspace member, and two of them reliably hold *copies* of real
    trees: `.git` worktree metadata, and VE's own worktree checkouts under
    `.claude/worktrees/` and `.ve/chunks/*/worktree`. Proposing those would offer
    the operator the same tree several times under different paths.
    """
    return name.startswith(".") or name in SCAN_SKIP_DIRS


def _is_excluded(rel_path: str, name: str, exclude: tuple[str, ...]) -> bool:
    """Return True if a candidate directory matches any exclude pattern.

    Patterns are matched against both the workspace-root-relative path and the
    directory's own name, so `--exclude '*_template'` drops a template directory
    wherever it sits, while `--exclude 'tools/templates'` drops one location.
    """
    for pattern in exclude:
        normalized = pattern.rstrip("/")
        if fnmatch(rel_path, normalized) or fnmatch(name, normalized):
            return True
    return False


# Chunk: docs/chunks/federation_workspace_manifest - Bootstrap scan for candidate trees
def scan_for_trees(root: Path, exclude: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Discover candidate VE trees under `root`.

    Proposes every directory containing `docs/trunk/`. Nesting is *not* pruned:
    a tree inside another tree is a legitimate, separately addressable member,
    which is the shape real monorepos take.

    Args:
        root: The workspace root to scan.
        exclude: Glob patterns matched against each directory's root-relative
            path and its own name. A matching directory is pruned along with
            everything beneath it.

    Returns:
        Sorted workspace-root-relative POSIX paths ("." for the root itself).
    """
    exclude = tuple(exclude)
    root = root.resolve()
    found: list[str] = []

    def walk(directory: Path, rel: str) -> None:
        if has_trunk(directory):
            found.append(rel)
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if _should_skip_dir(entry.name):
                continue
            child_rel = entry.name if rel == "." else posixpath.join(rel, entry.name)
            if _is_excluded(child_rel, entry.name, exclude):
                continue
            walk(entry, child_rel)

    if not _is_excluded(".", root.name, exclude):
        walk(root, ".")

    return sorted(found)


def _coerce_member_name(raw: str) -> str:
    """Coerce a directory name into the member name grammar."""
    coerced = "".join(
        char if char.isascii() and (char.isalnum() or char in "_-") else "_"
        for char in raw.lower()
    )
    return coerced or "tree"


# Chunk: docs/chunks/federation_workspace_manifest - Name suggestions for scanned trees
def suggest_member_names(
    rel_paths: list[str] | tuple[str, ...], root: Path
) -> list[tuple[str, str]]:
    """Suggest member names for scanned tree paths.

    A tree's directory name is the natural short name. Because two packages in
    different subtrees routinely share a directory name (`common`, `core`), a
    collision is disambiguated by prefixing the parent component, then by a
    numeric suffix.

    Args:
        rel_paths: Workspace-root-relative tree paths, as returned by
            :func:`scan_for_trees`.
        root: The workspace root (used to name the "." candidate).

    Returns:
        List of `(suggested_name, rel_path)` pairs in input order.
    """
    suggestions: list[tuple[str, str]] = []
    used: set[str] = set()

    for rel_path in rel_paths:
        parts = [] if rel_path == "." else rel_path.split("/")
        base = _coerce_member_name(parts[-1] if parts else root.name)

        name = base
        if name in used and len(parts) >= 2:
            name = f"{_coerce_member_name(parts[-2])}_{base}"
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1

        used.add(name)
        suggestions.append((name, rel_path))

    return suggestions


# Chunk: docs/chunks/federation_workspace_manifest - Member registration
def add_member(workspace: Workspace, name: str, path: str) -> Workspace:
    """Return a workspace with a new validated member appended.

    Validates the name grammar, the path shape, uniqueness of the name, and the
    filesystem facts (the path exists and holds a VE tree) before accepting it.

    Args:
        workspace: The workspace to extend.
        name: The member's short name.
        path: The member's path, relative to the workspace root.

    Returns:
        A new :class:`Workspace` with the member appended (not yet saved).

    Raises:
        WorkspaceManifestError: If any validation fails.
    """
    try:
        validate_member_name(name)
        normalized = normalize_member_path(path)
    except ValueError as exc:
        raise WorkspaceManifestError(str(exc)) from exc

    if workspace.manifest.get(name) is not None:
        existing = workspace.manifest.get(name)
        raise WorkspaceManifestError(
            f"member '{name}' is already registered, pointing at "
            f"'{existing.path}'. Member names must be unique because they are "
            f"what '<member>::' references resolve against."
        )

    member = WorkspaceMember(name=name, path=normalized)
    target = workspace.member_path(member)
    if not target.exists():
        raise WorkspaceManifestError(
            f"'{normalized}' does not exist relative to the workspace root "
            f"{workspace.root}"
        )
    if not target.is_dir():
        raise WorkspaceManifestError(f"'{normalized}' is not a directory")
    if not is_ve_tree(target):
        raise WorkspaceManifestError(
            f"'{normalized}' contains no VE tree: expected a docs/ directory "
            f"with one of {', '.join(VE_ARTIFACT_DIRS)}"
        )

    try:
        manifest = workspace.manifest.with_member(member)
    except ValidationError as exc:
        raise WorkspaceManifestError(str(exc)) from exc

    return Workspace(root=workspace.root, manifest=manifest)


# Chunk: docs/chunks/federation_workspace_manifest - Path input normalization for the CLI
def relativize_to_workspace(root: Path, path: str) -> str:
    """Convert an operator-supplied path into a workspace-root-relative path.

    Accepts absolute paths and paths relative to the workspace root, so an
    operator can paste either.

    Args:
        root: The workspace root.
        path: The operator-supplied path.

    Returns:
        The workspace-root-relative POSIX path.

    Raises:
        WorkspaceManifestError: If an absolute path lies outside the workspace.
    """
    candidate = Path(path)
    if not candidate.is_absolute():
        return path

    try:
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise WorkspaceManifestError(
            f"'{path}' is outside the workspace root {root}; a workspace member "
            f"must live inside the workspace"
        ) from exc

    return relative.as_posix() or "."


__all__ = [
    "SCAN_SKIP_DIRS",
    "VE_ARTIFACT_DIRS",
    "WORKSPACE_MANIFEST_NAME",
    "Workspace",
    "WorkspaceError",
    "WorkspaceManifestError",
    "WorkspaceNotFoundError",
    "add_member",
    "find_workspace_root",
    "has_trunk",
    "is_ve_tree",
    "load_manifest",
    "load_workspace",
    "relativize_to_workspace",
    "save_workspace",
    "scan_for_trees",
    "suggest_member_names",
    "validate_member_paths",
    "write_manifest",
]
