---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- tests/test_orchestrator_worktree.py
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager::_lock_worktree
    implements: "Lock worktrees to prevent premature pruning by git worktree prune"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_unlock_worktree
    implements: "Unlock worktrees before removal"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_save_base_branch
    implements: "Persist base branch at worktree creation time to eliminate race condition"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_load_base_branch
    implements: "Load persisted base branch for merge operations"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_without_checkout
    implements: "Checkout-free merge delegation to orchestrator.merge module"
  - ref: src/orchestrator/merge.py#merge_without_checkout
    implements: "Primary checkout-free merge using git merge-tree --write-tree (Git 2.38+)"
  - ref: src/orchestrator/merge.py#merge_via_index
    implements: "Fallback checkout-free merge for older Git versions"
  - ref: src/orchestrator/merge.py#update_working_tree_if_on_branch
    implements: "Update working tree after ref update when user is on target branch"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_to_base_single_repo
    implements: "Single-repo merge using checkout-free strategy"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_to_base_multi_repo
    implements: "Multi-repo merge using checkout-free strategy"
  - ref: tests/test_orchestrator_worktree.py#TestBaseBranchPersistence
    implements: "Tests for base branch capture at worktree creation time"
  - ref: tests/test_orchestrator_worktree.py#TestCheckoutFreeMerge
    implements: "Tests for merging without git checkout in main repo"
  - ref: tests/test_orchestrator_worktree.py#TestWorktreeLocking
    implements: "Tests for git worktree locking to prevent premature pruning"
  - ref: tests/test_orchestrator_worktree.py#TestMultiRepoBaseBranchPersistence
    implements: "Tests for base branch persistence in multi-repo mode"
  - ref: tests/test_orchestrator_worktree.py#TestMultiRepoCheckoutFreeMerge
    implements: "Tests for checkout-free merge in multi-repo mode"
  - ref: tests/test_orchestrator_worktree.py#TestMultiRepoWorktreeLocking
    implements: "Tests for worktree locking in multi-repo mode"
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

The orchestrator's `merge_to_base()` function currently performs `git checkout` on the main repository when merging completed work (line 731 in worktree.py). If the user is actively working in the main repository during parallel orchestrator execution, this checkout disrupts their working tree by switching branches unexpectedly. Additionally, `_get_repo_current_branch()` has a race condition: the base branch is captured at worktree creation time, but if someone changes branches between worktree creation and merge, the merge targets the wrong branch. Finally, created worktrees are not locked, so `git worktree prune` could remove active worktrees.

This chunk addresses these safety issues by:
1. Eliminating the disruptive `git checkout` in merge operations (investigate `git merge --no-checkout`, bare-repo merging, or worktree-based merge strategies)
2. Capturing the base branch at worktree creation time and storing it for use during merge, eliminating the race condition
3. Investigating `git worktree lock` to prevent premature pruning of active worktrees

This ensures parallel orchestrator execution cannot disrupt a user's active work in the main repository and prevents race conditions or accidental cleanup during multi-chunk execution.

## Success Criteria

1. **No git checkout in main repo during merge**: `merge_to_base()` (both `_merge_to_base_single_repo` and `_merge_to_base_multi_repo`) no longer performs `git checkout` on the main repository. Merges happen without switching branches in the user's working tree.

2. **Base branch captured at creation time**: The base branch is determined and stored when the worktree is created (in `create_worktree()` or `_create_branch()`), not queried later during merge. This eliminates the race condition where branch changes between worktree creation and merge cause merges to target the wrong branch.

3. **Worktrees are locked against prune**: After creating worktrees, `git worktree lock` is called to prevent `git worktree prune` from removing active worktrees. Worktrees are unlocked before removal.

4. **Tests validate the fix**: Test cases verify that:
   - A merge operation does not modify the checked-out branch in the main repository
   - The base branch used for merge matches the branch at worktree creation time, even if the main repo switches branches afterward
   - Locked worktrees are not removed by `git worktree prune`

5. **All existing tests pass**: No behavioral regressions in orchestrator functionality.

