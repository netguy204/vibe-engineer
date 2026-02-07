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
class ChunkStatus(StrEnum):
    """Status values for chunk lifecycle."""

    FUTURE = "FUTURE"  # Queued for future work, not yet being implemented
    IMPLEMENTING = "IMPLEMENTING"  # Currently being implemented
    ACTIVE = "ACTIVE"  # Accurately describes current or recently-merged work
    SUPERSEDED = "SUPERSEDED"  # Another chunk has modified the code this chunk governed
    HISTORICAL = "HISTORICAL"  # Significant drift; kept for archaeology only


# Chunk: docs/chunks/bug_type_field - BugType enum with SEMANTIC and IMPLEMENTATION values
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


# Chunk: docs/chunks/chunk_create_task_aware - Model for chunk GOAL.md frontmatter with dependents
class ChunkDependent(BaseModel):
    """Frontmatter schema for chunk GOAL.md files with dependents."""

    dependents: list[ExternalArtifactRef] = []


# Chunk: docs/chunks/chunk_frontmatter_model - Pydantic model for chunk GOAL.md frontmatter validation
# Chunk: docs/chunks/bug_type_field - bug_type field added to ChunkFrontmatter model
# Chunk: docs/chunks/investigation_chunk_refs - Optional investigation field in chunk frontmatter schema
# Chunk: docs/chunks/friction_chunk_linking - Added friction_entries field to chunk frontmatter schema
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
