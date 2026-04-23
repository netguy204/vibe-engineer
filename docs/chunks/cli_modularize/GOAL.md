---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/cli/__init__.py
- src/cli/utils.py
- src/cli/init_cmd.py
- src/cli/chunk.py
- src/cli/narrative.py
- src/cli/task.py
- src/cli/subsystem.py
- src/cli/investigation.py
- src/cli/external.py
- src/cli/artifact.py
- src/cli/orch.py
- src/cli/friction.py
- src/cli/migration.py
- src/cli/reviewer.py
- src/cli/board.py
- src/cli/entity.py
- src/cli/wiki.py
code_references:
  - ref: src/ve.py#main
    implements: "Thin entry point delegating to cli package"
  - ref: src/cli/__init__.py#cli
    implements: "Main CLI assembly point that registers all command groups"
  - ref: src/cli/utils.py#validate_short_name
    implements: "Shared identifier validation"
  - ref: src/cli/utils.py#warn_task_project_context
    implements: "Warning for local artifact creation in task context"
  - ref: src/cli/init_cmd.py#init
    implements: "CLI init command for project initialization"
  - ref: src/cli/init_cmd.py#validate
    implements: "CLI validate command for referential integrity"
  - ref: src/cli/chunk.py#chunk
    implements: "Chunk command group with all subcommands"
  - ref: src/cli/narrative.py#narrative
    implements: "Narrative command group with all subcommands"
  - ref: src/cli/task.py#task
    implements: "Task command group for cross-repo work"
  - ref: src/cli/subsystem.py#subsystem
    implements: "Subsystem command group with all subcommands"
  - ref: src/cli/investigation.py#investigation
    implements: "Investigation command group with all subcommands"
  - ref: src/cli/external.py#external
    implements: "External artifact reference command group"
  - ref: src/cli/artifact.py#artifact
    implements: "Artifact management command group"
  - ref: src/cli/orch.py#orch
    implements: "Orchestrator daemon command group"
  - ref: src/cli/orch.py#work_unit
    implements: "Work unit management subgroup"
  - ref: src/cli/orch.py#topological_sort_chunks
    implements: "Dependency-aware chunk sorting for injection"
  - ref: src/cli/friction.py#friction
    implements: "Friction log command group"
  - ref: src/cli/migration.py#migration
    implements: "Migration command group"
  - ref: src/cli/reviewer.py#reviewer
    implements: "Reviewer agent command group"
  - ref: src/cli/reviewer.py#decision
    implements: "Decision file subgroup under reviewer"
  - ref: src/cli/reviewer.py#decisions
    implements: "Decisions management subgroup with list/review commands"
  - ref: src/cli/board.py#board
    implements: "Board messaging command group"
  - ref: src/cli/entity.py#entity
    implements: "Entity management command group"
  - ref: src/cli/wiki.py#wiki
    implements: "Wiki command group with reindex and related subcommands"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- reviewer_decisions_nudge
created_after:
- reviewer_decision_template
- reviewer_remove_migration
---

# Chunk Goal

## Minor Goal

Refactor the monolithic `src/ve.py` CLI (4,500+ lines) into a modular `src/cli/` package structure. Each command group (chunk, narrative, orch, subsystem, etc.) becomes its own submodule, enabling agents to explore and modify specific CLI functionality without encountering token limits or losing context through grep-based navigation.

This advances the project's goal of agent-friendly development by reducing cognitive load when working on CLI commands.

## Success Criteria

- `src/cli/__init__.py` exists and exports the main `cli` Click group
- Each major command group lives in its own file:
  - `src/cli/chunk.py` - chunk command group
  - `src/cli/narrative.py` - narrative command group
  - `src/cli/orch.py` - orchestrator command group
  - `src/cli/subsystem.py` - subsystem command group
  - `src/cli/investigation.py` - investigation command group
  - `src/cli/artifact.py` - artifact command group
  - `src/cli/external.py` - external command group
  - `src/cli/friction.py` - friction command group
  - `src/cli/migration.py` - migration command group
  - `src/cli/reviewer.py` - reviewer command group
  - `src/cli/task.py` - task command group
- Shared utilities (output formatting, common options, validation helpers) extracted to `src/cli/utils.py` or similar
- `src/ve.py` reduced to a thin entry point that imports and assembles the CLI from the package
- All existing CLI commands work identically (no behavioral changes)
- `uv run pytest tests/` passes
- `uv run ve --help` shows the same command structure as before
