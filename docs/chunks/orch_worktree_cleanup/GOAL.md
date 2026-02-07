---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
- ref: src/orchestrator/scheduler.py#Scheduler::_run_work_unit
  implements: "Worktree cleanup logic when activate_chunk_in_worktree raises ValueError"
- ref: tests/test_orchestrator_scheduler.py#TestChunkActivationInWorkUnit::test_run_work_unit_cleans_up_worktree_on_activation_failure
  implements: "Test verifying worktree cleanup on activation failure"
- ref: tests/test_orchestrator_scheduler.py#TestChunkActivationInWorkUnit::test_run_work_unit_logs_cleanup_failure_without_crashing
  implements: "Test verifying cleanup failure is logged but doesn't crash"
narrative: arch_consolidation
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Fix a resource leak in the orchestrator's scheduler where worktrees are left behind when chunk activation fails. Currently in `scheduler.py` `_run_work_unit()` (lines 710-808), if the worktree is created successfully but `activate_chunk_in_worktree()` raises a `ValueError`, the method returns early without cleaning up the worktree. The `finally` block only removes the chunk from `_running_agents` but does not call `worktree_manager.remove_worktree()`.

This leak can accumulate orphaned worktrees over time, consuming disk space and potentially causing confusion when debugging orchestrator state. The fix ensures that activation failures trigger proper worktree cleanup, maintaining the property that the workflow should not grow more difficult over time.

## Success Criteria

- The `_run_work_unit()` method in `src/orchestrator/scheduler.py` tracks whether the worktree was successfully created
- When `activate_chunk_in_worktree()` raises a `ValueError` (lines 730-733), the worktree is cleaned up before returning
- The cleanup logic calls `self.worktree_manager.remove_worktree(chunk, remove_branch=False)` to match the cleanup pattern used elsewhere in the scheduler (e.g., line 1027 in `_advance_phase()`)
- A test case verifies that when activation fails, no worktree is left behind
- The fix does not interfere with normal success paths or other error paths (e.g., `WorktreeError` during worktree creation)

