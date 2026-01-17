<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk fixes two related bugs in the orchestrator's conflict resolution lifecycle:

**Bug 1** (resolve endpoint): The `resolve_conflict_endpoint` in `src/orchestrator/api.py`
correctly adds the other chunk to `blocked_by` on SERIALIZE verdict but fails to
transition the status to BLOCKED or clear the attention_reason. The fix adds these
two missing operations at lines 777-780.

**Bug 2** (automatic unblock): When a work unit transitions to DONE, no code scans
for units blocked by it. The fix adds a helper method `_unblock_dependents()` to the
scheduler that:
1. Queries all BLOCKED work units
2. Removes the completed chunk from their `blocked_by` lists
3. Transitions empty-blocked-by units to READY

The existing pattern for automatic status transitions is established in `api.py:782-789`
for the INDEPENDENT verdict case. We follow this pattern for consistency.

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`:
1. Write failing unit tests for the resolve endpoint status transition
2. Write failing unit tests for the automatic unblock logic
3. Implement the fixes
4. Write an integration test for the full lifecycle

## Subsystem Considerations

No subsystems are relevant to this work. The existing subsystems (`template_system`,
`workflow_artifacts`) do not govern orchestrator state management.

## Sequence

### Step 1: Write failing test for Bug 1 (SERIALIZE status transition)

Add test to `tests/test_orchestrator_api.py` that verifies:
- Create a work unit in NEEDS_ATTENTION state with an attention_reason
- Call resolve endpoint with SERIALIZE verdict
- Assert status transitions to BLOCKED
- Assert attention_reason is cleared
- Assert blocked_by contains the other chunk

Location: `tests/test_orchestrator_api.py`

### Step 2: Fix Bug 1 in resolve endpoint

Modify `resolve_conflict_endpoint` in `src/orchestrator/api.py` to:
- After adding to `blocked_by` for SERIALIZE verdict (line 780)
- Transition status from NEEDS_ATTENTION to BLOCKED
- Clear the attention_reason field

This mirrors the existing pattern at lines 786-789 for INDEPENDENT verdict.

Location: `src/orchestrator/api.py` (lines 777-780)

### Step 3: Write failing test for Bug 2 (automatic unblock)

Add test to `tests/test_orchestrator_scheduler.py` that verifies:
- Create two work units: A (RUNNING) and B (BLOCKED, blocked_by=[A])
- Transition A to DONE via `_advance_phase()` completion
- Assert B.blocked_by no longer contains A
- Assert B.status is READY

Location: `tests/test_orchestrator_scheduler.py`

### Step 4: Add StateStore method to find blocked units

Add `list_blocked_by_chunk(chunk: str)` method to StateStore that queries
work units where `blocked_by` JSON array contains the given chunk name.

SQLite JSON functions: `json_each()` can iterate over JSON arrays.

```sql
SELECT * FROM work_units
WHERE EXISTS (
    SELECT 1 FROM json_each(blocked_by) WHERE value = ?
)
```

Location: `src/orchestrator/state.py`

### Step 5: Implement automatic unblock in scheduler

Add `_unblock_dependents(completed_chunk: str)` method to Scheduler that:
1. Calls `store.list_blocked_by_chunk(completed_chunk)`
2. For each returned unit:
   - Remove completed_chunk from `blocked_by`
   - If `blocked_by` is now empty and status is BLOCKED, transition to READY
   - Call `store.update_work_unit(unit)`
3. Log each unblock operation

Call this method from `_advance_phase()` after setting status to DONE (line 660),
before returning.

Location: `src/orchestrator/scheduler.py` (after line 660)

### Step 6: Write integration test for full lifecycle

Add test to `tests/test_orchestrator_api.py` that exercises the complete flow:
1. Create chunk_a (READY) and chunk_b (READY)
2. Simulate conflict detection - move chunk_b to NEEDS_ATTENTION
3. Call resolve endpoint: serialize chunk_b after chunk_a
4. Verify chunk_b is BLOCKED
5. Transition chunk_a to DONE (via status update)
6. Verify chunk_b is now READY

This test validates the end-to-end behavior operators will experience.

Location: `tests/test_orchestrator_api.py`

### Step 7: Verify all tests pass

Run the full test suite to ensure:
- New tests pass
- Existing tests still pass (no regressions)

```bash
uv run pytest tests/test_orchestrator_api.py tests/test_orchestrator_scheduler.py -v
```

## Dependencies

None. All required infrastructure exists:
- `WorkUnitStatus.BLOCKED` is already defined in `models.py`
- StateStore update methods exist
- Resolve endpoint exists (just needs additional logic)
- `_advance_phase()` exists (just needs to call new unblock logic)

## Risks and Open Questions

**Risk: Race condition between scheduler and unblock**

The scheduler runs asynchronously. If `_unblock_dependents()` transitions a
work unit to READY at the same moment the scheduler is dispatching, there could
be a race. However, the scheduler already handles concurrent work unit updates
(multiple work units can complete simultaneously), and the SQLite connection
uses autocommit mode with proper locking. The existing patterns are sufficient.

**Open question: Should unblocking respect attention_reason?**

When a BLOCKED unit is unblocked, should we check if there's a stale
attention_reason that should be cleared? The current plan clears attention_reason
only at the resolve endpoint, not during automatic unblock. This seems correct
because:
1. BLOCKED status implies the conflict was resolved (via SERIALIZE verdict)
2. The attention_reason was already cleared when SERIALIZE was applied
3. If the attention_reason is still set, something unexpected happened

Decision: Don't clear attention_reason during automatic unblock. If this causes
issues, revisit.

## Deviations

<!-- Populate during implementation -->