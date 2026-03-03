---
decision: APPROVE
summary: All success criteria satisfied - merge_to_base called before remove_worktree, stale comment removed, merge failures preserve worktree for investigation, all 143 tests pass.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: In `Scheduler._advance_phase` completion handling, `merge_to_base` is called before `remove_worktree`

- **Status**: satisfied
- **Evidence**: In `src/orchestrator/scheduler.py` lines 1037-1079, the non-retain_worktree path now: (1) attempts `merge_to_base` via `has_changes()` check and `merge_to_base()` call at lines 1040-1056, (2) on failure returns early at line 1073, (3) only calls `remove_worktree` at line 1077 after successful merge. The comment at line 1037-1038 documents this new order.

### Criterion 2: The stale comment `# Remove the worktree (must be done before merge)` is removed

- **Status**: satisfied
- **Evidence**: Grep for "must be done before merge" returned no matches in scheduler.py. The old comment has been replaced with the new backreference comment "# Chunk: docs/chunks/orch_merge_before_delete - Merge before worktree removal" at line 1037.

### Criterion 3: When a merge fails and the work unit enters NEEDS_ATTENTION, the worktree directory still exists on disk

- **Status**: satisfied
- **Evidence**: Lines 1057-1073 handle the merge failure case: on `WorktreeError`, the work unit is marked `NEEDS_ATTENTION` with reason "Merge to base failed: {e}" and the method returns without ever calling `remove_worktree`. Test `test_advance_merge_failure_preserves_worktree` (lines 285-325) explicitly verifies `remove_worktree.assert_not_called()` when merge fails.

### Criterion 4: When a merge succeeds, the worktree is cleaned up as before

- **Status**: satisfied
- **Evidence**: Lines 1075-1079 call `remove_worktree(chunk, remove_branch=False)` only after the merge try block completes successfully. Test `test_advance_complete_marks_done` (lines 230-281) verifies `remove_worktree` is called and also verifies the correct order via call index comparison.

### Criterion 5: Existing tests pass; if there are tests covering completion flow, they reflect the new order

- **Status**: satisfied
- **Evidence**: All 143 tests in `test_orchestrator_scheduler.py` pass. The test `test_advance_complete_marks_done` was updated to verify merge-before-remove order (lines 268-281 check `has_changes` call index < `remove_worktree` call index). A new test `test_advance_merge_failure_preserves_worktree` was added (lines 283-325).

### Criterion 6: The `retain_worktree` path remains unaffected (it still skips both merge and deletion)

- **Status**: satisfied
- **Evidence**: Lines 1030-1035 show the `if work_unit.retain_worktree:` branch remains unchanged - it logs retention and skips to the end without calling merge or remove. The entire merge-then-delete logic is in the `else:` block starting at line 1036.
