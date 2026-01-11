# Implementation Plan

## Approach

This chunk adds a verification step to the orchestrator's completion flow that ensures a chunk's GOAL.md has been properly marked `status: ACTIVE` before proceeding to commit and merge. This guards against a common failure mode where `/chunk-complete` runs but the agent doesn't finish the final step of updating the status.

**Strategy:**
1. After the COMPLETE phase finishes in `_advance_phase`, read and parse the chunk's GOAL.md frontmatter from the worktree
2. Check if `status` is `ACTIVE` - if so, proceed to commit/merge as normal
3. If status is still `IMPLEMENTING`, resume the agent session with a targeted reminder to mark the status as ACTIVE
4. Track retry count to avoid infinite loops - after max retries (default 2), mark NEEDS_ATTENTION

**Building on existing code:**
- `Scheduler._advance_phase` in `src/orchestrator/scheduler.py` - the completion logic hook
- `AgentRunner.run_phase` with `resume_session_id` - for resuming suspended agents
- `Chunks.parse_chunk_frontmatter` in `src/chunks.py` - existing frontmatter parsing
- `AgentResult` model - for tracking session state

**Key insight:** The orchestrator runs agents in worktrees, so we must read the GOAL.md from the worktree path (not the main repo), as that's where the agent made (or failed to make) its changes.

**Error handling:**
- If GOAL.md doesn't exist or can't be parsed: mark NEEDS_ATTENTION with descriptive error
- If resume fails repeatedly: mark NEEDS_ATTENTION after max retries
- Log all verification outcomes for debugging

## Subsystem Considerations

No subsystems are relevant to this chunk. This is orchestrator-internal logic that doesn't touch cross-cutting patterns.

## Sequence

### Step 1: Add retry tracking to WorkUnit model

Add a new field `completion_retries: int = 0` to the `WorkUnit` model to track how many times we've attempted to resume the agent to fix incomplete completion. This is transient state (reset when work unit moves phases) but needs to persist across dispatch cycles.

Location: `src/orchestrator/models.py`

### Step 2: Add database schema migration for completion_retries

Add schema migration v3 to add `completion_retries` column to work_units table. Update `CURRENT_VERSION` constant.

Location: `src/orchestrator/state.py`

### Step 3: Create chunk status verification helper

Add a helper function `verify_chunk_active_status` that:
- Takes a worktree path and chunk name
- Reads `docs/chunks/{chunk}/GOAL.md` from the worktree
- Parses YAML frontmatter and extracts the `status` field
- Returns a result indicating: ACTIVE (proceed), IMPLEMENTING (needs retry), or ERROR (with message)

This helper uses yaml parsing directly rather than the `Chunks` class to work with the worktree path rather than the main project.

Location: `src/orchestrator/scheduler.py` (or a new `src/orchestrator/verification.py` if the scheduler is getting large)

### Step 4: Add resume prompt for incomplete completion

Add a method `AgentRunner.resume_for_active_status` that:
- Takes chunk, worktree_path, session_id, and log_callback
- Resumes the session with a targeted prompt: "The /chunk-complete command finished but the chunk's GOAL.md status was not updated to ACTIVE. Please mark the status as ACTIVE and remove the frontmatter comment block."
- Returns the same `AgentResult` structure

Location: `src/orchestrator/agent.py`

### Step 5: Modify _advance_phase to verify ACTIVE status

Update `Scheduler._advance_phase` to add verification after COMPLETE phase:

```python
if next_phase is None:
    # Work unit complete - verify ACTIVE status before commit/merge
    verification = verify_chunk_active_status(work_unit.worktree, work_unit.chunk)

    if verification.status == "IMPLEMENTING":
        # Agent didn't finish - check retry count
        if work_unit.completion_retries >= self.config.max_completion_retries:
            await self._mark_needs_attention(
                work_unit,
                f"Chunk status still IMPLEMENTING after {work_unit.completion_retries} retries"
            )
            return

        # Resume the agent to finish
        work_unit.completion_retries += 1
        self.store.update_work_unit(work_unit)

        result = await self.agent_runner.resume_for_active_status(
            chunk=work_unit.chunk,
            worktree_path=Path(work_unit.worktree),
            session_id=work_unit.session_id,
            log_callback=create_log_callback(...)
        )

        # Re-handle the result (will call _advance_phase again if completed)
        await self._handle_agent_result(work_unit, result)
        return

    elif verification.status == "ERROR":
        await self._mark_needs_attention(work_unit, verification.error)
        return

    # Status is ACTIVE - proceed with commit/merge
    # ... existing logic ...
```

Location: `src/orchestrator/scheduler.py`

### Step 6: Add max_completion_retries to OrchestratorConfig

Add `max_completion_retries: int = 2` to the `OrchestratorConfig` model.

Location: `src/orchestrator/models.py`

### Step 7: Write tests for status verification

Write tests that verify:
1. Completion proceeds when status is ACTIVE
2. Agent is resumed when status is IMPLEMENTING
3. NEEDS_ATTENTION is set after max retries exceeded
4. NEEDS_ATTENTION is set when GOAL.md is missing or unparseable

These tests use mocked worktrees with controlled GOAL.md content.

Location: `tests/test_orchestrator_scheduler.py` (new test class `TestActiveStatusVerification`)

### Step 8: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter to list the files touched:
- `src/orchestrator/models.py`
- `src/orchestrator/state.py`
- `src/orchestrator/scheduler.py`
- `src/orchestrator/agent.py`
- `tests/test_orchestrator_scheduler.py`

## Dependencies

- **orch_scheduling** (ACTIVE): Provides the `Scheduler`, `AgentRunner`, worktree management, and phase progression logic that this chunk modifies
- **PyYAML**: Already a dependency (used in `src/chunks.py`)

## Risks and Open Questions

1. **Session ID availability**: The `session_id` from the COMPLETE phase run is needed to resume the agent. If the agent crashed or the session wasn't captured, resume may fail. The implementation handles this by marking NEEDS_ATTENTION if resume isn't possible.

2. **Recursive _handle_agent_result**: After resuming, we call `_handle_agent_result` again, which may call `_advance_phase` again. This is intentional - if the resumed agent succeeds and marks ACTIVE, we want to proceed to commit/merge. But we need to ensure the retry counter prevents infinite recursion.

3. **GOAL.md path in worktree**: The chunk's GOAL.md is at `docs/chunks/{chunk}/GOAL.md` relative to the worktree root. The worktree should contain this path since it's a full clone of the branch. Need to verify this is always true.

4. **Comment block detection**: The success criteria mention checking that the "frontmatter comment block" is removed. However, this is secondary to the status check - if status is ACTIVE but the comment block remains, that's cosmetic. We verify status only, which is the meaningful check.

## Deviations

<!-- To be populated during implementation -->