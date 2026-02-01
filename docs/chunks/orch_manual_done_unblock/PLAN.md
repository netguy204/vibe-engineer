<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `_unblock_dependents` method in the scheduler already handles unblocking when a work unit transitions to DONE. The problem is that this method is only called from `_advance_phase` within the scheduler's internal flow. When a work unit status is manually set to DONE via the API (e.g., after `/orchestrator-investigate` resolves a merge conflict), `_unblock_dependents` is never called.

The solution is to extract `_unblock_dependents` to a module-level function and call it from:
1. The existing `_advance_phase` location (via a thin wrapper for backward compatibility)
2. The `update_work_unit_endpoint` in `api.py` when status changes to DONE
3. The `retry_merge_endpoint` in `api.py` after a successful merge retry

This follows the existing pattern where the scheduler's internal logic is kept in `scheduler.py` but exposed for API use when needed.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk IMPLEMENTS additional triggering points for the existing unblock logic. The subsystem already defines the unblock behavior pattern (removing chunks from `blocked_by` and transitioning BLOCKED/NEEDS_ATTENTION to READY). This chunk extends where that logic is invoked, not how it works.

## Sequence

### Step 1: Write failing test for manual DONE transition via API

Write a test that:
1. Creates two work units: `blocker_chunk` (DONE) and `dependent_chunk` (BLOCKED with `blocked_by=["blocker_chunk"]`)
2. Simulates what happens when `blocker_chunk` transitions to DONE via API (not scheduler)
3. Asserts that `dependent_chunk` should transition to READY with `blocked_by=[]`

This test will fail because the API doesn't call unblock logic.

Location: tests/test_orchestrator_scheduler.py (new test class `TestManualDoneUnblock`)

### Step 2: Extract `_unblock_dependents` to module-level function

Move the existing `_unblock_dependents` logic from `Scheduler._unblock_dependents` to a module-level function `unblock_dependents(store: StateStore, completed_chunk: str)` that:
1. Takes the StateStore and completed chunk name as parameters
2. Contains the existing unblock logic (find blocked work units, remove from blocked_by, transition BLOCKED/NEEDS_ATTENTION to READY)
3. Is synchronous (the existing method is sync)

Keep `Scheduler._unblock_dependents` as a thin wrapper that calls the module-level function for backward compatibility.

Location: src/orchestrator/scheduler.py

### Step 3: Add unblock call to `update_work_unit_endpoint`

In `api.py`, modify `update_work_unit_endpoint` to call `unblock_dependents` when:
1. The status field is being updated
2. The new status is DONE
3. The old status was not DONE (to avoid redundant calls)

Import `unblock_dependents` from `scheduler.py`.

Location: src/orchestrator/api.py

### Step 4: Add unblock call to `retry_merge_endpoint`

In `api.py`, modify `retry_merge_endpoint` to call `unblock_dependents` after a successful merge marks the work unit as DONE.

This endpoint already sets status to DONE on success, but doesn't trigger unblock.

Location: src/orchestrator/api.py

### Step 5: Verify test passes and add additional test cases

Run the test from Step 1 and verify it passes. Add additional test cases:
1. Test that manual DONE via API unblocks multiple dependent work units
2. Test that manual DONE via API handles partial unblock (dependent has multiple blockers)
3. Test that retry-merge success triggers unblock
4. Test that existing scheduler-driven unblock still works (regression test)

Location: tests/test_orchestrator_scheduler.py

### Step 6: Add backreference comments

Add chunk backreference comments to the modified functions:
- `unblock_dependents` function
- `update_work_unit_endpoint` (at the unblock call site)
- `retry_merge_endpoint` (at the unblock call site)

## Dependencies

None. The existing `_unblock_dependents` method and `list_blocked_by_chunk` StateStore method provide all the foundation needed.

## Risks and Open Questions

1. **WebSocket broadcasting**: The existing `_unblock_dependents` doesn't broadcast WebSocket updates for the unblocked work units. The API endpoints already broadcast after updating, but we should verify the order of operations doesn't cause race conditions or missed broadcasts. The pattern is: update state → broadcast.

2. **Concurrency**: If the scheduler is running and a manual DONE transition happens simultaneously, there could be a race where both try to unblock dependents. The existing logic is idempotent (removing a chunk from blocked_by that's already removed is a no-op), so this should be safe, but worth noting.

3. **Import cycle**: Importing from `scheduler.py` into `api.py` could create an import cycle if `scheduler.py` imports from `api.py`. A quick check shows `scheduler.py` doesn't import from `api.py`, so this is safe.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->