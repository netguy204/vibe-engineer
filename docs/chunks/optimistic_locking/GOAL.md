---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/state.py
  - src/orchestrator/scheduler.py
  - src/orchestrator/api/work_units.py
  - src/orchestrator/api/scheduling.py
  - src/orchestrator/api/attention.py
  - src/orchestrator/api/conflicts.py
  - src/orchestrator/api/worktrees.py
  - src/orchestrator/__init__.py
  - tests/test_orchestrator_state.py
code_references:
  - ref: src/orchestrator/state.py#StaleWriteError
    implements: "Exception class for detecting concurrent work unit modifications"
  - ref: src/orchestrator/state.py#StateStore::update_work_unit
    implements: "Optimistic locking check via expected_updated_at parameter"
  - ref: src/orchestrator/scheduler.py#unblock_dependents
    implements: "Retry logic for stale writes when unblocking dependents"
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Stale write detection at dispatch with worktree cleanup on conflict"
  - ref: tests/test_orchestrator_state.py#TestOptimisticLocking
    implements: "Unit tests for StaleWriteError and optimistic locking behavior"
  - ref: tests/test_orchestrator_state.py#TestSchedulerApiRace
    implements: "Integration tests for scheduler/API concurrent modification protection"
  - ref: src/orchestrator/__init__.py
    implements: "Export StaleWriteError for optimistic locking"
  - ref: src/orchestrator/api/attention.py
    implements: "Optimistic locking for answer submissions"
  - ref: src/orchestrator/api/conflicts.py
    implements: "Optimistic locking for conflict resolution and retry merge"
  - ref: src/orchestrator/api/scheduling.py
    implements: "Optimistic locking for priority updates"
  - ref: src/orchestrator/api/work_units.py
    implements: "Optimistic locking for API updates"
  - ref: src/orchestrator/api/worktrees.py
    implements: "Optimistic locking for prune operations"
narrative: arch_review_remediation
investigation: null
subsystems:
  - subsystem_id: orchestrator
    relationship: implements
friction_entries: []
bug_type: null
depends_on:
- sqlite_json_query_fix
created_after:
- model_package_cleanup
- orchestrator_api_decompose
- task_operations_decompose
---

# Chunk Goal

## Minor Goal

Work unit updates in the orchestrator's state store use optimistic locking to prevent stale writes. The orchestrator uses separate `StateStore` instances for the scheduler and the API (by design, for WAL-mode concurrent access), so without coordination the scheduler could read a work unit, the API could update that same work unit (e.g., priority change), and the scheduler could then write its now-stale version back, silently overwriting the API-driven change.

`update_work_unit` in `src/orchestrator/state.py` accepts an `expected_updated_at` parameter and verifies the work unit's `updated_at` timestamp matches before writing. When the timestamps disagree, the write is rejected with `StaleWriteError` indicating a concurrent modification, and the caller re-reads and retries (or skips, as appropriate).

## Success Criteria

- `update_work_unit` checks `updated_at` against the expected value before writing
- A stale write raises a clear error (e.g., `StaleWriteError`) rather than silently succeeding
- The scheduler handles the stale write error gracefully (re-reads and retries or skips)
- API-driven updates (priority changes, manual status transitions) are not lost due to scheduler overwrites
- All existing orchestrator tests pass; new test demonstrates stale write detection

