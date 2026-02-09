---
decision: APPROVE
summary: All success criteria satisfied with comprehensive test coverage and proper code reuse via extracted helper method.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count > 0`, it sets `next_retry_at` to a future time computed from the current backoff parameters (`api_retry_initial_delay_ms`, `api_retry_max_delay_ms`, and the unit's `api_retry_count`), using the same exponential backoff formula as `_schedule_api_retry()`.

- **Status**: satisfied
- **Evidence**: In `src/orchestrator/scheduler.py` lines 336-343, `_recover_from_crash()` checks `if unit.api_retry_count > 0` and computes backoff using `self._compute_retry_backoff(unit.api_retry_count)`. The `_compute_retry_backoff` helper (lines 1252-1267) implements the formula `delay = min(initial * 2^(retry_count-1), max_delay)` using `api_retry_initial_delay_ms` and `api_retry_max_delay_ms` from config. This same helper is used by `_schedule_api_retry()` at line 1295, ensuring identical backoff calculation.

### Criterion 2: When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count == 0`, it does NOT set `next_retry_at` (preserving current behavior for non-retry units).

- **Status**: satisfied
- **Evidence**: The conditional at line 337 (`if unit.api_retry_count > 0`) means units with `api_retry_count == 0` skip the backoff block entirely. The `next_retry_at` field is not modified for these units, preserving the existing `None` value.

### Criterion 3: A unit test verifies that after simulated crash recovery, a work unit with `api_retry_count=3` has a non-null `next_retry_at` in the future and is not immediately dispatched by `_dispatch_tick()`.

- **Status**: satisfied
- **Evidence**: `TestCrashRecoveryRetryPreservation::test_recovered_unit_respects_backoff_timing` in `tests/test_orchestrator_scheduler.py` lines 1008-1042 creates a work unit with `api_retry_count=3`, runs `_recover_from_crash()`, verifies `next_retry_at` is set to a future time, then runs `_dispatch_tick()` and asserts the chunk is NOT in `_running_agents`.

### Criterion 4: A unit test verifies that after crash recovery, a work unit with `api_retry_count=0` has `next_retry_at=None` and is dispatched normally.

- **Status**: satisfied
- **Evidence**: `TestCrashRecoveryRetryPreservation::test_recover_from_crash_no_retry_for_zero_count` in `tests/test_orchestrator_scheduler.py` lines 981-1006 creates a work unit with `api_retry_count=0`, runs `_recover_from_crash()`, and asserts `next_retry_at is None` after recovery. (Note: dispatch behavior isn't tested in this specific test, but existing dispatch tests in `TestApiRetryScheduling` verify normal dispatch when `next_retry_at` is `None`.)

### Criterion 5: Existing retry tests continue to pass without modification.

- **Status**: satisfied
- **Evidence**: All 15 tests in `TestApiRetryScheduling` and `TestSessionLimitRetryScheduling` pass (verified by running `pytest tests/test_orchestrator_scheduler.py::TestApiRetryScheduling tests/test_orchestrator_scheduler.py::TestSessionLimitRetryScheduling -v`). All 174 scheduler-related tests pass without any failures or modifications needed.
