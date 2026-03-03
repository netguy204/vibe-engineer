---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/state.py
- tests/test_orchestrator_state.py
code_references:
  - ref: src/orchestrator/state.py#StateStore
    implements: "Concurrency model documentation for dual-connection pattern"
  - ref: src/orchestrator/state.py#StateStore::transaction
    implements: "Context manager for explicit BEGIN/COMMIT transaction boundaries"
  - ref: src/orchestrator/state.py#StateStore::create_work_unit
    implements: "Atomic work unit creation with status log in single transaction"
  - ref: src/orchestrator/state.py#StateStore::update_work_unit
    implements: "Atomic work unit update with status log in single transaction"
narrative: arch_consolidation
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Add explicit SQLite transaction boundaries around multi-statement operations in the orchestrator's state store to prevent incomplete status logs and ensure atomicity. Currently, `update_work_unit()` performs a SELECT (get old status), UPDATE (new status), and INSERT (status log) as separate autocommitted statements. If the process dies between operations, the status log becomes incomplete or inconsistent with work unit state.

This chunk wraps these multi-statement sequences in explicit BEGIN/COMMIT blocks to ensure atomic updates. Additionally, review the dual-connection pattern where two separate StateStore instances connect to the same database (one from `start_daemon`, one from `create_app`) to ensure there are no unintended concurrency issues.

## Success Criteria

- `update_work_unit()` wraps SELECT + UPDATE + INSERT in a single transaction using explicit BEGIN/COMMIT
- `create_work_unit()` wraps INSERT + status log INSERT in a single transaction
- Any other multi-statement operations (e.g., conflict analysis storage) use explicit transactions
- The dual StateStore connection pattern is documented or refactored if problematic
- SQLite isolation level remains appropriate for concurrent access with WAL mode
- All existing orchestrator tests pass
- Manual testing confirms that status transitions are atomic (simulated crashes don't create incomplete logs)


