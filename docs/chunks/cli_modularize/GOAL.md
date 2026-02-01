---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
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