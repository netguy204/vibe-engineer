<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The current `StateStore` in `src/orchestrator/state.py` uses `isolation_level=None` (autocommit mode) which means each SQL statement commits independently. This is problematic for multi-statement operations like:

1. **`update_work_unit()`**: Performs SELECT (get old status) → UPDATE (new status) → INSERT (status log) as three separate autocommitted statements
2. **`create_work_unit()`**: Performs INSERT (work unit) → INSERT (status log) as two separate statements
3. **`save_conflict_analysis()`**: Single INSERT OR REPLACE, but worth reviewing in context

The fix is to add a context manager for explicit transaction boundaries. With `isolation_level=None`, we must issue explicit `BEGIN` and `COMMIT` statements.

**Strategy**: Add a `transaction()` context manager to `StateStore` that wraps operations in explicit `BEGIN`/`COMMIT` blocks. Then wrap the multi-statement methods in this context manager.

**Dual-connection pattern analysis**: The daemon creates two `StateStore` instances:
1. In `start_daemon()` (daemon.py:476) - used for initial setup and scheduler
2. In `create_app()` (api.py:1788) - used for API endpoints

Both connect to the same SQLite database. With WAL mode enabled (`PRAGMA journal_mode=WAL`), concurrent readers and a single writer are safe. Since both connections are in the same process and use autocommit mode, there's no transaction isolation concern - each statement completes immediately. Adding explicit transactions won't change this behavior; we just need to ensure each transaction is short-lived and doesn't hold locks unnecessarily.

**Testing approach**: Add unit tests that verify transaction atomicity by:
1. Testing that status logs are created atomically with work unit updates
2. Testing the context manager behavior (commit on success, rollback on exception)
3. Existing tests should continue to pass, validating no behavioral regressions

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS improved transaction handling for the StateStore component of this subsystem. The subsystem invariant "Work unit transitions are logged for debugging" is strengthened by making status logging atomic with the update.

## Sequence

### Step 1: Add a transaction context manager to StateStore

Add a `transaction()` method to `StateStore` that returns a context manager for explicit transaction boundaries.

```python
from contextlib import contextmanager

@contextmanager
def transaction(self):
    """Context manager for explicit transaction boundaries.

    With isolation_level=None (autocommit), we must use explicit
    BEGIN/COMMIT statements to group operations atomically.

    Usage:
        with store.transaction():
            store.connection.execute(...)
            store.connection.execute(...)
    """
    self.connection.execute("BEGIN")
    try:
        yield
        self.connection.execute("COMMIT")
    except Exception:
        self.connection.execute("ROLLBACK")
        raise
```

Location: `src/orchestrator/state.py` in the `StateStore` class, after the `close()` method

### Step 2: Wrap create_work_unit in a transaction

Modify `create_work_unit()` to wrap the INSERT + status log INSERT in an explicit transaction:

```python
def create_work_unit(self, work_unit: WorkUnit) -> WorkUnit:
    # ... existing setup code ...

    with self.transaction():
        try:
            self.connection.execute(...)  # INSERT work unit
        except sqlite3.IntegrityError:
            raise ValueError(...)

        # Log the initial status
        self._log_status_transition(work_unit.chunk, None, work_unit.status)

    return work_unit
```

Note: The IntegrityError needs special handling - we want to rollback on that error and raise a ValueError, which the context manager handles correctly.

Location: `src/orchestrator/state.py#StateStore.create_work_unit`

### Step 3: Wrap update_work_unit in a transaction

Modify `update_work_unit()` to wrap SELECT + UPDATE + conditional INSERT in an explicit transaction:

```python
def update_work_unit(self, work_unit: WorkUnit) -> WorkUnit:
    with self.transaction():
        # Get the old status for logging
        old_unit = self.get_work_unit(work_unit.chunk)
        if old_unit is None:
            raise ValueError(...)

        # ... UPDATE statement ...

        # Log status transition if status changed
        if old_unit.status != work_unit.status:
            self._log_status_transition(...)

    return work_unit
```

Location: `src/orchestrator/state.py#StateStore.update_work_unit`

### Step 4: Write unit tests for transaction atomicity

Add tests to `tests/test_orchestrator_state.py` that verify:

1. **Transaction context manager basics**: `BEGIN` is executed, `COMMIT` on success, `ROLLBACK` on exception
2. **create_work_unit atomicity**: If something fails after work unit insert but before status log, neither should persist
3. **update_work_unit atomicity**: Status log is only written if update succeeds

Test approach for atomicity verification:
- Use a mock or subclass to simulate failure after first statement
- Verify database state is consistent (either all changes or none)

Location: `tests/test_orchestrator_state.py`

### Step 5: Add documentation comment about dual-connection pattern

Add a comment in the `StateStore` class docstring (or as a separate code comment near the connection property) explaining that multiple StateStore instances may connect to the same database and why this is safe with WAL mode.

Location: `src/orchestrator/state.py#StateStore` class docstring or `connection` property

### Step 6: Run existing tests to verify no regressions

Execute `uv run pytest tests/test_orchestrator_state.py tests/test_orchestrator_*.py -v` to ensure:
- All existing state tests pass
- All orchestrator tests pass
- The transaction wrapper doesn't introduce deadlocks or behavioral changes

### Step 7: Manual testing of crash resilience

To verify atomicity, manually test (or create a test helper) that simulates process death:
1. Start a transaction
2. Complete the first statement
3. Raise an exception before commit
4. Verify database state is unchanged

This is primarily a confidence check that the context manager works correctly.

## Risks and Open Questions

1. **Nested transactions**: SQLite doesn't support true nested transactions. If code calls a method with a transaction from inside another transaction, we need to handle this. The simplest approach is to check if we're already in a transaction and skip BEGIN/COMMIT in that case. However, examining the code, none of the public methods call each other in ways that would create nesting.

2. **Long-held transactions**: The transaction should be short-lived. The current implementation keeps transactions brief (SELECT + UPDATE + INSERT), which is appropriate.

3. **Connection sharing between stores**: Two StateStore instances share the same database file but have separate connections. With WAL mode, read-read and read-write concurrency is safe. Write-write from different connections would block (one waits), but since operations are short, this is acceptable.

4. **Error handling in IntegrityError case**: When `create_work_unit` catches `IntegrityError`, the transaction should rollback. The context manager handles this via the exception propagation path.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
