<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The orchestrator uses separate `StateStore` instances for the scheduler and the API (by
design, for SQLite WAL-mode concurrent access). This creates a race condition where:

1. The scheduler reads a work unit, holds it in memory
2. The API updates the same work unit (e.g., priority change)
3. The scheduler writes its now-stale version back, silently overwriting the API's change

We fix this with **optimistic locking**—a standard concurrency control pattern:

1. Add a `StaleWriteError` exception to `state.py`
2. Modify `update_work_unit` to accept an optional `expected_updated_at` parameter
3. Before writing, verify the work unit's current `updated_at` matches the expected value
4. If it doesn't match, raise `StaleWriteError` instead of silently overwriting
5. Callers can catch this error and re-read/retry or skip the update

The key insight is that callers always have the `updated_at` from when they read the
work unit. By passing this as an expectation, we can detect when someone else has
modified the record.

For the scheduler, we wrap critical update paths with retry logic: on `StaleWriteError`,
re-read the work unit and either retry the operation or skip it (depending on whether
the re-read state makes the operation moot).

The API endpoints already read-modify-write in a single request, so they benefit from
optimistic locking automatically—a concurrent modification will raise an error that
the API can return as a 409 Conflict response.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS optimistic
  locking for the state store, which is a core component of the orchestrator subsystem.
  The change follows the existing pattern of exception classes in the orchestrator
  package (e.g., `WorktreeError`, `SchedulerError`).

## Sequence

### Step 1: Add StaleWriteError exception

Create a new exception class in `src/orchestrator/state.py`:

```python
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
class StaleWriteError(Exception):
    """Raised when a work unit has been modified since it was read.

    This indicates a concurrent modification - another process updated
    the work unit between when the caller read it and attempted to write.
    The caller should re-read the work unit and retry or skip the operation.

    Attributes:
        chunk: The chunk name that was being updated
        expected_updated_at: The timestamp the caller expected
        actual_updated_at: The current timestamp in the database
    """
    def __init__(self, chunk: str, expected_updated_at: datetime, actual_updated_at: datetime):
        self.chunk = chunk
        self.expected_updated_at = expected_updated_at
        self.actual_updated_at = actual_updated_at
        super().__init__(
            f"Stale write detected for work unit '{chunk}': "
            f"expected updated_at={expected_updated_at.isoformat()}, "
            f"actual={actual_updated_at.isoformat()}"
        )
```

Location: `src/orchestrator/state.py`, near other exception classes.

Also export it from `src/orchestrator/__init__.py`.

### Step 2: Modify update_work_unit signature

Update `StateStore.update_work_unit` to accept an optional `expected_updated_at`:

```python
def update_work_unit(
    self,
    work_unit: WorkUnit,
    expected_updated_at: Optional[datetime] = None,
) -> WorkUnit:
```

When `expected_updated_at` is provided:
1. Within the transaction, after fetching the old unit, compare `old_unit.updated_at`
   with `expected_updated_at`
2. If they don't match, raise `StaleWriteError(chunk, expected_updated_at, old_unit.updated_at)`
3. If they match (or `expected_updated_at` is None), proceed with the update

The None case provides backward compatibility—existing callers that don't pass the
parameter continue to work without optimistic locking.

Location: `src/orchestrator/state.py:476`

### Step 3: Write failing test for stale write detection

Before modifying the scheduler, write a test that verifies the stale write detection:

```python
class TestOptimisticLocking:
    """Tests for optimistic locking in work unit updates."""

    def test_stale_write_raises_error(self, store, sample_work_unit):
        """Updating with stale expected_updated_at raises StaleWriteError."""
        store.create_work_unit(sample_work_unit)

        # Simulate another process updating the work unit
        unit = store.get_work_unit(sample_work_unit.chunk)
        stale_timestamp = unit.updated_at

        unit.status = WorkUnitStatus.RUNNING
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)  # This advances updated_at

        # Now try to update with the stale timestamp
        unit2 = store.get_work_unit(sample_work_unit.chunk)
        unit2.priority = 999
        unit2.updated_at = datetime.now(timezone.utc)

        with pytest.raises(StaleWriteError) as exc_info:
            store.update_work_unit(unit2, expected_updated_at=stale_timestamp)

        assert exc_info.value.chunk == sample_work_unit.chunk
        assert exc_info.value.expected_updated_at == stale_timestamp

    def test_update_without_expected_timestamp_succeeds(self, store, sample_work_unit):
        """Updates without expected_updated_at bypass optimistic locking."""
        store.create_work_unit(sample_work_unit)

        unit = store.get_work_unit(sample_work_unit.chunk)
        unit.priority = 100
        unit.updated_at = datetime.now(timezone.utc)

        # Should succeed even without passing expected_updated_at
        updated = store.update_work_unit(unit)
        assert updated.priority == 100

    def test_update_with_matching_timestamp_succeeds(self, store, sample_work_unit):
        """Updates with matching expected_updated_at succeed."""
        store.create_work_unit(sample_work_unit)

        unit = store.get_work_unit(sample_work_unit.chunk)
        expected = unit.updated_at
        unit.priority = 200
        unit.updated_at = datetime.now(timezone.utc)

        updated = store.update_work_unit(unit, expected_updated_at=expected)
        assert updated.priority == 200
```

Location: `tests/test_orchestrator_state.py`

### Step 4: Add scheduler helper for retry-on-stale

Create a helper function or decorator in the scheduler for the common pattern of
"try to update, and if stale, re-read and decide whether to retry":

```python
def _update_with_retry(
    self,
    work_unit: WorkUnit,
    max_retries: int = 3,
) -> WorkUnit:
    """Update a work unit with retry on stale write.

    If a StaleWriteError is raised, re-reads the work unit and retries.
    Returns the updated work unit from the successful write.

    Raises StaleWriteError if max_retries exceeded.
    """
    expected_updated_at = work_unit.updated_at

    for attempt in range(max_retries):
        try:
            work_unit.updated_at = datetime.now(timezone.utc)
            return self.store.update_work_unit(work_unit, expected_updated_at=expected_updated_at)
        except StaleWriteError:
            if attempt == max_retries - 1:
                raise
            # Re-read and retry
            fresh = self.store.get_work_unit(work_unit.chunk)
            if fresh is None:
                raise ValueError(f"Work unit {work_unit.chunk} was deleted during update")
            # Copy over the changes we wanted to make
            # (caller needs to reapply their changes - this is a design choice)
            logger.warning(
                f"Stale write for {work_unit.chunk}, retrying (attempt {attempt + 2})"
            )
            work_unit = fresh
            expected_updated_at = fresh.updated_at
```

However, a simpler approach is to just catch `StaleWriteError` at each call site
and decide contextually whether to retry. Many scheduler updates are "fire and forget"—
if someone else updated the work unit, the scheduler's update might be moot anyway.

**Decision**: Start with explicit handling at key call sites rather than a generic
retry helper. This gives us more control over what happens when a stale write is
detected (sometimes we want to skip, sometimes retry with fresh data).

Location: `src/orchestrator/scheduler.py`

### Step 5: Update key scheduler call sites

Review all `store.update_work_unit()` calls in the scheduler and add optimistic
locking where it protects against data loss.

**Critical call sites** (where losing an API update is unacceptable):

1. `_dispatch_tick` (line ~434) - dispatching a work unit
   - Pass `expected_updated_at=work_unit.updated_at`
   - On stale write: re-read, check if still READY. If not, skip dispatch.

2. `_handle_agent_result` - after agent completion
   - Pass expected timestamp
   - On stale: re-read, the result handling might need to be skipped if status changed

3. `_mark_needs_attention` - marking work unit for operator attention
   - Pass expected timestamp
   - On stale: re-read, skip if status is already DONE or different

**Lower-risk call sites** (where stale write is less critical):

4. Conflict verdict caching - can be retried
5. Blocked_by updates - can be retried

For the critical sites, wrap in try/except and log when skipping due to stale data:

```python
try:
    self.store.update_work_unit(work_unit, expected_updated_at=original_updated_at)
except StaleWriteError as e:
    logger.warning(f"Skipping stale update for {work_unit.chunk}: {e}")
    # Re-read to see current state
    fresh = self.store.get_work_unit(work_unit.chunk)
    if fresh is None or fresh.status == WorkUnitStatus.DONE:
        # Someone else completed it - nothing to do
        return
    # Decide based on context whether to retry
```

Location: `src/orchestrator/scheduler.py`, multiple methods

### Step 6: Update API endpoint error handling

Modify `update_work_unit_endpoint` in `src/orchestrator/api/work_units.py` to:

1. Capture the `updated_at` when reading the work unit
2. Pass it as `expected_updated_at` when calling `store.update_work_unit`
3. Catch `StaleWriteError` and return HTTP 409 Conflict

```python
async def update_work_unit_endpoint(request: Request) -> JSONResponse:
    chunk = request.path_params["chunk"]
    store = get_store(request)

    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at
    old_status = unit.status

    # ... (field updates) ...

    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(unit, expected_updated_at=expected_updated_at)
    except StaleWriteError as e:
        return JSONResponse(
            {"error": "Concurrent modification detected", "detail": str(e)},
            status_code=409,
        )
    except ValueError as e:
        return error_response(str(e))
```

Also update other API endpoints that call `update_work_unit`:
- `src/orchestrator/api/scheduling.py` - `set_priority_endpoint`
- `src/orchestrator/api/attention.py` - `resolve_attention_endpoint`
- `src/orchestrator/api/conflicts.py` - conflict resolution endpoints
- `src/orchestrator/api/worktrees.py` - prune endpoints

Location: Multiple files in `src/orchestrator/api/`

### Step 7: Write integration test for scheduler/API race

Create a test that demonstrates the race condition protection:

```python
class TestSchedulerApiRace:
    """Tests for scheduler/API concurrent modification protection."""

    async def test_api_update_not_lost_during_scheduler_update(self, store):
        """API-driven priority change is not silently overwritten by scheduler."""
        # Setup: Create a READY work unit
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="race_test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            priority=0,
            created_at=now,
            updated_at=now,
        )
        store.create_work_unit(unit)

        # Simulate scheduler reading the work unit
        scheduler_view = store.get_work_unit("race_test")
        scheduler_expected = scheduler_view.updated_at

        # Simulate API updating priority while scheduler has stale view
        api_view = store.get_work_unit("race_test")
        api_view.priority = 100
        api_view.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(api_view, expected_updated_at=api_view.updated_at)

        # Now scheduler tries to update with stale data
        scheduler_view.status = WorkUnitStatus.RUNNING
        scheduler_view.updated_at = datetime.now(timezone.utc)

        with pytest.raises(StaleWriteError):
            store.update_work_unit(scheduler_view, expected_updated_at=scheduler_expected)

        # Verify API's priority change was preserved
        final = store.get_work_unit("race_test")
        assert final.priority == 100
```

Location: `tests/test_orchestrator_state.py`

### Step 8: Verify all existing tests pass

Run the full test suite to ensure backward compatibility:

```bash
uv run pytest tests/test_orchestrator_*.py -v
```

All existing tests should pass since we made `expected_updated_at` optional.

### Step 9: Update code_paths in GOAL.md

Add the files touched to the chunk's GOAL.md frontmatter:

```yaml
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
```

## Dependencies

- **sqlite_json_query_fix** (already ACTIVE): The chunk depends on this because both
  touch `state.py`. The JSON query fixes are already merged, so this chunk can proceed.

## Risks and Open Questions

1. **Retry loop complexity in scheduler**: The scheduler has many `update_work_unit`
   calls. Adding retry logic to each increases complexity. We mitigate this by:
   - Making `expected_updated_at` optional (backward compatible)
   - Starting with critical call sites only
   - Using contextual skip/retry decisions rather than generic retry wrapper

2. **Performance impact**: Optimistic locking adds a comparison before each write.
   This is negligible—SQLite already reads the row for the transaction, and a
   datetime comparison is trivial.

3. **Timestamp precision**: SQLite stores timestamps as ISO strings. Ensure
   `datetime.fromisoformat()` round-trips correctly. The existing code already
   does this, so this is low risk.

4. **API backward compatibility**: The HTTP client may not expect 409 responses.
   The `OrchestratorClient.update_work_unit` method should handle this gracefully
   or document it. Consider updating the client to raise a specific exception
   for 409 responses.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->