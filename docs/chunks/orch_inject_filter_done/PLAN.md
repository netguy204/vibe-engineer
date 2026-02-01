<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is straightforward: in `inject_endpoint` (src/orchestrator/api.py), before determining the initial status, filter the `blocked_by` list to remove any chunks that are already DONE. This requires:

1. Querying the store for each chunk in `blocked_by` to check its status
2. Keeping only chunks that are NOT DONE in the filtered list
3. Using the filtered list to determine both:
   - The initial status (READY if no remaining blockers, BLOCKED otherwise)
   - The stored `blocked_by` list (only non-DONE chunks)

This follows the existing pattern established by `orch_manual_done_unblock`, which handles the case where blockers transition to DONE *after* injection. This chunk handles the complementary case where blockers are *already* DONE at injection time.

**Testing Strategy** (per TESTING_PHILOSOPHY.md):
- Write tests FIRST that verify the behavior described in success criteria
- Tests will exercise the inject endpoint with various combinations of DONE and non-DONE blockers
- Tests will verify both the initial status and the stored `blocked_by` list

## Sequence

### Step 1: Write failing tests for DONE blocker filtering

Create tests in `tests/test_orchestrator_api.py` that verify:

1. **test_inject_filters_already_done_blocker**: Inject a chunk with `blocked_by=["done_chunk"]` where `done_chunk` exists and is DONE. Verify the injected work unit starts as READY with empty `blocked_by`.

2. **test_inject_filters_mixed_done_and_pending_blockers**: Inject a chunk with `blocked_by=["done_chunk", "pending_chunk"]` where `done_chunk` is DONE and `pending_chunk` is RUNNING. Verify the injected work unit starts as BLOCKED with `blocked_by=["pending_chunk"]` only.

3. **test_inject_keeps_all_blockers_when_none_done**: Inject with blockers where none are DONE. Verify existing behavior unchanged—status is BLOCKED with all blockers in the list.

4. **test_inject_nonexistent_blocker_kept**: Inject with a blocker that doesn't exist as a work unit. The blocker should be kept (we can't assume it's DONE) and the work unit starts as BLOCKED.

Location: `tests/test_orchestrator_api.py` - add a new test class `TestInjectFiltersDoneBlockers`

### Step 2: Implement the DONE blocker filtering in inject_endpoint

Modify `inject_endpoint` in `src/orchestrator/api.py`:

1. After validating `blocked_by` is a list, filter it to remove DONE chunks:
   ```python
   # Filter out already-DONE blockers from blocked_by
   active_blockers = []
   for blocker in blocked_by:
       blocker_unit = store.get_work_unit(blocker)
       # Keep blockers that don't exist (can't assume DONE) or aren't DONE
       if blocker_unit is None or blocker_unit.status != WorkUnitStatus.DONE:
           active_blockers.append(blocker)
   blocked_by = active_blockers
   ```

2. The existing logic `initial_status = WorkUnitStatus.BLOCKED if blocked_by else WorkUnitStatus.READY` will now correctly use the filtered list.

3. Add a backreference comment for this chunk.

Location: `src/orchestrator/api.py#inject_endpoint`

### Step 3: Verify tests pass

Run the new tests to confirm the implementation works correctly:
```bash
uv run pytest tests/test_orchestrator_api.py::TestInjectFiltersDoneBlockers -v
```

Also run the full orchestrator API test suite to ensure no regressions:
```bash
uv run pytest tests/test_orchestrator_api.py -v
```

## Dependencies

None. This chunk builds on existing infrastructure:
- `StateStore.get_work_unit()` - already exists for checking blocker status
- `WorkUnitStatus.DONE` - already defined
- `inject_endpoint` - the target function to modify

## Risks and Open Questions

**Decision: Non-existent blockers**

When a blocker chunk is specified but doesn't exist in the work pool (no WorkUnit record), what should happen?

Options considered:
1. Keep it in `blocked_by` (conservative - can't assume it's DONE)
2. Remove it (treat missing as implicitly DONE)
3. Reject the injection (strict validation)

**Decision**: Option 1 - Keep non-existent blockers. The orchestrator cannot know if a missing work unit represents:
- A chunk that will be injected later (should block)
- A chunk that was never injected (arguably shouldn't block)
- A typo (should be caught by validation elsewhere)

Being conservative matches the existing semantics where `blocked_by` is a trust-the-caller field. If the caller specifies a blocker, we respect it unless we have explicit evidence (WorkUnit with status=DONE) that it's complete.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->