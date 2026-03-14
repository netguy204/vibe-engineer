<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a semantic bug fix targeting the double-commit race in the orchestrator's finalization path. The fix has three prongs:

1. **Eliminate the double-commit**: The scheduler's `_finalize_completed_work_unit()` currently calls `commit_changes()` (lines 1042–1053) and then `finalize_work_unit()` calls it again (lines 1310–1311). We make `finalize_work_unit()` the single owner of the commit→remove→merge sequence. The scheduler's pre-commit block is narrowed to only fire for `retain_worktree` work units (which skip `finalize_work_unit()` entirely).

2. **Harden `commit_changes()` against empty-stderr exit-code-1**: `git commit` can return exit code 1 with empty stderr in edge cases (e.g., submodule entries make `git status --porcelain` non-empty but `git commit` finds nothing staged). The current code only checks for "nothing to commit" in stdout/stderr text. We add a fallback: exit code 1 with empty stderr is treated as a no-op (returns `False`), not an error.

3. **Submodule-resilient worktree removal**: `git worktree remove` fails on worktrees with submodules ("working trees containing submodules cannot be moved or removed"). The existing `_remove_worktree_from_repo` already has a fallback to `shutil.rmtree`, but we should ensure it also runs `git worktree prune` after the rmtree to clean up stale worktree metadata—which it currently does only on the intermediate retry, not the final fallback.

Tests follow TDD per docs/trunk/TESTING_PHILOSOPHY.md. We write failing tests first for each behavioral change, then implement the fix.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS bug fixes in the orchestrator's worktree finalization and scheduling paths. The orchestrator subsystem's invariant that "worktrees are isolated execution environments" is preserved—this fix ensures cleanup succeeds even when submodules are present. No deviations from the subsystem's patterns are introduced.

## Sequence

### Step 1: Write failing tests for `commit_changes()` empty-stderr hardening

Add a test to `tests/test_orchestrator_worktree_operations.py` in the `TestCommitChanges` class:

- **`test_commit_changes_empty_stderr_exit_code_1_returns_false`**: Set up a worktree where `git commit` returns exit code 1 with empty stderr (simulate by committing in a clean tree where `git add -A` stages nothing new). The method should return `False` instead of raising `WorktreeError`.

The existing test `test_commit_changes_nothing_to_commit` covers the "nothing to commit" text case. This new test covers the edge case where the exit code is 1 but stderr is empty (no "nothing to commit" message).

Location: `tests/test_orchestrator_worktree_operations.py`

### Step 2: Implement `commit_changes()` empty-stderr hardening

In `src/orchestrator/worktree.py`, modify `commit_changes()` (line 1193–1196). After the existing check for "nothing to commit" in stdout/stderr, add: if `result.returncode == 1` and `result.stderr.strip() == ""`, return `False`. This treats exit-code-1-with-empty-stderr as a no-op rather than an error.

Add a backreference comment:
```python
# Chunk: docs/chunks/finalize_double_commit - Harden against empty-stderr exit-code-1
```

Location: `src/orchestrator/worktree.py#WorktreeManager::commit_changes`

### Step 3: Write failing tests for double-commit elimination

Add tests to `tests/test_orchestrator_worktree_multirepo.py` in the `TestFinalizeWorkUnit` class or a nearby scheduler test file:

- **`test_finalize_work_unit_with_clean_tree_succeeds`**: Create a worktree, commit all changes manually (leaving the tree clean), then call `finalize_work_unit()`. It should succeed without error — `commit_changes()` should gracefully no-op and the merge should proceed.

Add a scheduler-level test (in `tests/test_orchestrator_scheduler.py` or appropriate file):

- **`test_finalize_completed_does_not_commit_before_finalize`**: Mock `worktree_manager.commit_changes` and `worktree_manager.finalize_work_unit`. After `_finalize_completed_work_unit()` runs with `retain_worktree=False`, assert that `commit_changes` was NOT called directly by the scheduler (only `finalize_work_unit` is called, which internally handles commits).

- **`test_finalize_completed_retain_worktree_commits_directly`**: With `retain_worktree=True`, assert the scheduler DOES call `commit_changes` directly (since `finalize_work_unit` is skipped).

Location: `tests/test_orchestrator_worktree_multirepo.py`, `tests/test_orchestrator_scheduler.py`

### Step 4: Eliminate the double-commit in the scheduler

In `src/orchestrator/scheduler.py`, modify `_finalize_completed_work_unit()`:

**Before** (lines 1040–1053): The scheduler unconditionally checks for uncommitted changes and commits them, then later calls `finalize_work_unit()`.

**After**: Move the commit block (lines 1042–1053) inside the `if work_unit.retain_worktree:` branch. For the normal (non-retain) path, `finalize_work_unit()` already handles commit→remove→merge as a single sequence. The displaced-chunk restoration (lines 1056–1061) stays before both branches since it applies regardless.

The restructured logic:
```python
# Restore displaced chunk (unchanged)
if work_unit.displaced_chunk:
    restore_displaced_chunk(...)

if work_unit.retain_worktree:
    # Retained worktrees skip finalize_work_unit, so commit here
    if self.worktree_manager.has_uncommitted_changes(chunk):
        try:
            committed = self.worktree_manager.commit_changes(chunk)
            ...
        except WorktreeError as e:
            ...
            return
    logger.info(f"Retaining worktree for {chunk} ...")
else:
    # finalize_work_unit owns the full commit→remove→merge sequence
    try:
        self.worktree_manager.finalize_work_unit(chunk)
    except WorktreeError as e:
        ...
```

Update the backreference comment on the commit block to reference this chunk:
```python
# Chunk: docs/chunks/finalize_double_commit - Commit only for retained worktrees
```

Location: `src/orchestrator/scheduler.py#Scheduler::_finalize_completed_work_unit`

### Step 5: Write failing tests for submodule-resilient worktree removal

Add a test to `tests/test_orchestrator_worktree_core.py`:

- **`test_remove_worktree_submodule_fallback`**: Create a worktree, add a `.gitmodules` file (or mock the subprocess to simulate the submodule error), then call `remove_worktree()`. Assert the worktree directory is removed and `git worktree prune` is called.

Location: `tests/test_orchestrator_worktree_core.py`

### Step 6: Harden `_remove_worktree_from_repo` for submodule worktrees

In `src/orchestrator/worktree.py`, modify `_remove_worktree_from_repo()` (lines 743–778). The current final fallback at line 777–778 does `shutil.rmtree` but does not follow up with `git worktree prune`. Add a `git worktree prune` call after the `shutil.rmtree` fallback to ensure git's worktree metadata is cleaned up.

The flow becomes:
1. Unlock worktree
2. Try `git worktree remove --force`
3. On failure: prune, retry `git worktree remove --force`
4. On second failure: `shutil.rmtree` + `git worktree prune` (the prune after rmtree is the new addition)

Add a backreference comment:
```python
# Chunk: docs/chunks/finalize_double_commit - Prune after rmtree fallback for submodule worktrees
```

Location: `src/orchestrator/worktree.py#WorktreeManager::_remove_worktree_from_repo`

### Step 7: Run full test suite and verify

Run `uv run pytest tests/` to verify:
- All existing tests continue to pass
- All new tests pass
- The double-commit path is eliminated
- `commit_changes()` handles the empty-stderr edge case
- Worktree removal handles submodule cases

## Dependencies

No external dependencies. This chunk modifies existing code in `src/orchestrator/scheduler.py` and `src/orchestrator/worktree.py`. The `merge_strategy_simplify` chunk (listed in `created_after`) is already ACTIVE.

## Risks and Open Questions

- **Displaced chunk restoration ordering**: The displaced chunk restore currently sits between the commit block and the retain/finalize branch. Moving the commit block into the retain branch means the restore still runs before both paths, which is correct. But verify that `restore_displaced_chunk` doesn't create new uncommitted changes that `finalize_work_unit` needs to capture.
- **Test isolation for scheduler tests**: The scheduler tests may need mocking of `worktree_manager` methods. Check how existing scheduler tests handle this (likely via `unittest.mock` or fixture-injected fakes) and follow the same pattern.
- **Submodule test realism**: Real submodule scenarios are hard to reproduce in test fixtures. The submodule removal test may need to mock subprocess output rather than set up actual git submodules, to keep tests fast and reliable.

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