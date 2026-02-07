"""Subsystem domain models for documentation lifecycle."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Subsystem module

from enum import StrEnum

from pydantic import BaseModel

from models.references import (
    ChunkRelationship,
    ExternalArtifactRef,
    ProposedChunk,
    SymbolicReference,
)


# Chunk: docs/chunks/subsystem_schemas_and_model - Subsystem status enum for documentation lifecycle
class SubsystemStatus(StrEnum):
    """Status values for subsystem documentation lifecycle."""

    DISCOVERING = "DISCOVERING"
    DOCUMENTED = "DOCUMENTED"
    REFACTORING = "REFACTORING"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"


# Chunk: docs/chunks/subsystem_status_transitions - State machine rules for status transitions
VALID_STATUS_TRANSITIONS: dict[SubsystemStatus, set[SubsystemStatus]] = {
    SubsystemStatus.DISCOVERING: {SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.DOCUMENTED: {SubsystemStatus.REFACTORING, SubsystemStatus.DEPRECATED},
    SubsystemStatus.REFACTORING: {SubsystemStatus.STABLE, SubsystemStatus.DOCUMENTED, SubsystemStatus.DEPRECATED},
    SubsystemStatus.STABLE: {SubsystemStatus.DEPRECATED, SubsystemStatus.REFACTORING},
    SubsystemStatus.DEPRECATED: set(),  # Terminal state
}


# Chunk: docs/chunks/subsystem_schemas_and_model - Frontmatter schema for subsystem OVERVIEW.md
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
