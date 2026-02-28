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
- tests/test_orchestrator_merge_retry.py
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

When a chunk completes the COMPLETE phase and its worktree is finalized, the merge-to-main step can fail with a merge conflict (another chunk merged to main in the meantime, causing divergence). Currently, this marks the work unit as `NEEDS_ATTENTION`, requiring operator intervention.

Instead, the orchestrator should automatically recover by cycling the work unit back to the REBASE phase. This lets an agent do a context-aware merge (it has the chunk's GOAL.md to inform conflict resolution), followed by a re-review, and then a second attempt at completion. This turns a manual escalation into a fully automated retry loop.

### Current flow on merge conflict during finalization

1. COMPLETE phase succeeds — chunk GOAL.md status is now ACTIVE
2. Mechanical commit runs
3. `finalize_work_unit` removes the worktree (`remove_branch=False`)
4. `merge_to_base` fails with a merge conflict
5. `WorktreeError` is caught → `NEEDS_ATTENTION` (operator must intervene)

### Desired flow

1. COMPLETE phase succeeds — chunk GOAL.md status is now ACTIVE
2. Mechanical commit runs
3. `finalize_work_unit` removes the worktree (`remove_branch=False`)
4. `merge_to_base` fails with a merge conflict
5. **Scheduler detects the merge conflict (vs other finalization errors)**
6. **Scheduler recreates the worktree from the surviving branch**
7. **Phase is set back to REBASE, status to READY**
8. Agent rebases the branch onto current main, resolves conflicts, runs tests
9. Reviewer re-reviews the merged result
10. COMPLETE phase runs again — chunk is already ACTIVE, so this must be idempotent
11. Finalization succeeds on retry

### Key complications

- **Worktree is already removed when the merge conflict is detected.** The branch survives (due to `remove_branch=False`), so the worktree can be recreated from it. The implementation must handle worktree recreation from an existing branch.
- **Chunk is already ACTIVE.** The COMPLETE phase (`/chunk-complete`) and `verify_chunk_active_status` must be idempotent — they should succeed when the chunk is already ACTIVE rather than failing because it's not IMPLEMENTING.
- **Infinite loop risk.** If the merge keeps failing (e.g., a pathological conflict pattern), the retry should be bounded. Two retry attempts are allowed — if the third merge also conflicts, escalate to `NEEDS_ATTENTION`.
- **Merge conflict vs other finalization errors.** Only merge conflicts should trigger the retry-via-rebase path. Other finalization errors (e.g., worktree removal failures, commit errors) should continue to escalate to `NEEDS_ATTENTION`.

## Success Criteria

- When `merge_to_base` fails with a merge conflict during finalization, the scheduler recreates the worktree from the surviving branch and cycles the work unit back to REBASE (status READY)
- On the retry cycle, the work unit progresses through REBASE → REVIEW → COMPLETE → finalization normally
- The COMPLETE phase and `verify_chunk_active_status` handle re-entry when the chunk is already ACTIVE (idempotent — no error, no status change needed)
- A merge conflict retry counter limits the cycle to two retries — a third merge conflict escalates to `NEEDS_ATTENTION` with a clear message
- Non-merge-conflict finalization errors continue to escalate to `NEEDS_ATTENTION` immediately (no retry)
- Tests cover: merge conflict triggers rebase retry, successful retry completes normally, third conflict escalates, non-conflict errors still escalate