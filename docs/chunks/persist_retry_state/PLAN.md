# Implementation Plan

## Approach

This chunk fixes a retry backoff bypass that occurs when the orchestrator daemon restarts. Currently, `_recover_from_crash()` resets RUNNING work units to READY without considering their retry state. When a work unit has `api_retry_count > 0` (indicating it was mid-retry for a 5xx API error), its `next_retry_at` is `None` because `_dispatch_tick()` cleared it when the agent was dispatched. After crash recovery, these units dispatch immediately without backoff.

**Strategy**: Modify `_recover_from_crash()` to be retry-aware:
1. When resetting a RUNNING work unit to READY with `api_retry_count > 0`, compute a new `next_retry_at` using the same exponential backoff formula as `_schedule_api_retry()`
2. When `api_retry_count == 0`, preserve current behavior (no `next_retry_at`)

This reuses the existing backoff calculation logic and configuration parameters (`api_retry_initial_delay_ms`, `api_retry_max_delay_ms`) from `OrchestratorConfig`.

**Testing Strategy**: Follow TDD per TESTING_PHILOSOPHY.md. Write failing tests first that verify:
- Crash recovery with `api_retry_count > 0` sets `next_retry_at` appropriately
- Crash recovery with `api_retry_count == 0` does NOT set `next_retry_at`
- Units with `next_retry_at` in the future are not immediately dispatched

The tests in `test_orchestrator_scheduler.py` already demonstrate the pattern for testing retry timing.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the retry resilience behavior within the orchestrator subsystem. The change is localized to `scheduler.py` and follows the existing retry patterns established by the `orch_api_retry` chunk.

## Sequence

### Step 1: Write failing tests for crash recovery retry preservation

Create test cases in `tests/test_orchestrator_scheduler.py` (or a new test file if preferred) that verify:

1. **test_recover_from_crash_preserves_retry_backoff**: Create a work unit with `status=RUNNING`, `api_retry_count=3`, and `next_retry_at=None`. Call `_recover_from_crash()`. Verify that the updated work unit has `status=READY` and `next_retry_at` is set to a future time computed from the backoff formula.

2. **test_recover_from_crash_no_retry_for_zero_count**: Create a work unit with `status=RUNNING`, `api_retry_count=0`. Call `_recover_from_crash()`. Verify that `next_retry_at` remains `None`.

3. **test_recovered_unit_respects_backoff_timing**: After recovery, a work unit with `next_retry_at` in the future should NOT be dispatched by `_dispatch_tick()`. This test already has a pattern in `test_dispatch_respects_retry_timing` that we can reference.

Location: `tests/test_orchestrator_scheduler.py`

### Step 2: Extract backoff calculation helper

The exponential backoff calculation in `_schedule_api_retry()` (lines 1116-1120) should be extracted into a helper function so `_recover_from_crash()` can reuse it without duplicating the formula.

Create a helper method in `src/orchestrator/scheduler.py`:

```python
def _compute_retry_backoff(self, retry_count: int) -> timedelta:
    """Compute exponential backoff delay for a retry attempt.

    Uses the formula: delay = min(initial * 2^(retry_count-1), max_delay)

    Args:
        retry_count: Current retry attempt number (1-indexed)

    Returns:
        timedelta representing the backoff delay
    """
```

Update `_schedule_api_retry()` to use this helper.

Location: `src/orchestrator/scheduler.py`

### Step 3: Modify _recover_from_crash to set next_retry_at

In `_recover_from_crash()`, after setting `unit.status = WorkUnitStatus.READY`, add logic to check `api_retry_count`:

```python
if unit.api_retry_count > 0:
    # Preserve retry backoff across daemon restart
    backoff = self._compute_retry_backoff(unit.api_retry_count)
    unit.next_retry_at = datetime.now(timezone.utc) + backoff
    logger.info(
        f"Preserving retry backoff for {unit.chunk} "
        f"(attempt {unit.api_retry_count}, backoff {backoff.total_seconds():.1f}s)"
    )
```

Location: `src/orchestrator/scheduler.py` in `_recover_from_crash()` method (around lines 322-328)

### Step 4: Add chunk backreference comment

Add a backreference comment to `_recover_from_crash()` indicating this chunk:

```python
# Chunk: docs/chunks/persist_retry_state - Preserve retry backoff across daemon restarts
```

Location: `src/orchestrator/scheduler.py` near the retry-aware logic

### Step 5: Run tests and verify

Run the test suite to confirm:
1. New tests pass
2. Existing retry tests (`TestApiRetryScheduling`, `TestSessionLimitRetryScheduling`) continue to pass
3. No regressions in other scheduler tests

Command: `uv run pytest tests/test_orchestrator_scheduler.py -v`

## Risks and Open Questions

- **Backoff timing after long outages**: If the daemon was down for hours, the computed `next_retry_at` based on current time + backoff might be shorter than desired. This is acceptable because the backoff is meant to give the API time to recover between attempts, and if the daemon was down long enough, the API has likely recovered. The current implementation doesn't know how long the daemon was down, so using "now + backoff" is the most reasonable behavior.

- **Retry count accumulation**: The retry count is already capped by `api_retry_max_attempts` in `_handle_agent_result()`, so we don't need to worry about runaway retry counts after crash recovery.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->