"""Narrative domain models for multi-chunk initiative lifecycle."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Narrative module

from enum import StrEnum

from pydantic import BaseModel

from models.references import ExternalArtifactRef, ProposedChunk


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
