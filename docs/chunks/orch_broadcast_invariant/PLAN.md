# Implementation Plan

## Approach

Fix the missing WebSocket broadcasts in the scheduler by adding `broadcast_work_unit_update()` calls at two locations where work unit state changes occur without notification to the dashboard:

1. **RUNNING transition** (line 405-409): When a work unit transitions from READY to RUNNING during `_run_work_unit()`
2. **READY transition on phase advance** (line 686-693): When a work unit advances phases and becomes READY in `_advance_phase()`

Additionally, establish discoverable documentation for the broadcast invariant by adding a prominent docstring to the Scheduler class that states the rule and provides an example pattern.

The existing code already correctly broadcasts in `_mark_needs_attention()`, `_handle_agent_result()` (for suspended results), and during merge errors in `_advance_phase()`. We follow these established patterns.

**Testing Strategy**: Per docs/trunk/TESTING_PHILOSOPHY.md, we write tests that verify the semantic behavior (broadcasts were sent) rather than just implementation details. We mock the broadcast functions to verify they are called with the correct parameters.

## Subsystem Considerations

No existing subsystems are directly relevant to this work. The template_system and workflow_artifacts subsystems do not cover orchestrator WebSocket patterns.

This chunk does NOT propose creating a new subsystem. The broadcast invariant is a localized pattern within the scheduler/API layer that doesn't warrant the overhead of a full subsystem document.

## Sequence

### Step 1: Add broadcast for RUNNING transition

Add `broadcast_work_unit_update()` call immediately after the work unit status is updated to RUNNING in `_run_work_unit()`.

**Location**: `src/orchestrator/scheduler.py` around line 409, after `self.store.update_work_unit(work_unit)`

**Code pattern** (follow existing patterns in `_mark_needs_attention()`):
```python
# Broadcast via WebSocket so dashboard updates
await broadcast_work_unit_update(
    chunk=work_unit.chunk,
    status=work_unit.status.value,
    phase=work_unit.phase.value,
)
```

### Step 2: Add broadcast for phase advance READY transition

Add `broadcast_work_unit_update()` call immediately after the work unit is updated to READY with a new phase in `_advance_phase()`.

**Location**: `src/orchestrator/scheduler.py` around line 693, after `self.store.update_work_unit(work_unit)` in the "else" branch

**Code pattern**:
```python
# Chunk: docs/chunks/orch_broadcast_invariant - Broadcast phase advancement
# Broadcast via WebSocket so dashboard updates
await broadcast_work_unit_update(
    chunk=work_unit.chunk,
    status=work_unit.status.value,
    phase=work_unit.phase.value,
)
```

### Step 3: Add broadcast for DONE transition

When a work unit completes (transitions to DONE), the dashboard should also be notified. This occurs at the end of the completion flow in `_advance_phase()`.

**Location**: `src/orchestrator/scheduler.py` around line 681-684, after `self.store.update_work_unit(work_unit)` sets status to DONE

**Code pattern**:
```python
# Chunk: docs/chunks/orch_broadcast_invariant - Broadcast completion
# Broadcast via WebSocket so dashboard updates
await broadcast_work_unit_update(
    chunk=work_unit.chunk,
    status=work_unit.status.value,
    phase=work_unit.phase.value,
)
```

### Step 4: Document the broadcast invariant in Scheduler class docstring

Update the Scheduler class docstring to establish the broadcast invariant clearly. This makes the requirement discoverable by agents modifying scheduler code.

**Location**: `src/orchestrator/scheduler.py`, Scheduler class docstring (around line 203-208)

**Updated docstring**:
```python
class Scheduler:
    """Manages work unit scheduling and agent dispatch.

    The scheduler maintains a pool of running agents and dispatches
    work units from the ready queue when slots are available.

    INVARIANT - WebSocket Broadcasting:
        Every work unit state change MUST call broadcast_work_unit_update()
        after updating the database. This ensures the dashboard receives
        real-time notifications. State changes include:
        - READY → RUNNING (dispatch)
        - Phase advancement (READY with new phase)
        - RUNNING → NEEDS_ATTENTION (error/question)
        - Completion (DONE)

        Pattern:
            work_unit.status = WorkUnitStatus.RUNNING
            self.store.update_work_unit(work_unit)
            await broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )

        See also: src/orchestrator/api.py which follows this invariant.
    """
```

### Step 5: Write tests for broadcast calls

Add tests to `tests/test_orchestrator_scheduler.py` that verify broadcast functions are called for each state transition. Use mocking to intercept the broadcast calls.

**Test cases**:
1. `test_run_work_unit_broadcasts_running_status` - Verify broadcast called when transitioning to RUNNING
2. `test_advance_phase_broadcasts_ready_status` - Verify broadcast called when advancing phases
3. `test_advance_phase_broadcasts_done_status` - Verify broadcast called when completing

**Testing approach** (per TESTING_PHILOSOPHY.md - test behavior, not implementation):
```python
@pytest.mark.asyncio
async def test_run_work_unit_broadcasts_running_status(
    scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
):
    """Dispatching a work unit broadcasts RUNNING status via WebSocket."""
    # Set up chunk...

    with patch('orchestrator.scheduler.broadcast_work_unit_update') as mock_broadcast:
        await scheduler._run_work_unit(work_unit)

        # Verify broadcast was called with RUNNING status
        mock_broadcast.assert_called()
        calls = [c for c in mock_broadcast.call_args_list
                 if c.kwargs.get('status') == 'RUNNING']
        assert len(calls) >= 1
```

### Step 6: Run tests and verify

Run the test suite to ensure:
1. New tests pass
2. Existing tests still pass
3. No regressions introduced

```bash
uv run pytest tests/test_orchestrator_scheduler.py -v
```

## Risks and Open Questions

1. **Race condition investigation (GOAL item 3)**: The GOAL mentions that NEEDS_ATTENTION broadcasts exist but may not be reaching the dashboard. After code review, the broadcast code at lines 888-894 (`_mark_needs_attention`) appears correct. This may be a timing issue or test environment artifact. If the issue persists after this chunk, it warrants a separate investigation.

2. **Test isolation**: The scheduler tests use mocks extensively. Adding broadcast mocking should not interfere with existing test fixtures, but we should verify no test pollution occurs.

3. **Async timing**: Broadcast calls are async. If an exception occurs between database update and broadcast, the dashboard would be out of sync. However, this is consistent with existing behavior and fixing it is out of scope.

## Deviations

- **Step 5 (Tests)**: Added a fourth test `test_mark_needs_attention_broadcasts_status` beyond the three planned tests. This test verifies that the existing `_mark_needs_attention()` method correctly broadcasts NEEDS_ATTENTION status. While this functionality already existed, adding a test documents the invariant and prevents regressions.