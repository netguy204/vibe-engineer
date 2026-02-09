<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a pure extraction refactoring with no behavioral changes. The approach is:

1. **Create the new merge module** (`src/orchestrator/merge.py`) containing the extracted functions
2. **Move the merge logic** from `worktree.py` to `merge.py` as module-level functions (not class methods)
3. **Update `worktree.py`** to import and delegate to the new module
4. **Preserve the public API** - `WorktreeManager.merge_to_base()` and `WorktreeManager.finalize_work_unit()` signatures remain unchanged

The extraction targets three private methods that represent the merge strategy logic:
- `_merge_without_checkout()` - Core checkout-free merge using `git merge-tree --write-tree` (Git 2.38+)
- `_merge_via_index()` - Fallback merge using a temporary index file for older Git versions
- `_update_working_tree_if_on_branch()` - Working tree sync after a ref update via `update-ref`

These become standalone functions in `merge.py` since they don't require WorktreeManager state beyond the parameters already passed to them.

The following methods stay in `worktree.py` but delegate to the new module:
- `merge_to_base()` - Public entry point
- `_merge_to_base_single_repo()` - Loads persisted base branch, calls merge
- `_merge_to_base_multi_repo()` - Iterates repos with rollback on failure

No new tests are needed since the existing test suite in `tests/test_orchestrator_worktree*.py` already covers merge behavior. The extraction is purely structural.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a structural improvement to the orchestrator's worktree module. The subsystem lists `worktree.py#WorktreeManager` as the canonical implementation location. After this extraction, `merge.py` becomes a supporting module that implements the merge strategy details while `worktree.py` retains the lifecycle management responsibility.

The orchestrator subsystem is DOCUMENTED status, so any discovered deviations should be noted but not prioritized for fixing in this chunk.

## Sequence

### Step 1: Create `src/orchestrator/merge.py` with module docstring and imports

Create the new module with:
- Module docstring explaining its purpose (checkout-free merge strategies for orchestrator worktrees)
- Chunk and subsystem backreferences
- Required imports: `subprocess`, `Path` from pathlib, `WorktreeError` from `orchestrator.worktree`

Location: `src/orchestrator/merge.py`

### Step 2: Move `_merge_without_checkout` to merge.py

Extract the `_merge_without_checkout` method from `WorktreeManager` and convert it to a module-level function:
- Function signature: `def merge_without_checkout(source_branch: str, target_branch: str, repo_dir: Path) -> None`
- Remove the `self` parameter (it wasn't used for state access)
- Keep the existing Chunk backreference comment from `orch_merge_safety`
- Add backreference to this chunk (`worktree_merge_extract`)

Location: `src/orchestrator/merge.py`

### Step 3: Move `_merge_via_index` to merge.py

Extract the `_merge_via_index` method and convert to module-level function:
- Function signature: `def merge_via_index(source_branch: str, source_sha: str, target_branch: str, target_sha: str, repo_dir: Path) -> None`
- Keep the existing Chunk backreference comment from `orch_merge_safety`
- Add backreference to this chunk

Location: `src/orchestrator/merge.py`

### Step 4: Move `_update_working_tree_if_on_branch` to merge.py

Extract the `_update_working_tree_if_on_branch` method and convert to module-level function:
- Function signature: `def update_working_tree_if_on_branch(target_branch: str, repo_dir: Path) -> None`
- Keep the existing Chunk backreference comment from `orch_merge_safety`
- Add backreference to this chunk

Location: `src/orchestrator/merge.py`

### Step 5: Update the merge functions to call each other correctly

Update internal references within `merge.py`:
- `merge_without_checkout` calls `merge_via_index` (for fallback) and `update_working_tree_if_on_branch`
- `merge_via_index` calls `update_working_tree_if_on_branch`

No self-references needed since these are now module functions.

### Step 6: Update `worktree.py` to import and delegate to merge.py

In `src/orchestrator/worktree.py`:
1. Add import: `from orchestrator.merge import merge_without_checkout`
2. Replace the body of `_merge_without_checkout` with a delegation call:
   - Keep the method signature for internal consistency
   - Call `merge_without_checkout(source_branch, target_branch, repo_dir)`
3. Remove the `_merge_via_index` method (now internal to merge.py)
4. Remove the `_update_working_tree_if_on_branch` method (now internal to merge.py)
5. Add backreference to this chunk at the import statement

### Step 7: Handle WorktreeError import in merge.py

The merge module needs `WorktreeError` but importing from `orchestrator.worktree` would create a circular import. Options:
- Move `WorktreeError` to a shared location (breaks goal of unchanged public API)
- Use a local exception class in merge.py that worktree.py maps
- Import with TYPE_CHECKING guard and use string annotation

**Solution**: Move `WorktreeError` to `merge.py` since it's logically an error related to merge operations, and re-export it from `worktree.py` for backward compatibility:

In `merge.py`:
```python
class WorktreeError(Exception):
    """Exception raised for worktree and merge-related errors."""
    pass
```

In `worktree.py`:
```python
from orchestrator.merge import WorktreeError  # Re-export for backward compatibility
```

This maintains the existing import pattern: `from orchestrator.worktree import WorktreeError`

### Step 8: Verify all existing tests pass

Run the existing test suite to ensure no regressions:
```bash
uv run pytest tests/test_orchestrator_worktree*.py tests/test_orchestrator_scheduler*.py -v
```

All tests should pass without modification since:
- The public API (`WorktreeManager.merge_to_base`, `WorktreeManager.finalize_work_unit`) is unchanged
- The error type (`WorktreeError`) is still importable from `orchestrator.worktree`
- The behavior is identical, just organized differently

### Step 9: Verify imports and exports in orchestrator/__init__.py

Confirm that `orchestrator/__init__.py` still exports `WorktreeError` and `WorktreeManager` correctly. No changes should be needed since the re-export from `worktree.py` maintains backward compatibility.

### Step 10: Add code backreferences to GOAL.md

Update the chunk's GOAL.md with code_references pointing to the new module and the updated delegation in worktree.py.

## Risks and Open Questions

1. **Circular import risk**: The `WorktreeError` import could cause circular dependencies. Resolved by moving the exception class to `merge.py` and re-exporting from `worktree.py`.

2. **Backward compatibility of imports**: Any code doing `from orchestrator.worktree import WorktreeError` must continue to work. The re-export pattern handles this.

3. **Test coverage of merge paths**: The existing tests cover the merge behavior but may not directly import `merge.py`. This is fine - the tests verify the public API behavior.

## Deviations

No significant deviations from the plan. The implementation followed the sequence as documented.

Minor improvements made during implementation:
- Moved `os` and `tempfile` imports to module level in `merge.py` instead of keeping them as local imports inside `merge_via_index`. This is cleaner Python style and has no behavioral impact.