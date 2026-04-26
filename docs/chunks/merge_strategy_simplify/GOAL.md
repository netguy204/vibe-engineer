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

The orchestrator's merge-back strategy in `src/orchestrator/merge.py` is branch-aware:

1. **User on target branch** → `git merge {chunk_branch}`. Git handles index + working tree + ref atomically. Git merge handles dirty working trees correctly — it merges files that don't conflict with uncommitted changes and refuses if there are conflicts. If the merge has branch-level conflicts, the merge is aborted and the chunk is routed back to the REBASE stage.
2. **User on different branch** → `update-ref` only (no working tree sync needed). The user does not see the change until they checkout the target branch, at which point git handles it natively.

The `update_working_tree_if_on_branch()` function does not exist. The `merge_without_checkout()` plumbing path is reserved for case 2 (not on target branch).

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

An alternative would fix `update_working_tree_if_on_branch()` by replacing `reset --mixed` + `checkout -- .` with `reset --hard HEAD` or `read-tree -u --reset HEAD`.

Rejected because: This is fighting git instead of using it. When the user is on the target branch, `git merge` does exactly what is needed atomically and correctly. The plumbing approach only makes sense when the target branch cannot be checked out (i.e., user is on a different branch).