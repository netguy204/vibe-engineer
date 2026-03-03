<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends the existing `orch_api_retry` infrastructure to handle a new category of transient errors: session-limit errors that include a deterministic reset time (e.g., "You've hit your limit - resets 10pm").

**Strategy:**
1. Add a new detection function `is_session_limit_error()` to `retry.py` that identifies session-limit errors with parseable reset times
2. Add a time parsing function `parse_reset_time()` that extracts and converts reset times to UTC datetime
3. Integrate session-limit detection into the scheduler's error handling path (`_handle_agent_result`)
4. Session-limit errors with parseable reset times use `_schedule_session_retry()` with a fixed retry time (not exponential backoff)
5. Session-limit errors WITHOUT parseable reset times fall through to `NEEDS_ATTENTION` (existing behavior)

**Key Design Choice:** This is additive to the existing 5xx retry infrastructure, not a modification. The error handling path checks session-limit first, then falls back to 5xx retry, then falls back to NEEDS_ATTENTION.

**Time Parsing Approach:**
- Parse reset time strings like "10pm", "10:30pm (America/New_York)", "2024-02-07T22:00:00Z"
- Support timezone hints in parentheses, defaulting to UTC if not specified
- Use Python's `datetime` and `zoneinfo` for timezone-aware parsing

**Testing Strategy (per TESTING_PHILOSOPHY.md):**
- Write failing tests first for the new detection and parsing functions
- Tests verify semantically meaningful properties (correct UTC datetime, correct error classification)
- Cover edge cases: various time formats, with/without timezone, unparseable errors

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional error handling logic following the orchestrator subsystem's patterns. The existing `is_retryable_api_error()` and `_schedule_api_retry()` set the precedent for error detection and retry scheduling.

## Sequence

### Step 1: Write failing tests for `is_session_limit_error()` detection

Create tests in `tests/test_orchestrator_retry.py` that verify:
- Session-limit errors with reset time ARE detected (e.g., "You've hit your limit - resets 10pm")
- Session-limit errors with timezone ARE detected (e.g., "...resets 10pm (America/New_York)")
- Session-limit errors with full timestamp ARE detected (e.g., "...resets 2024-02-07T22:00:00Z")
- Session-limit errors WITHOUT reset time are NOT detected (trigger NEEDS_ATTENTION fallback)
- Other error types are NOT detected as session limits

Location: `tests/test_orchestrator_retry.py`

### Step 2: Write failing tests for `parse_reset_time()` function

Create tests that verify:
- Parse "10pm" → correct UTC datetime (default UTC if no timezone)
- Parse "10pm (America/New_York)" → correct UTC datetime (converted from Eastern)
- Parse "10:30pm (America/Los_Angeles)" → correct UTC datetime (converted from Pacific)
- Parse "2024-02-07T22:00:00Z" → correct UTC datetime (ISO format)
- Return None for unparseable strings (not raise exceptions)

Location: `tests/test_orchestrator_retry.py`

### Step 3: Implement `is_session_limit_error()` in retry.py

Add function that:
- Takes an error string as input
- Uses regex to detect session-limit patterns with reset time indicators
- Returns `True` if the error matches, `False` otherwise
- Does NOT parse the time itself (that's `parse_reset_time()`'s job)

Patterns to match:
- "you've hit your limit" (case-insensitive) followed by "resets" with a time pattern
- "session limit" or "rate limit reset" with a time pattern

Location: `src/orchestrator/retry.py`

### Step 4: Implement `parse_reset_time()` in retry.py

Add function that:
- Takes an error string as input
- Extracts reset time pattern using regex
- Parses time with optional timezone in parentheses
- Converts to UTC datetime
- Returns `None` if parsing fails

Use `datetime.strptime()` for time parsing and `zoneinfo.ZoneInfo` for timezone conversion. Handle ambiguous times (e.g., "10pm" means today or tomorrow based on current time).

Location: `src/orchestrator/retry.py`

### Step 5: Write failing tests for scheduler session-limit retry behavior

Create tests in `tests/test_orchestrator_scheduler.py` that verify:
- Session-limit error with parseable reset time schedules retry at reset time (not NEEDS_ATTENTION)
- Session-limit error WITHOUT parseable reset time transitions to NEEDS_ATTENTION
- Retry uses `next_retry_at` set to the parsed reset time
- Work unit transitions to READY (not NEEDS_ATTENTION)
- Log message clearly indicates "Session limit hit, scheduled retry at {time}"

Location: `tests/test_orchestrator_scheduler.py`

### Step 6: Implement session-limit handling in scheduler

Modify `_handle_agent_result()` in `scheduler.py`:
1. Before checking `is_retryable_api_error()`, check `is_session_limit_error()`
2. If session-limit detected, call `parse_reset_time()` to get UTC reset time
3. If reset time parseable, call new `_schedule_session_retry()` method
4. If reset time NOT parseable, fall through to NEEDS_ATTENTION
5. Keep existing 5xx retry logic unchanged (order: session-limit → 5xx → NEEDS_ATTENTION)

Add new `_schedule_session_retry()` method:
- Similar to `_schedule_api_retry()` but uses fixed reset time, not exponential backoff
- Sets `next_retry_at` to the parsed reset time
- Sets `pending_answer = "continue"`
- Preserves `session_id` for resumption
- Logs "Session limit hit, scheduled retry at {time}"

Location: `src/orchestrator/scheduler.py`

### Step 7: Run tests and verify all pass

Run `uv run pytest tests/test_orchestrator_retry.py tests/test_orchestrator_scheduler.py -v` to verify:
- All new session-limit tests pass
- All existing `orch_api_retry` tests continue to pass
- No regressions in scheduler behavior

### Step 8: Update chunk's code_paths in GOAL.md

Add to `code_paths`:
- `src/orchestrator/retry.py`
- `src/orchestrator/scheduler.py`
- `tests/test_orchestrator_retry.py`
- `tests/test_orchestrator_scheduler.py`

Location: `docs/chunks/orch_session_auto_resume/GOAL.md`

## Dependencies

This chunk builds on:
- **orch_api_retry** (ACTIVE): Provides the existing retry infrastructure (`is_retryable_api_error()`, `_schedule_api_retry()`, `api_retry_count`, `next_retry_at`)
- **scheduler_decompose** (ACTIVE): Provides the extracted `retry.py` module where new detection functions will live

No external libraries needed - uses Python's standard `datetime`, `re`, and `zoneinfo` modules.

## Risks and Open Questions

1. **Time ambiguity**: If the error says "resets 10pm" and it's currently 11pm, should we assume tomorrow? The implementation should assume "next occurrence" of the given time.

2. **Timezone edge cases**: Daylight saving time transitions could cause unexpected behavior. Using `zoneinfo.ZoneInfo` handles this correctly.

3. **Clock skew**: If the orchestrator's clock differs significantly from Anthropic's, retries might happen too early. Accept this as an inherent limitation.

4. **Regex robustness**: The reset time patterns in real error messages may vary. Start with known patterns and expand based on real-world observations.

5. **Session resumption validity**: If the session has expired by the time of retry, the "continue" prompt may fail. This would result in a new error and the normal retry/NEEDS_ATTENTION flow would handle it.

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