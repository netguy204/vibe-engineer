<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add retry logic in the scheduler's `_handle_agent_result()` method. When an agent returns an error matching 5xx patterns, instead of immediately calling `_mark_needs_attention()`, we:

1. Check if the error looks like a 5xx API error (pattern matching on error string)
2. If it's a retryable 5xx error, schedule a retry with exponential backoff
3. Track retry count on the WorkUnit to enforce the 30-attempt maximum
4. After exhausting retries, fall through to the existing NEEDS_ATTENTION behavior

The retry mechanism will:
- Store retry state on the WorkUnit (`api_retry_count`, `next_retry_at`)
- Use a new database field or reuse `pending_answer` with special value "continue"
- Resume the session by setting `pending_answer = "continue"` and scheduling the work unit

This approach integrates cleanly with existing patterns:
- Session resumption already works via `pending_answer` + `resume_session_id`
- The scheduler's dispatch loop already checks for READY work units periodically
- We add a new status (RETRY_PENDING) or use existing READY with a `next_retry_at` timestamp

Configuration values (100ms initial, 5s max, 30 retries) will be added to `OrchestratorConfig`.

## Subsystem Considerations

No relevant subsystems in docs/subsystems/. The orchestrator has 35+ chunks but no documented subsystem yet.

## Sequence

### Step 1: Add retry configuration to OrchestratorConfig

Add three new fields to `OrchestratorConfig` in `src/orchestrator/models.py`:

```python
api_retry_initial_delay_ms: int = 100  # Initial backoff delay
api_retry_max_delay_ms: int = 5000     # Maximum backoff delay
api_retry_max_attempts: int = 30       # Maximum retry attempts
```

Update `model_dump_json_serializable()` to include these fields.

Location: `src/orchestrator/models.py#OrchestratorConfig`

### Step 2: Add retry state fields to WorkUnit

Add database migration (v12) to add two new columns to work_units table:

- `api_retry_count INTEGER DEFAULT 0` - Current retry attempt number
- `next_retry_at TEXT` - ISO timestamp when next retry is allowed (null = immediate)

Update the WorkUnit model and StateStore methods to handle these fields.

Location: `src/orchestrator/state.py`

### Step 3: Add helper function to detect 5xx errors

Create a function `is_retryable_api_error(error: str) -> bool` that pattern-matches error strings for 5xx status codes. Check for:
- "500", "502", "503", "504", "529" in error text
- "Internal Server Error", "Bad Gateway", "Service Unavailable", "Gateway Timeout", "overloaded" patterns

Location: `src/orchestrator/scheduler.py`

### Step 4: Implement retry scheduling logic in scheduler

Modify `_handle_agent_result()` to check for retryable errors before marking NEEDS_ATTENTION:

```python
elif result.error:
    if is_retryable_api_error(result.error) and work_unit.api_retry_count < config.api_retry_max_attempts:
        # Schedule retry with exponential backoff
        await self._schedule_api_retry(work_unit, result.error)
    else:
        # Exhausted retries or non-retryable error
        await self._mark_needs_attention(work_unit, result.error)
```

Add `_schedule_api_retry()` method that:
1. Increments `api_retry_count`
2. Calculates backoff delay: `min(initial * 2^retry_count, max_delay)`
3. Sets `next_retry_at` timestamp
4. Sets `pending_answer = "continue"` to inject the prompt on resume
5. Sets status back to READY (will be picked up by dispatch loop)
6. Logs the retry attempt

Location: `src/orchestrator/scheduler.py#Scheduler`

### Step 5: Update dispatch loop to respect retry timing

Modify `_dispatch_ready_work()` to check `next_retry_at` before dispatching:

```python
# Skip work units that are waiting for retry backoff
if work_unit.next_retry_at:
    retry_time = datetime.fromisoformat(work_unit.next_retry_at)
    if datetime.now(timezone.utc) < retry_time:
        continue  # Not ready yet
    # Clear the retry timestamp, we're ready to go
    work_unit.next_retry_at = None
```

Location: `src/orchestrator/scheduler.py#Scheduler._dispatch_ready_work`

### Step 6: Reset retry state on success

When a work unit completes successfully or advances phases, reset the retry state:

```python
work_unit.api_retry_count = 0
work_unit.next_retry_at = None
```

Add this to `_advance_phase()` and anywhere else status transitions to success.

Location: `src/orchestrator/scheduler.py#Scheduler._advance_phase`

### Step 7: Add logging for retry visibility

Log retry attempts with enough detail for operators:

```python
logger.info(
    f"Retrying {chunk} after API error (attempt {retry_count}/{max_attempts}, "
    f"backoff {delay_ms}ms): {error[:100]}"
)
```

Log when retries are exhausted:

```python
logger.warning(
    f"Exhausted {max_attempts} retries for {chunk}, marking NEEDS_ATTENTION"
)
```

Location: `src/orchestrator/scheduler.py`

### Step 8: Write tests

Write tests in `tests/test_orchestrator_scheduler.py`:

1. **test_is_retryable_api_error_detects_5xx** - Verify pattern matching for various 5xx error strings
2. **test_is_retryable_api_error_rejects_4xx** - Verify 4xx errors are not retryable
3. **test_schedule_api_retry_increments_count** - Verify retry count increments
4. **test_schedule_api_retry_calculates_backoff** - Verify exponential backoff formula
5. **test_schedule_api_retry_caps_at_max_delay** - Verify backoff caps at 5s
6. **test_dispatch_respects_retry_timing** - Verify work units wait for backoff
7. **test_retry_exhaustion_marks_needs_attention** - Verify NEEDS_ATTENTION after 30 retries
8. **test_successful_completion_resets_retry_state** - Verify state clears on success

Location: `tests/test_orchestrator_scheduler.py`

## Dependencies

No external dependencies. All required infrastructure exists:
- Database migrations pattern established (state.py has migrations v1-v11)
- OrchestratorConfig pattern established (models.py)
- Session resumption with `pending_answer` already works
- Logging infrastructure in place

## Risks and Open Questions

1. **Error string format variability** - API errors might not always contain the status code literally. The pattern matching function should be generous, looking for multiple patterns like "500", "Internal Server Error", "error_type.*server", etc.

2. **Session resumption reliability** - Injecting "continue" assumes the session can be resumed cleanly. If the SDK session state is corrupted by the error, resumption might fail. This is acceptable; it will just retry again until exhausted.

3. **Backoff timing precision** - The dispatch loop runs every `dispatch_interval_seconds` (default 1s). With a 100ms initial backoff, the first retry might actually happen after 1s. This is acceptable; the backoff is a minimum, not exact.

4. **Race between retry scheduling and dispatch** - If we set status to READY and dispatch happens before we finish updating retry fields, we could dispatch prematurely. Solution: update all fields before changing status to READY.

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