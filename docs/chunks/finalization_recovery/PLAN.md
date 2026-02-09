<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds crash recovery for incomplete work unit finalization to the orchestrator scheduler. The existing `_recover_from_crash()` method handles orphaned RUNNING work units by resetting them to READY. We need to extend it to also detect and handle a more subtle failure mode: work units that crashed during the `finalize_work_unit()` sequence (commit → remove worktree → merge).

The key insight is that after a crash during finalization:
1. The work unit is in COMPLETE phase (or DONE status but with incomplete merge)
2. The worktree has been removed (by `remove_worktree()` which runs before `merge_to_base()`)
3. The `orch/<chunk>` branch exists with commits ahead of the persisted base branch
4. The merge to base was never completed

**Recovery strategy:**
- **Auto-recovery path**: If the merge would be clean (fast-forward or no conflicts), complete it automatically and transition to DONE
- **Escalation path**: If the merge has conflicts, transition to NEEDS_ATTENTION with a descriptive message

We will add a new helper method `_recover_incomplete_finalization()` to the Scheduler, called from `_recover_from_crash()`. This method will use the existing `WorktreeManager` infrastructure:
- `_branch_exists()` to check if the orch branch still exists
- `_load_base_branch()` to get the persisted base branch for the chunk
- `has_changes()` to check if the branch has commits ahead of base
- `merge_to_base()` to attempt the merge (raises `WorktreeError` on conflict)
- `delete_branch()` to clean up after successful merge

The implementation follows the existing patterns in the orchestrator subsystem (DEC-009: ArtifactManager Template Method Pattern applies to the subsystem's consistent use of lifecycle methods).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional crash recovery logic for the orchestrator scheduler, specifically extending `_recover_from_crash()` to handle incomplete finalization. The implementation follows the subsystem's existing patterns for state transitions and logging.

No deviations from subsystem patterns are expected.

## Sequence

### Step 1: Add helper method to detect incomplete finalization

Add a new private method `_find_incomplete_finalizations()` to the `Scheduler` class that:
1. Lists all work units in COMPLETE phase or DONE status
2. For each, checks if the `orch/<chunk>` branch exists
3. If branch exists and worktree does NOT exist (using `worktree_exists()`), checks if branch has commits ahead of base
4. Returns a list of chunk names needing recovery

Location: `src/orchestrator/scheduler.py`

```python
def _find_incomplete_finalizations(self) -> list[str]:
    """Find work units that crashed during finalization.

    Looks for work units where:
    - Status is DONE or phase is COMPLETE
    - The orch/<chunk> branch still exists
    - The worktree has been removed
    - The branch has commits ahead of base (merge wasn't completed)

    Returns:
        List of chunk names needing finalization recovery
    """
```

### Step 2: Add recovery method for incomplete finalization

Add a new private method `_recover_incomplete_finalization()` to handle a single chunk's recovery:

1. Load the persisted base branch for the chunk
2. Attempt to merge the branch to base using `merge_to_base()`
3. On success:
   - Log a warning about the auto-recovery
   - If work unit is in COMPLETE phase, transition to DONE
   - Call `unblock_dependents()` to unblock any waiting work
4. On `WorktreeError` (conflict):
   - Transition work unit to NEEDS_ATTENTION
   - Set `attention_reason` to explain the issue and dangling branch name

Location: `src/orchestrator/scheduler.py`

```python
def _recover_incomplete_finalization(self, chunk: str) -> None:
    """Recover a work unit that crashed during finalization.

    Attempts to complete the merge to base. On conflict, escalates
    to NEEDS_ATTENTION with a descriptive message.

    Args:
        chunk: The chunk name to recover
    """
```

### Step 3: Integrate recovery into _recover_from_crash()

Modify `_recover_from_crash()` to call the new recovery logic after handling orphaned RUNNING work units:

1. Call `_find_incomplete_finalizations()` to get chunks needing recovery
2. For each chunk, call `_recover_incomplete_finalization()`
3. Preserve existing behavior for RUNNING work units and orphaned worktrees

Location: `src/orchestrator/scheduler.py` (modify existing method)

The ordering matters: process RUNNING units first (existing behavior), then check for incomplete finalizations (new behavior).

### Step 4: Add test for auto-recovery success case

Write a test that simulates the crash-during-finalization scenario where merge is clean:

1. Create a git repo with initial commit
2. Create a StateStore and WorktreeManager
3. Create a worktree, make a commit on the branch
4. Remove the worktree (but NOT merge/delete branch)
5. Create a work unit in COMPLETE phase
6. Run `_recover_from_crash()`
7. Assert: work unit is now DONE, branch is deleted, merge happened

Location: `tests/test_orchestrator_scheduler.py` (new class `TestFinalizationRecovery`)

### Step 5: Add test for conflict escalation case

Write a test that simulates the crash-during-finalization scenario where merge has conflicts:

1. Create a git repo with initial commit
2. Create a worktree, make a commit on the branch
3. Make a conflicting commit on the base branch
4. Remove the worktree (but NOT merge/delete branch)
5. Create a work unit in COMPLETE phase
6. Run `_recover_from_crash()`
7. Assert: work unit is now NEEDS_ATTENTION, attention_reason mentions the branch name

Location: `tests/test_orchestrator_scheduler.py` (add to `TestFinalizationRecovery` class)

### Step 6: Add test verifying existing crash recovery is preserved

Write a regression test to ensure existing behavior isn't broken:

1. Create a work unit in RUNNING status
2. Run `_recover_from_crash()`
3. Assert: work unit is reset to READY (existing behavior still works)

Location: `tests/test_orchestrator_scheduler.py` (add to `TestFinalizationRecovery` class)

### Step 7: Add logging for recovery events

Ensure all recovery events are logged at WARNING level:
- "Found incomplete finalization for {chunk}: branch {branch} exists but merge not completed"
- "Auto-recovered incomplete finalization for {chunk}: merged to {base_branch}"
- "Incomplete finalization for {chunk} has merge conflict: escalating to NEEDS_ATTENTION"

Location: `src/orchestrator/scheduler.py` (within the new methods)

### Step 8: Handle edge case - branch exists but no changes

Add logic to handle the case where the branch exists but has no commits ahead of base (rare but possible if crash happened after merge but before branch deletion):

1. In `_find_incomplete_finalizations()`, use `has_changes()` to filter
2. If branch exists but no changes, just delete the branch (cleanup)

Location: `src/orchestrator/scheduler.py`

## Dependencies

- **Existing infrastructure**: This chunk builds on existing `WorktreeManager` methods (`_branch_exists`, `_load_base_branch`, `has_changes`, `merge_to_base`, `delete_branch`, `worktree_exists`) and `StateStore` work unit operations.
- **No new dependencies required**: All git operations use the existing worktree module.

## Risks and Open Questions

1. **Race condition with concurrent recovery**: If the daemon restarts while a finalization is already in progress (another process), the recovery logic might interfere. This is low-risk because:
   - The daemon uses a PID file to prevent multiple instances
   - The worktree removal happens before merge, so the absence of worktree is a strong signal

2. **Multi-repo (task context) mode**: The current implementation focuses on single-repo mode. Multi-repo would need to recover all repo merges. This is acceptable for now as multi-repo orchestration is less common and the recovery would simply escalate to NEEDS_ATTENTION if any repo has issues.

3. **Branch name conflicts**: If someone manually creates a branch with the `orch/` prefix, recovery might incorrectly try to merge it. This is low-risk because the recovery also checks for a matching work unit in COMPLETE phase.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->