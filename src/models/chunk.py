"""Chunk domain models for implementation lifecycle."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Chunk module

from enum import StrEnum

from pydantic import BaseModel

from models.friction import FrictionEntryReference
from models.references import (
    ExternalArtifactRef,
    ProposedChunk,
    SubsystemRelationship,
    SymbolicReference,
)


# Chunk: docs/chunks/chunk_frontmatter_model - Chunk lifecycle status StrEnum
# Chunk: docs/chunks/intent_principles - COMPOSITE status added; see docs/trunk/CHUNKS.md
class ChunkStatus(StrEnum):
    """Status values for chunk lifecycle.

    Status answers a single question: how much of the intent does this chunk
    own? See docs/trunk/CHUNKS.md for the full principle.
    """

    FUTURE = "FUTURE"  # Not yet owned. Queued for later.
    IMPLEMENTING = "IMPLEMENTING"  # Being taken into ownership. At most one per worktree.
    ACTIVE = "ACTIVE"  # Fully owns the intent that governs the code.
    COMPOSITE = "COMPOSITE"  # Shares ownership with other chunks. Read alongside its co-owners.
    SUPERSEDED = "SUPERSEDED"  # Legacy; being retired by intent_ownership narrative.
    HISTORICAL = "HISTORICAL"  # No longer owns intent. Kept for archaeological context.


# Chunk: docs/chunks/bug_type_field - BugType enum with SEMANTIC and IMPLEMENTATION values
class BugType(StrEnum):
    """Classification of bug fix chunks to guide completion behavior.

    When a chunk is a bug fix, this field distinguishes between:
    - semantic: The bug revealed new understanding of intended behavior (discovery)
    - implementation: The bug corrected known-wrong code (we knew how it should work)
    """

    SEMANTIC = "semantic"  # Bug revealed new understanding; code backreferences required
    IMPLEMENTATION = "implementation"  # Bug corrected known-wrong code; backreferences optional


# Chunk: docs/chunks/intent_principles - COMPOSITE transitions added; see docs/trunk/CHUNKS.md
VALID_CHUNK_TRANSITIONS: dict[ChunkStatus, set[ChunkStatus]] = {
    ChunkStatus.FUTURE: {ChunkStatus.IMPLEMENTING, ChunkStatus.HISTORICAL},
    ChunkStatus.IMPLEMENTING: {ChunkStatus.ACTIVE, ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL},
    ChunkStatus.ACTIVE: {ChunkStatus.SUPERSEDED, ChunkStatus.COMPOSITE, ChunkStatus.HISTORICAL},
    ChunkStatus.COMPOSITE: {ChunkStatus.ACTIVE, ChunkStatus.HISTORICAL},
    ChunkStatus.SUPERSEDED: {ChunkStatus.HISTORICAL},
    ChunkStatus.HISTORICAL: set(),  # Terminal state
}


# Chunk: docs/chunks/chunk_create_task_aware - Model for chunk GOAL.md frontmatter with dependents
# Chunk: docs/chunks/consolidate_ext_refs - Updated to use ExternalArtifactRef for cross-repo references
class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalArtifactRef] = []


# Chunk: docs/chunks/chunk_frontmatter_model - Pydantic model for chunk GOAL.md frontmatter validation
# Chunk: docs/chunks/bug_type_field - bug_type field added to ChunkFrontmatter model
# Chunk: docs/chunks/investigation_chunk_refs - Optional investigation field in chunk frontmatter schema
# Chunk: docs/chunks/friction_chunk_linking - Added friction_entries field to chunk frontmatter schema
# Chunk: docs/chunks/consolidate_ext_refs - Updated dependents field to use ExternalArtifactRef
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
    friction_entries: list[FrictionEntryReference] = []
    bug_type: BugType | None = None
    depends_on: list[str] | None = None


# Chunk: docs/chunks/cli_decompose - Extract pure parsing logic from CLI layer
def parse_status_filters(
    status_strings: tuple[str, ...],
    future_flag: bool = False,
    active_flag: bool = False,
    implementing_flag: bool = False,
) -> tuple[set[ChunkStatus] | None, str | None]:
    """Parse and validate status filters from CLI options.

    This function is pure parsing logic with no CLI dependencies. It validates
    status strings and returns either a set of statuses to filter by or an error.

    Args:
        status_strings: Tuple of status strings (may include comma-separated)
        future_flag: Whether --future flag was set
        active_flag: Whether --active flag was set
        implementing_flag: Whether --implementing flag was set

    Returns:
        Tuple of (status_set, error_message). status_set is None if no filtering
        requested, or a set of ChunkStatus values. error_message is None on
        success, or contains the error message with valid options listed.
    """
    statuses: set[ChunkStatus] = set()

    # Add statuses from convenience flags
    if future_flag:
        statuses.add(ChunkStatus.FUTURE)
    if active_flag:
        statuses.add(ChunkStatus.ACTIVE)
    if implementing_flag:
        statuses.add(ChunkStatus.IMPLEMENTING)

    # Parse statuses from option (handles comma-separated and multiple options)
    for status_str in status_strings:
        # Split by comma to handle "FUTURE,ACTIVE"
        parts = [s.strip() for s in status_str.split(",") if s.strip()]
        for part in parts:
            # Case-insensitive lookup
            upper_part = part.upper()
            try:
                statuses.add(ChunkStatus(upper_part))
            except ValueError:
                valid_statuses = ", ".join(s.value for s in ChunkStatus)
                return None, f"Invalid status '{part}'. Valid statuses: {valid_statuses}"

    # Return None if no filtering requested (empty set means show all)
    if not statuses:
        return None, None

    return statuses, None
