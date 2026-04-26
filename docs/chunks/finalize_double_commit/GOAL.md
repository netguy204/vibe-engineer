---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- src/orchestrator/worktree.py
- tests/test_orchestrator_worktree_operations.py
- tests/test_orchestrator_worktree_core.py
- tests/test_orchestrator_worktree_multirepo.py
- tests/test_orchestrator_scheduler.py
code_references:
- ref: src/orchestrator/scheduler.py#Scheduler::_finalize_completed_work_unit
  implements: "Commits only on the retain_worktree path; delegates commit-remove-merge to finalize_work_unit otherwise (no double-commit)"
- ref: src/orchestrator/worktree.py#WorktreeManager::commit_changes
  implements: "Treats empty-stderr exit-code-1 from git commit as a no-op (e.g., submodule entries leaving nothing actually staged)"
- ref: src/orchestrator/worktree.py#WorktreeManager::_remove_worktree_from_repo
  implements: "Falls back to shutil.rmtree followed by git worktree prune when git worktree remove fails for submodule-containing worktrees"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- merge_strategy_simplify
---

# Chunk Goal

## Minor Goal

`finalize_work_unit()` is the single owner of the commit-remove-merge sequence for non-retained worktrees. The scheduler's `_finalize_completed_work_unit()` only commits directly on the `retain_worktree` path (where `finalize_work_unit()` is skipped); on the normal path, it delegates to `finalize_work_unit()` so commit, remove, and merge happen as one sequence. This avoids any double-commit pattern where a clean tree triggers a spurious second `commit_changes()` failure that would mark the work unit NEEDS_ATTENTION.

`commit_changes()` treats `git commit` exit code 1 with empty stderr as a no-op (returning `False`, like "nothing to commit") so submodule entries and similar cases where `git status --porcelain` is non-empty but nothing is staged do not raise `WorktreeError`.

Worktree removal handles submodule-containing worktrees by falling back to `shutil.rmtree` followed by `git worktree prune` when `git worktree remove --force` fails (submodule worktrees report "working trees containing submodules cannot be moved or removed").

## Success Criteria

- The scheduler's `_finalize_completed_work_unit()` no longer calls `commit_changes()` before `finalize_work_unit()`. For the `retain_worktree` path, the scheduler commits directly. For the normal path, `finalize_work_unit()` owns the full commit-remove-merge sequence.
- `commit_changes()` treats `git commit` exit code 1 with empty stderr as "nothing to commit" (returns `False` instead of raising `WorktreeError`).
- `remove_worktree()` handles submodule-containing worktrees by falling back to `rm -rf` + `git worktree prune` when `git worktree remove` fails due to submodules.
- A work unit whose COMPLETE phase agent commits all changes (leaving the tree clean) finalizes successfully without entering NEEDS_ATTENTION.
- Existing tests continue to pass; new tests cover the no-op commit and submodule worktree removal scenarios.