---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/worktree.py
- src/orchestrator/merge.py
- src/orchestrator/__init__.py
code_references:
  - ref: src/orchestrator/merge.py#merge_without_checkout
    implements: "Primary checkout-free merge using git merge-tree --write-tree (Git 2.38+)"
  - ref: src/orchestrator/merge.py#merge_via_index
    implements: "Fallback merge using temporary index file for older Git versions"
  - ref: src/orchestrator/merge.py#update_working_tree_if_on_branch
    implements: "Working tree sync after ref update via update-ref"
  - ref: src/orchestrator/merge.py#WorktreeError
    implements: "Exception class for worktree and merge-related errors"
  - ref: src/orchestrator/worktree.py#WorktreeManager::_merge_without_checkout
    implements: "Delegation wrapper that calls orchestrator.merge.merge_without_checkout"
narrative: arch_review_gaps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- cli_decompose
- integrity_deprecate_standalone
- low_priority_cleanup
- optimistic_locking
- spec_and_adr_update
- test_file_split
- orch_session_auto_resume
---

# Chunk Goal

## Minor Goal

Extract the merge strategy logic from `src/orchestrator/worktree.py` (1,439 lines) into a dedicated `src/orchestrator/merge.py` module. The worktree module currently mixes two distinct responsibilities: worktree lifecycle management (create, remove, lock, unlock, list, path resolution) and checkout-free merge strategies (~200 lines of git plumbing). Separating these concerns reduces the cognitive load of working in either area and makes merge strategy code independently testable.

The following methods move to `merge.py`:
- `_merge_without_checkout` -- core checkout-free merge using `git merge-tree --write-tree` (Git 2.38+)
- `_merge_via_index` -- fallback merge using a temporary index file for older Git versions
- `_update_working_tree_if_on_branch` -- working tree sync after a ref update via `update-ref`

The following methods stay in `worktree.py` but delegate to `merge.py`:
- `merge_to_base` -- public entry point, dispatches to single-repo or multi-repo merge
- `_merge_to_base_single_repo` -- loads persisted base branch, calls merge, optionally deletes branch
- `_merge_to_base_multi_repo` -- iterates repos with rollback on failure

The public API of `WorktreeManager` does not change. Callers continue to import `WorktreeManager` from `orchestrator.worktree` and call `merge_to_base()` or `finalize_work_unit()` exactly as before. The extraction is purely internal.

This advances the project goal of maintaining document and code health over time (docs/trunk/GOAL.md, Required Properties): smaller, focused modules are easier for agents and humans to reason about, reducing the cost of future change in the orchestrator subsystem.

## Success Criteria

- A new module `src/orchestrator/merge.py` exists containing the extracted merge functions: checkout-free merge via `git merge-tree`, fallback merge via temporary index, and working tree update after ref changes
- `src/orchestrator/worktree.py` no longer contains the merge algorithm implementations (`_merge_without_checkout`, `_merge_via_index`, `_update_working_tree_if_on_branch`); it imports and delegates to `merge.py`
- The public API of `WorktreeManager` is unchanged: `merge_to_base()`, `finalize_work_unit()`, and all other public methods retain their existing signatures and behavior
- All existing imports of `WorktreeManager` and `WorktreeError` from `orchestrator.worktree` continue to work without modification (verified by grep of callers in `scheduler.py`, `api/worktrees.py`, `api/work_units.py`, `api/conflicts.py`, `orchestrator/__init__.py`)
- All existing tests pass without modification (test files: `test_orchestrator_worktree*.py`, `test_orchestrator_scheduler*.py`, and any other tests exercising merge behavior)
- `worktree.py` line count is reduced by approximately 200 lines (the merge strategy implementations)
- Code backreferences in `merge.py` link back to this chunk and the `orch_merge_safety` chunk where the merge strategies originated
