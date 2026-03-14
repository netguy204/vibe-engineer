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
  implements: "Moved commit logic into retain_worktree branch, eliminating the double-commit with finalize_work_unit"
- ref: src/orchestrator/worktree.py#WorktreeManager::commit_changes
  implements: "Hardened against empty-stderr exit-code-1 edge case (e.g., submodule entries)"
- ref: src/orchestrator/worktree.py#WorktreeManager::_remove_worktree_from_repo
  implements: "Added git worktree prune after shutil.rmtree fallback for submodule-containing worktrees"
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

The orchestrator's `_finalize_completed_work_unit()` in `scheduler.py` commits uncommitted changes at lines 1042-1053, then calls `worktree.finalize_work_unit()` at line 1079, which attempts to commit *again* at line 1310-1311. When the first commit leaves the tree clean but `has_uncommitted_changes()` still returns `True` (e.g., due to git submodule entries in `git status --porcelain` output), the second `commit_changes()` call fails with an empty stderr, raising `WorktreeError("git commit failed: ")`. This bubbles up to the scheduler, which marks the work unit NEEDS_ATTENTION — blocking all downstream chunks even though the implementation work completed successfully.

This chunk eliminates the double-commit by making `finalize_work_unit()` the single owner of the commit-remove-merge sequence. The scheduler's pre-commit block (lines 1042-1053) is replaced with a narrower role: for `retain_worktree` work units, the scheduler commits directly (since `finalize_work_unit()` is skipped); for all other work units, `finalize_work_unit()` handles commit-remove-merge as one sequence. This preserves the existing behavior where retained worktrees still get their uncommitted changes committed.

The chunk also hardens `commit_changes()` to treat exit-code-1-with-empty-stderr as a no-op (same as "nothing to commit"), making it resilient to submodule and other edge cases.

Additionally, `git worktree remove` fails on worktrees containing submodules ("working trees containing submodules cannot be moved or removed"). The cleanup path should fall back to `rm -rf` + `git worktree prune` when submodules are present.

## Success Criteria

- The scheduler's `_finalize_completed_work_unit()` no longer calls `commit_changes()` before `finalize_work_unit()`. For the `retain_worktree` path, the scheduler commits directly. For the normal path, `finalize_work_unit()` owns the full commit-remove-merge sequence.
- `commit_changes()` treats `git commit` exit code 1 with empty stderr as "nothing to commit" (returns `False` instead of raising `WorktreeError`).
- `remove_worktree()` handles submodule-containing worktrees by falling back to `rm -rf` + `git worktree prune` when `git worktree remove` fails due to submodules.
- A work unit whose COMPLETE phase agent commits all changes (leaving the tree clean) finalizes successfully without entering NEEDS_ATTENTION.
- Existing tests continue to pass; new tests cover the no-op commit and submodule worktree removal scenarios.