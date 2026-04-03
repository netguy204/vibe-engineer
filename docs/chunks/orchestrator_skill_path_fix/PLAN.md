

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The orchestrator's `AgentRunner` hardcodes skill paths using the pre-migration
format: `.claude/commands/<name>.md`. After the `agentskills_migration` chunk,
skills live at `.agents/skills/<name>/SKILL.md` with per-file symlinks in
`.claude/commands/` for backwards compatibility.

The root cause has two parts:

1. **`PHASE_SKILL_FILES` uses old filenames** — The mapping uses `"chunk-plan.md"`
   instead of the new directory-based `"chunk-plan/SKILL.md"` structure.

2. **`get_skill_path()` constructs the old path** — It builds
   `project_dir / ".claude" / "commands" / skill_file`, which should work via
   symlinks — but only if `.claude/commands/chunk-plan.md` exists as a symlink
   pointing to `../../.agents/skills/chunk-plan/SKILL.md`.

The fix is straightforward: update `PHASE_SKILL_FILES` and `get_skill_path()`
to use the canonical `.agents/skills/<name>/SKILL.md` path directly, rather
than relying on the backwards-compatibility symlinks. This is more robust and
aligns with the migration's intent.

The worktree symlink setup (`_setup_agent_environment_symlinks`) already
creates `.agents -> task_dir/.agents` symlinks, so the new paths will resolve
correctly in worktrees too.

Tests follow TDD per docs/trunk/TESTING_PHILOSOPHY.md: update existing tests
to assert the new path structure, then change the implementation.

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk fixes a bug in the orchestrator
  subsystem's agent runner. The change is scoped to path construction only.

## Sequence

### Step 1: Update tests to assert new skill paths (TDD red phase)

Location: `tests/test_orchestrator_agent_skills.py`

**a)** Update the `project_dir` fixture to create the new directory structure:
- Create `.agents/skills/<name>/SKILL.md` files instead of `.claude/commands/<name>.md`
- Keep the `.claude/commands/` directory but populate it with symlinks to the
  `.agents/skills/` files (matching what `ve init` does in production)

**b)** Update `TestPhaseSkillFiles.test_skill_file_format`:
- Change assertion: skill names no longer end in `.md` — they are bare names
  like `"chunk-plan"` used to construct `<name>/SKILL.md` paths

**c)** Update `TestAgentRunner.test_get_skill_path`:
- Assert the returned path is `project_dir / ".agents" / "skills" / name / "SKILL.md"`
  instead of `project_dir / ".claude" / "commands" / name + ".md"`

**d)** Update `TestAgentRunner.test_get_phase_prompt_loads_content` and
`test_get_phase_prompt_goal_replaces_arguments`:
- These should work once the fixture and paths are updated

Run tests — they should fail (red phase).

### Step 2: Update PHASE_SKILL_FILES mapping

Location: `src/orchestrator/agent.py`, lines 46–53

Change the values from `"chunk-plan.md"` to bare skill names `"chunk-plan"`.
These are now directory names, not filenames.

```python
PHASE_SKILL_FILES = {
    WorkUnitPhase.GOAL: "chunk-create",
    WorkUnitPhase.PLAN: "chunk-plan",
    WorkUnitPhase.IMPLEMENT: "chunk-implement",
    WorkUnitPhase.REBASE: "chunk-rebase",
    WorkUnitPhase.REVIEW: "chunk-review",
    WorkUnitPhase.COMPLETE: "chunk-complete",
}
```

### Step 3: Update get_skill_path() method

Location: `src/orchestrator/agent.py`, lines 482–492

Change the path construction from:
```python
return self.project_dir / ".claude" / "commands" / skill_file
```
to:
```python
return self.project_dir / ".agents" / "skills" / skill_name / "SKILL.md"
```

Also update the docstring for `get_phase_prompt()` (line 497) which references
`.claude/commands/`.

Add a chunk backreference comment on `get_skill_path`.

### Step 4: Run tests — verify green

Run `uv run pytest tests/test_orchestrator_agent_skills.py -v` to confirm
the updated tests pass with the new implementation.

### Step 5: Run full test suite

Run `uv run pytest tests/` to ensure no other tests broke. Other test files
that reference `.claude/commands/` in their fixtures (e.g.,
`test_orchestrator_agent_runner.py`, `test_orchestrator_agent_sandbox.py`, etc.)
will also need their `project_dir` fixtures updated to use the new structure.

### Step 6: Verify worktree symlink coverage

Confirm that `_setup_agent_environment_symlinks` in `src/orchestrator/worktree.py`
already creates the `.agents` symlink (it does — line 612). No changes needed
to the worktree manager, but verify in tests that the symlink chain resolves:
`worktree/.agents -> task_dir/.agents -> (real directory with skills)`.

## Dependencies

- `agentskills_migration` chunk (ACTIVE) — established the `.agents/skills/` structure

## Risks and Open Questions

- **Test fixture sprawl**: Multiple test files create their own `project_dir`
  fixtures with `.claude/commands/` paths. Step 5 may reveal more files needing
  updates than anticipated. If so, consider a shared conftest fixture.
- **Symlink resolution in CI**: The worktree uses symlinks to reach the task
  directory's `.agents/`. If CI environments have symlink restrictions, the
  skill path resolution could fail. This is an existing risk from the migration
  and not new to this chunk.

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