<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the foundational schema layer for the per-file reviewer decision system. The design follows the investigation findings in `docs/investigations/reviewer_log_concurrency/OVERVIEW.md`, which established:

1. Per-file decisions at `docs/reviewers/{reviewer}/decisions/{chunk}_{iteration}.md`
2. Union-typed operator review field: `Union[Literal["good", "bad"], FeedbackReview]`
3. Structured frontmatter with decision, summary, and operator_review fields

The implementation follows existing patterns in `src/models.py` for pydantic model definitions, particularly the pattern used by `ReviewerMetadata` and related reviewer models added in the `reviewer_infrastructure` chunk.

**Strategy:**
- Add new pydantic models to `src/models.py` alongside existing reviewer models (TrustLevel, ReviewerMetadata, etc.)
- Create the decisions directory structure under baseline reviewer
- Write tests following TESTING_PHILOSOPHY.md - focusing on validation behavior (rejection of invalid inputs) rather than trivial storage assertions

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk IMPLEMENTS new reviewer decision models following the existing workflow artifact patterns. The models follow the established conventions in `src/models.py` for StrEnum-based status types, frontmatter models, and field validation.

## Sequence

### Step 1: Define the ReviewerDecision enum

Create a StrEnum representing valid decision outcomes for a reviewer decision file.

Location: `src/models.py`

Values:
- `APPROVE` - Implementation meets documented intent
- `FEEDBACK` - Issues found that need addressing
- `ESCALATE` - Cannot decide, requires operator intervention

This mirrors the existing `ReviewDecision` enum in `src/orchestrator/models.py` but is for decision file frontmatter rather than orchestrator routing.

### Step 2: Define the FeedbackReview model

Create a pydantic model for the structured feedback variant of operator review.

Location: `src/models.py`

Fields:
- `feedback: str` - The operator's feedback message (required, non-empty)

Validation:
- Reject empty or whitespace-only feedback

### Step 3: Define the DecisionFrontmatter model

Create the main pydantic model for decision file frontmatter.

Location: `src/models.py`

Fields:
- `decision: ReviewerDecision | None` - The reviewer's decision (nullable for templates)
- `summary: str | None` - One-sentence rationale (nullable for templates)
- `operator_review: Union[Literal["good", "bad"], FeedbackReview] | None` - Operator's review (nullable until reviewed)

Validation:
- Accept `None` for all fields (decision files start as templates)
- When `decision` is provided, validate it's a valid `ReviewerDecision`
- When `operator_review` is provided:
  - Accept string literals `"good"` or `"bad"`
  - Accept dict/object with `feedback` field (parsed as `FeedbackReview`)

### Step 4: Write tests for DecisionFrontmatter validation

Location: `tests/test_models.py`

Test cases:
- Empty frontmatter (all None) parses successfully
- Valid decision values accepted
- Invalid decision values rejected
- `operator_review: good` and `operator_review: bad` accepted
- `operator_review: {feedback: "message"}` accepted
- `operator_review: {feedback: ""}` rejected (empty feedback)
- Invalid `operator_review` types rejected

### Step 5: Create the decisions directory

Create the directory structure for per-file decisions.

Location: `docs/reviewers/baseline/decisions/`

Add a `.gitkeep` file to ensure the empty directory is tracked in git.

### Step 6: Add integration test for decision template parsing

Add a test that validates the prototype decision template from the investigation can be parsed by the model.

Location: `tests/test_models.py`

Test:
- Parse the YAML frontmatter from `docs/investigations/reviewer_log_concurrency/prototypes/decision_template.md`
- Verify it parses successfully as `DecisionFrontmatter`
- Verify all fields default to None (as expected for a template)

---

**BACKREFERENCE COMMENTS**

When implementing, add chunk backreferences to new models:
```python
# Chunk: docs/chunks/reviewer_decision_schema - Per-file decision schema
```

## Dependencies

- **reviewer_infrastructure**: The reviewer metadata models (`TrustLevel`, `ReviewerMetadata`, etc.) must exist in `src/models.py` - these are already present.
- **pydantic**: Already a project dependency for model validation.

## Risks and Open Questions

- **Union type discrimination**: Pydantic should handle the `Union[Literal["good", "bad"], FeedbackReview]` type naturally, discriminating by whether the value is a string or dict. Verify this works correctly in tests.
- **Nullable fields for templates**: Decision files start as templates with all null values. Ensure the model accepts this state without requiring a separate "template" model.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->