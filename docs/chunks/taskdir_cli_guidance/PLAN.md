<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements two complementary safeguards to prevent agents from accidentally
creating project-level artifacts when operating in a task context:

1. **CLAUDE.md guidance** - Add explicit instructions in the task CLAUDE.md template
   that artifact creation commands should run from the task directory.

2. **CLI warning** - Add detection logic to artifact creation commands that emits
   a non-blocking warning when running from inside a project that is part of a task.

The implementation builds on existing infrastructure:
- `find_task_directory()` in `task_utils.py` already walks up to find `.ve-task.yaml`
- `load_task_config()` provides the list of participating projects
- The task CLAUDE.md template (`src/templates/task/CLAUDE.md.jinja2`) is where guidance lives
- The template_system subsystem governs template rendering

Tests will follow TDD: write failing tests first, then implement the detection logic.

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk IMPLEMENTS
  additional task context detection functionality within the cross-repo operations
  pattern. The existing `find_task_directory()` provides the foundation for the
  warning mechanism.

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template
  system to add guidance content to the task CLAUDE.md template.

## Sequence

### Step 1: Add Task CLAUDE.md Template Guidance

Add a new section to `src/templates/task/CLAUDE.md.jinja2` that explicitly instructs
agents to run artifact creation commands from the task directory, not from individual
project directories.

The section should:
- Explain what happens when commands are run from task vs project context
- List the affected commands: `ve chunk create`, `ve narrative create`,
  `ve investigation create`, `ve subsystem discover`
- Explain the consequence: task-level creates cross-repo artifacts, project-level
  creates local artifacts

Location: `src/templates/task/CLAUDE.md.jinja2`

### Step 2: Write Failing Tests for CLI Context Warning

Create tests in `tests/test_task_cli_context.py` (new file) that verify:
1. Warning appears when `ve chunk create` is run from inside a project that is
   part of a task
2. Warning does NOT appear when running from the task root
3. Warning does NOT appear for standalone projects (no task context above)
4. Same pattern for other artifact commands: `narrative create`, `investigation create`,
   `subsystem discover`
5. Warning is non-blocking (command still executes)

Use the existing `setup_task_directory()` helper from `conftest.py`.

Location: `tests/test_task_cli_context.py`

### Step 3: Implement `check_task_project_context()` Detection Function

Add a function to `task_utils.py` that:
1. Walks up from cwd looking for `.ve-task.yaml` using `find_task_directory()`
2. If found, loads the task config
3. Checks if cwd is within one of the task's project directories
4. Returns context info: `(task_dir, project_ref)` or `None` if not in a project

This function provides the detection logic that CLI commands will use.

Location: `src/task_utils.py#check_task_project_context`

### Step 4: Create Shared Warning Helper

Add a helper function that emits the standardized warning message:
```
Warning: You are running this command from within project {project} which is
part of task {task_dir}. To create a cross-repo artifact, run from the task
directory instead.
```

The helper should:
- Accept the context tuple from `check_task_project_context()`
- Emit warning to stderr via `click.echo(..., err=True)`
- Return immediately if context is None

Location: `src/ve.py` (near top, with other helpers) or potentially `task_utils.py`

### Step 5: Add Warning to `ve chunk create`

Modify the `create()` command in `ve.py` to:
1. Before entering the single-repo mode branch, call `check_task_project_context()`
2. If a task project context is detected, emit the warning
3. Continue with normal execution (non-blocking)

The check should happen when `is_task_directory(project_dir)` returns False,
because that's when we're about to create a project-level chunk.

Location: `src/ve.py#create`

### Step 6: Add Warning to Other Artifact Commands

Apply the same pattern to:
- `ve narrative create` (in `narrative_create()` command)
- `ve investigation create` (in `investigation_create()` command)
- `ve subsystem discover` (in `subsystem_discover()` command)

Each command should call `check_task_project_context()` and emit the warning
when creating local artifacts while inside a task's project.

Location: `src/ve.py` (multiple command functions)

### Step 7: Verify All Tests Pass

Run the full test suite to ensure:
- New tests pass (warning behavior)
- Existing tests still pass (no regressions)
- The warning is correctly formatted

```bash
uv run pytest tests/
```

## Dependencies

No external dependencies. All required infrastructure exists:
- `find_task_directory()` and `load_task_config()` in `task_utils.py`
- `resolve_repo_directory()` for checking project membership
- Jinja2 template system for CLAUDE.md rendering

## Risks and Open Questions

1. **Warning message wording**: The exact phrasing should be helpful but not
   overly verbose. The proposed text is actionable and concise.

2. **Performance of upward directory walk**: The `find_task_directory()` function
   walks up the filesystem tree. For deeply nested directories, this could be
   slow, but in practice task directories are near the project root.

3. **Edge case: symlinked project directories**: If a project is symlinked into
   the task directory, the path comparison logic might fail. The implementation
   should use `Path.resolve()` to handle symlinks properly.

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