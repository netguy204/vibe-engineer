---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/state.py
- src/orchestrator/models.py
- tests/orchestrator/test_scheduler.py
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

Ensure that orchestrator daemon restarts preserve retry backoff behavior for work units that were mid-retry when the daemon stopped.

Currently, the `_recover_from_crash()` method in `scheduler.py` resets all RUNNING work units to READY status without considering their retry state. When a work unit has `api_retry_count > 0` (indicating it was in an exponential backoff retry cycle for a 5xx API error), its `next_retry_at` field is `None` because the dispatch loop cleared it when the agent was dispatched (line 400 of `_dispatch_tick`). After crash recovery, these units dispatch immediately without backoff, defeating the purpose of the retry mechanism and potentially overwhelming a struggling API endpoint.

The fix is to make `_recover_from_crash()` retry-aware: when resetting a RUNNING work unit to READY, if `api_retry_count > 0`, compute a new `next_retry_at` based on the current retry count and the configured backoff parameters. This preserves the intent of the exponential backoff across daemon restarts.

This matters for the orchestrator's reliability as a long-running daemon managing parallel agent work. The orchestrator subsystem is the backbone for scaling the documentation-driven workflow to multiple concurrent chunks, and daemon restarts should be transparent to the retry mechanism rather than a loophole that resets backoff state.

## Success Criteria

- When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count > 0`, it sets `next_retry_at` to a future time computed from the current backoff parameters (`api_retry_initial_delay_ms`, `api_retry_max_delay_ms`, and the unit's `api_retry_count`), using the same exponential backoff formula as `_schedule_api_retry()`.
- When `_recover_from_crash()` resets a RUNNING work unit to READY and `api_retry_count == 0`, it does NOT set `next_retry_at` (preserving current behavior for non-retry units).
- A unit test verifies that after simulated crash recovery, a work unit with `api_retry_count=3` has a non-null `next_retry_at` in the future and is not immediately dispatched by `_dispatch_tick()`.
- A unit test verifies that after crash recovery, a work unit with `api_retry_count=0` has `next_retry_at=None` and is dispatched normally.
- Existing retry tests continue to pass without modification.

