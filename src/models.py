"""Pydantic models for chunk validation."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations

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


class InvestigationStatus(StrEnum):
    """Status values for investigation lifecycle."""

    ONGOING = "ONGOING"  # Investigation in progress
    SOLVED = "SOLVED"  # Investigation led to action; chunks were proposed/created
    NOTED = "NOTED"  # Findings documented but no action required
    DEFERRED = "DEFERRED"  # Investigation paused; may be revisited later


VALID_INVESTIGATION_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.ONGOING: {InvestigationStatus.SOLVED, InvestigationStatus.NOTED, InvestigationStatus.DEFERRED},
    InvestigationStatus.SOLVED: set(),  # Terminal state
    InvestigationStatus.NOTED: set(),  # Terminal state
    InvestigationStatus.DEFERRED: {InvestigationStatus.ONGOING},  # Can resume
}


class ChunkStatus(StrEnum):
    """Status values for chunk lifecycle."""

    FUTURE = "FUTURE"  # Queued for future work, not yet being implemented
    IMPLEMENTING = "IMPLEMENTING"  # Currently being implemented
    ACTIVE = "ACTIVE"  # Accurately describes current or recently-merged work
    SUPERSEDED = "SUPERSEDED"  # Another chunk has modified the code this chunk governed
    HISTORICAL = "HISTORICAL"  # Significant drift; kept for archaeology only


class BugType(StrEnum):
    """Classification of bug fix chunks to guide completion behavior.

    When a chunk is a bug fix, this field distinguishes between:
    - semantic: The bug revealed new understanding of intended behavior (discovery)
    - implementation: The bug corrected known-wrong code (we knew how it should work)
    """

    SEMANTIC = "semantic"  # Bug revealed new understanding; code backreferences required
    IMPLEMENTATION = "implementation"  # Bug corrected known-wrong code; backreferences optional


VALID_CHUNK_TRANSITIONS: dict[ChunkStatus, set[ChunkStatus]] = {
    ChunkStatus.FUTURE: {ChunkStatus.IMPLEMENTING, ChunkStatus.HISTORICAL},
    ChunkStatus.IMPLEMENTING: {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL},
    ChunkStatus.ACTIVE: {ChunkStatus.SUPERSEDED, ChunkStatus.HISTORICAL},
    ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},
    ChunkStatus.HISTORICAL: set(),  # Terminal state
}


class ArtifactType(StrEnum):
    """Types of workflow artifacts that can be ordered."""

    CHUNK = "chunk"
    NARRATIVE = "narrative"
    INVESTIGATION = "investigation"
    SUBSYSTEM = "subsystem"


VALID_STATUS_TRANSITIONS: dict[SubsystemStatus, set[SubsystemStatus]] = {
    SubsystemStatus.DISCOVERING: {SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.DOCUMENTED: {SubsystemStatus.REFACTORING, SubsystemStatus.DEPRECATED},
    SubsystemStatus.REFACTORING: {SubsystemStatus.STABLE, SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.STABLE: {SubsystemStatus.DEPRECATED, SubsystemStatus.REFACTORING},
    SubsystemStatus.DEPRECATED: set(),  # Terminal state
}


class ComplianceLevel(StrEnum):
    """Compliance level for code references in subsystem documentation.

    Indicates how well referenced code follows the subsystem's patterns.
    """

    COMPLIANT = "COMPLIANT"  # Fully follows the subsystem's patterns
    PARTIAL = "PARTIAL"  # Partially follows but has some deviations
    NON_COMPLIANT = "NON_COMPLIANT"  # Does not follow the patterns


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


# Regex for validating artifact ID format: {NNNN}-{short_name} (legacy) or {short_name} (new)
# Legacy pattern: 4 digits, hyphen, then name
# New pattern: lowercase letters, digits, underscores, hyphens (no leading digits)
ARTIFACT_ID_PATTERN = re.compile(r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$")

# Legacy regex for backward compatibility in existing code
CHUNK_ID_PATTERN = re.compile(r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$")


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
    """Configuration for cross-repository workflow artifact management.

    All repository references use GitHub's org/repo format.
    The external_artifact_repo specifies where all external workflow artifacts
    (chunks, narratives, investigations, subsystems) are stored.
    """

    external_artifact_repo: str  # org/repo format
    projects: list[str]  # list of org/repo format

    @field_validator("external_artifact_repo")
    @classmethod
    def validate_external_artifact_repo(cls, v: str) -> str:
        """Validate external_artifact_repo is in org/repo format."""
        return _require_valid_repo_ref(v, "external_artifact_repo")

    @field_validator("projects")
    @classmethod
    def validate_projects(cls, v: list[str]) -> list[str]:
        """Validate projects list is non-empty with org/repo format entries."""
        if not v:
            raise ValueError("projects must contain at least one project")
        for project in v:
            _require_valid_repo_ref(project, "project")
        return v


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


class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalArtifactRef] = []


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

    Format: {file_path}, {file_path}#{symbol_path}, or {org/repo::file_path}#{symbol_path}

    Examples:
        - src/chunks.py (entire module)
        - src/chunks.py#Chunks (class)
        - src/chunks.py#Chunks::create_chunk (method)
        - src/ve.py#validate_short_name (standalone function)
        - acme/project::src/foo.py#Bar (class in another project)

    For subsystem documentation, the optional compliance field indicates how well
    the referenced code follows the subsystem's patterns:
        - COMPLIANT: Fully follows the subsystem's patterns (canonical implementation)
        - PARTIAL: Partially follows but has some deviations
        - NON_COMPLIANT: Does not follow the patterns (deviation to be addressed)
    """

    ref: str  # format: {file_path}, {file_path}#{symbol_path}, or {org/repo::...}
    implements: str  # description of what this reference implements
    compliance: ComplianceLevel | None = None  # optional, used in subsystem docs

    @field_validator("ref")
    @classmethod
    def validate_ref(cls, v: str) -> str:
        """Validate ref field format.

        Supports both local references and project-qualified references:
        - Local: file_path or file_path#symbol_path
        - Qualified: org/repo::file_path or org/repo::file_path#symbol_path
        """
        if not v:
            raise ValueError("ref cannot be empty")

        if v.startswith("#"):
            raise ValueError("ref must start with a file path, not #")

        if v.count("#") > 1:
            raise ValueError("ref cannot contain multiple # characters")

        # Check for project qualifier (:: must come before # if present)
        hash_pos = v.find("#")
        if hash_pos == -1:
            ref_before_symbol = v
        else:
            ref_before_symbol = v[:hash_pos]

        # Check for :: in the portion before #
        double_colon_pos = ref_before_symbol.find("::")
        if double_colon_pos != -1:
            project = ref_before_symbol[:double_colon_pos]
            file_path_part = ref_before_symbol[double_colon_pos + 2:]

            # Validate that there's no second :: before #
            if "::" in file_path_part:
                raise ValueError("ref cannot have multiple :: delimiters before #")

            # Validate project qualifier is not empty
            if not project:
                raise ValueError("project qualifier cannot be empty before ::")

            # Validate project is in org/repo format using existing validator
            # Wrap with contextual error message that includes the invalid value
            try:
                _require_valid_repo_ref(project, "project qualifier")
            except ValueError:
                raise ValueError(
                    f"project qualifier must be in 'org/repo' format "
                    f"(e.g., 'acme/project::path'), got '{project}'"
                )

            # Check that file path portion is not empty
            if not file_path_part:
                raise ValueError("file path cannot be empty after ::")
        else:
            # No project qualifier, ref_before_symbol is the file path
            file_path_part = ref_before_symbol

        if "#" in v:
            symbol_path = v.split("#", 1)[1]
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


class SubsystemFrontmatter(BaseModel):
    """Frontmatter schema for subsystem OVERVIEW.md files.

    Validates the YAML frontmatter in subsystem documentation.
    """

    status: SubsystemStatus
    chunks: list[ChunkRelationship] = []
    code_references: list[SymbolicReference] = []
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo subsystems


class NarrativeStatus(StrEnum):
    """Status values for narrative lifecycle."""

    DRAFTING = "DRAFTING"  # Narrative is being refined; chunks not yet created
    ACTIVE = "ACTIVE"  # Chunks are being created and implemented
    COMPLETED = "COMPLETED"  # All chunks created and narrative's ambition realized


VALID_NARRATIVE_TRANSITIONS: dict[NarrativeStatus, set[NarrativeStatus]] = {
    NarrativeStatus.DRAFTING: {NarrativeStatus.ACTIVE},
    NarrativeStatus.ACTIVE: {NarrativeStatus.COMPLETED},
    NarrativeStatus.COMPLETED: set(),  # Terminal state
}


class NarrativeFrontmatter(BaseModel):
    """Frontmatter schema for narrative OVERVIEW.md files.

    Validates the YAML frontmatter in narrative documentation.
    """

    status: NarrativeStatus
    advances_trunk_goal: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo narratives


class InvestigationFrontmatter(BaseModel):
    """Frontmatter schema for investigation OVERVIEW.md files.

    Validates the YAML frontmatter in investigation documentation.
    """

    status: InvestigationStatus
    trigger: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo investigations


# Subsystem: docs/subsystems/friction_tracking - Friction log management
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
    investigation: str | None = None
    subsystems: list[SubsystemRelationship] = []
    proposed_chunks: list[ProposedChunk] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo artifacts
    created_after: list[str] = []
    friction_entries: list["FrictionEntryReference"] = []
    bug_type: BugType | None = None


class FrictionTheme(BaseModel):
    """A friction theme/category in the frontmatter.

    Themes emerge organically as friction is logged. Agents see existing
    themes when appending and cluster new entries accordingly.
    """

    id: str  # Short identifier like "code-refs"
    name: str  # Human-readable name like "Code Reference Friction"

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate id is non-empty."""
        if not v or not v.strip():
            raise ValueError("id cannot be empty")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is non-empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v


class FrictionProposedChunk(BaseModel):
    """A proposed chunk that addresses friction entries.

    Similar to ProposedChunk but includes an addresses array linking to
    friction entry IDs for bidirectional traceability.
    """

    prompt: str
    chunk_directory: str | None = None  # Populated when chunk is created
    addresses: list[str] = []  # List of F-number IDs like ["F001", "F003"]

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is non-empty."""
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        return v


# Regex for validating friction entry ID format: F followed by digits
FRICTION_ENTRY_ID_PATTERN = re.compile(r"^F\d+$")


class ExternalFrictionSource(BaseModel):
    """Reference to friction entries in an external repository.

    Used in project FRICTION.md frontmatter to track friction entries that
    originated from external artifact repositories in task contexts.
    """

    repo: str  # External repo ref in org/repo format (e.g., "acme/ext")
    track: str = "main"  # Branch to track
    pinned: str  # Commit SHA when reference was created
    entry_ids: list[str] = []  # List of F-numbers in that repo this project cares about

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repo is in org/repo format."""
        return _require_valid_repo_ref(v, "repo")

    @field_validator("pinned")
    @classmethod
    def validate_pinned(cls, v: str) -> str:
        """Validate pinned is a 40-character hex SHA."""
        if not SHA_PATTERN.match(v):
            raise ValueError("pinned must be a 40-character lowercase hex SHA")
        return v

    @field_validator("entry_ids")
    @classmethod
    def validate_entry_ids(cls, v: list[str]) -> list[str]:
        """Validate entry_ids are valid friction entry IDs."""
        for entry_id in v:
            if not FRICTION_ENTRY_ID_PATTERN.match(entry_id):
                raise ValueError(
                    f"entry_id '{entry_id}' must match pattern F followed by digits (e.g., F001, F123)"
                )
        return v


class FrictionFrontmatter(BaseModel):
    """Frontmatter schema for FRICTION.md files.

    Validates the YAML frontmatter in friction log documentation.
    """

    themes: list[FrictionTheme] = []
    proposed_chunks: list[FrictionProposedChunk] = []
    external_friction_sources: list[ExternalFrictionSource] = []


class FrictionEntryReference(BaseModel):
    """Reference to a friction entry that a chunk addresses.

    Used in chunk frontmatter to link chunks to the friction entries they resolve.
    Provides "why did we do this work?" traceability from implementation back to
    accumulated pain points.
    """

    entry_id: str  # e.g., "F001"
    scope: Literal["full", "partial"] = "full"

    @field_validator("entry_id")
    @classmethod
    def validate_entry_id(cls, v: str) -> str:
        """Validate entry_id matches the friction entry ID pattern (F followed by digits)."""
        if not v:
            raise ValueError("entry_id cannot be empty")
        if not FRICTION_ENTRY_ID_PATTERN.match(v):
            raise ValueError(
                "entry_id must match pattern F followed by digits (e.g., F001, F123)"
            )
        return v


# Scratchpad storage models
# Subsystem: docs/subsystems/workflow_artifacts - User-global scratchpad storage variant
# Chunk: docs/chunks/scratchpad_storage - Foundation for scratchpad infrastructure


class ScratchpadChunkStatus(StrEnum):
    """Status values for scratchpad chunk lifecycle.

    Scratchpad chunks have a simpler lifecycle than in-repo chunks:
    - No FUTURE status (scratchpad work is personal, not queued)
    - No SUPERSEDED status (no code reference tracking)
    """

    IMPLEMENTING = "IMPLEMENTING"  # Currently working on
    ACTIVE = "ACTIVE"  # Work completed but entry retained
    ARCHIVED = "ARCHIVED"  # Moved to archive, kept for reference


class ScratchpadChunkFrontmatter(BaseModel):
    """Frontmatter schema for scratchpad chunk GOAL.md files.

    Simpler than in-repo chunks - no code_references, subsystems, etc.
    Designed for personal work notes outside git repositories.
    """

    status: ScratchpadChunkStatus
    ticket: str | None = None  # Optional Linear/Jira ticket reference
    success_criteria: list[str] = []  # Goals for this work
    created_at: str  # ISO timestamp


class ScratchpadNarrativeStatus(StrEnum):
    """Status values for scratchpad narrative lifecycle."""

    DRAFTING = "DRAFTING"  # Planning multi-chunk work
    ACTIVE = "ACTIVE"  # Chunks being worked on
    ARCHIVED = "ARCHIVED"  # Moved to archive


class ScratchpadNarrativeFrontmatter(BaseModel):
    """Frontmatter schema for scratchpad narrative OVERVIEW.md files.

    Simpler than in-repo narratives - designed for personal planning.
    """

    status: ScratchpadNarrativeStatus
    ambition: str | None = None  # High-level goal
    chunk_prompts: list[str] = []  # Planned work items
    created_at: str  # ISO timestamp
