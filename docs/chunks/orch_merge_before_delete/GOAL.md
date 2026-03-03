---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Merge-before-delete completion flow: merges worktree branch to base before worktree removal, preserving worktree for investigation on merge failure"
  - ref: tests/test_orchestrator_scheduler.py#TestPhaseAdvancement::test_advance_merge_failure_preserves_worktree
    implements: "Test verifying worktree preservation when merge fails"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- artifact_manager_base
- cli_exit_codes
- cli_help_text
- cli_task_context_dedup
- frontmatter_io
- integrity_subsystem_bidir
- orch_cli_extract
- orch_daemon_stale_files
- orch_merge_safety
- orch_state_transactions
---

# Chunk Goal

## Minor Goal

Reorder the scheduler's completion flow to merge the worktree branch to base **before** deleting the worktree. Currently (`scheduler.py` ~line 1025), the worktree is removed first and then the merge is attempted. If the merge fails (e.g., due to conflicts), the worktree is already gone, leaving the work unit in NEEDS_ATTENTION with no local working directory to inspect.

The comment `# Remove the worktree (must be done before merge)` is a stale assumption from before `orch_merge_safety` introduced checkout-free merging via git plumbing (`merge-tree`, `commit-tree`, `update-ref`). Since the merge never touches the working directory, the worktree's existence does not interfere.

Swapping to merge-then-delete means:
- If the merge succeeds, the worktree is deleted as before (no behavior change for the happy path)
- If the merge fails, the worktree is still present for investigation, making NEEDS_ATTENTION resolution easier and reducing the need for `--retain` as a safety mechanism

## Success Criteria

- In `Scheduler._advance_phase` completion handling, `merge_to_base` is called before `remove_worktree`
- The stale comment `# Remove the worktree (must be done before merge)` is removed
- When a merge fails and the work unit enters NEEDS_ATTENTION, the worktree directory still exists on disk
- When a merge succeeds, the worktree is cleaned up as before
- Existing tests pass; if there are tests covering completion flow, they reflect the new order
- The `retain_worktree` path remains unaffected (it still skips both merge and deletion)