<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds automatic retry-via-rebase when merge conflicts occur during
work unit finalization. The approach builds on the existing finalization flow
in `scheduler._finalize_completed_work_unit` and the worktree infrastructure in
`WorktreeManager`.

**High-level strategy:**

1. **Distinguish merge conflicts from other errors** — The `WorktreeError`
   raised by `merge_to_base` on conflict needs to be distinguishable from other
   errors. We'll create a `MergeConflictError` subclass of `WorktreeError`.

2. **Add a retry counter to WorkUnit** — Track `merge_conflict_retries` to
   bound the retry loop (max 2 retries, escalate on third conflict).

3. **Recreate worktree from existing branch** — When a merge conflict is
   detected post-worktree-removal, recreate the worktree from the surviving
   `orch/<chunk>` branch using an existing branch variant of `create_worktree`.

4. **Make verify_chunk_active_status idempotent** — Update `_is_post_implementing`
   to treat ACTIVE status as valid (already complete), not as an error.

5. **Cycle back to REBASE phase** — On merge conflict detection, set the work
   unit phase to REBASE and status to READY for the scheduler to pick up.

**Following existing patterns:**

- The `finalization_recovery` chunk (already in `created_after`) handles crash
  recovery for incomplete finalizations — this chunk handles runtime conflicts.
- The `phase_aware_recovery` chunk shows how to handle worktree recreation for
  existing branches.
- The retry pattern mirrors `api_retry_count` and `completion_retries` fields.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of
  the orchestrator subsystem's finalization and recovery logic. It extends the
  existing patterns in `scheduler.py`, `worktree.py`, and `activation.py`.

## Sequence

### Step 1: Add MergeConflictError to distinguish merge conflicts

Create a `MergeConflictError` subclass of `WorktreeError` in `src/orchestrator/merge.py`.
Raise this specific exception when a merge conflict is detected in
`merge_without_checkout` (when "CONFLICT" is in output) and `merge_via_index`
(when read-tree fails).

Location: `src/orchestrator/merge.py`

This allows callers to catch merge conflicts specifically, while other
`WorktreeError` cases continue to escalate normally.

### Step 2: Add merge_conflict_retries field to WorkUnit model

Add `merge_conflict_retries: int = 0` field to the `WorkUnit` model in
`src/orchestrator/models.py`. Also add it to `model_dump_json_serializable()`.

Location: `src/orchestrator/models.py`

### Step 3: Add migration for merge_conflict_retries column

Add a SQLite migration in `src/orchestrator/state.py` to add the
`merge_conflict_retries` column to the `work_units` table with default 0.
Update `_row_to_work_unit` to read this field.

Location: `src/orchestrator/state.py`

### Step 4: Add create_worktree_from_branch method to WorktreeManager

Add a new method `create_worktree_from_branch(chunk: str)` that creates a
worktree from an existing `orch/<chunk>` branch (rather than creating the
branch from base). This is needed because after finalization removes the
worktree, the branch survives and we need to recreate the worktree from it.

The method should:
1. Verify the branch exists
2. Create the worktree directory
3. Run `git worktree add <path> <branch>` (branch already exists)
4. Lock the worktree

Location: `src/orchestrator/worktree.py`

### Step 5: Update _finalize_completed_work_unit to handle merge conflicts

Modify `_finalize_completed_work_unit` in `src/orchestrator/scheduler.py` to:

1. Import `MergeConflictError` from `orchestrator.merge`
2. Catch `MergeConflictError` specifically during the `finalize_work_unit` call
3. Check if `merge_conflict_retries < 2` (allow 2 retries)
4. If retries available:
   - Increment `merge_conflict_retries`
   - Recreate worktree from existing branch via `create_worktree_from_branch`
   - Set phase to `REBASE`, status to `READY`
   - Update and persist work unit
   - Broadcast update via WebSocket
   - Log the retry
5. If retries exhausted (≥2):
   - Escalate to `NEEDS_ATTENTION` with clear message about 3 failed merges
6. Other `WorktreeError` cases continue to escalate immediately

Location: `src/orchestrator/scheduler.py`

### Step 6: Make verify_chunk_active_status idempotent for ACTIVE chunks

Update `verify_chunk_active_status` in `src/orchestrator/activation.py` to
return `VerificationStatus.COMPLETED` when the chunk is already ACTIVE. This
is already partially handled by `_is_post_implementing`, but we should verify
it works correctly when re-entering COMPLETE phase after a merge conflict retry.

The function already checks `_is_post_implementing(frontmatter.status)`, and
ACTIVE is reachable from IMPLEMENTING in the state machine, so this should
already work. Add a test to confirm this behavior.

Location: `src/orchestrator/activation.py` (verification/testing only)

### Step 7: Reset merge_conflict_retries on successful completion

In `_finalize_completed_work_unit`, after successful finalization (when
transitioning to DONE), reset `merge_conflict_retries` to 0 for cleanliness.

Location: `src/orchestrator/scheduler.py`

### Step 8: Write tests for merge conflict retry behavior

Create tests in a new file `tests/test_orchestrator_merge_retry.py`:

1. **Test merge conflict triggers rebase retry** — Mock `finalize_work_unit` to
   raise `MergeConflictError`, verify work unit cycles to REBASE with status
   READY and incremented `merge_conflict_retries`.

2. **Test successful retry completes normally** — Verify that after a conflict
   retry, the work unit can complete normally when merge succeeds.

3. **Test third conflict escalates** — Set `merge_conflict_retries=2`, trigger
   another conflict, verify escalation to `NEEDS_ATTENTION` with appropriate
   message.

4. **Test non-conflict errors still escalate immediately** — Verify that
   `WorktreeError` (non-merge-conflict) escalates to `NEEDS_ATTENTION` without
   retry.

5. **Test ACTIVE chunk idempotency** — Verify `verify_chunk_active_status`
   returns COMPLETED for already-ACTIVE chunks.

Location: `tests/test_orchestrator_merge_retry.py`

### Step 9: Update WorktreeManager.finalize_work_unit to propagate MergeConflictError

Ensure `finalize_work_unit` in `src/orchestrator/worktree.py` propagates
`MergeConflictError` from `merge_to_base` without catching and rewrapping it.
Currently it catches `WorktreeError` — since `MergeConflictError` is a subclass,
it should propagate correctly, but verify this behavior.

Location: `src/orchestrator/worktree.py`

### Step 10: Update GOAL.md code_paths and subsystems

Update the chunk's GOAL.md frontmatter with:
- `code_paths`: List all files touched
- `subsystems`: Add orchestrator with relationship "implements"

Location: `docs/chunks/orch_merge_rebase_retry/GOAL.md`

## Risks and Open Questions

1. **Race condition during worktree recreation** — If another process creates
   a worktree for the same chunk between conflict detection and recreation,
   we may fail. This is unlikely in practice since only one work unit per chunk
   exists. Mitigation: The worktree creation already handles "already exists"
   gracefully.

2. **Branch state after partial merge** — When `merge_to_base` fails with a
   conflict, the branch should be unchanged (we use plumbing commands that
   don't modify the branch until success). Verify this assumption in testing.

3. **Displaced chunk handling** — If a chunk had a displaced chunk before the
   conflict, we need to handle this correctly on retry. The `displaced_chunk`
   field persists on the work unit, so restore logic should work correctly.

4. **Existing test coverage** — Need to verify that the existing finalization
   tests don't break with the new error handling.

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
