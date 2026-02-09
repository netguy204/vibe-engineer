<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix addresses a semantic mismatch where `_run_work_unit()` unconditionally
calls `activate_chunk_in_worktree()` regardless of which phase is being executed.
Activation is a PLAN-phase concept (transitioning a chunk from FUTURE to
IMPLEMENTING), but post-PLAN phases already have the chunk in IMPLEMENTING,
ACTIVE, or HISTORICAL status on the branch.

The solution has two parts:

1. **Phase-aware activation in `_run_work_unit()`**: Only call activation during
   the PLAN phase. For all other phases, the worktree creation is sufficient
   since the chunk is already in the correct status on the branch.

2. **Worktree preservation in `_recover_from_crash()`**: If the worktree
   directory still exists on disk after a crash, preserve the worktree reference
   on the work unit rather than unconditionally clearing it. This avoids needless
   worktree recreation and the activation failure that follows.

This follows the existing patterns in the scheduler:
- Phase-specific handling already exists (e.g., REVIEW phase routing in
  `_handle_agent_result`, REBASE phase advancement)
- The worktree manager already has idempotent worktree creation

Tests will follow TDD principles per docs/trunk/TESTING_PHILOSOPHY.md, writing
failing tests first for each behavior change.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS
  phase-aware recovery behavior within the orchestrator subsystem. The chunk
  modifies `scheduler.py` and `activation.py`, both of which are core
  orchestrator components.

The orchestrator subsystem status is DOCUMENTED, so discovered deviations will
be logged but not fixed as part of this work.

## Sequence

### Step 1: Write failing tests for phase-aware activation

Add tests to `tests/test_orchestrator_scheduler.py` (or a new focused test
module `tests/test_orchestrator_phase_recovery.py`) that verify:

1. `_run_work_unit()` calls `activate_chunk_in_worktree()` during PLAN phase
2. `_run_work_unit()` does NOT call activation during IMPLEMENT phase
3. `_run_work_unit()` does NOT call activation during REBASE phase
4. `_run_work_unit()` does NOT call activation during REVIEW phase
5. `_run_work_unit()` does NOT call activation during COMPLETE phase

Use mock patching to verify `activate_chunk_in_worktree` call counts.

Location: `tests/test_orchestrator_phase_recovery.py`

### Step 2: Implement phase-aware activation check

Modify `_run_work_unit()` in `src/orchestrator/scheduler.py` to conditionally
call `activate_chunk_in_worktree()` only when `work_unit.phase == WorkUnitPhase.PLAN`.

The change wraps the existing activation call in a phase check:

```python
# Only activate during PLAN phase. Later phases already have the chunk
# in the correct status on the branch (IMPLEMENTING, ACTIVE, HISTORICAL).
if phase == WorkUnitPhase.PLAN:
    try:
        displaced = activate_chunk_in_worktree(worktree_path, chunk)
        if displaced:
            work_unit.displaced_chunk = displaced
            logger.info(f"Stored displaced chunk '{displaced}' for later restoration")
    except ValueError as e:
        # ... existing error handling ...
```

Add a backreference comment:
```python
# Chunk: docs/chunks/phase_aware_recovery - Phase-aware activation check
```

Location: `src/orchestrator/scheduler.py`, around line 610-630

### Step 3: Write failing tests for worktree preservation in recovery

Add tests that verify `_recover_from_crash()` behavior:

1. RUNNING work unit with worktree that still exists → worktree reference preserved
2. RUNNING work unit with worktree that no longer exists → worktree reference cleared
3. After recovery with preserved worktree, dispatch tick re-uses existing worktree

These tests will use the mock worktree manager to simulate the worktree existence
check.

Location: `tests/test_orchestrator_phase_recovery.py`

### Step 4: Implement worktree preservation in crash recovery

Modify `_recover_from_crash()` in `src/orchestrator/scheduler.py` to check if
the worktree directory still exists before clearing the worktree reference:

```python
for unit in running_units:
    logger.warning(f"Found orphaned RUNNING work unit: {unit.chunk}")
    unit.status = WorkUnitStatus.READY

    # Chunk: docs/chunks/phase_aware_recovery - Preserve worktree if still exists
    # Only clear the worktree reference if the worktree no longer exists.
    # This enables recovery to resume from the existing worktree rather than
    # recreating it and potentially hitting activation failures.
    if unit.worktree and self.worktree_manager.worktree_exists(unit.chunk):
        logger.info(f"Preserving existing worktree for {unit.chunk}")
    else:
        unit.worktree = None

    unit.updated_at = datetime.now(timezone.utc)
    # ... rest of existing logic ...
```

Location: `src/orchestrator/scheduler.py`, around line 329-345

### Step 5: Write integration tests for crash recovery at each phase

Add end-to-end tests that simulate daemon restart during each phase and verify
successful re-dispatch:

1. Crash during PLAN phase (chunk is FUTURE) → recovery succeeds, PLAN resumes
2. Crash during IMPLEMENT phase (chunk is IMPLEMENTING) → recovery succeeds, IMPLEMENT resumes
3. Crash during REBASE phase (chunk is IMPLEMENTING) → recovery succeeds
4. Crash during REVIEW phase (chunk is IMPLEMENTING) → recovery succeeds
5. Crash during COMPLETE phase (chunk is ACTIVE/HISTORICAL) → recovery succeeds without activation failure

These tests set up realistic chunk GOAL.md status for each phase scenario.

Location: `tests/test_orchestrator_phase_recovery.py`

### Step 6: Verify existing tests pass

Run the full orchestrator test suite to ensure no regressions:

```bash
uv run pytest tests/test_orchestrator*.py -v
```

All existing tests must continue to pass.

### Step 7: Add backreference comments to modified code

Ensure all modified sections have appropriate chunk backreference comments
following the format:

```python
# Chunk: docs/chunks/phase_aware_recovery - <brief description>
```

## Risks and Open Questions

1. **Worktree state consistency**: If a worktree exists but is in an
   inconsistent state (e.g., uncommitted changes from a previous crash), will
   resume behave correctly? The existing TOCTOU guard and worktree creation
   should handle this, but needs verification.

2. **Displaced chunk handling on resume**: When recovering with an existing
   worktree, the displaced_chunk field should already be set from the original
   dispatch. Verify this is preserved through recovery.

3. **WorktreeManager.worktree_exists() implementation**: Need to verify this
   method exists and correctly checks for the worktree directory on disk.
   If not, may need to add it.

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
-->
