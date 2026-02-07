---
decision: FEEDBACK
summary: Core REBASE phase implementation is complete and tested, but `ve orch tail` lacks REBASE in phase_order list preventing log detection for this phase
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: A new `WorkUnitPhase.REBASE` value exists in the phase enum

- **Status**: satisfied
- **Evidence**: `src/orchestrator/models.py:73` defines `REBASE = "REBASE"` with comment at line 63 linking to this chunk

### Criterion 2: The phase progression map in `scheduler.py:907-913` includes `IMPLEMENT → REBASE` and `REBASE → REVIEW`

- **Status**: satisfied
- **Evidence**: `src/orchestrator/scheduler.py:925-932` shows the correct progression map:
  - `WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REBASE`
  - `WorkUnitPhase.REBASE: WorkUnitPhase.REVIEW`

### Criterion 3: On entering REBASE, the scheduler always spawns an agent in the worktree

- **Status**: satisfied
- **Evidence**: Standard scheduler flow applies - `_run_work_unit()` spawns agent for all phases. REBASE is in `PHASE_SKILL_FILES` mapping at `agent.py:50` pointing to `"chunk-rebase.md"`

### Criterion 4: The agent commits any uncommitted work from the IMPLEMENT phase before merging

- **Status**: satisfied
- **Evidence**: The skill template at `.claude/commands/chunk-rebase.md` instructs the agent to first check `git status` and commit any uncommitted changes before merging

### Criterion 5: The agent merges main into the worktree branch and resolves any conflicts in light of the chunk's GOAL.md

- **Status**: satisfied
- **Evidence**: The skill template instructions include fetching origin/main, merging, and resolving conflicts with guidance to "Read the chunk's GOAL.md to understand what this chunk is trying to accomplish"

### Criterion 6: The agent runs the test suite to verify the integrated result

- **Status**: satisfied
- **Evidence**: The skill template includes step 4 "Run Tests" with `uv run pytest tests/` command

### Criterion 7: On agent success, the phase advances to REVIEW

- **Status**: satisfied
- **Evidence**: `scheduler.py:895-898` handles REBASE phase completion by calling `_advance_phase()`, which progresses to REVIEW per the phase map. Test `test_rebase_success_advances_to_review` confirms this.

### Criterion 8: On agent failure (unresolvable conflicts or test failures), the work unit is marked NEEDS_ATTENTION with a descriptive reason including which files conflicted

- **Status**: satisfied
- **Evidence**: Standard error handling in `_handle_agent_result()` routes failures through `_mark_needs_attention()`. Tests `test_rebase_conflict_marks_needs_attention` and `test_rebase_test_failure_marks_needs_attention` verify this behavior. The error message from the agent is stored in `attention_reason`.

### Criterion 9: The state store migration adds REBASE as a valid phase value

- **Status**: satisfied
- **Evidence**: `state.py:364-378` defines `_migrate_v13()` which documents REBASE as a valid phase value. The migration correctly notes that no schema change is needed since phase is stored as TEXT.

### Criterion 10: A REBASE-specific agent prompt template is created that instructs the agent on the commit-merge-resolve-test workflow

- **Status**: satisfied
- **Evidence**: Template exists at `src/templates/commands/chunk-rebase.md.jinja2` and renders to `.claude/commands/chunk-rebase.md`. The template includes all four steps: commit uncommitted work, merge trunk, handle conflicts, run tests.

### Criterion 11: Existing work units in IMPLEMENT phase are unaffected (they'll hit REBASE on their next phase transition)

- **Status**: satisfied
- **Evidence**: Migration v13 doesn't modify existing data - only documents the new valid phase value. Existing IMPLEMENT work units will naturally advance to REBASE on their next phase transition.

### Criterion 12: All existing scheduler tests pass; new tests cover: clean merge, conflicting merge with agent resolution, uncommitted work handling, and unresolvable merge (NEEDS_ATTENTION)

- **Status**: satisfied
- **Evidence**: All 149 scheduler tests pass. 8 new REBASE-specific tests exist in `TestRebasePhase` class covering:
  - `test_implement_advances_to_rebase_not_review`
  - `test_rebase_success_advances_to_review`
  - `test_rebase_conflict_marks_needs_attention`
  - `test_rebase_test_failure_marks_needs_attention`
  - `test_rebase_phase_in_full_lifecycle`
  - `test_rebase_suspended_for_question_marks_needs_attention`

### Criterion 13: The `ve orch status` and dashboard correctly display work units in REBASE phase

- **Status**: gap
- **Evidence**: The `ve orch status` command displays phases correctly by reading `unit['phase']` directly from the work unit (lines 176/178 in orch.py), so REBASE will display correctly. However, the `phase_order` list in `ve orch tail` (lines 890-896) does NOT include REBASE, meaning `ve orch tail -f` won't detect when work units transition to REBASE phase. The list only includes: GOAL, PLAN, IMPLEMENT, REVIEW, COMPLETE.

## Feedback Items

### Issue 1: src/cli/orch.py:890-896

**Concern:** The `phase_order` list used by `ve orch tail` is missing the REBASE phase. This means `ve orch tail -f` will not detect phase transitions to REBASE and won't find/display rebase.txt log files.

**Suggestion:** Add `WorkUnitPhase.REBASE` to the `phase_order` list between `IMPLEMENT` and `REVIEW`:
```python
phase_order = [
    WorkUnitPhase.GOAL,
    WorkUnitPhase.PLAN,
    WorkUnitPhase.IMPLEMENT,
    WorkUnitPhase.REBASE,  # Add this line
    WorkUnitPhase.REVIEW,
    WorkUnitPhase.COMPLETE,
]
```

**Severity:** functional
**Confidence:** high
