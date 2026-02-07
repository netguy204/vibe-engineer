---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/utils.py
- src/cli/chunk.py
- src/cli/narrative.py
- src/cli/investigation.py
- src/cli/subsystem.py
- src/cli/friction.py
- src/cli/external.py
- tests/test_cli_utils.py
code_references:
  - ref: src/cli/utils.py#handle_task_context
    implements: "Core task-context routing helper that checks is_task_directory and executes handler"
  - ref: tests/test_cli_utils.py#TestHandleTaskContext
    implements: "Unit tests for handle_task_context helper"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Eliminate the repeated task-context branching pattern that appears in 6+ CLI modules by introducing a decorator or context manager that handles the `is_task_directory()` check and routing to task-specific handlers. This reduces 10+ instances of near-identical branching logic (`if is_task_directory(project_dir): _task_handler(...); return`) across chunk.py, narrative.py, investigation.py, subsystem.py, friction.py, and external.py.

This consolidation improves CLI maintainability by centralizing the task-context detection logic and reducing the surface area for bugs when the branching pattern changes.

## Success Criteria

- A decorator or context manager pattern is implemented that handles task-context detection and routing
- All 10+ instances of `if is_task_directory(project_dir): _task_handler(...); return` are replaced with the new abstraction across:
  - chunk.py: create (lines 140-145), list (lines 415-417), list-proposed (lines 745-747)
  - narrative.py: create (lines 57-59), list (lines 120-122)
  - investigation.py: create (lines 53-55), list (lines 107-109)
  - subsystem.py: list (lines 44-46), discover (lines 99-100)
  - friction.py: log (lines 57-62)
  - external.py: resolve (lines 63-64)
- The new abstraction preserves existing behavior (task handlers are called when in task directory, single-repo handlers otherwise)
- All existing CLI tests pass without modification
- The abstraction reduces code duplication by at least 30 lines of boilerplate

