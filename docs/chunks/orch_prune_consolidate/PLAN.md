<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extracts duplicated worktree prune/merge/cleanup logic from three locations into a single consolidated method in `worktree.py`. The approach is pure refactoring with no behavioral changes.

**Current State:**

The following ~50-line sequence appears in three places:
1. `scheduler.py::_advance_phase()` (lines ~1000-1080) - on work unit completion
2. `api.py::prune_work_unit_endpoint()` (lines ~1390-1420) - for single worktree prune
3. `api.py::prune_all_endpoint()` (lines ~1469-1500) - batch prune iteration

**Duplicated Logic Pattern:**
```python
# 1. Commit any uncommitted changes
if worktree_manager.has_uncommitted_changes(chunk):
    worktree_manager.commit_changes(chunk)

# 2. Remove worktree (must be done before merge)
worktree_manager.remove_worktree(chunk, remove_branch=False)

# 3. Merge the branch back to base if it has changes
if worktree_manager.has_changes(chunk):
    worktree_manager.merge_to_base(chunk, delete_branch=True)
else:
    # Clean up the empty branch
    branch = worktree_manager.get_branch_name(chunk)
    if worktree_manager._branch_exists(branch):
        subprocess.run(["git", "branch", "-d", branch], ...)
```

**New Method:**

Create `finalize_work_unit(chunk: str) -> None` in `worktree.py` that:
1. Encapsulates the entire commit → remove → merge/cleanup sequence
2. Handles errors consistently (raises `WorktreeError`)
3. Is called by all three current locations

**Testing Strategy (per TESTING_PHILOSOPHY.md):**

This is pure refactoring. All existing tests should pass unchanged since behavior is preserved. We add one new test for the new method to verify the consolidated sequence works correctly.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the orchestrator subsystem by consolidating worktree lifecycle logic. The subsystem is in DOCUMENTED status, so we add this chunk to its implementing chunks but don't attempt broader refactoring.

## Sequence

### Step 1: Add finalize_work_unit method to WorktreeManager

Create the new consolidated method in `src/orchestrator/worktree.py`.

**Method signature:**
```python
def finalize_work_unit(self, chunk: str) -> None:
    """Finalize a completed work unit by committing, removing worktree, and merging.

    This method handles the complete lifecycle cleanup for a work unit:
    1. Commits any uncommitted changes with a standard message
    2. Removes the worktree (but keeps the branch for merge)
    3. Merges changes to base branch (or deletes empty branch)

    Args:
        chunk: Chunk name

    Raises:
        WorktreeError: If any step fails (commit, remove, merge)
    """
```

**Implementation:**
- Check for uncommitted changes with `has_uncommitted_changes()` and commit with `commit_changes()` if present
- Call `remove_worktree(chunk, remove_branch=False)` to remove worktree but keep branch
- Check `has_changes(chunk)` to determine if merge is needed
- If changes: call `merge_to_base(chunk, delete_branch=True)`
- If no changes: delete the empty branch with git command

Location: `src/orchestrator/worktree.py` (add after `commit_changes` method)

### Step 2: Update scheduler._advance_phase to use finalize_work_unit

Replace the inline commit/merge/cleanup sequence in `scheduler.py::_advance_phase()` with a call to `worktree_manager.finalize_work_unit(chunk)`.

**Before:**
```python
# Check for uncommitted changes that need to be committed
if self.worktree_manager.has_uncommitted_changes(chunk):
    ...
    self.worktree_manager.commit_changes(chunk)
    ...

# Remove worktree...
# Merge the branch back to base...
```

**After:**
```python
# Finalize worktree - commit, merge to base, and cleanup
try:
    self.worktree_manager.finalize_work_unit(chunk)
except WorktreeError as e:
    ...
```

Note: The retain_worktree check remains in the scheduler since that's a policy decision about whether to call finalize at all.

Location: `src/orchestrator/scheduler.py::_advance_phase()` (~lines 1000-1080)

### Step 3: Update api.prune_work_unit_endpoint to use finalize_work_unit

Replace the inline prune logic in the single-chunk prune endpoint.

**Before:**
```python
# Commit any uncommitted changes
if worktree_path.exists() and worktree_manager.has_uncommitted_changes(chunk):
    worktree_manager.commit_changes(chunk)

# Remove worktree (must be done before merge)
worktree_manager.remove_worktree(chunk, remove_branch=False)

# Merge the branch back to base if it has changes
if worktree_manager.has_changes(chunk):
    worktree_manager.merge_to_base(chunk, delete_branch=True)
else:
    ...
```

**After:**
```python
try:
    worktree_manager.finalize_work_unit(chunk)
except WorktreeError as e:
    ...
```

Location: `src/orchestrator/api.py::prune_work_unit_endpoint()` (~lines 1390-1420)

### Step 4: Update api.prune_all_endpoint to use finalize_work_unit

Replace the inline prune logic in the batch prune endpoint.

**Before:**
```python
for unit in retained_units:
    chunk = unit.chunk
    try:
        # Commit any uncommitted changes
        ...
        # Remove worktree (must be done before merge)
        worktree_manager.remove_worktree(chunk, remove_branch=False)
        # Merge the branch back to base if it has changes
        ...
```

**After:**
```python
for unit in retained_units:
    chunk = unit.chunk
    try:
        worktree_manager.finalize_work_unit(chunk)
        ...
```

Location: `src/orchestrator/api.py::prune_all_endpoint()` (~lines 1469-1500)

### Step 5: Add test for finalize_work_unit

Add a test case in `tests/test_orchestrator_worktree.py` to verify the consolidated method works correctly.

**Test class: TestFinalizeWorkUnit**

Tests to add:
1. `test_finalize_work_unit_commits_and_merges` - Make changes in worktree, call finalize, verify changes are on base branch
2. `test_finalize_work_unit_handles_no_changes` - No changes, verify empty branch is deleted
3. `test_finalize_work_unit_removes_worktree` - Verify worktree is removed after finalize
4. `test_finalize_work_unit_raises_on_error` - Verify WorktreeError propagates

Location: `tests/test_orchestrator_worktree.py`

### Step 6: Run tests and verify no behavioral changes

Execute the full test suite to confirm:
- All existing orchestrator tests pass without modification
- New `finalize_work_unit` tests pass
- No regressions in scheduler or API behavior

Command: `uv run pytest tests/test_orchestrator*.py -v`

## Dependencies

None - this chunk is independent and can be implemented immediately.

## Risks and Open Questions

1. **Import Dependency**: The scheduler needs to import `WorktreeError` - verify this doesn't create circular imports. (Low risk: WorktreeError is already imported in scheduler.py)

2. **Error Handling Semantics**: The original code in scheduler had specific error handling that marked work units as NEEDS_ATTENTION. Need to ensure the calling code still handles this correctly after the refactor.

3. **Multi-repo (task context) mode**: The original code in `_advance_phase` only uses single-repo mode. The API endpoints don't appear to support multi-repo prune. The new method should match existing behavior (single-repo only for now). Multi-repo support can be added as a future enhancement.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->