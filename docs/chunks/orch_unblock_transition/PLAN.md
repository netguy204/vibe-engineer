<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk fixes three related bugs in the orchestrator's status transition logic:

1. **NEEDS_ATTENTION to READY transition on unblock**: When `_unblock_dependents()`
   removes the last blocker from a work unit's `blocked_by` list, the code checks
   for `status == BLOCKED` but the actual status is `NEEDS_ATTENTION`. This leaves
   work units orphaned. The fix extends the condition to also check for
   `NEEDS_ATTENTION` status.

2. **Stale `attention_reason` on status transitions**: The `attention_reason` field
   persists when work units transition to READY or RUNNING states. This causes
   confusing output in `ve orch ps`. The fix clears `attention_reason` whenever a
   work unit transitions to READY or RUNNING.

3. **Stale `blocked_by` when transitioning to RUNNING**: The `blocked_by` list is
   not cleared when work units start running, leading to confusing display. The
   fix clears `blocked_by` when a work unit transitions to RUNNING.

The implementation follows Test-Driven Development per docs/trunk/TESTING_PHILOSOPHY.md:
write failing tests first, then implement the fix, then verify tests pass.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS fixes to
  the Scheduler class within the orchestrator subsystem. The subsystem's invariant
  "Work unit transitions are logged for debugging" is maintained.

## Sequence

### Step 1: Write failing tests for NEEDS_ATTENTION to READY transition

Create tests in `tests/test_orchestrator_scheduler.py` that verify:

1. When a blocker completes and a work unit has `status=NEEDS_ATTENTION` with
   `blocked_by` becoming empty, it transitions to `status=READY`
2. The `attention_reason` field is cleared on this transition
3. Multiple work units blocked by the same chunk all transition correctly

Location: `tests/test_orchestrator_scheduler.py` (new test class `TestNeedsAttentionUnblock`)

These tests should fail initially because the current code only checks for
`status == BLOCKED` in `_unblock_dependents`.

### Step 2: Fix the NEEDS_ATTENTION to READY transition in scheduler

Modify `_unblock_dependents()` in `src/orchestrator/scheduler.py` to:

1. Check for both `BLOCKED` and `NEEDS_ATTENTION` statuses when determining if
   a work unit should transition to `READY` after its last blocker completes
2. Clear `attention_reason` when transitioning to `READY`

The existing code at lines 901-912:
```python
# If no more blockers and status is BLOCKED, transition to READY
if not unit.blocked_by and unit.status == WorkUnitStatus.BLOCKED:
    logger.info(
        f"Unblocking {unit.chunk} - blocker {completed_chunk} completed"
    )
    unit.status = WorkUnitStatus.READY
```

Should be extended to also handle `NEEDS_ATTENTION`:
```python
# If no more blockers and status is BLOCKED or NEEDS_ATTENTION, transition to READY
if not unit.blocked_by and unit.status in (
    WorkUnitStatus.BLOCKED, WorkUnitStatus.NEEDS_ATTENTION
):
    logger.info(
        f"Unblocking {unit.chunk} - blocker {completed_chunk} completed"
    )
    unit.status = WorkUnitStatus.READY
    unit.attention_reason = None  # Clear stale reason
```

Location: `src/orchestrator/scheduler.py#_unblock_dependents`

### Step 3: Write failing tests for attention_reason cleanup on transitions

Add tests that verify:

1. `attention_reason` is cleared when a work unit transitions to `READY` (via
   API update or scheduler phase advancement)
2. `attention_reason` is cleared when a work unit transitions to `RUNNING`
   (via scheduler dispatch)

Location: `tests/test_orchestrator_scheduler.py` (extend or add test class)

### Step 4: Clear attention_reason on READY transitions in scheduler

Modify `_advance_phase()` in `src/orchestrator/scheduler.py` to clear
`attention_reason` when transitioning to `READY` status (around line 709):

```python
work_unit.phase = next_phase
work_unit.status = WorkUnitStatus.READY
work_unit.session_id = None
work_unit.attention_reason = None  # Clear any stale reason
```

Location: `src/orchestrator/scheduler.py#_advance_phase`

### Step 5: Clear attention_reason and blocked_by on RUNNING transition

Modify `_run_work_unit()` in `src/orchestrator/scheduler.py` to clear both
`attention_reason` and `blocked_by` when transitioning to `RUNNING` (around
lines 417-420):

```python
work_unit.status = WorkUnitStatus.RUNNING
work_unit.worktree = str(worktree_path)
work_unit.attention_reason = None  # Clear any stale reason
work_unit.blocked_by = []  # Clear stale blockers
work_unit.updated_at = datetime.now(timezone.utc)
```

Location: `src/orchestrator/scheduler.py#_run_work_unit`

### Step 6: Write failing tests for blocked_by cleanup on RUNNING

Add tests that verify `blocked_by` is cleared when work units transition
to `RUNNING` status.

Location: `tests/test_orchestrator_scheduler.py`

### Step 7: Run all tests and verify existing tests still pass

Run the full test suite to ensure:
- New tests pass
- Existing orchestrator tests continue to pass
- No regressions introduced

```bash
uv run pytest tests/test_orchestrator_scheduler.py -v
```

### Step 8: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter with the files that were modified:
- `src/orchestrator/scheduler.py`
- `tests/test_orchestrator_scheduler.py`

## Risks and Open Questions

1. **WebSocket broadcast timing**: The scheduler already calls
   `broadcast_work_unit_update()` after updating work units. Need to verify that
   clearing `attention_reason` doesn't require a separate broadcast call for
   the attention queue.

2. **Race conditions with API updates**: The API at `api.py` also allows manual
   status updates. Should the API also clear `attention_reason`/`blocked_by` on
   transitions to READY/RUNNING? After review, the API's `update_work_unit_endpoint`
   doesn't automatically manage these fields - it trusts the caller. This is
   acceptable since the scheduler is the primary state machine manager.

3. **Backwards compatibility**: Existing work units may have stale `attention_reason`
   or `blocked_by` values. When they next transition, these will be cleared. This
   is the desired behavior.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->