<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Fix the resource leak in `_run_work_unit()` by tracking whether the worktree was successfully created and cleaning it up when activation fails. The fix follows the existing cleanup pattern used in `_advance_phase()` at line 1027.

The key insight is that the current code structure creates a worktree at line 722, then attempts to activate the chunk at line 726. If activation fails (lines 730-733), the method returns early without cleaning up the worktree created on line 722. The fix adds tracking of worktree creation success and ensures cleanup on the activation failure path.

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md, we write the failing test first, then implement the fix.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a bug fix within the scheduler, which is part of the orchestrator subsystem. The invariant "Worktrees are isolated execution environments" is being maintained by ensuring proper cleanup prevents orphaned worktrees.

## Sequence

### Step 1: Write failing test for activation failure cleanup

Create a test in `tests/test_orchestrator_scheduler.py` that verifies worktree cleanup when `activate_chunk_in_worktree()` raises a `ValueError`. The test should:
- Mock the worktree_manager to track `remove_worktree` calls
- Mock `activate_chunk_in_worktree` to raise `ValueError`
- Verify that `remove_worktree(chunk, remove_branch=False)` is called after activation failure

Location: `tests/test_orchestrator_scheduler.py`

### Step 2: Implement worktree tracking and cleanup on activation failure

Modify `_run_work_unit()` to:
1. Add a local variable `worktree_created = False` after the worktree is created successfully (after line 722)
2. Set `worktree_created = True` after `create_worktree()` succeeds
3. In the `except ValueError` block (lines 730-733), before returning, add cleanup:
   ```python
   if worktree_created:
       try:
           self.worktree_manager.remove_worktree(chunk, remove_branch=False)
           logger.info(f"Cleaned up worktree for {chunk} after activation failure")
       except WorktreeError as cleanup_error:
           logger.warning(f"Failed to clean up worktree for {chunk}: {cleanup_error}")
   ```

This pattern matches the cleanup at line 1027 which uses `remove_branch=False`.

Location: `src/orchestrator/scheduler.py`

### Step 3: Verify the test passes

Run the new test to confirm the fix works correctly.

### Step 4: Add edge case test - cleanup failure is logged but doesn't crash

Add a test that verifies if `remove_worktree` itself raises an exception during cleanup, the error is logged but doesn't prevent the original attention marking from completing.

Location: `tests/test_orchestrator_scheduler.py`

### Step 5: Update code_paths in GOAL.md

Update the `code_paths` frontmatter field to reflect the files touched.

---

**BACKREFERENCE COMMENTS**

Add chunk backreference to the new cleanup code:
```python
# Chunk: docs/chunks/orch_worktree_cleanup - Worktree cleanup on activation failure
```

## Risks and Open Questions

1. **Race conditions**: The `finally` block runs async with a lock. The cleanup happens before `finally` and outside the lock, which should be safe since the worktree is not yet associated with any running agent state. The cleanup is purely filesystem cleanup.

2. **Branch cleanup**: Using `remove_branch=False` is intentional - the branch was just created and may be useful for debugging. This matches the pattern at line 1027 where the branch is only deleted during merge operations.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->