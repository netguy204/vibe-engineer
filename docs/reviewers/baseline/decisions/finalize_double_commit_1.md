---
decision: APPROVE
summary: "All five success criteria satisfied — double-commit eliminated, commit_changes hardened, submodule worktree removal resilient, clean-tree finalization succeeds, and 128 tests pass including new coverage."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: The scheduler's `_finalize_completed_work_unit()` no longer calls `commit_changes()` before `finalize_work_unit()`. For the `retain_worktree` path, the scheduler commits directly. For the normal path, `finalize_work_unit()` owns the full commit-remove-merge sequence.

- **Status**: satisfied
- **Evidence**: The unconditional commit block (lines 1040–1053) was removed from `scheduler.py`. The commit logic is now inside the `if work_unit.retain_worktree:` branch. For non-retained worktrees, only `finalize_work_unit()` is called. Tests `test_finalize_completed_does_not_commit_before_finalize` and `test_finalize_completed_retain_worktree_commits_directly` verify both paths. Existing test `test_mechanical_commit_delegated_to_finalize_work_unit` was updated to match.

### Criterion 2: `commit_changes()` treats `git commit` exit code 1 with empty stderr as "nothing to commit" (returns `False` instead of raising `WorktreeError`).

- **Status**: satisfied
- **Evidence**: `worktree.py` adds a new check after the existing "nothing to commit" text check: `if result.returncode == 1 and result.stderr.strip() == "": return False`. Test `test_commit_changes_empty_stderr_exit_code_1_returns_false` covers this path by mocking git commit to return exit code 1 with empty stderr.

### Criterion 3: `remove_worktree()` handles submodule-containing worktrees by falling back to `rm -rf` + `git worktree prune` when `git worktree remove` fails due to submodules.

- **Status**: satisfied
- **Evidence**: `worktree.py` `_remove_worktree_from_repo` now calls `git worktree prune` after the `shutil.rmtree` fallback (previously only prune ran on the intermediate retry, not the final fallback). Test `test_remove_worktree_submodule_fallback` mocks `git worktree remove` to always fail and verifies the directory is removed and prune is called at least twice.

### Criterion 4: A work unit whose COMPLETE phase agent commits all changes (leaving the tree clean) finalizes successfully without entering NEEDS_ATTENTION.

- **Status**: satisfied
- **Evidence**: Test `test_finalize_work_unit_with_clean_tree_succeeds` creates a worktree, commits changes manually (leaving tree clean), then calls `finalize_work_unit()` — it succeeds without error and the changes are merged to base. This directly exercises the bug scenario described in the goal.

### Criterion 5: Existing tests continue to pass; new tests cover the no-op commit and submodule worktree removal scenarios.

- **Status**: satisfied
- **Evidence**: All 128 tests pass across the 5 affected test files. New tests added: `test_commit_changes_empty_stderr_exit_code_1_returns_false`, `test_remove_worktree_submodule_fallback`, `test_finalize_work_unit_with_clean_tree_succeeds`, `test_finalize_completed_does_not_commit_before_finalize`, `test_finalize_completed_retain_worktree_commits_directly`. Existing tests were updated to match the new behavior (e.g., `test_mechanical_commit_delegated_to_finalize_work_unit`, `test_finalization_error_marks_needs_attention`).
