"""Pydantic models for workflow artifact validation.

Re-exports all public names from domain-specific modules for backward compatibility.
Existing `from models import X` statements continue to work via these re-exports.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/models_subpackage - Package re-exports

# Shared utilities
from models.shared import (
    SHA_PATTERN,
    TaskConfig,
    extract_short_name,
)

# Reference types used across multiple artifacts
from models.references import (
    ARTIFACT_ID_PATTERN,
    CHUNK_ID_PATTERN,
    ArtifactRelationship,
    ArtifactType,
    ChunkRelationship,
    CodeRange,
    CodeReference,
    ComplianceLevel,
    ExternalArtifactRef,
    ProposedChunk,
    SubsystemRelationship,
    SymbolicReference,
)

# Subsystem domain
from models.subsystem import (
    VALID_STATUS_TRANSITIONS,
    SubsystemFrontmatter,
    SubsystemStatus,
)

# Investigation domain
from models.investigation import (
    VALID_INVESTIGATION_TRANSITIONS,
    InvestigationFrontmatter,
    InvestigationStatus,
)

# Narrative domain
from models.narrative import (
    VALID_NARRATIVE_TRANSITIONS,
    NarrativeFrontmatter,
    NarrativeStatus,
)

# Friction domain
from models.friction import (
    FRICTION_ENTRY_ID_PATTERN,
    ExternalFrictionSource,
    FrictionEntryReference,
    FrictionFrontmatter,
    FrictionProposedChunk,
    FrictionTheme,
)

# Reviewer domain
from models.reviewer import (
    DecisionFrontmatter,
    FeedbackReview,
    LoopDetectionConfig,
    ReviewerDecision,
    ReviewerMetadata,
    ReviewerStats,
    TrustLevel,
)

# Chunk domain
from models.chunk import (
    VALID_CHUNK_TRANSITIONS,
    BugType,
    ChunkDependent,
    ChunkFrontmatter,
    ChunkStatus,
    parse_status_filters,
)

__all__ = [
    # Shared utilities
    "extract_short_name",
    "SHA_PATTERN",
    "TaskConfig",
    # Reference types
    "ArtifactRelationship",
    "ArtifactType",
    "ARTIFACT_ID_PATTERN",
    "CHUNK_ID_PATTERN",
    "ChunkRelationship",
    "SubsystemRelationship",
    "ComplianceLevel",
    "SymbolicReference",
    "CodeRange",
    "CodeReference",
    "ExternalArtifactRef",
    "ProposedChunk",
    # Subsystem domain
    "SubsystemStatus",
    "VALID_STATUS_TRANSITIONS",
    "SubsystemFrontmatter",
    # Investigation domain
    "InvestigationStatus",
    "VALID_INVESTIGATION_TRANSITIONS",
    "InvestigationFrontmatter",
    # Narrative domain
    "NarrativeStatus",
    "VALID_NARRATIVE_TRANSITIONS",
    "NarrativeFrontmatter",
    # Friction domain
    "FrictionTheme",
    "FrictionProposedChunk",
    "FRICTION_ENTRY_ID_PATTERN",
    "ExternalFrictionSource",
    "FrictionFrontmatter",
    "FrictionEntryReference",
    # Reviewer domain
    "TrustLevel",
    "LoopDetectionConfig",
    "ReviewerStats",
    "ReviewerMetadata",
    "ReviewerDecision",
    "FeedbackReview",
    "DecisionFrontmatter",
    # Chunk domain
    "ChunkStatus",
    "BugType",
    "VALID_CHUNK_TRANSITIONS",
    "ChunkDependent",
    "ChunkFrontmatter",
    "parse_status_filters",
]
