<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

We will refactor `src/ve.py` (4,523 lines) into a modular `src/cli/` package by:

1. **Creating `src/cli/__init__.py`** as the main assembly point that defines the root `cli` Click group and imports command groups from submodules
2. **Extracting each command group into its own file** - one file per major command group
3. **Creating `src/cli/utils.py`** to hold shared utilities (validation helpers, common formatting functions)
4. **Reducing `src/ve.py` to a thin entry point** that re-exports `cli` from the package

The entry point in `pyproject.toml` remains `ve = "ve:cli"`, but `ve.py` will simply:
```python
from cli import cli  # noqa: F401
```

This preserves all existing imports (`from ve import cli`) while enabling modular development.

**Key patterns:**
- Each command group file exports its group function (e.g., `chunk`, `narrative`)
- `src/cli/__init__.py` imports these groups and adds them to the root `cli` using `cli.add_command()`
- Shared code (validation, warnings, etc.) lives in `src/cli/utils.py`
- Nested subgroups (e.g., `orch work-unit`, `reviewer decision/decisions`) stay within their parent module

## Subsystem Considerations

This chunk touches multiple existing subsystems via backreference comments in `ve.py`:
- **docs/subsystems/workflow_artifacts** - Many CLI commands
- **docs/subsystems/template_system** - Template rendering in reviewer commands
- **docs/subsystems/cross_repo_operations** - Task context handling
- **docs/subsystems/cluster_analysis** - Cluster commands
- **docs/subsystems/friction_tracking** - Friction commands

**Approach**: This is a pure structural refactoring. The subsystem backreference comments at module level will be moved to the appropriate submodule files. No subsystem patterns are being changed; we're just reorganizing the code structure.

## Sequence

### Step 1: Create `src/cli/utils.py` with shared utilities

Extract shared utilities from `ve.py` to `src/cli/utils.py`:
- `validate_short_name()` - validates identifier short_name
- `validate_ticket_id()` - validates ticket identifier
- `validate_combined_chunk_name()` - validates chunk directory name length
- `warn_task_project_context()` - emits warning when creating local artifacts in task context

These are used across multiple command groups.

Location: `src/cli/utils.py`

### Step 2: Create `src/cli/__init__.py` skeleton

Create the package init file with:
- Import `click`
- Define the root `cli` Click group
- Import top-level commands (`init`, `validate`) directly
- Space for importing and adding command groups

Location: `src/cli/__init__.py`

### Step 3: Create `src/cli/init_cmd.py` for top-level commands

Extract the `init` and `validate` commands to their own module. These are direct commands on the root `cli` group.

Location: `src/cli/init_cmd.py`

### Step 4: Create `src/cli/chunk.py` - chunk command group

Extract the `chunk` group and all its subcommands (lines ~221-1418):
- `chunk create`
- `chunk list`
- `chunk complete`
- `chunk list-proposed`
- `chunk activate`
- `chunk status`
- `chunk overlap`
- `chunk suggest-prefix`
- `chunk backrefs`
- `chunk cluster`
- `chunk validate`
- `chunk cluster-rename`
- `chunk cluster-list`

Also extract helper functions used only by chunk commands:
- `_start_task_chunk()`
- `_start_task_chunks()`
- `_parse_status_filters()`
- `_format_grouped_artifact_list()`
- `_list_task_chunks()`
- `_format_proposed_chunks_by_source()`
- `_format_grouped_proposed_chunks()`
- `_list_task_proposed_chunks()`

Location: `src/cli/chunk.py`

### Step 5: Create `src/cli/narrative.py` - narrative command group

Extract the `narrative` group and subcommands (lines ~1420-1755):
- `narrative create`
- `narrative list`
- `narrative status`
- `narrative compact`
- `narrative update-refs`

Also extract helper function:
- `_start_task_narrative()`
- `_list_task_narratives_cmd()`

Location: `src/cli/narrative.py`

### Step 6: Create `src/cli/task.py` - task command group

Extract the `task` group and subcommand (lines ~1757-1793):
- `task init`

Location: `src/cli/task.py`

### Step 7: Create `src/cli/subsystem.py` - subsystem command group

Extract the `subsystem` group and subcommands (lines ~1795-2103):
- `subsystem list`
- `subsystem discover`
- `subsystem validate`
- `subsystem status`
- `subsystem overlap`

Also extract helper function:
- `_list_task_subsystems()`
- `_create_task_subsystem()`

Location: `src/cli/subsystem.py`

### Step 8: Create `src/cli/investigation.py` - investigation command group

Extract the `investigation` group and subcommands (lines ~2105-2285):
- `investigation create`
- `investigation list`
- `investigation status`

Also extract helper functions:
- `_create_task_investigation()`
- `_list_task_investigations()`

Location: `src/cli/investigation.py`

### Step 9: Create `src/cli/external.py` - external command group

Extract the `external` group and subcommand (lines ~2287-2505):
- `external resolve`

Also extract helper functions:
- `_detect_artifact_type_from_id()`
- `_resolve_external_task_directory()`
- `_resolve_external_single_repo()`
- `_display_resolve_result()`

Location: `src/cli/external.py`

### Step 10: Create `src/cli/artifact.py` - artifact command group

Extract the `artifact` group and subcommands (lines ~2507-2621):
- `artifact promote`
- `artifact copy-external`
- `artifact remove-external`

Location: `src/cli/artifact.py`

### Step 11: Create `src/cli/orch.py` - orchestrator command group

Extract the `orch` group and all subcommands including the nested `work-unit` subgroup (lines ~2623-3718):
- `orch start`
- `orch stop`
- `orch status`
- `orch url`
- `orch ps`
- `work-unit create`, `work-unit status`, `work-unit show`, `work-unit list`, `work-unit delete`
- `orch inject`
- `orch queue`
- `orch prioritize`
- `orch config`
- `orch attention`
- `orch answer`
- `orch conflicts`
- `orch resolve`
- `orch analyze`
- `orch tail`

Also extract helper functions:
- `topological_sort_chunks()`
- `read_chunk_dependencies()`
- `validate_external_dependencies()`

Location: `src/cli/orch.py`

### Step 12: Create `src/cli/friction.py` - friction command group

Extract the `friction` group and subcommands (lines ~3720-4065):
- `friction log`
- `friction list`
- `friction analyze`

Also extract helper function:
- `_log_entry_task_context()`

Location: `src/cli/friction.py`

### Step 13: Create `src/cli/migration.py` - migration command group

Extract the `migration` group and subcommands (lines ~4067-4212):
- `migration create`
- `migration status`
- `migration list`
- `migration pause`
- `migration abandon`

Location: `src/cli/migration.py`

### Step 14: Create `src/cli/reviewer.py` - reviewer command group

Extract the `reviewer` group with nested subgroups (lines ~4218-4523):
- `reviewer decision create`
- `reviewer decisions` (with --pending, --recent flags)
- `reviewer decisions review`
- `reviewer decisions list`

Location: `src/cli/reviewer.py`

### Step 15: Update `src/cli/__init__.py` to assemble all groups

Update the init file to:
- Import `init`, `validate` from `init_cmd` and add them
- Import each command group module
- Add each group to the root `cli` using `cli.add_command()`

This is where the final assembly happens.

### Step 16: Reduce `src/ve.py` to thin entry point

Replace `src/ve.py` content with a simple re-export:
```python
"""Vibe Engineer CLI entry point.

The CLI implementation lives in src/cli/. This module re-exports
the main cli group to maintain backward compatibility with:
- pyproject.toml entry point: ve = "ve:cli"
- Test imports: from ve import cli
"""
from cli import cli  # noqa: F401

if __name__ == "__main__":
    cli()
```

This preserves the `from ve import cli` import pattern used by all tests.

### Step 17: Run tests and verify

Run the full test suite:
```bash
uv run pytest tests/
```

Verify:
- All 49 test files that import `from ve import cli` still work
- `uv run ve --help` shows the same command structure
- All commands function identically

### Step 18: Verify CLI help output

Run `uv run ve --help` and compare to expected output. Ensure:
- All command groups appear (chunk, narrative, task, subsystem, investigation, external, artifact, orch, friction, migration, reviewer)
- Top-level commands appear (init, validate)
- No duplicate or missing commands

## Risks and Open Questions

1. **Import order**: Click commands must be defined before being added to groups. The import order in `__init__.py` matters.

2. **Circular imports**: Care must be taken to avoid circular imports between `utils.py` and command modules. The utility module should have no dependencies on command modules.

3. **Test compatibility**: All 49 test files use `from ve import cli`. The thin `ve.py` re-export approach should maintain this, but needs verification.

4. **Subsystem backreferences**: The module-level subsystem comments in `ve.py` reference multiple subsystems. These need to be moved to the appropriate command submodules so they remain accurate.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
