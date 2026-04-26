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

The orchestrator's state store wraps multi-statement operations in explicit SQLite transactions so status logs stay consistent with work unit state. `StateStore.transaction()` provides a context manager that emits `BEGIN`/`COMMIT` (and `ROLLBACK` on exception) against the autocommit-mode connection. `create_work_unit()` uses it to atomically write the work unit row and its initial status log entry; `update_work_unit()` uses it to bundle the SELECT (for old status), UPDATE, and status-log INSERT into a single atomic unit. A process death between statements either commits the full transition or none of it.

The dual-connection pattern — separate `StateStore` instances from `start_daemon` and `create_app` connecting to the same database — is documented on the `StateStore` class. WAL mode plus short-lived transactions keep concurrent writes from corrupting state; SQLite serializes writes across connections.

## Success Criteria

- `update_work_unit()` wraps SELECT + UPDATE + INSERT in a single transaction using explicit BEGIN/COMMIT
- `create_work_unit()` wraps INSERT + status log INSERT in a single transaction
- Any other multi-statement operations (e.g., conflict analysis storage) use explicit transactions
- The dual StateStore connection pattern is documented or refactored if problematic
- SQLite isolation level remains appropriate for concurrent access with WAL mode
- All existing orchestrator tests pass
- Manual testing confirms that status transitions are atomic (simulated crashes don't create incomplete logs)


