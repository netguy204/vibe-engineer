---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/merge.py
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/orchestrator/worktree.py
- src/orchestrator/scheduler.py
- src/orchestrator/activation.py
- tests/test_orchestrator_scheduler_merge_conflict.py
code_references:
- ref: src/orchestrator/scheduler.py#Scheduler::_handle_merge_conflict_retry
  implements: "Detect merge conflicts during finalization and cycle back to REBASE phase"
- ref: src/orchestrator/worktree.py#WorktreeManager::recreate_worktree_from_branch
  implements: "Recreate worktree from surviving branch after merge conflict"
- ref: src/orchestrator/merge.py#is_merge_conflict_error
  implements: "Distinguish merge conflicts from other finalization errors"
- ref: tests/test_orchestrator_scheduler_merge_conflict.py
  implements: "Tests for merge conflict retry logic"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- dead_code_removal
- narrative_compact_extract
- persist_retry_state
- repo_cache_dry
- reviewer_decisions_dedup
- worktree_merge_extract
- phase_aware_recovery
---

# Chunk Goal

## Minor Goal

When a chunk's worktree is finalized after the COMPLETE phase, the merge-to-main step can fail with a merge conflict if another chunk merged to main in the meantime. The orchestrator recovers from this automatically by cycling the work unit back to the REBASE phase rather than escalating to `NEEDS_ATTENTION`. Cycling back lets an agent perform a context-aware merge (with the chunk's GOAL.md to inform conflict resolution), followed by a re-review, and then a second attempt at completion — converting what would otherwise be a manual escalation into a fully automated retry loop.

### Finalization-time merge conflict flow

1. COMPLETE phase succeeds — chunk GOAL.md status is now ACTIVE
2. Mechanical commit runs
3. `finalize_work_unit` removes the worktree (`remove_branch=False`)
4. `merge_to_base` fails with a merge conflict
5. The scheduler distinguishes the merge conflict from other finalization errors
6. The scheduler recreates the worktree from the surviving branch
7. The phase is set back to REBASE, status to READY
8. An agent rebases the branch onto current main, resolves conflicts, runs tests
9. The reviewer re-reviews the merged result
10. The COMPLETE phase runs again idempotently — the chunk is already ACTIVE, so re-entry succeeds without error
11. Finalization succeeds on retry

### Key constraints

- **Worktree is already removed when the merge conflict is detected.** The branch survives (because `remove_branch=False`), so worktree recreation works from the surviving branch.
- **Chunk is already ACTIVE.** The COMPLETE phase (`/chunk-complete`) and `verify_chunk_active_status` are idempotent — they succeed when the chunk is already ACTIVE rather than failing for not being IMPLEMENTING.
- **Infinite loop bound.** Two retry attempts are allowed — if the third merge also conflicts, the work unit escalates to `NEEDS_ATTENTION`.
- **Merge conflict vs other finalization errors.** Only merge conflicts trigger the retry-via-rebase path. Other finalization errors (worktree removal failures, commit errors) escalate to `NEEDS_ATTENTION` immediately.

## Success Criteria

- When `merge_to_base` fails with a merge conflict during finalization, the scheduler recreates the worktree from the surviving branch and cycles the work unit back to REBASE (status READY)
- On the retry cycle, the work unit progresses through REBASE → REVIEW → COMPLETE → finalization normally
- The COMPLETE phase and `verify_chunk_active_status` handle re-entry when the chunk is already ACTIVE (idempotent — no error, no status change needed)
- A merge conflict retry counter limits the cycle to two retries — a third merge conflict escalates to `NEEDS_ATTENTION` with a clear message
- Non-merge-conflict finalization errors continue to escalate to `NEEDS_ATTENTION` immediately (no retry)
- Tests cover: merge conflict triggers rebase retry, successful retry completes normally, third conflict escalates, non-conflict errors still escalate