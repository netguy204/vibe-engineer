

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Fix at the model layer: add a Pydantic `field_validator` on
`MemoryFrontmatter.last_reinforced` that normalizes naive datetimes to
UTC-aware on construction. This ensures every caller — `entity_shutdown.py`,
`entity_decay.py`, and any future consumer — always gets timezone-aware
datetimes without per-call guards.

`entity_decay.py` already has a per-call guard (`_days_since_reinforced`), but
it doesn't cover the `surviving_tier2.sort(key=lambda m: m[0].last_reinforced)`
comparison on line 172, which can also fail when mixing naive and aware
datetimes. Fixing at the model layer covers all sites.

The model-layer fix is the canonical pattern here: constrain the type more
strictly so invariants don't need to be re-asserted throughout the codebase.

Per `docs/trunk/TESTING_PHILOSOPHY.md`, tests are written first (TDD): write
the failing tests, then write the fix, then verify the tests pass.

## Sequence

### Step 1: Write failing tests

Add two tests to `tests/test_entity_shutdown.py`:

**Test A — model-level validator:**
- Construct `MemoryFrontmatter` with a naive `last_reinforced` datetime (no
  `tzinfo`).
- Assert that after construction `fm.last_reinforced.tzinfo` is not None (i.e.,
  the validator normalized it to UTC).
- This test verifies the validator's behavior directly.

**Test B — full pipeline regression:**
- Create a temp entity directory with existing consolidated memory files whose
  YAML frontmatter contains naive ISO 8601 timestamps (e.g.,
  `last_reinforced: "2026-01-01T10:00:00"`).
- Also create a core memory file with a UTC-aware timestamp to confirm mixed
  naive/aware handling works.
- Mock the Anthropic API client (`anthropic.Anthropic`) to return a valid
  consolidation response that includes both consolidated and core memories.
- Call `run_consolidation(entity_name, extracted_json, project_dir)`.
- Assert it returns the summary dict without raising `TypeError`.

Both tests should **fail** before Step 2 because Pydantic parses
`"2026-01-01T10:00:00"` as a naive datetime and no normalization is applied.

### Step 2: Add Pydantic validator to `MemoryFrontmatter`

In `src/models/entity.py`:

1. Add `timezone` to the `datetime` import: `from datetime import datetime, timezone`
2. Add a `field_validator` on `last_reinforced` to the `MemoryFrontmatter` class:

```python
# Chunk: docs/chunks/shutdown_tz_normalization - Normalize naive datetimes to UTC
@field_validator("last_reinforced", mode="after")
@classmethod
def normalize_last_reinforced_tz(cls, v: datetime) -> datetime:
    """Ensure last_reinforced is always timezone-aware (UTC).

    Memory files written by older code versions may omit timezone info.
    Normalizing here prevents TypeError when subtracting or comparing
    naive and aware datetimes during decay and consolidation.
    """
    if v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v
```

The `mode="after"` validator runs after Pydantic's built-in datetime parsing,
so it receives a `datetime` object regardless of whether the input was a string
or already a datetime.

### Step 3: Run tests and verify

Run `uv run pytest tests/test_entity_shutdown.py -x` and confirm:
- Test A (model-level) passes: validator normalizes naive datetimes.
- Test B (pipeline regression) passes: `run_consolidation` no longer crashes.
- All pre-existing entity shutdown tests still pass.

### Step 4: Run the full test suite

Run `uv run pytest tests/` and confirm all tests pass.

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
-->