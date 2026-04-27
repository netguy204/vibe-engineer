---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/orchestrator/merge.py
- tests/test_orchestrator_worktree_persistence.py
- tests/test_orchestrator_worktree_multirepo.py
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
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_to_base_single_repo
    implements: "Single-repo merge using checkout-free strategy"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_to_base_multi_repo
    implements: "Multi-repo merge using checkout-free strategy"
  - ref: tests/test_orchestrator_worktree_persistence.py#TestBaseBranchPersistence
    implements: "Tests for base branch capture at worktree creation time"
  - ref: tests/test_orchestrator_worktree_persistence.py#TestCheckoutFreeMerge
    implements: "Tests for merging without git checkout in main repo"
  - ref: tests/test_orchestrator_worktree_persistence.py#TestWorktreeLocking
    implements: "Tests for git worktree locking to prevent premature pruning"
  - ref: tests/test_orchestrator_worktree_multirepo.py#TestMultiRepoBaseBranchPersistence
    implements: "Tests for base branch persistence in multi-repo mode"
  - ref: tests/test_orchestrator_worktree_multirepo.py#TestMultiRepoCheckoutFreeMerge
    implements: "Tests for checkout-free merge in multi-repo mode"
  - ref: tests/test_orchestrator_worktree_multirepo.py#TestMultiRepoWorktreeLocking
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

The orchestrator's `merge_to_base()` performs checkout-free merges so that parallel orchestrator execution does not disrupt a user's active work in the main repository. Three safety properties hold:

1. **No `git checkout` in the main repo during merge.** Merges route through `git merge-tree --write-tree` (Git 2.38+) with a plumbing-level fallback (`merge_via_index`) for older Git, so the user's checked-out branch is never switched.
2. **Base branch captured at worktree creation time.** The base branch each chunk should merge into is persisted when the worktree is created and reloaded at merge time, so changing branches in the main repo between creation and merge does not redirect the merge.
3. **Active worktrees are locked.** `git worktree lock` is applied at creation and released before removal, preventing `git worktree prune` from collecting in-flight worktrees.

Together these properties make parallel orchestrator execution safe to run alongside interactive work in the host repository.

## Success Criteria

1. **No git checkout in main repo during merge**: `merge_to_base()` (both `_merge_to_base_single_repo` and `_merge_to_base_multi_repo`) no longer performs `git checkout` on the main repository. Merges happen without switching branches in the user's working tree.

2. **Base branch captured at creation time**: The base branch is determined and stored when the worktree is created (in `create_worktree()` or `_create_branch()`), not queried later during merge. This eliminates the race condition where branch changes between worktree creation and merge cause merges to target the wrong branch.

3. **Worktrees are locked against prune**: After creating worktrees, `git worktree lock` is called to prevent `git worktree prune` from removing active worktrees. Worktrees are unlocked before removal.

4. **Tests validate the fix**: Test cases verify that:
   - A merge operation does not modify the checked-out branch in the main repository
   - The base branch used for merge matches the branch at worktree creation time, even if the main repo switches branches afterward
   - Locked worktrees are not removed by `git worktree prune`

5. **All existing tests pass**: No behavioral regressions in orchestrator functionality.

