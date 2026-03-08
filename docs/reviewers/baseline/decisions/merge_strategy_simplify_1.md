---
decision: APPROVE
summary: All success criteria satisfied - branch-aware merge strategy implemented with native git merge for on-branch clean-tree case, plumbing fallback for other cases, proper conflict abort handling, and comprehensive test coverage.
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: When the user is on the target branch with a clean tree, the orchestrator runs `git merge {chunk_branch}` and the working tree, index, and ref are all consistent after merge

- **Status**: satisfied
- **Evidence**: `merge_without_checkout()` at line 203 checks `is_on_branch(target_branch, repo_dir) and has_clean_working_tree(repo_dir)` and calls `merge_native()` which runs `git merge --no-edit`. Test `test_merge_on_target_branch_clean_tree_updates_working_tree` verifies working tree is updated and `git status` is clean.

### Criterion 2: When `git merge` produces conflicts, the merge is aborted (`git merge --abort`) and the chunk is routed to REBASE stage

- **Status**: satisfied
- **Evidence**: `merge_native()` at lines 130-138 checks for "CONFLICT" in output, runs `git merge --abort`, and raises `WorktreeError` with "Merge conflict" message. The scheduler (tested in `test_orchestrator_scheduler_merge_conflict.py`) routes merge conflicts to REBASE stage. Test `test_merge_conflict_aborts_and_raises` verifies abort behavior.

### Criterion 3: When the user is on a different branch, `update-ref` moves the target branch pointer without touching the working tree or index

- **Status**: satisfied
- **Evidence**: `merge_without_checkout()` falls through to plumbing path (lines 207-299) when not on target branch. For fast-forward, uses `update-ref` at line 219. For real merges, uses `merge-tree`/`commit-tree`/`update-ref` sequence. Test `test_merge_on_different_branch_updates_ref_only` verifies working tree unchanged.

### Criterion 4: The `update_working_tree_if_on_branch()` function is deleted

- **Status**: satisfied
- **Evidence**: Grep search for `update_working_tree_if_on_branch` in `src/orchestrator` returns no files found. Function has been completely removed.

### Criterion 5: The `merge_without_checkout()` plumbing path (`merge-tree`/`commit-tree`/`update-ref`) is only used when the user is NOT on the target branch

- **Status**: satisfied
- **Evidence**: Line 203 shows the conditional: `if is_on_branch(target_branch, repo_dir) and has_clean_working_tree(repo_dir): merge_native(...); return`. Only if this condition fails does the code proceed to the plumbing path (line 207 onwards).

### Criterion 6: Existing merge tests pass or are updated to reflect the new strategy

- **Status**: satisfied
- **Evidence**: All 62 merge-related tests pass (`uv run pytest tests/ -k "merge"`). Test file `tests/test_orchestrator_merge.py` has been completely rewritten with new tests covering all scenarios: on-branch clean tree, on-branch conflict, different branch, dirty tree, already merged, fast-forward.

### Criterion 7: Bug is verified fixed: after merge-back while on target branch, `git status` shows a clean tree

- **Status**: satisfied
- **Evidence**: Test `test_merge_on_target_branch_clean_tree_updates_working_tree` explicitly verifies this at lines 145-151: runs `git status --porcelain` and asserts output is empty with message "git status should be clean after merge".
