<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk establishes the reviewer infrastructure by:

1. **Creating the docs/reviewers/ directory structure** with the baseline reviewer, copying files from the investigation prototype at `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/`.

2. **Adding a Pydantic model** to `src/models.py` for validating reviewer METADATA.yaml files. This follows the established pattern of centralized Pydantic models in models.py (see existing models like `ChunkFrontmatter`, `SubsystemFrontmatter`, etc.).

3. **Writing unit tests** in `tests/test_models.py` that verify schema validation, following the testing philosophy of testing meaningful behavior (validation rejection of invalid configs) rather than trivial assignments.

The approach aligns with:
- **DEC-004**: All references in documentation are relative to project root
- Existing patterns in `src/models.py` for artifact frontmatter validation

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts**: This chunk USES the workflow_artifacts subsystem patterns for Pydantic model definitions. The `ReviewerMetadata` model will follow the same patterns as `ChunkFrontmatter`, `SubsystemFrontmatter`, etc.

No deviations discovered—adding a new model following existing patterns.

## Sequence

### Step 1: Define the ReviewerMetadata Pydantic model

Add Pydantic models to `src/models.py` for validating reviewer METADATA.yaml files:

```python
class TrustLevel(StrEnum):
    """Trust levels for reviewer agents."""
    OBSERVATION = "observation"
    CALIBRATION = "calibration"
    DELEGATION = "delegation"
    FULL = "full"

class LoopDetectionConfig(BaseModel):
    """Loop detection settings for reviewer."""
    max_iterations: int = 3
    escalation_threshold: int = 2
    same_issue_threshold: int = 2

    @field_validator("max_iterations", "escalation_threshold", "same_issue_threshold")
    @classmethod
    def validate_positive(cls, v: int, info) -> int:
        if v < 1:
            raise ValueError(f"{info.field_name} must be at least 1")
        return v

class ReviewerStats(BaseModel):
    """Review statistics for a reviewer."""
    reviews_completed: int = 0
    approvals: int = 0
    feedbacks: int = 0
    escalations: int = 0
    examples_marked_good: int = 0
    examples_marked_bad: int = 0

    @field_validator("reviews_completed", "approvals", "feedbacks", "escalations",
                     "examples_marked_good", "examples_marked_bad")
    @classmethod
    def validate_non_negative(cls, v: int, info) -> int:
        if v < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return v

class ReviewerMetadata(BaseModel):
    """Frontmatter schema for reviewer METADATA.yaml files."""
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
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v
```

Location: `src/models.py`

### Step 2: Write unit tests for ReviewerMetadata model

Add tests to `tests/test_models.py` that verify meaningful behavior:

**Tests to write:**
- `test_reviewer_metadata_rejects_empty_name` - Name validation
- `test_reviewer_metadata_rejects_invalid_trust_level` - Enum validation
- `test_reviewer_metadata_rejects_negative_stats` - Stats bounds checking
- `test_reviewer_metadata_rejects_zero_loop_detection` - Loop detection bounds
- `test_reviewer_metadata_valid_minimal` - Minimal valid config parses
- `test_reviewer_metadata_valid_full` - Full config with all fields parses

Following TESTING_PHILOSOPHY.md: These test validation behavior (rejection of invalid inputs), not trivial storage.

Location: `tests/test_models.py`

### Step 3: Create docs/reviewers/baseline/ directory structure

Create the directory structure with three files copied from the investigation prototype:

1. `docs/reviewers/baseline/METADATA.yaml` - Copy from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/METADATA.yaml`
2. `docs/reviewers/baseline/PROMPT.md` - Copy from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/PROMPT.md`
3. `docs/reviewers/baseline/DECISION_LOG.md` - Copy from `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/DECISION_LOG.md`

The DECISION_LOG.md already contains a header comment explaining the expected entry format.

### Step 4: Verify prototype files parse with the model

After copying, verify that:
- `docs/reviewers/baseline/METADATA.yaml` parses successfully with the new `ReviewerMetadata` model
- All field values match the prototype's intended defaults

This can be done as a manual check or added to an integration test.

### Step 5: Run tests and verify

Run `uv run pytest tests/test_models.py` to ensure:
- All new tests pass
- Existing tests still pass
- No regressions introduced

---

**BACKREFERENCE COMMENTS**

Add chunk backreference to the new model classes in `src/models.py`:

```python
# Chunk: docs/chunks/reviewer_infrastructure - Reviewer entity model
class TrustLevel(StrEnum):
    ...
```

## Dependencies

- **Prototype files exist**: The prototype reviewer files at `docs/investigations/orchestrator_quality_assurance/prototypes/reviewers/baseline/` already exist and contain the content to be copied.
- **Pydantic already in use**: The project already uses Pydantic for model validation (see existing imports in `src/models.py`).

## Risks and Open Questions

1. **Date field format**: The prototype uses `created_at: 2026-01-13` (ISO date). We're storing this as a string rather than validating as a proper date object—simple approach, but means invalid dates could slip through. Acceptable for MVP; can tighten later.

2. **Reviewer discovery**: This chunk creates the directory structure but doesn't add a `ve reviewer list` command or similar. Discovery will be manual initially. Future chunks may add CLI support.

3. **METADATA.yaml vs frontmatter**: Unlike other artifacts (chunks, narratives) that use YAML frontmatter in markdown files, reviewers use a standalone METADATA.yaml file. This is intentional per the investigation design—reviewers are config-first, not prose-first.

## Deviations

- **Step 3: Date field format in METADATA.yaml**: The prototype METADATA.yaml had `created_at: 2026-01-13` (unquoted), which YAML parses as a `datetime.date` object. The Pydantic model expects a string per the plan. Changed to quoted format `created_at: "2026-01-13"` so YAML parses it as a string. This is a minor adjustment—the file format is slightly different from the prototype, but this ensures the METADATA.yaml file validates correctly with the model.