<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation adds a guard to `ve chunk start` (and its alias `create`) that prevents creating a new IMPLEMENTING chunk when one already exists. This mirrors the existing guard in `activate_chunk()`.

**Strategy:**
- Add a check in `Chunks.create_chunk()` that calls `get_current_chunk()` before creating
- When an IMPLEMENTING chunk exists and `status != "FUTURE"`, raise `ValueError` with a descriptive message
- The `--future` flag already passes `status="FUTURE"`, so it naturally bypasses the guard
- Error messages identify the existing chunk and suggest running `ve chunk complete`

**Patterns used:**
- Reuses existing `get_current_chunk()` method for IMPLEMENTING chunk detection
- Mirrors error message format from `activate_chunk()` for consistency
- Follows TDD: write failing tests first per docs/trunk/TESTING_PHILOSOPHY.md

**Existing code built on:**
- `Chunks.get_current_chunk()` (src/chunks.py:167-181) - already detects IMPLEMENTING chunks
- `Chunks.activate_chunk()` (src/chunks.py:185-227) - already has similar guard logic
- `tests/test_chunk_start.py` - existing test patterns for chunk start command
- `tests/test_chunk_activate.py` - test for activate guard (test_fails_when_another_chunk_implementing)

## Subsystem Considerations

No subsystems are relevant to this chunk. The guard logic is simple validation at the chunk creation boundary and does not touch any cross-cutting patterns.

## Sequence

### Step 1: Write failing tests for chunk start guard

Add a new test class `TestImplementingGuard` to `tests/test_chunk_start.py` with the following tests:

1. `test_start_fails_when_implementing_exists` - Create an IMPLEMENTING chunk first, then verify that `ve chunk start <new_name>` fails with exit code != 0 and error message containing the existing chunk name and "IMPLEMENTING"

2. `test_start_error_suggests_complete` - Same setup, verify error message suggests running `ve chunk complete`

3. `test_future_flag_bypasses_guard` - Create an IMPLEMENTING chunk, then verify that `ve chunk start <new_name> --future` succeeds (creates a FUTURE chunk without blocking)

Location: tests/test_chunk_start.py

### Step 2: Implement the guard in create_chunk()

Add guard logic to `Chunks.create_chunk()` that:
1. Checks if `status != "FUTURE"` (only guard non-future chunk creation)
2. Calls `self.get_current_chunk()` to find any existing IMPLEMENTING chunk
3. If one exists, raises `ValueError` with message format:
   `"Cannot create: chunk '{current}' is already IMPLEMENTING. Run 've chunk complete' first."`

The check should occur after duplicate detection (line 253) and before creating the chunk directory. This ensures all validation happens before side effects.

Location: src/chunks.py (within `create_chunk()` method, around line 254)

Add backreference comment:
```python
# Chunk: docs/chunks/chunk_create_guard - Prevent multiple IMPLEMENTING chunks
```

### Step 3: Run tests and verify

Run the full test suite to ensure:
- New guard tests pass
- Existing tests continue to pass (especially TestFutureFlag which depends on --future working)
- The error message format matches success criteria

```bash
pytest tests/test_chunk_start.py tests/test_chunk_activate.py -v
```

### Step 4: Verify activate guard behavior (already implemented)

The existing `activate_chunk()` method already has the guard per lines 205-210. Verify the existing test `test_fails_when_another_chunk_implementing` in `tests/test_chunk_activate.py` covers this requirement. No code changes needed, just confirmation.

Review existing error message format to confirm it:
- Identifies the existing IMPLEMENTING chunk by name
- Suggests completing or marking it as ACTIVE first

## Dependencies

None. All required infrastructure already exists:
- `Chunks.get_current_chunk()` method for detecting IMPLEMENTING chunks
- `ValueError` exception pattern for chunk validation errors
- Test fixtures in `tests/conftest.py` (temp_project, runner)

## Risks and Open Questions

**Low risk:** This is a straightforward validation addition that follows an established pattern in `activate_chunk()`.

**Consideration:** The error message should suggest `ve chunk complete` rather than just "complete the chunk" since that's the actual command. The GOAL.md specifies this explicitly.

## Deviations

None. Implementation followed the plan exactly.
