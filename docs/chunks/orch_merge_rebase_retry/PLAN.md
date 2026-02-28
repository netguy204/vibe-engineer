# Implementation Plan

## Approach

This chunk implements automatic recovery from merge conflicts during finalization by cycling work units back to the REBASE phase. The implementation builds on existing infrastructure:

1. **Error classification in `finalize_work_unit`**: The current code catches `WorktreeError` generically. We need to distinguish merge conflicts from other finalization errors. The `WorktreeError` exceptions raised by `merge_without_checkout` (in `src/orchestrator/merge.py`) already include "Merge conflict" in the message, so we can detect them via string matching.

2. **Worktree recreation**: The `WorktreeManager.create_worktree` method already handles the case where the `orch/<chunk>` branch exists but no worktree is present — it creates a worktree from the existing branch. This is exactly what we need for recreation after a merge conflict.

3. **Retry counter on WorkUnit**: We'll add a `merge_conflict_retries` field to track how many times we've cycled back to REBASE due to merge conflicts. When this reaches 2, the third conflict escalates to NEEDS_ATTENTION.

4. **Idempotent COMPLETE phase**: The `/chunk-complete` skill and `verify_chunk_active_status` already handle re-entry when the chunk is ACTIVE (line 83-84 of `activation.py` checks for post-IMPLEMENTING status). We may need to ensure no errors are raised when re-completing an already-ACTIVE chunk.

The high-level flow:
```
finalize_work_unit() → merge_to_base() fails with merge conflict
    ↓
detect merge conflict (vs other errors)
    ↓
check merge_conflict_retries < 2
    ↓
recreate worktree from orch/<chunk> branch
    ↓
set phase=REBASE, status=READY, increment merge_conflict_retries
    ↓
agent rebases, resolves conflicts, runs tests
    ↓
REVIEW phase re-reviews the merged result
    ↓
COMPLETE phase (already ACTIVE, idempotent)
    ↓
finalize_work_unit() succeeds (or retry again if conflict)
```

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional recovery logic following the subsystem's patterns for work unit state transitions and finalization.

The orchestrator subsystem invariants that apply:
- Work unit transitions are logged for debugging
- Worktrees are isolated execution environments
- Daemon must broadcast state changes to dashboard

## Sequence

### Step 1: Add `merge_conflict_retries` field to WorkUnit model

Location: `src/orchestrator/models.py`

Add a new field to the `WorkUnit` model:
```python
merge_conflict_retries: int = 0  # Retry count for merge conflict recovery
```

Also update `model_dump_json_serializable()` to include this field.

### Step 2: Add database migration for `merge_conflict_retries`

Location: `src/orchestrator/state.py`

Add a migration to add the `merge_conflict_retries` column to the `work_units` table. Follow the existing migration pattern used for `api_retry_count`.

Update `_row_to_work_unit()` to read this new column.

### Step 3: Create helper to detect merge conflict errors

Location: `src/orchestrator/merge.py`

Add a helper function to classify `WorktreeError` exceptions:
```python
def is_merge_conflict_error(error: Union[WorktreeError, str]) -> bool:
    """Check if an error indicates a merge conflict vs other errors."""
    error_str = str(error) if isinstance(error, WorktreeError) else error
    return "Merge conflict" in error_str or "CONFLICT" in error_str
```

This centralizes the detection logic for reuse.

### Step 4: Extract merge-conflict recovery logic to a method

Location: `src/orchestrator/scheduler.py`

Add a new async method to the `Scheduler` class:
```python
async def _handle_merge_conflict_retry(
    self,
    work_unit: WorkUnit,
    error: WorktreeError,
) -> bool:
    """Handle merge conflict during finalization by cycling back to REBASE.

    Returns True if retry was initiated, False if escalated to NEEDS_ATTENTION.
    """
```

This method:
1. Checks if `work_unit.merge_conflict_retries >= 2` — if so, escalates to NEEDS_ATTENTION with a clear message about exceeding retry limit
2. Recreates the worktree from the surviving `orch/<chunk>` branch
3. Sets `phase=REBASE, status=READY`
4. Increments `merge_conflict_retries`
5. Persists the work unit
6. Broadcasts via WebSocket
7. Returns `True`

### Step 5: Modify `_finalize_completed_work_unit` to handle merge conflicts

Location: `src/orchestrator/scheduler.py`

In `_finalize_completed_work_unit()`, around line 1013-1032 where `finalize_work_unit()` is called and `WorktreeError` is caught:

1. Import `is_merge_conflict_error` from `orchestrator.merge`
2. In the `except WorktreeError` block:
   - Check `is_merge_conflict_error(e)`
   - If True, call `await self._handle_merge_conflict_retry(work_unit, e)`
   - If `_handle_merge_conflict_retry` returns `True`, return early (retry initiated)
   - If `False` (retry limit exceeded), the method already escalated to NEEDS_ATTENTION
   - If not a merge conflict, fall through to existing NEEDS_ATTENTION logic

### Step 6: Add worktree recreation method to WorktreeManager

Location: `src/orchestrator/worktree.py`

The current `create_worktree` method already handles this case, but we should add a more explicit helper for clarity:
```python
def recreate_worktree_from_branch(self, chunk: str) -> Path:
    """Recreate a worktree from an existing orch/<chunk> branch.

    Used for merge conflict recovery where the worktree was removed
    but the branch with committed work survives.

    Args:
        chunk: Chunk name

    Returns:
        Path to the recreated worktree

    Raises:
        WorktreeError: If branch doesn't exist or creation fails
    """
```

This method:
1. Verifies the `orch/<chunk>` branch exists
2. Creates a worktree pointing to that branch
3. Returns the worktree path

### Step 7: Verify COMPLETE phase idempotency

Location: `src/orchestrator/activation.py`

The `verify_chunk_active_status` function already returns `COMPLETED` for post-IMPLEMENTING statuses (ACTIVE, SUPERSEDED, HISTORICAL). This is the correct behavior.

Verify that `/chunk-complete` skill is idempotent — when called on an already-ACTIVE chunk, it should succeed without error. If it raises an error, we need to update the skill to handle this case.

Review the skill implementation (likely in `.claude/commands/chunk-complete.md.jinja2` or the rendered version).

### Step 8: Reset `merge_conflict_retries` on successful completion

Location: `src/orchestrator/scheduler.py`

In `_finalize_completed_work_unit`, after successful `finalize_work_unit()` call (line 1033-1040 area), reset the retry counter:
```python
work_unit.merge_conflict_retries = 0
```

This ensures the counter is clean for future work.

### Step 9: Write tests for merge conflict retry flow

Location: `tests/test_orchestrator_scheduler_merge_conflict.py` (new file)

Tests to write:

1. **test_merge_conflict_triggers_rebase_retry**:
   - Mock `finalize_work_unit` to raise `WorktreeError("Merge conflict...")`
   - Verify work unit transitions to REBASE phase, READY status
   - Verify `merge_conflict_retries` is incremented
   - Verify worktree recreation is called

2. **test_successful_retry_completes_normally**:
   - Set up work unit in COMPLETE phase with `merge_conflict_retries=1`
   - Verify normal finalization succeeds
   - Verify work unit transitions to DONE
   - Verify `merge_conflict_retries` is reset to 0

3. **test_third_conflict_escalates_to_needs_attention**:
   - Set up work unit with `merge_conflict_retries=2`
   - Mock merge conflict on finalization
   - Verify work unit transitions to NEEDS_ATTENTION
   - Verify `attention_reason` mentions retry limit exceeded
   - Verify no worktree recreation is attempted

4. **test_non_conflict_error_escalates_immediately**:
   - Mock `finalize_work_unit` to raise `WorktreeError("Failed to remove worktree...")`
   - Verify work unit transitions to NEEDS_ATTENTION immediately
   - Verify `merge_conflict_retries` is NOT incremented

5. **test_merge_conflict_detection**:
   - Unit test for `is_merge_conflict_error()` helper
   - Test various error message formats

### Step 10: Update conftest.py with scheduler fixtures if needed

Location: `tests/conftest.py`

Review if the existing scheduler fixtures are sufficient for the new tests. May need to add helpers for setting up work units in specific states.

## Risks and Open Questions

1. **Skill idempotency**: Need to verify `/chunk-complete` skill handles re-entry gracefully. If it errors on already-ACTIVE chunks, the retry flow will fail at the COMPLETE phase.

2. **Worktree state after conflict**: When `finalize_work_unit` fails on merge, the worktree has already been removed (step 2 of finalization is remove_worktree). We need to ensure the branch still exists and has the committed work. This should be the case since `finalize_work_unit` uses `remove_branch=False`.

3. **Agent context on retry**: When the agent runs REBASE after a merge conflict retry, it will have a fresh context. The GOAL.md should provide sufficient context for conflict resolution. May want to add the conflict error message to `attention_reason` temporarily to give the agent context.

4. **Race conditions**: If two chunks complete simultaneously and both hit merge conflicts with each other, the retry loop could theoretically continue indefinitely (each rebase succeeds, but merge conflicts again). The 2-retry limit prevents infinite loops.

5. **WebSocket broadcasting**: Need to ensure proper broadcasting of the phase/status change when cycling back to REBASE.

## Deviations

1. **Step 7 (COMPLETE phase idempotency)**: No changes were needed. The existing `verify_chunk_active_status` function already handles post-IMPLEMENTING statuses (ACTIVE, SUPERSEDED, HISTORICAL) as `COMPLETED`, which means the COMPLETE phase is already idempotent. When a chunk is already ACTIVE, verification returns `VerificationStatus.COMPLETED` and finalization proceeds normally.

2. **Step 10 (conftest.py fixtures)**: No changes needed. The existing scheduler fixtures in conftest.py were sufficient for all tests.

3. **Updated existing test**: Modified `test_advance_finalization_failure_marks_needs_attention` in `test_orchestrator_scheduler_dispatch.py` to use a non-merge-conflict error message ("Failed to remove worktree" instead of "Merge conflict") since the original message now triggers the new retry path rather than immediate escalation to NEEDS_ATTENTION.
