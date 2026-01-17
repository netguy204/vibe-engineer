---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/api.py
- src/orchestrator/worktree.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
    implements: "Worktree creation at dispatch time (READY → RUNNING transition)"
  - ref: tests/test_orchestrator_scheduler.py#TestDeferredWorktreeCreation
    implements: "Unit tests verifying worktree is not created at inject time"
  - ref: tests/test_orchestrator_scheduler.py#TestBlockedWorkDeferredWorktree
    implements: "Tests for blocked work units and deferred worktree creation"
  - ref: tests/test_orchestrator_scheduler.py#TestDeferredWorktreeCreationIntegration
    implements: "Integration tests with real git repos verifying dispatch-time worktree state"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- orch_activate_on_inject
---

# Chunk Goal

## Minor Goal

Defer git worktree creation until work can actually begin execution, rather than creating worktrees at inject time.

Currently, when work is injected via `ve orch inject`, the worktree is created immediately. This is problematic because:

1. **Stale base state**: A worktree created at inject time reflects the repository state when the work was queued, not when it actually runs. If the work is blocked or there are no agent slots available, other work may complete and change the repository before this work starts.

2. **Blocked work sees outdated code**: Work that depends on other chunks (via `created_after`) gets a worktree based on the state *before* its dependencies complete. The work should see the state *after* its dependencies have merged.

3. **Resource waste**: Creating worktrees for work that can't run yet consumes disk space and git resources unnecessarily.

**Solution**: Create worktrees at the moment a work unit transitions from READY to RUNNING (i.e., when an agent slot becomes available and the scheduler dispatches the work). This ensures:
- The worktree reflects the most current repository state
- Blocked work sees the changes from the work it was waiting on
- Resources are allocated only when actually needed

## Success Criteria

1. **Worktree creation moved to dispatch time**
   - `ve orch inject` does NOT create a worktree
   - Worktree is created in `Scheduler._run_work_unit()` just before agent execution begins
   - The worktree is created from the current HEAD at dispatch time, not inject time

2. **Blocked work waits for current state**
   - Work with unmet dependencies (BLOCKED status) does not have a worktree
   - When dependencies complete and work transitions BLOCKED → READY → RUNNING, worktree is created at RUNNING transition
   - The worktree reflects repository state after dependency merges

3. **Queue-only work has no worktree**
   - Work units in READY status waiting for agent slots do not have worktrees
   - Only RUNNING work units have worktrees

4. **Tests validate deferred creation**
   - Integration test: inject work, verify no worktree exists, start agent, verify worktree created
   - Integration test: blocked work gains worktree only when dependencies complete and it starts running
   - Existing tests continue to pass (worktree cleanup, phase execution, etc.)

