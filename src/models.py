"""Pydantic models for chunk validation."""

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator

from validation import validate_identifier


class SubsystemStatus(StrEnum):
    """Status values for subsystem documentation lifecycle."""

    DISCOVERING = "DISCOVERING"
    DOCUMENTED = "DOCUMENTED"
    REFACTORING = "REFACTORING"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"


class ComplianceLevel(StrEnum):
    """Compliance level for code references in subsystem documentation.

    Indicates how well referenced code follows the subsystem's patterns.
    """

    COMPLIANT = "COMPLIANT"  # Fully follows the subsystem's patterns
    PARTIAL = "PARTIAL"  # Partially follows but has some deviations
    NON_COMPLIANT = "NON_COMPLIANT"  # Does not follow the patterns


# Regex for validating chunk ID format: {NNNN}-{short_name}
CHUNK_ID_PATTERN = re.compile(r"^\d{4}-.+$")


class ChunkRelationship(BaseModel):
    """Relationship between a subsystem and a chunk.

    Captures how chunks relate to subsystem documentation:
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem
    """

    chunk_id: str  # format: {NNNN}-{short_name}
    relationship: Literal["implements", "uses"]

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
        """Validate chunk_id matches {NNNN}-{short_name} pattern."""
        if not v:
            raise ValueError("chunk_id cannot be empty")
        if not CHUNK_ID_PATTERN.match(v):
            raise ValueError(
                "chunk_id must match pattern {NNNN}-{short_name} "
                "(4 digits, hyphen, name)"
            )
        # Ensure there's actually a name after the hyphen
        parts = v.split("-", 1)
        if len(parts) < 2 or not parts[1]:
            raise ValueError("chunk_id must have a name after the hyphen")
        return v


class SubsystemRelationship(BaseModel):
    """Relationship between a chunk and a subsystem.

    Captures how a chunk relates to subsystem documentation (inverse of ChunkRelationship):
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem
    """

    subsystem_id: str  # format: {NNNN}-{short_name}
    relationship: Literal["implements", "uses"]

    @field_validator("subsystem_id")
    @classmethod
    def validate_subsystem_id(cls, v: str) -> str:
        """Validate subsystem_id matches {NNNN}-{short_name} pattern."""
        if not v:
            raise ValueError("subsystem_id cannot be empty")
        if not CHUNK_ID_PATTERN.match(v):
            raise ValueError(
                "subsystem_id must match pattern {NNNN}-{short_name} "
                "(4 digits, hyphen, name)"
            )
        # Ensure there's actually a name after the hyphen
        parts = v.split("-", 1)
        if len(parts) < 2 or not parts[1]:
            raise ValueError("subsystem_id must have a name after the hyphen")
        return v


# Forward reference for SymbolicReference used in SubsystemFrontmatter
# (SymbolicReference is defined later in the file)


def _require_valid_dir_name(value: str, field_name: str) -> str:
    """Validate a directory name, raising ValueError if invalid."""
    errors = validate_identifier(value, field_name, allow_dot=True, max_length=31)
    if errors:
        raise ValueError("; ".join(errors))
    return value


def _require_valid_repo_ref(value: str, field_name: str) -> str:
    """Validate a GitHub-style org/repo reference.

    Format: {org}/{repo} where both parts are valid identifiers.
    """
    if "/" not in value:
        raise ValueError(f"{field_name} must be in 'org/repo' format")

    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError(f"{field_name} must have exactly one slash (org/repo format)")

    org, repo = parts
    if not org:
        raise ValueError(f"{field_name} org part cannot be empty")
    if not repo:
        raise ValueError(f"{field_name} repo part cannot be empty")

    # Validate org part (allow dots, max 39 chars per GitHub)
    org_errors = validate_identifier(org, f"{field_name} org", allow_dot=True, max_length=39)
    if org_errors:
        raise ValueError("; ".join(org_errors))

    # Validate repo part (allow dots, max 100 chars per GitHub)
    repo_errors = validate_identifier(repo, f"{field_name} repo", allow_dot=True, max_length=100)
    if repo_errors:
        raise ValueError("; ".join(repo_errors))

    return value


# Regex for validating 40-character hex SHA
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class TaskConfig(BaseModel):
    """Configuration for cross-repository chunk management.

    All repository references use GitHub's org/repo format.
    """

    external_chunk_repo: str  # org/repo format
    projects: list[str]  # list of org/repo format

    @field_validator("external_chunk_repo")
    @classmethod
    def validate_external_chunk_repo(cls, v: str) -> str:
        """Validate external_chunk_repo is in org/repo format."""
        return _require_valid_repo_ref(v, "external_chunk_repo")

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str]) -> list[str]:
        """Validate projects list is non-empty with org/repo format entries."""
        if not v:
            raise ValueError("projects must contain at least one project")
        for project in v:
            _require_valid_repo_ref(project, "project")
        return v


class ExternalChunkRef(BaseModel):
    """Reference to a chunk in another repository.

    Used for both:
    - external.yaml files in participating repos (with track/pinned)
    - dependents list in external chunk GOAL.md (without track/pinned)
    """

    repo: str  # GitHub-style org/repo format
    chunk: str  # Chunk directory name
    track: str | None = None  # Branch to follow (optional)
    pinned: str | None = None  # 40-char SHA (optional)

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repo is in org/repo format."""
        return _require_valid_repo_ref(v, "repo")

    @field_validator("chunk")
    @classmethod
    def validate_chunk(cls, v: str) -> str:
        """Validate chunk is a valid directory name."""
        return _require_valid_dir_name(v, "chunk")

    @field_validator("pinned")
    @classmethod
    def validate_pinned(cls, v: str | None) -> str | None:
        """Validate pinned is a 40-character hex SHA if provided."""
        if v is None:
            return v
        if not SHA_PATTERN.match(v):
            raise ValueError("pinned must be a 40-character lowercase hex SHA")
        return v


class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalChunkRef] = []


class CodeRange(BaseModel):
    """A range of lines in a file that implements a specific requirement."""

    lines: str  # "N-M" or "N" format
    implements: str


class CodeReference(BaseModel):
    """A file with code ranges that implement requirements."""

    file: str
    ranges: list[CodeRange]


class SymbolicReference(BaseModel):
    """A symbolic reference to code that implements a requirement.

    Format: {file_path} or {file_path}#{symbol_path}

    Examples:
        - src/chunks.py (entire module)
        - src/chunks.py#Chunks (class)
        - src/chunks.py#Chunks::create_chunk (method)
        - src/ve.py#validate_short_name (standalone function)

    For subsystem documentation, the optional compliance field indicates how well
    the referenced code follows the subsystem's patterns:
        - COMPLIANT: Fully follows the subsystem's patterns (canonical implementation)
        - PARTIAL: Partially follows but has some deviations
        - NON_COMPLIANT: Does not follow the patterns (deviation to be addressed)
    """

    ref: str  # format: {file_path} or {file_path}#{symbol_path}
    implements: str  # description of what this reference implements
    compliance: ComplianceLevel | None = None  # optional, used in subsystem docs

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, v: str) -> str:
        """Validate ref field format."""
        if not v:
            raise ValueError("ref cannot be empty")

        if v.startswith("#"):
            raise ValueError("ref must start with a file path, not #")

        if v.count("#") > 1:
            raise ValueError("ref cannot contain multiple # characters")

        if "#" in v:
            file_path, symbol_path = v.split("#", 1)
            if not symbol_path:
                raise ValueError("symbol path cannot be empty after #")

            # Check for empty components in symbol path
            parts = symbol_path.split("::")
            for part in parts:
                if not part:
                    raise ValueError("symbol path cannot have empty component between ::")

        return v

    @field_validator("implements")
    @classmethod
    def validate_implements(cls, v: str) -> str:
        """Validate implements field is non-empty."""
        if not v or not v.strip():
            raise ValueError("implements cannot be empty")
        return v


class SubsystemFrontmatter(BaseModel):
    """Frontmatter schema for subsystem OVERVIEW.md files.

    Validates the YAML frontmatter in subsystem documentation.
    """

    status: SubsystemStatus
    chunks: list[ChunkRelationship] = []
    code_references: list[SymbolicReference] = []
