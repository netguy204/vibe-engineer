---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/orchestrator/api/work_units.py
- src/orchestrator/client.py
- src/cli/orch.py
- src/templates/trunk/ORCHESTRATOR.md.jinja2
- tests/test_orchestrator_api.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::has_unmerged_commits
    implements: "Check for unmerged commits before branch deletion"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_remove_single_repo_worktree
    implements: "Safe branch delete using -d by default, -D when force=True"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_remove_task_context_worktrees
    implements: "Safe branch delete in multi-repo mode"
  - ref: src/orchestrator/worktree.py#WorktreeManager::remove_worktree
    implements: "Force parameter threading to branch deletion"
  - ref: src/orchestrator/api/work_units.py#delete_work_unit_endpoint
    implements: "Pre-delete unmerged commit check with force override"
  - ref: src/orchestrator/client.py#OrchestratorClient::delete_work_unit
    implements: "Force parameter in client API"
  - ref: src/cli/orch.py#work_unit_delete
    implements: "--force CLI flag for safe deletion override"
  - ref: tests/test_orchestrator_api.py#TestDeleteWorkUnitSafeBranch
    implements: "Tests for safe branch deletion behavior"
narrative: null
investigation: orch_stuck_recovery
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_merge_rebase_retry
- orch_review_approve_bypass
---

# Chunk Goal

## Minor Goal

Prevent `ve orch work-unit delete` from destroying branches that contain unmerged implementation code. Currently, the delete endpoint (`api/work_units.py:264-270`) calls `remove_worktree(chunk, remove_branch=True)` which uses `git branch -D` (force delete) at `worktree.py:666` — no check on whether the branch has commits not yet on main.

This caused data loss in the motivating incident: an operator deleted work units for chunks stuck at NEEDS_ATTENTION, force-deleting branches that held the only copy of implementation code. Recovery required `git reflog` archaeology.

The normal finalization path (`finalize_work_unit`) already uses `git branch -d` (safe delete) which refuses to delete unmerged branches. The fix brings the manual delete path to the same safety level.

## Success Criteria

- `delete_work_unit_endpoint` checks for unmerged commits before deleting the branch (via `git rev-list main..orch/<chunk> --count` or equivalent)
- If unmerged commits exist, the delete is refused with a clear error message showing the commit count
- A `--force` flag (CLI) / `force` query param (API) overrides the safety check when the operator explicitly intends to discard the work
- `_remove_single_repo_worktree` uses `git branch -d` (safe delete) by default instead of `git branch -D`
- Force delete (`-D`) is only used when the force flag is set
- Tests cover: delete with merged branch succeeds, delete with unmerged branch fails, delete with unmerged branch + force succeeds
- Existing orchestrator tests pass