<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The current orchestrator creates worktrees at inject time (when `ve orch inject` is called). This is problematic because:

1. Blocked work gets a worktree reflecting stale state (before dependencies complete)
2. Work waiting in the READY queue consumes resources unnecessarily
3. The worktree doesn't reflect the current HEAD when work actually starts

The fix: Move worktree creation from inject time to dispatch time (when `Scheduler._run_work_unit()` is called). This is a focused refactor that:

1. **Removes worktree creation from inject** - Currently `inject_endpoint` in `api.py` only creates the work unit (no worktree), so this is already correct. The worktree is created in `Scheduler._run_work_unit()`.

2. **Verifies blocked work behavior** - Work units with `blocked_by` dependencies transition through BLOCKED → READY → RUNNING. Worktree creation happens at the RUNNING transition, which means blocked work gets a worktree from current HEAD only when dependencies complete.

3. **Adds tests to verify deferred creation** - Integration tests that verify:
   - Inject creates work unit but NOT a worktree
   - Worktree is created only when transitioning to RUNNING
   - Blocked work gets worktree after dependency completion

After examining the codebase, **the current implementation already defers worktree creation to dispatch time** (in `_run_work_unit`). The work for this chunk is primarily:
- Adding tests that explicitly verify this behavior (currently not tested)
- Ensuring blocked work correctly defers worktree creation
- Documenting this as an architectural invariant

## Subsystem Considerations

No subsystems are relevant to this chunk. The `template_system` and `workflow_artifacts` subsystems don't touch orchestrator scheduling logic.

## Sequence

### Step 1: Write failing test - inject does not create worktree

Create a test that verifies `ve orch inject` creates a work unit but does NOT create a worktree. This test documents the expected behavior.

Location: tests/test_orchestrator_scheduler.py

Test should:
1. Set up a git repo with a FUTURE chunk
2. Call inject (via API or directly through StateStore)
3. Verify work unit exists with status READY
4. Verify worktree does NOT exist (via WorktreeManager.worktree_exists())

### Step 2: Write failing test - worktree created at dispatch time

Create a test that verifies the worktree is created when `_run_work_unit` is called (i.e., when transitioning READY → RUNNING).

Location: tests/test_orchestrator_scheduler.py

Test should:
1. Set up git repo with FUTURE chunk
2. Create READY work unit
3. Call `_run_work_unit` (or trigger dispatch)
4. Verify worktree now exists
5. Verify worktree is on the correct branch (`orch/<chunk>`)
6. Verify worktree reflects current HEAD state

### Step 3: Write failing test - blocked work waits for current state

Create an integration test that verifies blocked work gets worktree from current HEAD only when dependencies complete and it starts running.

Location: tests/test_orchestrator_scheduler.py

Test should:
1. Create two FUTURE chunks: chunk_a and chunk_b where chunk_b depends on chunk_a (`created_after: [chunk_a]`)
2. Inject both chunks
3. Verify chunk_b has status BLOCKED
4. Verify NO worktree exists for chunk_b
5. Complete chunk_a (mock the agent, update status to DONE)
6. Trigger dependency check / scheduler tick
7. Verify chunk_b transitions to READY
8. Trigger dispatch for chunk_b
9. Verify worktree is created for chunk_b at this point
10. Verify the worktree reflects any changes that chunk_a would have merged

### Step 4: Verify existing implementation and fix if needed

Review the current scheduler implementation to ensure:
1. `inject_endpoint` does NOT call `worktree_manager.create_worktree()`
2. `_run_work_unit()` calls `create_worktree()` at the beginning
3. Blocked work units don't have worktrees until they transition to RUNNING

The current implementation in `scheduler.py` lines 374-376 shows:
```python
# Create worktree
logger.info(f"Creating worktree for {chunk}")
worktree_path = self.worktree_manager.create_worktree(chunk)
```

This is already in `_run_work_unit`, which is correct. The key verification is that no other code path creates worktrees prematurely.

Location: src/orchestrator/scheduler.py, src/orchestrator/api.py

### Step 5: Add dependency-aware worktree creation test

Enhance the blocked work test to verify the worktree picks up the latest state:

Location: tests/test_orchestrator_scheduler.py

Test should:
1. Create git repo with initial commit
2. Create chunk_a with FUTURE status
3. Create chunk_b with FUTURE status and `created_after: [chunk_a]`
4. Inject both
5. Simulate chunk_a completion: create worktree, make file changes, commit, merge
6. Trigger chunk_b dispatch
7. Verify chunk_b's worktree contains the file changes from chunk_a

### Step 6: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched by this implementation.

Location: docs/chunks/deferred_worktree_creation/GOAL.md

Expected code_paths:
- src/orchestrator/scheduler.py (verified, not modified)
- src/orchestrator/api.py (verified, not modified)
- tests/test_orchestrator_scheduler.py (new tests added)

## Dependencies

- `orch_scheduling` chunk (ACTIVE) - Provides the scheduler foundation and worktree manager
- `orch_activate_on_inject` chunk (ACTIVE) - Provides chunk activation logic that runs in `_run_work_unit`

Both dependencies are already complete, so this chunk can proceed.

## Risks and Open Questions

1. **Blocked dependency resolution timing** - The scheduler must check blocked work units and transition them to READY when dependencies complete. Need to verify this logic exists and is correct.

2. **Race condition on base branch** - If chunk_a completes and merges while chunk_b is still READY, chunk_b's worktree should see chunk_a's changes. This depends on the worktree being created from the current base branch HEAD at dispatch time, not from a stale commit.

3. **Test isolation** - Tests that create git worktrees need proper cleanup. The existing `git_repo` fixture in `test_orchestrator_worktree.py` provides a pattern to follow.

## Deviations

- Steps 1-3 were combined since the tests are closely related and it was more
  efficient to write them together. All tests are in `TestDeferredWorktreeCreation`
  and `TestBlockedWorkDeferredWorktree` classes.

- Step 4 confirmed the existing implementation is already correct. No code
  changes were needed - the worktree creation was already deferred to
  `_run_work_unit()` in the scheduler. The tests serve to document and verify
  this architectural invariant.

- Step 5 was implemented as part of `TestDeferredWorktreeCreationIntegration`
  with two integration tests using real git repos:
  - `test_worktree_reflects_current_head_at_dispatch_time`
  - `test_blocked_work_sees_dependency_changes_when_dispatched`

- Step 6 was not needed as the GOAL.md already had correct code_paths listed.