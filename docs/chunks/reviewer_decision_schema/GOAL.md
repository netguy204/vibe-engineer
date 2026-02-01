---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- tests/test_models.py
- docs/reviewers/baseline/decisions/.gitkeep
code_references:
  - ref: src/models.py#ReviewerDecision
    implements: "StrEnum for decision outcomes (APPROVE/FEEDBACK/ESCALATE)"
  - ref: src/models.py#FeedbackReview
    implements: "Pydantic model for structured feedback variant of operator review"
  - ref: src/models.py#DecisionFrontmatter
    implements: "Pydantic model for per-file decision frontmatter with union-typed operator_review"
  - ref: tests/test_models.py#TestReviewerDecision
    implements: "Tests for ReviewerDecision enum"
  - ref: tests/test_models.py#TestFeedbackReview
    implements: "Tests for FeedbackReview validation (empty/whitespace rejection)"
  - ref: tests/test_models.py#TestDecisionFrontmatter
    implements: "Tests for DecisionFrontmatter validation (union type discrimination)"
  - ref: tests/test_models.py#TestDecisionFrontmatterIntegration
    implements: "Integration test parsing prototype decision template"
narrative: null
investigation: reviewer_log_concurrency
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- reviewer_init_templates
- integrity_bidirectional
- integrity_code_backrefs
- integrity_fix_existing
- integrity_proposed_chunks
- integrity_validate
- orch_reviewer_decision_mcp
---

# Chunk Goal

## Minor Goal

Create pydantic models and directory structure for per-file reviewer decisions. This enables concurrent chunk reviews without merge conflicts by giving each decision its own file.

## Success Criteria

- Pydantic model for decision file frontmatter exists with fields: decision (APPROVE/FEEDBACK/ESCALATE), summary (str), operator_review (union type)
- The operator_review field is typed as `Union[Literal["good", "bad"], FeedbackReview]` where FeedbackReview has a `feedback: str` field
- Directory `docs/reviewers/baseline/decisions/` exists
- Schema validation integrated into reviewer subsystem
- See `docs/investigations/reviewer_log_concurrency/prototypes/decision_template.md` for reference