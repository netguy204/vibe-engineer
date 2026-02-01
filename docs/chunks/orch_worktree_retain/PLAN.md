<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk changes the orchestrator's worktree lifecycle from automatic cleanup to explicit user-controlled removal. The key insight is that worktrees are valuable work artifacts that should be preserved until the user explicitly removes them.

**Current behavior (problematic):**
1. `scheduler.py#_advance_phase()` removes worktrees immediately after successful merge
2. `scheduler.py#_recover_from_crash()` removes orphaned worktrees on daemon restart

**New behavior (safe):**
1. Worktrees are retained after completion (merge succeeds, worktree stays)
2. Worktrees are retained during orphan recovery (logged, not deleted)
3. New CLI commands provide explicit worktree management

**Strategy:**
- Remove the `remove_worktree()` call from `_advance_phase()` after successful completion
- Remove the `remove_worktree()` call from `_recover_from_crash()` for orphaned worktrees
- Add new API endpoints for worktree listing and removal
- Add new CLI commands under `ve orch worktree` subgroup
- Add worktree count tracking and warning threshold via config
- Update dashboard to show worktree status

This follows the existing patterns in `src/cli/orch.py` for CLI subgroups and `src/orchestrator/api.py` for new endpoints.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS new functionality
  (worktree retention) within the orchestrator subsystem. The worktree management logic
  is already part of the orchestrator pattern; this chunk extends it with retention
  behavior and CLI/API exposure.

## Sequence

### Step 1: Write tests for worktree retention behavior

Following TDD, write failing tests for:
- Worktrees NOT removed after successful completion
- Worktrees NOT removed during orphan recovery
- Worktree list API returns correct status (completed, orphaned, active)
- Worktree removal API removes specific worktree
- Worktree prune removes all completed worktrees
- Warning logged when worktree count exceeds threshold

Location: `tests/test_orchestrator_worktree.py`, `tests/test_orchestrator_scheduler.py`

### Step 2: Add WorktreeInfo model for worktree metadata

Create a model to represent worktree status information:
- `chunk`: Chunk name
- `path`: Path to worktree
- `status`: "active" | "completed" | "orphaned"
- `work_unit_status`: Optional[WorkUnitStatus] - linked work unit status if exists
- `created_at`: Timestamp from worktree directory mtime

Location: `src/orchestrator/models.py`

### Step 3: Extend WorktreeManager with list_worktrees_with_status()

Add method to list all worktrees with their status:
- "active": Work unit exists and is RUNNING
- "completed": Work unit exists and is DONE
- "orphaned": No work unit exists for this worktree, or work unit is not RUNNING/DONE

This method needs access to the StateStore to check work unit status.

Location: `src/orchestrator/worktree.py`

### Step 4: Add worktree count threshold to OrchestratorConfig

Add new config field:
- `worktree_warning_threshold: int = 10` (default 10)

This is stored in the config table and can be updated via `ve orch config`.

Location: `src/orchestrator/models.py`

### Step 5: Remove automatic worktree deletion from _advance_phase()

In `scheduler.py#_advance_phase()`, remove the `remove_worktree()` call that happens
after successful merge. The worktree should remain for potential recovery.

The specific code to remove is:
```python
# Remove the worktree (must be done before merge)
try:
    self.worktree_manager.remove_worktree(chunk, remove_branch=False)
except WorktreeError as e:
    logger.warning(f"Failed to remove worktree for {chunk}: {e}")
```

**Note:** The worktree must still be removed before `merge_to_base()` because git
cannot merge while a worktree references the branch. The new approach:
1. Call `remove_worktree(chunk, remove_branch=False)` before merge (keep branch)
2. After successful merge, delete the branch but leave the worktree directory
3. The worktree directory remains as an "orphaned" artifact until explicit cleanup

Wait - this approach has a problem. Once we call `git worktree remove`, the directory
is either deleted or becomes a regular directory (not a git worktree). We need a
different approach:

**Revised approach:**
1. After successful completion, do NOT remove the worktree at all
2. The `merge_to_base()` method handles this by first removing the worktree, then merging
3. We need to refactor: separate the "remove worktree for merge" step from cleanup
4. Alternative: Keep worktree directory as a non-git archive for recovery

Actually, looking more carefully at the code:
- `merge_to_base()` is called from `_advance_phase()`
- Before `merge_to_base()`, the code calls `remove_worktree()`
- The worktree MUST be removed before merge because git prevents merging a checked-out branch

So the retention needs to happen differently:
1. Keep the `.ve/chunks/<chunk>/` directory structure
2. Remove the worktree proper (required for merge)
3. But preserve log files and potentially a snapshot of the work

For this chunk's scope (recovering work from failed phases), we should:
1. NOT remove `.ve/chunks/<chunk>/` directory after completion (currently removed by `remove_worktree`)
2. The `worktree/` subdirectory will be removed (required for merge)
3. Logs remain in `log/` subdirectory
4. Add a new `prune` command to clean up completed chunk directories

Wait, looking at `remove_worktree()`:
```python
def _remove_single_repo_worktree(self, chunk: str, remove_branch: bool) -> None:
    worktree_path = self.get_worktree_path(chunk)  # .ve/chunks/<chunk>/worktree
    # ... removes just the worktree, not the parent directory
```

So the directory structure `.ve/chunks/<chunk>/` with `log/` already survives!
The issue in the incident was the worktree removal during `_recover_from_crash()`.

Let me re-read the goal more carefully:
1. Worktrees deleted after completion in `_handle_completion()` - this is actually fine since logs remain
2. Worktrees deleted during `_recover_from_crash()` - THIS is the problem

The incident: `cli_modularize` had work in the worktree that wasn't committed. When
the COMPLETE phase orphaned and the daemon restarted, `_recover_from_crash()` deleted
the worktree with all the uncommitted changes.

**Actual fix:**
1. In `_recover_from_crash()`, do NOT delete orphaned worktrees - just log their presence
2. Add CLI commands to manually clean up worktrees after recovery
3. The worktree after completion is fine to remove (work is merged)

Location: `src/orchestrator/scheduler.py`

### Step 6: Remove automatic worktree deletion from _recover_from_crash()

In `scheduler.py#_recover_from_crash()`, change the behavior:
- Still mark RUNNING work units as READY (they'll retry)
- Do NOT delete orphaned worktrees
- Instead, log a warning about retained worktrees and their count
- If count exceeds threshold, log additional warning

Current code to modify:
```python
# Clean up orphaned worktrees
orphaned = self.worktree_manager.cleanup_orphaned_worktrees()
for chunk in orphaned:
    unit = self.store.get_work_unit(chunk)
    if unit is None or unit.status != WorkUnitStatus.RUNNING:
        logger.info(f"Removing orphaned worktree for {chunk}")
        try:
            self.worktree_manager.remove_worktree(chunk, remove_branch=False)
        except WorktreeError as e:
            logger.warning(f"Failed to remove orphaned worktree: {e}")
```

New behavior:
```python
# Detect orphaned worktrees but do NOT remove them automatically
orphaned = self.worktree_manager.list_worktrees()
if orphaned:
    logger.warning(
        f"Found {len(orphaned)} retained worktrees. "
        f"Use 've orch worktree list' to view and 've orch worktree prune' to clean up."
    )
    if len(orphaned) > self.config.worktree_warning_threshold:
        logger.warning(
            f"Worktree count ({len(orphaned)}) exceeds threshold "
            f"({self.config.worktree_warning_threshold}). Consider pruning."
        )
```

Location: `src/orchestrator/scheduler.py`

### Step 7: Add worktree list API endpoint

Add `GET /worktrees` endpoint that returns all worktrees with status:
- Calls `WorktreeManager.list_worktrees()`
- For each worktree, looks up work unit status to determine state
- Returns JSON array with chunk, path, status, work_unit_status

Location: `src/orchestrator/api.py`

### Step 8: Add worktree remove API endpoint

Add `DELETE /worktrees/{chunk}` endpoint:
- Validates worktree exists
- Removes worktree and optionally branch
- Returns success/failure

Location: `src/orchestrator/api.py`

### Step 9: Add worktree prune API endpoint

Add `POST /worktrees/prune` endpoint:
- Removes all worktrees for DONE work units
- Returns list of pruned chunks and count

Location: `src/orchestrator/api.py`

### Step 10: Add ve orch worktree subgroup to CLI

Create new subgroup under `orch`:
```python
@orch.group("worktree")
def worktree():
    """Worktree management commands."""
    pass
```

Location: `src/cli/orch.py`

### Step 11: Add ve orch worktree list command

Implement `ve orch worktree list`:
- Calls the worktree list API
- Displays table: CHUNK, STATUS, WORKTREE_PATH
- Optionally filter by status with `--status` flag

Location: `src/cli/orch.py`

### Step 12: Add ve orch worktree remove command

Implement `ve orch worktree remove <chunk>`:
- Calls the worktree remove API
- Reports success/failure
- Option `--keep-branch` to preserve branch

Location: `src/cli/orch.py`

### Step 13: Add ve orch worktree prune command

Implement `ve orch worktree prune`:
- Calls the worktree prune API
- Reports list of pruned worktrees and count
- Requires confirmation or `--yes` flag

Location: `src/cli/orch.py`

### Step 14: Update ve orch config for worktree threshold

Extend `ve orch config` to show and update `worktree_warning_threshold`:
- `ve orch config` shows current threshold
- `ve orch config --worktree-threshold N` updates it

Location: `src/cli/orch.py`

### Step 15: Update dashboard worktree display

Add worktree count and status to dashboard:
- Show count of retained worktrees
- Show warning indicator if count exceeds threshold
- Link to cleanup documentation or action

Location: `src/orchestrator/templates/dashboard.html`

### Step 16: Update ORCHESTRATOR.md documentation

Document the new worktree retention behavior:
- Explain why worktrees are retained
- Document `ve orch worktree list/remove/prune` commands
- Explain the warning threshold and how to configure it
- Add recovery workflow for accessing orphaned worktree content

Location: `docs/trunk/ORCHESTRATOR.md`

### Step 17: Run all tests and verify behavior

- Run `uv run pytest tests/test_orchestrator_*.py`
- Verify all new tests pass
- Verify existing tests still pass
- Manual test: inject chunk, complete it, verify worktree retained

## Dependencies

- `cli_modularize` chunk must be complete (this chunk depends on the modular CLI structure)

## Risks and Open Questions

1. **Disk space**: Retained worktrees consume disk space. Mitigation: warning threshold
   and prune command make it easy to clean up. Document recommended cleanup frequency.

2. **Git worktree limits**: Git has a soft limit on worktrees. The warning threshold
   (default 10) should keep us well under any practical limits.

3. **Branch name collisions**: After pruning a worktree, the branch may still exist
   (if `--keep-branch` was used). Re-injecting the same chunk would fail. Mitigation:
   by default remove branch during prune; document the edge case.

4. **Multi-repo worktrees**: The task context mode creates worktrees across multiple
   repos. The prune logic must handle both `worktree/` and `work/<repo>/` structures.
   Use `WorktreeManager.is_task_context()` to detect and handle appropriately.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->