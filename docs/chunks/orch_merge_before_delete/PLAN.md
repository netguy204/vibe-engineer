# Implementation Plan

## Approach

Swap the order of `remove_worktree` and `merge_to_base` in the `Scheduler._advance_phase` completion flow. The `orch_merge_safety` chunk (ACTIVE) already implemented checkout-free merging via git plumbing (`merge-tree`, `commit-tree`, `update-ref`), which means the worktree's existence no longer interferes with the merge operation. The stale comment claiming the worktree "must be done before merge" predates that work.

**Strategy:**
1. Reorder the operations: attempt merge first, only remove worktree on success
2. Remove the stale comment
3. Ensure merge failure leaves the worktree intact for investigation
4. Add a test verifying the new behavior (worktree persists on merge failure)

This is a minimal, surgical change. The `retain_worktree` path remains unchanged (it skips both merge and deletion). The happy path remains unchanged (merge succeeds, then worktree is removed). Only the failure path changes: now the worktree survives for debugging.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the orchestrator subsystem's scheduler component. The change aligns with the subsystem's invariant that "worktrees are isolated execution environments" - keeping them around on failure makes investigation easier.

## Sequence

### Step 1: Reorder operations in `_advance_phase`

Location: `src/orchestrator/scheduler.py` (~lines 1036-1078)

In the `else` branch (non-`retain_worktree` path):
1. Remove the stale comment `# Remove the worktree (must be done before merge)`
2. Move the merge attempt (`merge_to_base` and `has_changes` check) BEFORE `remove_worktree`
3. Only call `remove_worktree` if the merge succeeds or there were no changes to merge
4. When merge fails, the worktree is NOT removed - the work unit goes to NEEDS_ATTENTION with the worktree still intact

**Before:**
```python
else:
    # Remove the worktree (must be done before merge)
    try:
        self.worktree_manager.remove_worktree(chunk, remove_branch=False)
    except WorktreeError as e:
        logger.warning(f"Failed to remove worktree for {chunk}: {e}")

    # Merge the branch back to base if it has changes
    try:
        if self.worktree_manager.has_changes(chunk):
            # ... merge logic
        else:
            # ... skip merge, clean up branch
    except WorktreeError as e:
        # Mark as needs attention - but worktree is already gone!
```

**After:**
```python
else:
    # Chunk: docs/chunks/orch_merge_before_delete - Merge before worktree removal
    # Merge first so worktree remains available for investigation if merge fails
    merge_succeeded = False
    try:
        if self.worktree_manager.has_changes(chunk):
            logger.info(
                f"Merging {chunk} branch back to "
                f"{self.worktree_manager.base_branch}"
            )
            self.worktree_manager.merge_to_base(chunk, delete_branch=True)
        else:
            logger.info(f"No changes in {chunk}, skipping merge")
            # Clean up the empty branch
            # ... existing branch cleanup logic
        merge_succeeded = True
    except WorktreeError as e:
        logger.error(f"Failed to merge {chunk} to base: {e}")
        # Mark as needs attention - worktree remains for investigation
        # ... existing needs_attention handling, then return

    # Only remove worktree after successful merge
    try:
        self.worktree_manager.remove_worktree(chunk, remove_branch=False)
    except WorktreeError as e:
        logger.warning(f"Failed to remove worktree for {chunk}: {e}")
```

### Step 2: Update existing test to verify new order

Location: `tests/test_orchestrator_scheduler.py`

Find the test `test_advance_completes_work_unit` (around line 230-267) which verifies that `remove_worktree` is called. Update it to also verify:
1. `has_changes` or `merge_to_base` is called BEFORE `remove_worktree`
2. Use mock call ordering assertions to verify the sequence

### Step 3: Add test for merge failure with worktree preservation

Location: `tests/test_orchestrator_scheduler.py`

Add a new test `test_advance_merge_failure_preserves_worktree` that:
1. Sets up a work unit in COMPLETE phase
2. Configures `mock_worktree_manager.has_changes.return_value = True`
3. Configures `mock_worktree_manager.merge_to_base.side_effect = WorktreeError("Merge conflict")`
4. Calls `scheduler._advance_phase(work_unit)`
5. Asserts:
   - Work unit status is `NEEDS_ATTENTION`
   - Work unit `attention_reason` contains "Merge to base failed"
   - `mock_worktree_manager.remove_worktree` was NOT called (the key assertion!)

This test explicitly verifies the goal: when merge fails, the worktree remains.

### Step 4: Run tests and verify

Run `uv run pytest tests/test_orchestrator_scheduler.py -v` to ensure:
- All existing tests pass (no regressions)
- New merge failure test passes
- Order verification test passes

## Risks and Open Questions

- **Minimal**: The change is straightforward reordering. The `retain_worktree` path is untouched.
- **Edge case**: If `remove_worktree` fails after a successful merge, we log a warning but proceed. This matches existing behavior.
- **Branch cleanup**: In the no-changes path, we still delete the empty branch before removing the worktree. This is fine because there's nothing to merge back anyway.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->
