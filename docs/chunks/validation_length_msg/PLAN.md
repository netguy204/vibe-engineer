<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a straightforward clarity improvement to the `validate_identifier()` function in `src/validation.py`. The current implementation uses an equivalent but confusing expression (`len(value) >= max_length + 1`) with an equally confusing error message ("must be less than {max_length + 1} characters").

The fix is purely cosmetic:
1. Simplify the condition to the idiomatic form: `len(value) > max_length`
2. Clarify the error message to: "must be at most {max_length} characters"

Both expressions are logically equivalent, but the new form is immediately understandable. When `max_length=31`, the old message said "must be less than 32 characters" but the new message will say "must be at most 31 characters" — which directly communicates the limit.

Per docs/trunk/TESTING_PHILOSOPHY.md, we should write failing tests first. However, there are currently no dedicated tests for the `validate_identifier()` function, and the success criteria state "All existing tests continue to pass with the updated message." Since no existing tests assert the specific error message text, we need to:
1. Add a test that verifies the new error message format
2. Make the implementation change
3. Verify all existing tests pass

## Subsystem Considerations

The file `src/validation.py` has an existing subsystem backreference comment:
```python
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
```

This chunk modifies code within that subsystem's scope but is a trivial clarity fix that doesn't affect the subsystem's patterns or invariants. No subsystem documentation updates are needed.

## Sequence

### Step 1: Add a test for the length validation error message

Create a new test in `tests/test_validation.py` that verifies the `validate_identifier()` function returns the expected error message format when the length exceeds the maximum.

The test should:
- Call `validate_identifier("a" * 32, "test_field", max_length=31)`
- Assert the returned error list contains exactly one error
- Assert the error message says "must be at most 31 characters (got 32)"

Location: `tests/test_validation.py` (new file)

### Step 2: Simplify the length condition

Change line 27 in `src/validation.py` from:
```python
if max_length is not None and len(value) >= max_length + 1:
```
to:
```python
if max_length is not None and len(value) > max_length:
```

Location: `src/validation.py`

### Step 3: Update the error message

Change lines 28-31 in `src/validation.py` from:
```python
errors.append(
    f"{field_name} must be less than {max_length + 1} characters "
    f"(got {len(value)})"
)
```
to:
```python
errors.append(
    f"{field_name} must be at most {max_length} characters "
    f"(got {len(value)})"
)
```

Location: `src/validation.py`

### Step 4: Run all tests to verify no regressions

Run `uv run pytest tests/` to ensure:
- The new test passes with the updated message format
- All existing tests continue to pass

---

**BACKREFERENCE COMMENTS**

This is a small clarification fix that doesn't warrant a chunk backreference comment. The existing subsystem backreference in `src/validation.py` is sufficient.

## Dependencies

None. This chunk has no dependencies on other chunks or external infrastructure.

## Risks and Open Questions

**Low risk**: The `validation_chunk_name` chunk's GOAL.md references the old message format in its example: "must be less than 32 characters (got 35)". This is documentation showing expected behavior, not code that needs updating. If the example becomes confusing after this change, it can be updated in a separate chunk, but it's not blocking.

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