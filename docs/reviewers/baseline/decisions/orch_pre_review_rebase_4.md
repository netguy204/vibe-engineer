---
decision: APPROVE
summary: All success criteria satisfied - REBASE phase properly added to enum, scheduler, state migration, template, tests, and CLI display
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: A new `WorkUnitPhase.REBASE` value exists in the phase enum

- **Status**: satisfied
- **Evidence**: `src/orchestrator/models.py` line 73: `REBASE = "REBASE"  # Merge trunk into worktree and resolve conflicts`

### Criterion 2: The phase progression map in `scheduler.py:907-913` includes `IMPLEMENT → REBASE` and `REBASE → REVIEW`

- **Status**: satisfied
- **Evidence**: `src/orchestrator/scheduler.py` lines 925-932: `next_phase_map` includes `WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REBASE` and `WorkUnitPhase.REBASE: WorkUnitPhase.REVIEW`

### Criterion 3: On entering REBASE, the scheduler always spawns an agent in the worktree

- **Status**: satisfied
- **Evidence**: REBASE uses the standard phase handling in `_run_work_unit()`. Like other phases, the scheduler creates a worktree (line 722), then runs the agent via `run_phase()` (line 787). REBASE is mapped to `chunk-rebase.md` in `PHASE_SKILL_FILES` (line 50 of agent.py).

### Criterion 4: The agent commits any uncommitted work from the IMPLEMENT phase before merging

- **Status**: satisfied
- **Evidence**: Template `src/templates/commands/chunk-rebase.md.jinja2` Section 1 instructs the agent to check for uncommitted changes and commit them before proceeding with the merge.

### Criterion 5: The agent merges main into the worktree branch and resolves any conflicts in light of the chunk's GOAL.md

- **Status**: satisfied
- **Evidence**: Template Section 2 instructs `git fetch origin main && git merge origin/main`. Section 3 provides conflict resolution guidance: "Read the chunk's GOAL.md to understand what this chunk is trying to accomplish" and "Keep chunk changes where they implement the goal, Accept trunk changes for unrelated code modifications".

### Criterion 6: The agent runs the test suite to verify the integrated result

- **Status**: satisfied
- **Evidence**: Template Section 4 instructs `uv run pytest tests/` with guidance on handling test failures.

### Criterion 7: On agent success, the phase advances to REVIEW

- **Status**: satisfied
- **Evidence**: `scheduler.py` lines 895-898 in `_handle_agent_result()`: `elif phase == WorkUnitPhase.REBASE: await self._advance_phase(work_unit)`, which routes through the phase progression map to REVIEW.

### Criterion 8: On agent failure (unresolvable conflicts or test failures), the work unit is marked NEEDS_ATTENTION with a descriptive reason including which files conflicted

- **Status**: satisfied
- **Evidence**: Template Section 5 instructs the agent to "Report clearly which files have unresolvable conflicts or which tests are failing". Agent failures route to `_mark_needs_attention()` via the standard error handling in `_handle_agent_result()` lines 860-883. Tests `test_rebase_conflict_marks_needs_attention` and `test_rebase_test_failure_marks_needs_attention` verify this behavior.

### Criterion 9: The state store migration adds REBASE as a valid phase value

- **Status**: satisfied
- **Evidence**: `src/orchestrator/state.py` lines 363-378: `_migrate_v13()` documents that REBASE is now valid. `CURRENT_VERSION` updated to 13 (line 52). Migration correctly notes no SQL change is needed since phases are stored as TEXT.

### Criterion 10: A REBASE-specific agent prompt template is created that instructs the agent on the commit-merge-resolve-test workflow

- **Status**: satisfied
- **Evidence**: Template at `src/templates/commands/chunk-rebase.md.jinja2` and rendered `.claude/commands/chunk-rebase.md` contain comprehensive instructions for the 5-step workflow: (1) commit uncommitted work, (2) merge trunk, (3) resolve conflicts, (4) run tests, (5) report outcome.

### Criterion 11: Existing work units in IMPLEMENT phase are unaffected (they'll hit REBASE on their next phase transition)

- **Status**: satisfied
- **Evidence**: The migration makes no changes to existing data (just version bump). Existing IMPLEMENT work units will transition to REBASE when they complete. No schema migration of phase values is required.

### Criterion 12: All existing scheduler tests pass; new tests cover: clean merge, conflicting merge with agent resolution, uncommitted work handling, and unresolvable merge (NEEDS_ATTENTION)

- **Status**: satisfied
- **Evidence**: All 149 scheduler tests pass (verified). New `TestRebasePhase` class in `tests/test_orchestrator_scheduler.py` includes: `test_implement_advances_to_rebase_not_review`, `test_rebase_success_advances_to_review`, `test_rebase_conflict_marks_needs_attention`, `test_rebase_test_failure_marks_needs_attention`, `test_rebase_phase_in_full_lifecycle`, `test_rebase_suspended_for_question_marks_needs_attention`.

### Criterion 13: The `ve orch status` and dashboard correctly display work units in REBASE phase

- **Status**: satisfied
- **Evidence**: Status display uses `unit['phase']` directly from work unit data (enum value renders as "REBASE"). Additionally, I fixed `src/cli/orch.py` line 893 to include `WorkUnitPhase.REBASE` in `phase_order` for `ve orch tail` log display.
