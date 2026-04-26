---
discovered_by: audit batch 7e
discovered_at: 2026-04-26T02:05:09Z
severity: medium
status: open
artifacts:
  - docs/chunks/orch_merge_before_delete/GOAL.md
  - src/orchestrator/worktree.py
  - tests/test_orchestrator_scheduler.py
---

## Claim

`docs/chunks/orch_merge_before_delete/GOAL.md` (status: ACTIVE) asserts that the orchestrator's completion flow has been reordered to merge-before-delete:

- Frontmatter `code_references`:
  - `src/orchestrator/scheduler.py#Scheduler::_advance_phase` — "Merge-before-delete completion flow: merges worktree branch to base before worktree removal, preserving worktree for investigation on merge failure"
  - `tests/test_orchestrator_scheduler.py#TestPhaseAdvancement::test_advance_merge_failure_preserves_worktree` — "Test verifying worktree preservation when merge fails"
- Success criteria: "In `Scheduler._advance_phase` completion handling, `merge_to_base` is called before `remove_worktree`"; "When a merge fails and the work unit enters NEEDS_ATTENTION, the worktree directory still exists on disk"; "The stale comment `# Remove the worktree (must be done before merge)` is removed".

## Reality

The completion flow still removes the worktree before attempting the merge, and the stale comment is still present.

In `src/orchestrator/worktree.py` lines 1398-1437 (`WorktreeManager.finalize_work_unit`, the function `Scheduler._finalize_completed_work_unit` actually calls):

```
# Step 2: Remove worktree (must be done before merge to avoid conflicts)
self.remove_worktree(chunk, remove_branch=False)

# Step 3: Merge the branch back to base if it has changes
if self.has_changes(chunk):
    self.merge_to_base(chunk, delete_branch=True)
```

That is, `remove_worktree` is invoked before `merge_to_base`, with the comment "must be done before merge" still in place — exactly the structure the chunk claims to have replaced.

Additionally:

- `Scheduler._advance_phase` itself does not call `merge_to_base` or `remove_worktree` directly; the actual merge/delete logic was moved into `WorktreeManager.finalize_work_unit` by the `orch_prune_consolidate` chunk. So the chunk's `code_references` point at a function that no longer owns this responsibility at all.
- `tests/test_orchestrator_scheduler.py` contains no test named `test_advance_merge_failure_preserves_worktree` and no `TestPhaseAdvancement` class — `grep -n` returns zero results.

## Workaround

None — the chunk is ACTIVE but its intent (merge-before-delete) is not realized in current code. The audit left the GOAL.md prose untouched (veto on rewrite when undeclared over-claim is detected) and logged this entry instead.

## Fix paths

1. (Preferred) Land the implementation: in `WorktreeManager.finalize_work_unit`, swap the order so `merge_to_base` runs before `remove_worktree`, remove the stale comment, update the `code_references` to point at `worktree.py#WorktreeManager::finalize_work_unit` (and any test that gets added), and verify the NEEDS_ATTENTION-with-worktree-present behavior with a real test.
2. Reframe the chunk: if merge-before-delete turns out to be unsafe given the current `merge_to_base` implementation (it uses git plumbing per `orch_merge_safety`, which the chunk's prose already cites — so this should be safe, but verify), document why and historicalize. Do not leave the chunk ACTIVE while pointing at code that contradicts it.
