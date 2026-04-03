---
decision: FEEDBACK
summary: "Core fix to agent.py is correct but 31 tests across 6 other test files fail because their project_dir fixtures were not updated to use the new .agents/skills/ path structure"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Orchestrator PLAN phase succeeds with the new skill path structure

- **Status**: satisfied
- **Evidence**: `get_skill_path()` now returns `project_dir / ".agents" / "skills" / skill_name / "SKILL.md"` (agent.py:493). `PHASE_SKILL_FILES` updated to bare names (agent.py:47-53). The `_setup_agent_environment_symlinks` in worktree.py already creates `.agents` symlinks in worktrees, so paths resolve correctly.

### Criterion 2: All orchestrator skill path references updated to `.agents/skills/<name>/SKILL.md`

- **Status**: satisfied
- **Evidence**: Grep for `.claude.*commands` in `src/orchestrator/` returns zero matches. `get_phase_prompt()` docstring updated to reference `.agents/skills/` (agent.py:499). Backreference comment added (agent.py:482).

### Criterion 3: Worktree setup creates necessary symlinks before agent execution

- **Status**: satisfied
- **Evidence**: `_setup_agent_environment_symlinks` at worktree.py:589 creates `.agents -> task_dir/.agents` symlinks. This is called at worktree.py:584, before the worktree path is returned and before any agent runs.

### Criterion 4: Existing tests pass

- **Status**: gap
- **Evidence**: `tests/test_orchestrator_agent_skills.py` — 11/11 pass. However, 31 tests fail across 6 other files: `test_orchestrator_agent_runner.py` (4 failures), `test_orchestrator_agent_sandbox.py` (4), `test_orchestrator_agent_review.py` (6), `test_orchestrator_agent_callbacks.py` (3), `test_orchestrator_agent_stream.py` (5), `test_orchestrator_reentry.py` (5), `test_orchestrator_feedback_injection.py` (4). All fail with `FileNotFoundError: .agents/skills/<name>/SKILL.md` because their `project_dir` fixtures still create files at `.claude/commands/<name>.md`.

### Criterion 5: New test verifying orchestrator finds skills after migration

- **Status**: satisfied
- **Evidence**: `test_get_skill_path` (test_orchestrator_agent_skills.py:324) asserts the path is `project_dir / ".agents" / "skills" / skill_name / "SKILL.md"`. `test_skill_name_format` (line 144) asserts skill names have no `.md` extension and no `/`. The fixture creates both canonical `.agents/skills/` files and `.claude/commands/` symlinks.

## Feedback Items

### Issue 1: 31 tests fail due to outdated project_dir fixtures

- **ID**: issue-fixture-sprawl
- **Location**: `tests/test_orchestrator_agent_runner.py`, `tests/test_orchestrator_agent_sandbox.py`, `tests/test_orchestrator_agent_review.py`, `tests/test_orchestrator_agent_callbacks.py`, `tests/test_orchestrator_agent_stream.py`, `tests/test_orchestrator_reentry.py`, `tests/test_orchestrator_feedback_injection.py`
- **Severity**: functional
- **Confidence**: high
- **Concern**: Each of these test files has its own `project_dir` fixture that creates skill files at `.claude/commands/<name>.md`. After the change to `get_skill_path()`, these tests fail with `FileNotFoundError` because skills are now looked up at `.agents/skills/<name>/SKILL.md`. The PLAN explicitly identified this in Step 5 ("Other test files that reference `.claude/commands/` in their fixtures will also need their `project_dir` fixtures updated") but the implementation only updated `test_orchestrator_agent_skills.py`.
- **Suggestion**: Update the `project_dir` fixture in each of the 7 failing test files to create the canonical `.agents/skills/<name>/SKILL.md` structure plus `.claude/commands/` symlinks, matching the pattern in `test_orchestrator_agent_skills.py`. Given the duplication across 8 files, strongly consider extracting a shared fixture into `tests/conftest.py` (or an orchestrator-specific conftest) to avoid maintaining the same setup in 8 places. The pattern is already proven in `test_orchestrator_agent_skills.py:104-132`.
