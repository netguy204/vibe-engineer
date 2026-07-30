"""Pydantic models for the workspace manifest (`.ve-workspace.yaml`).

# Chunk: docs/chunks/federation_workspace_manifest - Workspace manifest schema

A *workspace* is a repository containing multiple VE project trees. The manifest
at the workspace root maps member short names to tree paths::

    members:
      pybusiness: packages/libs/pybusiness
      visualization: apps/viz

The manifest is the single authority for resolving tree-qualified references
(``<member>::docs/...``) and the iteration surface for workspace-wide commands.

Only *shape* is validated here (name grammar, path shape, uniqueness).
Filesystem facts — does the path exist, does it hold a VE tree — are validated
by :mod:`workspace`, which knows the workspace root.
"""

from __future__ import annotations

import posixpath
import re
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

# Member names share the identifier grammar of artifact short names. The
# grammar deliberately excludes "/" and ":", which is what keeps a member name
# unambiguous against an `org/repo` qualifier in the shared `::` reference
# syntax: `pybusiness::docs/...` is a workspace member, `acme/hub::docs/...` is
# another repository, and the presence of "/" tells them apart (see
# models/references.py#SymbolicReference).
MEMBER_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")


# Chunk: docs/chunks/federation_workspace_manifest - Member name grammar enforcement
def validate_member_name(value: str, field_name: str = "member name") -> str:
    """Validate a workspace member name against the member grammar.

    Args:
        value: The candidate member name.
        field_name: Name used in error messages.

    Returns:
        The validated name.

    Raises:
        ValueError: If the name is empty or outside the grammar.
    """
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if not MEMBER_NAME_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must match [a-z0-9_-]+ (lowercase letters, digits, "
            f"underscores, hyphens), got '{value}'. In particular '/' and '::' "
            f"are not allowed: they are what distinguishes a workspace member "
            f"from an 'org/repo' qualifier in a '::' reference"
        )
    return value


# Chunk: docs/chunks/federation_workspace_manifest - Member path normalization
def normalize_member_path(value: str, field_name: str = "member path") -> str:
    """Normalize a member path to a workspace-root-relative POSIX path.

    Member paths are relative to the workspace root so that they mean the same
    thing regardless of the working directory a command runs from.

    Args:
        value: The candidate path.
        field_name: Name used in error messages.

    Returns:
        The normalized relative POSIX path ("." for the workspace root itself).

    Raises:
        ValueError: If the path is empty, absolute, or escapes the root.
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")

    raw = value.strip().replace("\\", "/")
    if raw.startswith("/"):
        raise ValueError(
            f"{field_name} must be relative to the workspace root, got absolute "
            f"path '{value}'"
        )

    normalized = posixpath.normpath(raw)
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(
            f"{field_name} must stay inside the workspace root, but '{value}' "
            f"escapes it"
        )

    return normalized


# Chunk: docs/chunks/federation_workspace_manifest - Workspace member model
class WorkspaceMember(BaseModel):
    """One VE tree registered in a workspace.

    Attributes:
        name: Short name that ``<member>::`` references resolve against.
        path: Workspace-root-relative POSIX path to the tree root.
    """

    name: str
    path: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return validate_member_name(v, "member name")

    @field_validator("path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        return normalize_member_path(v, "member path")


# Chunk: docs/chunks/federation_workspace_manifest - Workspace manifest model
class WorkspaceManifest(BaseModel):
    """The contents of a `.ve-workspace.yaml` file.

    Members are held as an ordered list so declaration order is preserved for
    display, while :meth:`get` provides name lookup. The on-disk representation
    is a ``name: path`` mapping; :meth:`model_validate` accepts either form.
    """

    members: list[WorkspaceMember] = []

    @model_validator(mode="before")
    @classmethod
    def _accept_mapping_form(cls, data: Any) -> Any:
        """Convert the on-disk ``{name: path}`` mapping into the list form."""
        if not isinstance(data, dict):
            return data

        members = data.get("members")
        if members is None:
            return {**data, "members": []}
        if isinstance(members, dict):
            converted = [
                {"name": name, "path": path} for name, path in members.items()
            ]
            return {**data, "members": converted}
        return data

    @field_validator("members")
    @classmethod
    def _reject_duplicate_names(cls, v: list[WorkspaceMember]) -> list[WorkspaceMember]:
        """A member name is a resolution key, so it must be unique."""
        seen: set[str] = set()
        for member in v:
            if member.name in seen:
                raise ValueError(
                    f"duplicate member name '{member.name}': member names must be "
                    f"unique because they are what '<member>::' references resolve "
                    f"against"
                )
            seen.add(member.name)
        return v

    def names(self) -> list[str]:
        """Member names, in declaration order."""
        return [member.name for member in self.members]

    def get(self, name: str) -> WorkspaceMember | None:
        """Return the member with this name, or None if it is not registered."""
        for member in self.members:
            if member.name == name:
                return member
        return None

    def to_mapping(self) -> dict[str, str]:
        """Return the on-disk ``{name: path}`` mapping, in declaration order."""
        return {member.name: member.path for member in self.members}

    def with_member(self, member: WorkspaceMember) -> "WorkspaceManifest":
        """Return a new manifest with `member` appended.

        Raises:
            ValueError: If the name is already registered (via validation).
        """
        return WorkspaceManifest(members=[*self.members, member])
