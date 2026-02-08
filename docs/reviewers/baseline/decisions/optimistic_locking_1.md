---
decision: APPROVE
summary: All success criteria satisfied - StaleWriteError exception implemented with optimistic locking check in update_work_unit, scheduler handles gracefully with retry/skip patterns, API returns 409 Conflict, all 739 orchestrator tests pass including 6 new tests for stale write detection.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `update_work_unit` checks `updated_at` against the expected value before writing

- **Status**: satisfied
- **Evidence**: `src/orchestrator/state.py:506-552` - The `update_work_unit` method accepts an optional `expected_updated_at` parameter. When provided, it compares `old_unit.updated_at != expected_updated_at` and raises `StaleWriteError` on mismatch. The check occurs within a transaction after fetching the old unit.

### Criterion 2: A stale write raises a clear error (e.g., `StaleWriteError`) rather than silently succeeding

- **Status**: satisfied
- **Evidence**: `src/orchestrator/state.py:31-54` - `StaleWriteError` exception class is implemented with helpful attributes (`chunk`, `expected_updated_at`, `actual_updated_at`) and a descriptive message including ISO timestamps. Also exported from `src/orchestrator/__init__.py:15`.

### Criterion 3: The scheduler handles the stale write error gracefully (re-reads and retries or skips)

- **Status**: satisfied
- **Evidence**:
  - `src/orchestrator/scheduler.py:475-489` - In `_run_work_unit`, on StaleWriteError, logs warning and cleans up the just-created worktree before returning (skip pattern).
  - `src/orchestrator/scheduler.py:95-148` - In `unblock_dependents`, implements proper retry loop with max 3 attempts, re-reads fresh work unit on stale, exits early if already unblocked by another process.

### Criterion 4: API-driven updates (priority changes, manual status transitions) are not lost due to scheduler overwrites

- **Status**: satisfied
- **Evidence**:
  - All API endpoints capture `expected_updated_at` at read time and pass it to `update_work_unit`:
    - `src/orchestrator/api/work_units.py:167-168,211-218` - update endpoint returns 409 on StaleWriteError
    - `src/orchestrator/api/scheduling.py:279-287` - priority endpoint returns 409 on StaleWriteError
    - `src/orchestrator/api/attention.py:161-169` - resolve endpoint returns 409 on StaleWriteError
    - `src/orchestrator/api/conflicts.py:191-199,289-297` - conflict endpoints return 409 on StaleWriteError
    - `src/orchestrator/api/worktrees.py:200-204,257-261` - prune endpoints handle stale writes gracefully (best effort)
  - HTTP 409 Conflict responses include `{"error": "Concurrent modification detected", "detail": <error message>}`

### Criterion 5: All existing orchestrator tests pass; new test demonstrates stale write detection

- **Status**: satisfied
- **Evidence**:
  - Ran `pytest tests/test_orchestrator_*.py -v` - all 739 tests pass
  - New tests in `tests/test_orchestrator_state.py`:
    - `TestOptimisticLocking` class with 4 tests: `test_stale_write_raises_error`, `test_update_without_expected_timestamp_succeeds`, `test_update_with_matching_timestamp_succeeds`, `test_stale_write_error_message`
    - `TestSchedulerApiRace` class with 2 tests: `test_api_update_not_lost_during_scheduler_update`, `test_sequential_updates_with_optimistic_locking`
