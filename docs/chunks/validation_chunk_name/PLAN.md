<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk fixes two related bugs:

1. **Chunk name length validation at creation time**: The `validate_short_name` function in `src/ve.py` already enforces the 31-character limit. However, when a ticket_id is provided, the final directory name becomes `{short_name}-{ticket_id}`, which can exceed 31 characters even when both parts individually pass validation. We need to validate the **combined** name length at creation time.

2. **Frontmatter parsing error surfacing**: When `ChunkFrontmatter` validation fails (e.g., due to the 31-character limit on `artifact_id`), commands like `ve chunk list` currently show `[UNKNOWN]` status with no explanation. The `parse_chunk_frontmatter_with_errors` method in `src/chunks.py` already exists and returns detailed Pydantic validation errors - we need to use it in the CLI to surface these errors.

**Approach:**
- Add a validation check in `ve chunk create` that validates the final combined chunk name (short_name + optional ticket_id) against the 31-character limit
- Update `ve chunk list` to use `parse_chunk_frontmatter_with_errors` and display `[PARSE ERROR: <reason>]` instead of `[UNKNOWN]`
- Apply the same pattern to `ve chunk activate` for consistency
- Follow TDD: write failing tests first, then implement

**Existing infrastructure:**
- `validate_identifier()` in `src/validation.py` - validates identifiers with max_length parameter
- `parse_chunk_frontmatter_with_errors()` in `src/chunks.py` - returns detailed Pydantic errors
- `validate_short_name()` in `src/ve.py` - validates short_name only (needs extension)

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifact patterns for chunk management, including the `ChunkFrontmatter` model and `parse_chunk_frontmatter_with_errors` method.

## Sequence

### Step 1: Write failing tests for chunk name length validation

Add tests in `tests/test_chunk_start.py` that verify:
1. `ve chunk create my_very_long_chunk_name_that_exceeds_limit` exits with error
2. Error message explains the 31-character limit and shows actual length
3. Combined name (short_name + ticket_id) is validated, not just individual parts

Location: `tests/test_chunk_start.py`

### Step 2: Add combined name validation in ve chunk create

Create a new helper function `validate_chunk_name()` in `src/ve.py` that:
1. Computes the final directory name (short_name or short_name-ticket_id)
2. Validates it doesn't exceed 31 characters
3. Returns a clear error message with the limit and actual length

Update the `create` command to call this validator after individual part validation.

Location: `src/ve.py`

### Step 3: Write failing tests for frontmatter parse error surfacing

Add tests in `tests/test_chunk_list.py` that verify:
1. When a chunk has invalid frontmatter, `ve chunk list` shows `[PARSE ERROR: ...]`
2. The error message includes the specific validation failure (e.g., field name, reason)

Location: `tests/test_chunk_list.py`

### Step 4: Update ve chunk list to surface parse errors

Modify the `list_chunks` command in `src/ve.py` to:
1. Use `parse_chunk_frontmatter_with_errors()` instead of `parse_chunk_frontmatter()`
2. When parsing fails, display `[PARSE ERROR: <first error>]` instead of `[UNKNOWN]`

Location: `src/ve.py`

### Step 5: Update ve chunk activate to surface parse errors

Modify the `activate` command and `Chunks.activate_chunk()` method to:
1. Use `parse_chunk_frontmatter_with_errors()` and include error details in exception messages
2. Ensure error messages are displayed to the user

Location: `src/ve.py`, `src/chunks.py`

### Step 6: Verify all tests pass

Run the test suite to verify both behaviors work correctly:
- `uv run pytest tests/test_chunk_start.py -v`
- `uv run pytest tests/test_chunk_list.py -v`
- `uv run pytest tests/test_chunk_activate.py -v`

## Dependencies

None - all required infrastructure already exists:
- `validate_identifier()` function in `src/validation.py`
- `parse_chunk_frontmatter_with_errors()` method in `src/chunks.py`
- Test fixtures in `tests/conftest.py`

## Risks and Open Questions

1. **Test setup complexity for invalid frontmatter**: Creating chunks with invalid frontmatter requires manually writing files rather than using the CLI (which validates input). This is acceptable for test purposes but adds some test complexity.

2. **Error message format consistency**: The `parse_chunk_frontmatter_with_errors` method returns a list of errors from Pydantic. We need to decide how to format these for display - currently planning to show the first error to avoid overwhelming output while still being informative.

## Deviations

(To be populated during implementation)