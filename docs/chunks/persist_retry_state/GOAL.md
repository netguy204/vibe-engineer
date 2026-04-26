---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/state.py
- src/orchestrator/models.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_recover_from_crash
    implements: "Retry-aware crash recovery that preserves backoff state for units with api_retry_count > 0"
  - ref: src/orchestrator/scheduler.py#Scheduler::_compute_retry_backoff
    implements: "Extracted helper for computing exponential backoff delay, reused by both _recover_from_crash and _schedule_api_retry"
  - ref: tests/test_orchestrator_scheduler.py#TestCrashRecoveryRetryPreservation
    implements: "Tests verifying crash recovery preserves retry backoff state"
narrative: arch_review_gaps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_decompose
- integrity_deprecate_standalone
- low_priority_cleanup
- optimistic_locking
- spec_and_adr_update
- test_file_split
- orch_session_auto_resume
---

# Chunk Goal

## Minor Goal

Orchestrator daemon restarts preserve retry backoff behavior for work units that were mid-retry when the daemon stopped.

The `_recover_from_crash()` method in `scheduler.py` is retry-aware: when resetting a RUNNING work unit to READY, it inspects `api_retry_count`. If `api_retry_count > 0` (indicating the unit was in an exponential backoff retry cycle for a 5xx API error), the recovery logic computes a new `next_retry_at` from the configured backoff parameters using `_compute_retry_backoff()` — the same exponential backoff helper `_schedule_api_retry()` uses. If `api_retry_count == 0`, `next_retry_at` stays `None` and the unit dispatches normally. This preserves the intent of the exponential backoff across daemon restarts so a struggling API endpoint isn't overwhelmed by units that would otherwise dispatch immediately.

This matters for the orchestrator's reliability as a long-running daemon managing parallel agent work. The orchestrator subsystem is the backbone for scaling the documentation-driven workflow to multiple concurrent chunks, and daemon restarts are transparent to the retry mechanism rather than a loophole that resets backoff state.

## Success Criteria

- When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count > 0`, it sets `next_retry_at` to a future time computed from the current backoff parameters (`api_retry_initial_delay_ms`, `api_retry_max_delay_ms`, and the unit's `api_retry_count`), using the same exponential backoff formula as `_schedule_api_retry()`.
- When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count == 0`, it does NOT set `next_retry_at` (preserving current behavior for non-retry units).
- A unit test verifies that after simulated crash recovery, a work unit with `api_retry_count=3` has a non-null `next_retry_at` in the future and is not immediately dispatched by `_dispatch_tick()`.
- A unit test verifies that after crash recovery, a work unit with `api_retry_count=0` has `next_retry_at=None` and is dispatched normally.
- Existing retry tests continue to pass without modification.

