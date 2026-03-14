---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/merge.py
- tests/test_orchestrator_merge.py
code_references:
  - ref: src/orchestrator/merge.py#is_on_branch
    implements: "Helper to detect if HEAD is on a given branch"
  - ref: src/orchestrator/merge.py#has_clean_working_tree
    implements: "Helper to detect if working tree has uncommitted changes (used by tests, no longer gating merge strategy)"
  - ref: src/orchestrator/merge.py#merge_native
    implements: "Native git merge for on-branch merges (handles dirty trees correctly)"
  - ref: src/orchestrator/merge.py#merge_without_checkout
    implements: "Branch-aware merge strategy: native merge when on-branch, plumbing when off-branch"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- rename_rebase_guard
---

# Chunk Goal

## Minor Goal

Simplify the orchestrator's merge-back strategy in `src/orchestrator/merge.py`. The current approach uses git plumbing commands (`merge-tree`, `commit-tree`, `update-ref`) for all merges, then attempts to sync the working tree with a fragile `reset --mixed` + `checkout -- .` sequence. This leaves the working tree in a broken state: git log shows the merge, git diff is clean, but git status shows all merged files as modified and the tree contents are pre-merge.

Replace with a branch-aware strategy:

1. **User on target branch** → `git merge {chunk_branch}`. Git handles index + working tree + ref atomically. Git merge handles dirty working trees correctly — it merges files that don't conflict with uncommitted changes and refuses if there are conflicts. If the merge has branch-level conflicts, abort the merge and route the chunk back to the REBASE stage.
2. **User on different branch** → Use `update-ref` only (no working tree sync needed). The user won't see the change until they checkout the target branch, at which point git handles it natively.

Delete the `update_working_tree_if_on_branch()` function entirely. The `merge_without_checkout()` plumbing path is retained only for case 2 (not on target branch).

## Success Criteria

- When the user is on the target branch (clean or dirty), the orchestrator runs `git merge {chunk_branch}` and the working tree, index, and ref are all consistent after merge
- When `git merge` produces conflicts, the merge is aborted (`git merge --abort`) and the chunk is routed to REBASE stage
- When the user is on a different branch, `update-ref` moves the target branch pointer without touching the working tree or index
- The `update_working_tree_if_on_branch()` function is deleted
- The `merge_without_checkout()` plumbing path (`merge-tree`/`commit-tree`/`update-ref`) is only used when the user is NOT on the target branch
- Existing merge tests pass or are updated to reflect the new strategy
- Bug is verified fixed: after merge-back while on target branch, `git status` shows a clean tree

## Rejected Ideas

### Keep the plumbing approach and fix the working tree sync

We could fix `update_working_tree_if_on_branch()` by replacing `reset --mixed` + `checkout -- .` with `reset --hard HEAD` or `read-tree -u --reset HEAD`.

Rejected because: This is fighting git instead of using it. When the user is on the target branch, `git merge` does exactly what we need atomically and correctly. The plumbing approach only makes sense when we can't checkout the target branch (i.e., user is on a different branch).