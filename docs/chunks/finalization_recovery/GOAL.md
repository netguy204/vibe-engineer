---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/scheduler.py
- tests/test_orchestrator_scheduler.py
code_references:
  - ref: src/orchestrator/scheduler.py#Scheduler::_find_incomplete_finalizations
    implements: "Detect work units that crashed during finalization (worktree removed, branch unmerged)"
  - ref: src/orchestrator/scheduler.py#Scheduler::_recover_incomplete_finalization
    implements: "Auto-merge clean branches or escalate to NEEDS_ATTENTION on conflict"
  - ref: src/orchestrator/scheduler.py#Scheduler::_recover_from_crash
    implements: "Integration point - calls finalization recovery after RUNNING unit recovery"
narrative: arch_review_gaps
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: semantic
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

The orchestrator daemon is resilient to crashes during the finalization window of `WorktreeManager.finalize_work_unit()`, whose sequence is (1) commit changes, (2) remove worktree, (3) merge branch to base. A crash between steps 2 and 3 leaves committed changes only as a dangling `orch/<chunk>` branch ref with no worktree, which the basic RUNNING-unit reset path cannot detect.

The scheduler's `_recover_from_crash()` startup path includes incomplete-finalization recovery. After handling orphaned RUNNING work units, `_find_incomplete_finalizations()` scans for work units that show signs of interrupted finalization: the work unit is in COMPLETE phase (or DONE status), its `orch/<chunk>` branch exists with commits ahead of the persisted base branch (via `_load_base_branch`), and no worktree is present. For each such case, `_recover_incomplete_finalization()` either auto-completes the merge and calls `unblock_dependents` (when the merge is clean — fast-forward or conflict-free), or transitions the work unit to NEEDS_ATTENTION with an `attention_reason` naming the dangling `orch/<chunk>` branch the operator must merge manually (when the merge has conflicts). A warning is logged for every incomplete finalization detected, regardless of which branch is taken.

Existing crash recovery behavior is preserved: RUNNING work units are still reset to READY, and orphaned worktree detection continues to function. This prevents silent data loss of completed chunk work when the daemon dies mid-finalization.

## Success Criteria

- `Scheduler._recover_from_crash()` detects work units in COMPLETE phase (or DONE with incomplete merge) whose `orch/<chunk>` branch exists, has commits ahead of the persisted base branch (via `_load_base_branch`), and whose worktree has already been removed.
- For each detected incomplete finalization where the merge is clean (fast-forward or conflict-free merge), the recovery logic automatically completes the merge to base and deletes the branch, then transitions the work unit to DONE and calls `unblock_dependents`.
- For each detected incomplete finalization where the merge has conflicts, the work unit is transitioned to NEEDS_ATTENTION with an `attention_reason` that identifies the dangling branch name (`orch/<chunk>`) and explains the operator must manually complete the merge.
- A warning is logged for every incomplete finalization detected, regardless of whether auto-recovery succeeds or the work unit is escalated to NEEDS_ATTENTION.
- Existing crash recovery behavior is preserved: RUNNING work units are still reset to READY, and orphaned worktree detection continues to function as before.
- Tests verify the recovery path for both the auto-merge success case and the conflict/NEEDS_ATTENTION case, using the existing `StateStore` and `WorktreeManager` test infrastructure.

