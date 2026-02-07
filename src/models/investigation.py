"""Investigation domain models for exploration lifecycle."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/models_subpackage - Investigation module

from enum import StrEnum

from pydantic import BaseModel

from models.references import ExternalArtifactRef, ProposedChunk


# Chunk: docs/chunks/investigation_commands - InvestigationStatus enum with lifecycle values
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


# Chunk: docs/chunks/investigation_commands - InvestigationFrontmatter model for validation
# Chunk: docs/chunks/task_aware_investigations - Investigation frontmatter with dependents field
class InvestigationFrontmatter(BaseModel):
    """Frontmatter schema for investigation OVERVIEW.md files.

    Validates the YAML frontmatter in investigation documentation.
    """

    status: InvestigationStatus
    trigger: str | None = None
    proposed_chunks: list[ProposedChunk] = []
    created_after: list[str] = []
    dependents: list[ExternalArtifactRef] = []  # For cross-repo investigations
