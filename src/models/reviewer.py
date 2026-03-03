"""Reviewer agent domain models for trusted review lifecycle."""
# Chunk: docs/chunks/models_subpackage - Reviewer module

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator


# Chunk: docs/chunks/reviewer_infrastructure - Reviewer agent trust level and metadata models
class TrustLevel(StrEnum):
    """Trust levels for reviewer agents.

    Trust levels determine what actions a reviewer can take autonomously:
    - OBSERVATION: Reviewer can only observe and report; all decisions go to operator
    - CALIBRATION: Reviewer can suggest decisions; operator reviews and calibrates
    - DELEGATION: Reviewer can auto-decide for delegated categories; escalate others
    - FULL: Reviewer can auto-decide all categories; escalate only when uncertain
    """

    OBSERVATION = "observation"
    CALIBRATION = "calibration"
    DELEGATION = "delegation"
    FULL = "full"


class LoopDetectionConfig(BaseModel):
    """Loop detection settings for reviewer.

    Controls when a reviewer escalates due to suspected review loops:
    - max_iterations: Maximum review rounds before escalating
    - escalation_threshold: Consecutive feedbacks before escalating
    - same_issue_threshold: Repeated same issues before escalating
    """

    max_iterations: int = 3
    escalation_threshold: int = 2
    same_issue_threshold: int = 2

    @field_validator("max_iterations", "escalation_threshold", "same_issue_threshold")
    @classmethod
    def validate_positive(cls, v: int, info) -> int:
        """Validate that thresholds are at least 1."""
        if v < 1:
            raise ValueError(f"{info.field_name} must be at least 1")
        return v


class ReviewerStats(BaseModel):
    """Review statistics for a reviewer.

    Tracks cumulative review activity for trust calibration and analysis.
    """

    reviews_completed: int = 0
    approvals: int = 0
    feedbacks: int = 0
    escalations: int = 0
    examples_marked_good: int = 0
    examples_marked_bad: int = 0

    @field_validator(
        "reviews_completed",
        "approvals",
        "feedbacks",
        "escalations",
        "examples_marked_good",
        "examples_marked_bad",
    )
    @classmethod
    def validate_non_negative(cls, v: int, info) -> int:
        """Validate that statistics cannot be negative."""
        if v < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return v


class ReviewerMetadata(BaseModel):
    """Frontmatter schema for reviewer METADATA.yaml files.

    Validates the configuration of persistent reviewer entities that act as
    "trusted lieutenants" for reviewing chunk implementations.
    """

    name: str
    description: str | None = None
    trust_level: TrustLevel = TrustLevel.OBSERVATION
    domain_scope: list[str] = []  # Glob patterns, empty = all domains
    delegated_categories: list[str] = []
    loop_detection: LoopDetectionConfig = LoopDetectionConfig()
    forked_from: str | None = None
    forked_at: str | None = None  # ISO date string
    created_at: str | None = None  # ISO date string
    stats: ReviewerStats = ReviewerStats()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty."""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v


# Chunk: docs/chunks/reviewer_decision_schema - Per-file decision schema
class ReviewerDecision(StrEnum):
    """Decision outcomes for reviewer decision files.

    Each per-file decision record captures the reviewer's assessment:
    - APPROVE: Implementation meets documented intent; proceed to completion
    - FEEDBACK: Issues found that need addressing; implementor should fix and re-review
    - ESCALATE: Cannot decide; ambiguity requires operator intervention
    """

    APPROVE = "APPROVE"
    FEEDBACK = "FEEDBACK"
    ESCALATE = "ESCALATE"


# Chunk: docs/chunks/reviewer_decision_schema - Per-file decision schema
class FeedbackReview(BaseModel):
    """Structured feedback variant for operator review.

    Used when the operator wants to provide a detailed message rather than
    just marking the decision as "good" or "bad".
    """

    feedback: str

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        """Validate that feedback is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("feedback cannot be empty")
        return v


# Chunk: docs/chunks/reviewer_decision_schema - Per-file decision schema
class DecisionFrontmatter(BaseModel):
    """Frontmatter schema for per-file reviewer decision files.

    Located at: docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md

    All fields are nullable to support template instantiation where the
    reviewer fills in values after creation.
    """

    decision: ReviewerDecision | None = None
    summary: str | None = None
    operator_review: Literal["good", "bad"] | FeedbackReview | None = None
