---
decision: APPROVE
summary: All success criteria satisfied - worktree cleanup on activation failure implemented with tests, following existing scheduler cleanup patterns.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: The `_run_work_unit()` method in `src/orchestrator/scheduler.py` tracks whether the worktree was successfully created

- **Status**: satisfied
- **Evidence**: Line 724 adds `worktree_created = True` immediately after `create_worktree()` succeeds on line 722. This boolean tracks worktree creation state for later cleanup logic.

### Criterion 2: When `activate_chunk_in_worktree()` raises a `ValueError` (lines 730-733), the worktree is cleaned up before returning

- **Status**: satisfied
- **Evidence**: Lines 734-743 add cleanup logic inside the `except ValueError` block that checks `worktree_created` and calls `remove_worktree()` before the `return` statement at line 745.

### Criterion 3: The cleanup logic calls `self.worktree_manager.remove_worktree(chunk, remove_branch=False)` to match the cleanup pattern used elsewhere in the scheduler (e.g., line 1027 in `_advance_phase()`)

- **Status**: satisfied
- **Evidence**: Line 738 calls `self.worktree_manager.remove_worktree(chunk, remove_branch=False)` which matches the pattern at line 1039 (previously ~1027) in `_advance_phase()`. Both use `remove_branch=False` and wrap in try/except for `WorktreeError`.

### Criterion 4: A test case verifies that when activation fails, no worktree is left behind

- **Status**: satisfied
- **Evidence**: Two test cases added to `TestChunkActivationInWorkUnit` class in `tests/test_orchestrator_scheduler.py`:
  - `test_run_work_unit_cleans_up_worktree_on_activation_failure` verifies cleanup is called with correct parameters
  - `test_run_work_unit_logs_cleanup_failure_without_crashing` verifies cleanup failure is handled gracefully
  Both tests pass (confirmed via pytest run, 142 total tests pass).

### Criterion 5: The fix does not interfere with normal success paths or other error paths (e.g., `WorktreeError` during worktree creation)

- **Status**: satisfied
- **Evidence**:
  1. The `worktree_created = True` is set only after `create_worktree()` succeeds, so `WorktreeError` during creation triggers the separate `except WorktreeError` block at line 807.
  2. All 142 existing scheduler tests pass, including tests for normal success paths, `WorktreeError` handling, and other error cases.
  3. The cleanup is scoped to the `except ValueError` block and only runs if `worktree_created` is True.
