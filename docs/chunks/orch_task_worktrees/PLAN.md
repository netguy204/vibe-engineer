<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the existing `WorktreeManager` class in `src/orchestrator/worktree.py` to support task context mode where multiple repositories need coordinated worktrees under a shared `work/` directory.

**Core strategy:**
1. Add an optional `repo_paths` parameter to `create_worktree()` that signals task context mode
2. When in task context: create `work/` and `log/` directories, with worktrees for each repo under `work/<repo-name>/`
3. Keep existing single-repo behavior unchanged when `repo_paths` is not provided
4. Extend `remove_worktree()` and `merge_to_base()` to handle multi-repo cleanup and merging

**Key design decisions:**
- Each repo worktree uses branch `orch/<chunk>` in its respective repository
- The `work/` directory is the agent's working directory; repos appear as sibling directories
- Commits and merges happen independently per repo; orchestrator coordinates success verification
- Single-repo mode continues to use `.ve/chunks/<chunk>/worktree/` (no `work/` wrapper)

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the worktree management portion of the orchestrator subsystem, extending `WorktreeManager` for task context support. The subsystem is DOCUMENTED status, so this is new functionality extending existing patterns rather than fixing deviations.

## Sequence

### Step 1: Add tests for multi-repo worktree creation (TDD red phase)

Write failing tests for the new task context behavior before implementing.

Location: `tests/test_orchestrator_worktree.py`

Tests to add:
- `test_create_worktree_with_repo_paths_creates_work_dir`: Verify `work/` directory structure created
- `test_create_worktree_with_repo_paths_creates_worktrees_per_repo`: Verify each repo gets a worktree under `work/<repo-name>/`
- `test_create_worktree_with_repo_paths_uses_correct_branches`: Verify each worktree is on `orch/<chunk>` branch
- `test_create_worktree_single_repo_unchanged`: Verify existing behavior still works when `repo_paths` not provided
- `test_get_work_directory_returns_work_path`: Test new `get_work_directory()` method

Use the existing `setup_task_directory()` helper from `conftest.py` to create test fixtures.

### Step 2: Implement multi-repo worktree creation

Extend `create_worktree()` to accept an optional `repo_paths` parameter.

Location: `src/orchestrator/worktree.py`

Changes:
```python
def create_worktree(
    self,
    chunk: str,
    repo_paths: Optional[list[Path]] = None,
) -> Path:
```

Behavior:
- If `repo_paths` is `None`: existing single-repo behavior (unchanged)
- If `repo_paths` is provided:
  1. Create `.ve/chunks/<chunk>/work/` directory
  2. Create `.ve/chunks/<chunk>/log/` directory
  3. For each repo in `repo_paths`:
     - Create worktree at `.ve/chunks/<chunk>/work/<repo.name>/`
     - Create branch `orch/<chunk>` in that repo if it doesn't exist
     - Add the worktree on that branch
  4. Return path to `work/` directory (the agent's working directory)

Add helper method:
```python
def get_work_directory(self, chunk: str) -> Path:
    """Get the work directory for a chunk in task context."""
    return self._get_worktree_base_path(chunk) / "work"
```

Add backreference comment:
```python
# Chunk: docs/chunks/orch_task_worktrees - Task context multi-repo worktree support
```

### Step 3: Add tests for multi-repo worktree removal (TDD red phase)

Write failing tests for cleanup behavior.

Location: `tests/test_orchestrator_worktree.py`

Tests to add:
- `test_remove_worktree_with_repo_paths_cleans_all`: Verify all repo worktrees removed
- `test_remove_worktree_with_repo_paths_removes_branches`: Verify branches deleted when requested
- `test_remove_worktree_single_repo_unchanged`: Verify existing cleanup behavior unchanged

### Step 4: Implement multi-repo worktree removal

Extend `remove_worktree()` to handle multi-repo case.

Location: `src/orchestrator/worktree.py`

Changes:
```python
def remove_worktree(
    self,
    chunk: str,
    remove_branch: bool = False,
    repo_paths: Optional[list[Path]] = None,
) -> None:
```

Behavior:
- If `repo_paths` is `None`: existing single-repo behavior
- If `repo_paths` is provided:
  1. For each repo in `repo_paths`:
     - Run `git worktree remove` for `.ve/chunks/<chunk>/work/<repo.name>/`
     - Optionally delete branch `orch/<chunk>` in that repo
  2. Remove the `work/` directory if empty
  3. Prune worktrees in each repo

### Step 5: Add tests for multi-repo merge (TDD red phase)

Write failing tests for merge behavior.

Location: `tests/test_orchestrator_worktree.py`

Tests to add:
- `test_merge_to_base_with_repo_paths_merges_all`: Verify merge happens in each repo
- `test_merge_to_base_partial_failure_reports_which_failed`: If one repo fails to merge, report clearly
- `test_has_changes_with_repo_paths`: Test checking for changes across multiple repos

### Step 6: Implement multi-repo merge

Extend `merge_to_base()` to handle multi-repo case.

Location: `src/orchestrator/worktree.py`

Changes:
```python
def merge_to_base(
    self,
    chunk: str,
    delete_branch: bool = True,
    repo_paths: Optional[list[Path]] = None,
) -> None:
```

Behavior:
- If `repo_paths` is `None`: existing single-repo behavior
- If `repo_paths` is provided:
  1. For each repo in `repo_paths`:
     - Checkout base branch (determined per-repo)
     - Merge `orch/<chunk>` into base
     - Optionally delete the branch
  2. If any merge fails, abort all merges that succeeded (rollback) and raise with details

Add similar extension to `has_changes()`:
```python
def has_changes(
    self,
    chunk: str,
    repo_paths: Optional[list[Path]] = None,
) -> bool | dict[str, bool]:
```
- Single-repo: returns `bool` (existing behavior)
- Multi-repo: returns `dict[str, bool]` mapping repo name to whether it has changes

### Step 7: Add tests for worktree listing in task context

Location: `tests/test_orchestrator_worktree.py`

Tests to add:
- `test_list_worktrees_includes_task_context_chunks`: Verify chunks with `work/` directories detected
- `test_worktree_exists_task_context`: Verify `worktree_exists()` works for task context structure

### Step 8: Update helper methods for task context detection

Add method to check if a chunk is in task context mode:

Location: `src/orchestrator/worktree.py`

```python
def is_task_context(self, chunk: str) -> bool:
    """Check if a chunk uses task context (multi-repo) structure."""
    return (self._get_worktree_base_path(chunk) / "work").exists()
```

Update `worktree_exists()` to handle both modes:
- Single-repo: check for `worktree/.git`
- Task context: check for `work/` with at least one repo subdirectory containing `.git`

Update `list_worktrees()` to detect both modes.

### Step 9: Run full test suite and verify

Run all tests to ensure:
1. New multi-repo tests pass
2. Existing single-repo tests still pass (no regressions)

```bash
uv run pytest tests/test_orchestrator_worktree.py -v
```

### Step 10: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/orchestrator/worktree.py`
- `tests/test_orchestrator_worktree.py`

## Dependencies

No external dependencies. This chunk builds on:
- Existing `WorktreeManager` class in `src/orchestrator/worktree.py`
- Existing test fixtures in `tests/conftest.py` (`setup_task_directory()`, `make_ve_initialized_git_repo()`)

## Risks and Open Questions

1. **Base branch per repo**: In task context, each repository may have a different default branch (main vs master). The current `WorktreeManager` captures the base branch at initialization. For multi-repo, we need to determine the base branch per-repo. **Mitigation**: Query each repo for its current branch at worktree creation time rather than using `self._base_branch`.

2. **Merge rollback complexity**: If merging succeeds in repo A but fails in repo B, we need to undo the merge in repo A. Git merge undo is possible but adds complexity. **Mitigation**: Start with a simple approach that reports which repos failed; full transactional semantics can be added later if needed.

3. **Return type change for `has_changes()`**: Changing return type from `bool` to `bool | dict[str, bool]` could break callers. **Mitigation**: This is internal API; callers are within the orchestrator module and can be updated. Review call sites in scheduler/daemon.

4. **Worktree path uniqueness**: When multiple repos are in `work/`, repo names must be unique (they are - they're directory names within the task directory).

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

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->