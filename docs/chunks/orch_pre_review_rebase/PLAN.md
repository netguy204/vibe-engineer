# Implementation Plan

## Approach

This chunk adds a REBASE phase to the orchestrator between IMPLEMENT and REVIEW. The REBASE phase is agent-driven—when a work unit finishes IMPLEMENT, it transitions to REBASE, where an agent merges trunk into the worktree branch and resolves any conflicts before REVIEW sees the code.

**Key design decisions:**

1. **Agent-driven merge**: The entire REBASE phase is executed by an agent, not mechanically. The agent needs chunk context to:
   - Commit any uncommitted work left by IMPLEMENT (staging, consolidation)
   - Merge main into the worktree branch
   - Resolve conflicts in light of the chunk's GOAL.md
   - Run the test suite to verify integration

2. **Phase progression update**: `IMPLEMENT → REBASE → REVIEW` replaces `IMPLEMENT → REVIEW`. All existing phase routing code is localized in `scheduler.py:_advance_phase`.

3. **NEEDS_ATTENTION on failure**: If the agent cannot resolve conflicts or tests fail, the work unit is marked NEEDS_ATTENTION with a descriptive reason including which files conflicted.

4. **Template-based prompts**: A new `chunk-rebase.md` skill file provides the agent's instructions, following the pattern of existing phase skills.

**Building on existing code:**
- The scheduler's phase progression map (lines 919-925) defines phase transitions
- `PHASE_SKILL_FILES` in `agent.py` maps phases to skill files
- The `WorkUnitPhase` enum in `models.py` defines valid phases
- State migrations in `state.py` handle schema evolution

**Testing strategy:**
Following TESTING_PHILOSOPHY.md, we'll write tests first for:
- Phase progression: IMPLEMENT → REBASE → REVIEW on success
- NEEDS_ATTENTION: Agent reports merge conflict or test failure
- Uncommitted work: Agent stages and commits before merge
- Clean merge: No conflicts, tests pass, advances to REVIEW

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a new phase in the orchestrator subsystem. The subsystem defines the pattern for work unit lifecycle, phase transitions, and agent dispatch. This chunk extends the phase enum and progression map following the established pattern.

## Sequence

### Step 1: Add REBASE to WorkUnitPhase enum

Add `REBASE = "REBASE"` to the `WorkUnitPhase` enum in `src/orchestrator/models.py`. Place it between `IMPLEMENT` and `REVIEW` for semantic clarity.

Location: `src/orchestrator/models.py#WorkUnitPhase`

Backreference comment:
```python
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase between IMPLEMENT and REVIEW
```

### Step 2: Create chunk-rebase.md skill template

Create the Jinja2 template at `src/templates/commands/chunk-rebase.md.jinja2` with instructions for the REBASE agent:

1. Commit any uncommitted changes (stage all, commit with descriptive message)
2. Merge the current trunk (main) into the worktree branch
3. If conflicts:
   - Read the chunk's GOAL.md to understand intent
   - Resolve conflicts in favor of chunk's implementation where it serves the goal
   - Accept trunk changes for unrelated code
4. Run the test suite (`uv run pytest tests/`)
5. Report success or failure (with conflicting files if merge failed)

Template should include:
- Frontmatter: `description: Merge trunk into worktree and resolve conflicts`
- CWD instructions (from existing templates)
- Clear failure criteria: unresolvable conflict, test failure

Location: `src/templates/commands/chunk-rebase.md.jinja2`

### Step 3: Regenerate command files via ve init

Run `uv run ve init` to render the template to `.claude/commands/chunk-rebase.md`.

Verify the rendered file contains the expected content.

### Step 4: Add REBASE to PHASE_SKILL_FILES mapping

Update the `PHASE_SKILL_FILES` dict in `src/orchestrator/agent.py` to map `WorkUnitPhase.REBASE` to `"chunk-rebase.md"`.

Location: `src/orchestrator/agent.py#PHASE_SKILL_FILES`

Backreference comment:
```python
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE skill for pre-review trunk integration
```

### Step 5: Update phase progression map in scheduler

Update the `next_phase_map` dict in `scheduler.py:_advance_phase` (lines 919-925):
- Change `IMPLEMENT` to point to `REBASE` (was `REVIEW`)
- Add `REBASE` pointing to `REVIEW`

Before:
```python
next_phase_map = {
    WorkUnitPhase.GOAL: WorkUnitPhase.PLAN,
    WorkUnitPhase.PLAN: WorkUnitPhase.IMPLEMENT,
    WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REVIEW,
    WorkUnitPhase.REVIEW: WorkUnitPhase.COMPLETE,
    WorkUnitPhase.COMPLETE: None,
}
```

After:
```python
next_phase_map = {
    WorkUnitPhase.GOAL: WorkUnitPhase.PLAN,
    WorkUnitPhase.PLAN: WorkUnitPhase.IMPLEMENT,
    WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REBASE,
    WorkUnitPhase.REBASE: WorkUnitPhase.REVIEW,
    WorkUnitPhase.REVIEW: WorkUnitPhase.COMPLETE,
    WorkUnitPhase.COMPLETE: None,
}
```

Location: `src/orchestrator/scheduler.py#_advance_phase`

Backreference comment:
```python
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase inserted between IMPLEMENT and REVIEW
```

### Step 6: Add REBASE phase handling in scheduler

The REBASE phase needs special handling because the agent may report:
- Success: merge clean, tests pass → advance to REVIEW
- Failure: unresolvable conflict or test failure → NEEDS_ATTENTION

Add a `_handle_rebase_result` method (similar to `_handle_review_result`) that:
1. Parses the agent's output for success/failure indicators
2. On success: calls `_advance_phase` to move to REVIEW
3. On failure: calls `_mark_needs_attention` with descriptive reason

In `_handle_agent_result`, add a check for `phase == WorkUnitPhase.REBASE` that routes to `_handle_rebase_result` (following the pattern of REVIEW phase handling).

Location: `src/orchestrator/scheduler.py`

Backreference comment:
```python
# Chunk: docs/chunks/orch_pre_review_rebase - Special handling for REBASE phase outcomes
```

### Step 7: Add state migration for REBASE phase value

Add `_migrate_v13()` in `state.py` that:
1. Documents that REBASE is now a valid WorkUnitPhase value
2. No schema change needed—phase is stored as TEXT and REBASE is a valid string value

Update `CURRENT_VERSION` to 13 and add v13 to the migrations dict.

Note: SQLite stores phases as TEXT strings. Adding a new enum value doesn't require ALTER TABLE—existing rows have valid phase values, and new rows can use REBASE.

Location: `src/orchestrator/state.py`

### Step 8: Write tests for REBASE phase

Create tests in `tests/test_orchestrator_scheduler.py`:

1. **test_advance_implement_to_rebase**: Verify IMPLEMENT → REBASE on success
2. **test_advance_rebase_to_review**: Verify REBASE → REVIEW on success
3. **test_rebase_clean_merge**: Mock agent returns success, phase advances
4. **test_rebase_conflict_needs_attention**: Mock agent returns error with "conflict", work unit marked NEEDS_ATTENTION with reason containing "conflict"
5. **test_rebase_test_failure_needs_attention**: Mock agent returns error with "test", work unit marked NEEDS_ATTENTION
6. **test_rebase_uncommitted_work**: Verify agent is invoked even when worktree has uncommitted changes (agent handles staging)

Follow existing test patterns: use fixtures for state_store, mock_worktree_manager, mock_agent_runner.

Location: `tests/test_orchestrator_scheduler.py`

### Step 9: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter `code_paths` field with the files touched:
- `src/orchestrator/models.py`
- `src/orchestrator/agent.py`
- `src/orchestrator/scheduler.py`
- `src/orchestrator/state.py`
- `src/templates/commands/chunk-rebase.md.jinja2`
- `.claude/commands/chunk-rebase.md`
- `tests/test_orchestrator_scheduler.py`

### Step 10: Run tests and verify

Run `uv run pytest tests/` to ensure:
- All existing scheduler tests pass (no regressions)
- New REBASE phase tests pass
- Phase progression works end-to-end

### Step 11: Manual verification with `ve orch status`

Verify that `ve orch status` correctly displays work units in REBASE phase:
- The status display code uses `WorkUnitPhase` enum values for display
- No explicit update needed if display iterates over enum values
- Verify the dashboard (if applicable) shows REBASE in the phase column

## Risks and Open Questions

1. **Agent output parsing**: The REBASE agent needs to output success/failure in a parseable format. Consider using a structured YAML block (like REVIEW does) or relying on `result.error` being set on failure.

2. **Test suite location**: The skill template assumes `uv run pytest tests/` is the test command. This is correct for vibe-engineer but may need configuration for other projects.

3. **Merge conflict detail**: When the agent reports a conflict, we should extract which files conflicted for the NEEDS_ATTENTION reason. This may require parsing agent output or relying on the agent to format the message clearly.

4. **Existing work units in IMPLEMENT**: Per the goal, existing IMPLEMENT work units are unaffected—they'll hit REBASE on their next phase transition. No migration of existing work unit phases is needed.

5. **Worktree state after failed REBASE**: If REBASE fails (conflict, test failure), the worktree may be in a partial merge state. The NEEDS_ATTENTION handler should document this for the operator.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->