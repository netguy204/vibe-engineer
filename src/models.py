"""Pydantic models for chunk validation."""
# Chunk: docs/chunks/chunk_validate - Code reference models
# Chunk: docs/chunks/cross_repo_schemas - Cross-repository schemas
# Chunk: docs/chunks/symbolic_code_refs - Symbolic reference model
# Chunk: docs/chunks/subsystem_schemas_and_model - Subsystem schemas
# Chunk: docs/chunks/subsystem_template - Compliance levels
# Chunk: docs/chunks/bidirectional_refs - Subsystem relationship
# Chunk: docs/chunks/subsystem_status_transitions - Status transitions
# Chunk: docs/chunks/investigation_commands - Investigation schemas

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator

from validation import validate_identifier


# Chunk: docs/chunks/subsystem_schemas_and_model - Subsystem lifecycle states
class SubsystemStatus(StrEnum):
    """Status values for subsystem documentation lifecycle."""

    DISCOVERING = "DISCOVERING"
    DOCUMENTED = "DOCUMENTED"
    REFACTORING = "REFACTORING"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"


# Chunk: docs/chunks/investigation_commands - Investigation lifecycle states
class InvestigationStatus(StrEnum):
    """Status values for investigation lifecycle."""

    ONGOING = "ONGOING"  # Investigation in progress
    SOLVED = "SOLVED"  # Investigation led to action; chunks were proposed/created
    NOTED = "NOTED"  # Findings documented but no action required
    DEFERRED = "DEFERRED"  # Investigation paused; may be revisited later


# Chunk: docs/chunks/valid_transitions - State transition validation
VALID_INVESTIGATION_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.ONGOING: {InvestigationStatus.SOLVED, InvestigationStatus.NOTED, InvestigationStatus.DEFERRED},
    InvestigationStatus.SOLVED: set(),  # Terminal state
    InvestigationStatus.NOTED: set(),  # Terminal state
    InvestigationStatus.DEFERRED: {InvestigationStatus.ONGOING},  # Can resume
}


# Chunk: docs/chunks/chunk_frontmatter_model - Chunk lifecycle states
class ChunkStatus(StrEnum):
    """Status values for chunk lifecycle."""

    FUTURE = "FUTURE"  # Queued for future work, not yet being implemented
    IMPLEMENTING = "IMPLEMENTING"  # Currently being implemented
    ACTIVE = "ACTIVE"  # Accurately describes current or recently-merged work
    SUPERSEDED = "SUPERSEDED"  # Another chunk has modified the code this chunk governed
    HISTORICAL = "HISTORICAL"  # Significant drift; kept for archaeology only


# Chunk: docs/chunks/valid_transitions - State transition validation
VALID_CHUNK_TRANSITIONS: dict[ChunkStatus, set[ChunkStatus]] = {
    ChunkStatus.FUTURE: {ChunkStatus.IMPLEMENTING, ChunkStatus.HISTORICAL},
    ChunkStatus.IMPLEMENTING: {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL},
    ChunkStatus.ACTIVE: {ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL},
    ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},
    ChunkStatus.HISTORICAL: set(),  # Terminal state
}


# Chunk: docs/chunks/artifact_ordering_index - Artifact type enum for ordering
# Chunk: docs/chunks/consolidate_ext_refs - Moved from artifact_ordering.py
class ArtifactType(StrEnum):
    """Types of workflow artifacts that can be ordered."""

    CHUNK = "chunk"
    NARRATIVE = "narrative"
    INVESTIGATION = "investigation"
    SUBSYSTEM = "subsystem"


# Chunk: docs/chunks/subsystem_status_transitions - Valid state transitions
VALID_STATUS_TRANSITIONS: dict[SubsystemStatus, set[SubsystemStatus]] = {
    SubsystemStatus.DISCOVERING: {SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.DOCUMENTED: {SubsystemStatus.REFACTORING, SubsystemStatus.DEPRECATED},
    SubsystemStatus.REFACTORING: {SubsystemStatus.STABLE, SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.STABLE: {SubsystemStatus.DEPRECATED, SubsystemStatus.REFACTORING},
    SubsystemStatus.DEPRECATED: set(),  # Terminal state
}


# Chunk: docs/chunks/subsystem_template - Code reference compliance levels
class ComplianceLevel(StrEnum):
    """Compliance level for code references in subsystem documentation.

    Indicates how well referenced code follows the subsystem's patterns.
    """

    COMPLIANT = "COMPLIANT"  # Fully follows the subsystem's patterns
    PARTIAL = "PARTIAL"  # Partially follows but has some deviations
    NON_COMPLIANT = "NON_COMPLIANT"  # Does not follow the patterns


# Chunk: docs/chunks/remove_sequence_prefix - Short name extraction utility
def extract_short_name(dir_name: str) -> str:
    """Extract short name from directory name, handling both patterns.

    Supports both legacy "{NNNN}-{short_name}" format and new "{short_name}" format.

    Args:
        dir_name: Either "NNNN-short_name" or "short_name" format

    Returns:
        The short name portion
    """
    if re.match(r"^\d{4}-", dir_name):
        return dir_name.split("-", 1)[1]
    return dir_name


# Chunk: docs/chunks/remove_sequence_prefix - Artifact ID pattern (both formats)
# Regex for validating artifact ID format: {NNNN}-{short_name} (legacy) or {short_name} (new)
# Legacy pattern: 4 digits, hyphen, then name
# New pattern: lowercase letters, digits, underscores, hyphens (no leading digits)
ARTIFACT_ID_PATTERN = re.compile(r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$")

# Legacy regex for backward compatibility in existing code
CHUNK_ID_PATTERN = re.compile(r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$")


# Chunk: docs/chunks/subsystem_schemas_and_model - Chunk-to-subsystem relationship
# Chunk: docs/chunks/remove_sequence_prefix - Accept both legacy and new ID formats
class ChunkRelationship(BaseModel):
    """Relationship between a subsystem and a chunk.

    Captures how chunks relate to subsystem documentation:
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem
    """

    chunk_id: str  # format: {NNNN}-{short_name} (legacy) or {short_name} (new)
    relationship: Literal["implements", "uses"]

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
        """Validate chunk_id matches valid artifact ID pattern.

        Accepts both legacy {NNNN}-{short_name} format and new {short_name} format.
        """
        if not v:
            raise ValueError("chunk_id cannot be empty")
        if not ARTIFACT_ID_PATTERN.match(v):
            raise ValueError(
                "chunk_id must match pattern {NNNN}-{short_name} (legacy) "
                "or {short_name} (new: lowercase, starting with letter)"
            )
        # For legacy format, ensure there's content after the hyphen
        if re.match(r"^\d{4}-", v):
            parts = v.split("-", 1)
            if len(parts) < 2 or not parts[1]:
                raise ValueError("chunk_id must have a name after the prefix")
        return v


# Chunk: docs/chunks/bidirectional_refs - Subsystem-to-chunk relationship
# Chunk: docs/chunks/remove_sequence_prefix - Accept both legacy and new ID formats
class SubsystemRelationship(BaseModel):
    """Relationship between a chunk and a subsystem.

    Captures how a chunk relates to subsystem documentation (inverse of ChunkRelationship):
    - "implements": chunk directly implements part of the subsystem
    - "uses": chunk uses/depends on the subsystem
    """

    subsystem_id: str  # format: {NNNN}-{short_name} (legacy) or {short_name} (new)
    relationship: Literal["implements", "uses"]

    @field_validator("subsystem_id")
    @classmethod
    def validate_subsystem_id(cls, v: str) -> str:
        """Validate subsystem_id matches valid artifact ID pattern.

        Accepts both legacy {NNNN}-{short_name} format and new {short_name} format.
        """
        if not v:
            raise ValueError("subsystem_id cannot be empty")
        if not ARTIFACT_ID_PATTERN.match(v):
            raise ValueError(
                "subsystem_id must match pattern {NNNN}-{short_name} (legacy) "
                "or {short_name} (new: lowercase, starting with letter)"
            )
        # For legacy format, ensure there's content after the hyphen
        if re.match(r"^\d{4}-", v):
            parts = v.split("-", 1)
            if len(parts) < 2 or not parts[1]:
                raise ValueError("subsystem_id must have a name after the prefix")
        return v


# Forward reference for SymbolicReference used in SubsystemFrontmatter
# (SymbolicReference is defined later in the file)


# Chunk: docs/chunks/cross_repo_schemas - Directory name validation
def _require_valid_dir_name(value: str, field_name: str) -> str:
    """Validate a directory name, raising ValueError if invalid."""
    errors = validate_identifier(value, field_name, allow_dot=True, max_length=31)
    if errors:
        raise ValueError("; ".join(errors))
    return value


# Chunk: docs/chunks/chunk_create_task_aware - Repository ref validation
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


# Chunk: docs/chunks/cross_repo_schemas - Cross-repo task configuration
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


# Chunk: docs/chunks/cross_repo_schemas - External chunk reference
# Chunk: docs/chunks/external_chunk_causal - Local causal ordering for external refs
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
    created_after: list[str] = []  # Local causal ordering (for external.yaml)

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


# Chunk: docs/chunks/consolidate_ext_refs - Generic external artifact reference
class ExternalArtifactRef(BaseModel):
    """Reference to a workflow artifact in another repository.

    Used for external.yaml files that reference artifacts (chunks, narratives,
    investigations, subsystems) in an external repository. This is a type-agnostic
    replacement for ExternalChunkRef that supports all workflow artifact types.
    """

    artifact_type: ArtifactType
    artifact_id: str  # Short name of the referenced artifact
    repo: str  # GitHub-style org/repo format
    track: str | None = None  # Branch to follow (optional)
    pinned: str | None = None  # 40-char SHA (optional)
    created_after: list[str] = []  # Local causal ordering

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repo is in org/repo format."""
        return _require_valid_repo_ref(v, "repo")

    @field_validator("artifact_id")
    @classmethod
    def validate_artifact_id(cls, v: str) -> str:
        """Validate artifact_id is a valid directory name."""
        return _require_valid_dir_name(v, "artifact_id")

    @field_validator("pinned")
    @classmethod
    def validate_pinned(cls, v: str | None) -> str | None:
        """Validate pinned is a 40-character hex SHA if provided."""
        if v is None:
            return v
        if not SHA_PATTERN.match(v):
            raise ValueError("pinned must be a 40-character lowercase hex SHA")
        return v


# Chunk: docs/chunks/cross_repo_schemas - Chunk dependents schema
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use ExternalArtifactRef
class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalArtifactRef] = []


# Chunk: docs/chunks/chunk_validate - Line range for code references
class CodeRange(BaseModel):
    """A range of lines in a file that implements a specific requirement."""

    lines: str  # "N-M" or "N" format
    implements: str


# Chunk: docs/chunks/chunk_validate - File-based code reference
class CodeReference(BaseModel):
    """A file with code ranges that implement requirements."""

    file: str
    ranges: list[CodeRange]


# Chunk: docs/chunks/symbolic_code_refs - Symbolic code reference
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


# Chunk: docs/chunks/proposed_chunks_frontmatter - Proposed chunk schema
class ProposedChunk(BaseModel):
    """A proposed chunk entry used across narratives, subsystems, and investigations.

    Represents a chunk that has been proposed but may or may not have been created yet.
    When chunk_directory is None or empty, the chunk has not yet been created.
    """

    prompt: str  # The chunk prompt text
    chunk_directory: str | None = None  # Populated when chunk is created

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        return v


# Chunk: docs/chunks/subsystem_schemas_and_model - Subsystem frontmatter schema
# Chunk: docs/chunks/proposed_chunks_frontmatter - Added proposed_chunks field
# Chunk: docs/chunks/created_after_field - Causal ordering field
class SubsystemFrontmatter(BaseModel):
    """Frontmatter schema for subsystem OVERVIEW.md files.

    Validates the YAML frontmatter in subsystem documentation.
    """

    status: SubsystemStatus
    chunks: list[ChunkRelationship] = []
    code_references: list[SymbolicReference] = []
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []


# Chunk: docs/chunks/proposed_chunks_frontmatter - Narrative status enum
class NarrativeStatus(StrEnum):
    """Status values for narrative lifecycle."""

    DRAFTING = "DRAFTING"  # Narrative is being refined; chunks not yet created
    ACTIVE = "ACTIVE"  # Chunks are being created and implemented
    COMPLETED = "COMPLETED"  # All chunks created and narrative's ambition realized


# Chunk: docs/chunks/valid_transitions - State transition validation
VALID_NARRATIVE_TRANSITIONS: dict[NarrativeStatus, set[NarrativeStatus]] = {
    NarrativeStatus.DRAFTING: {NarrativeStatus.ACTIVE},
    NarrativeStatus.ACTIVE: {NarrativeStatus.COMPLETED},
    NarrativeStatus.COMPLETED: set(),  # Terminal state
}


# Chunk: docs/chunks/proposed_chunks_frontmatter - Narrative frontmatter schema
# Chunk: docs/chunks/created_after_field - Causal ordering field
class NarrativeFrontmatter(BaseModel):
    """Frontmatter schema for narrative OVERVIEW.md files.

    Validates the YAML frontmatter in narrative documentation.
    """

    status: NarrativeStatus
    advances_trunk_goal: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []


# Chunk: docs/chunks/investigation_commands - Investigation frontmatter schema
# Chunk: docs/chunks/proposed_chunks_frontmatter - Updated to use ProposedChunk
# Chunk: docs/chunks/created_after_field - Causal ordering field
class InvestigationFrontmatter(BaseModel):
    """Frontmatter schema for investigation OVERVIEW.md files.

    Validates the YAML frontmatter in investigation documentation.
    """

    status: InvestigationStatus
    trigger: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []


# Chunk: docs/chunks/chunk_frontmatter_model - Chunk frontmatter schema
# Chunk: docs/chunks/created_after_field - Causal ordering field
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use ExternalArtifactRef
class ChunkFrontmatter(BaseModel):
    """Frontmatter schema for chunk GOAL.md files.

    Validates the YAML frontmatter in chunk documentation.
    """

    status: ChunkStatus
    ticket: str | None = None
    parent_chunk: str | None = None
    code_paths: list[str] = []
    code_references: list[SymbolicReference] = []
    narrative: str | None = None
    subsystems: list[SubsystemRelationship] = []
    proposed_chunks: list[ProposedChunk] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo artifacts
    created_after: list[str] = []
