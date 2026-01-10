<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Use Click's `name` parameter to rename the command from `start` to `create`, then add an alias
by registering the same function under the old name using `add_command()`. This is the standard
Click pattern for backward-compatible command renames.

The change involves:
1. Renaming the command function and decorator
2. Adding an alias for backward compatibility
3. Updating all documentation references
4. Updating the subsystem to resolve the known deviation

This follows the existing pattern in the codebase where other workflow types use `create`
(e.g., `ve narrative create`, `ve investigation create`).

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the CLI command
  naming convention, resolving the known deviation "CLI Command Inconsistency: `chunk start`
  vs `create`". Since the subsystem is REFACTORING, this work directly addresses the deviation.

## Sequence

### Step 1: Rename command in src/ve.py

Rename the `start` command to `create`:
- Change `@chunk.command()` to `@chunk.command("create")`
- Rename the function from `start` to `create`
- Update the docstring from "Start a new chunk." to "Create a new chunk."
- Add the `start` alias using `chunk.add_command(create, name="start")`
- Update the chunk backreference comment to reference this chunk

Location: `src/ve.py`

### Step 2: Update the slash command template

Update `src/templates/commands/chunk-create.md.jinja2` to reference `ve chunk create`
instead of `ve chunk start`.

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 3: Update the installed slash command

Update `.claude/commands/chunk-create.md` to reference `ve chunk create` instead of
`ve chunk start`. This is the installed version of the template.

Location: `.claude/commands/chunk-create.md`

### Step 4: Update README.md

Update all CLI examples in README.md from `ve chunk start` to `ve chunk create`.

Location: `README.md`

### Step 5: Update workflow_artifacts subsystem documentation

In `docs/subsystems/workflow_artifacts/OVERVIEW.md`:
- Update the code reference `src/ve.py#start` to `src/ve.py#create`
- Remove the "CLI Command Inconsistency" known deviation section
- Update the Consolidation Chunks section to mark this item as resolved

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

### Step 6: Run tests and verify

Run the test suite to ensure no regressions. Tests may need updates to use the new
command name, but should also verify the alias works.

```bash
uv run pytest tests/test_chunk_start.py -v
```

Also manually verify:
- `ve chunk create foo` works
- `ve chunk start foo` still works (alias)
- `ve chunk --help` shows `create` as primary command

## Dependencies

None. This is a self-contained rename with no external dependencies.

## Risks and Open Questions

- **Historical chunk docs**: Many historical chunks reference `ve chunk start` in their
  GOAL.md or PLAN.md. These are intentionally NOT being updated - they are historical
  records of what was done at the time. Only update live documentation (README,
  templates, slash commands).

## Deviations

<!-- Populate during implementation -->