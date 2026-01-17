---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/task_utils.py
- src/subsystems.py
- src/ve.py
- tests/test_task_subsystem_discover.py
- tests/test_task_subsystem_list.py
code_references:
  - ref: src/models.py#SubsystemFrontmatter
    implements: "Added dependents field to SubsystemFrontmatter for cross-repo subsystem references"
  - ref: src/task_utils.py#TaskSubsystemError
    implements: "Error class for user-friendly task subsystem error messages"
  - ref: src/task_utils.py#add_dependents_to_subsystem
    implements: "Update subsystem OVERVIEW.md frontmatter with dependents list"
  - ref: src/task_utils.py#create_task_subsystem
    implements: "Orchestrate multi-repo subsystem creation in task directory context"
  - ref: src/task_utils.py#list_task_subsystems
    implements: "List subsystems from external repo with dependents"
  - ref: src/ve.py#list_subsystems
    implements: "CLI command with task directory detection for subsystem listing"
  - ref: src/ve.py#_list_task_subsystems
    implements: "Handler for task-aware subsystem listing"
  - ref: src/ve.py#discover
    implements: "CLI command with task directory detection for subsystem discovery"
  - ref: src/ve.py#_create_task_subsystem
    implements: "Handler for task-aware subsystem creation"
  - ref: tests/test_task_subsystem_discover.py
    implements: "Integration tests for task-aware subsystem discovery"
  - ref: tests/test_task_subsystem_list.py
    implements: "Integration tests for task-aware subsystem listing"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["external_resolve_all_types", "sync_all_workflows", "task_aware_narrative_cmds"]
---

# Chunk Goal

## Minor Goal

Extend `ve subsystem discover` and `ve subsystem list` commands to support task directory context, following the pattern established by chunk and narrative task-aware commands. When executed in a task directory (containing `.ve-task.yaml`):

- `ve subsystem discover`: Creates the subsystem in the external repository, then creates `external.yaml` references in each project directory with proper causal ordering.
- `ve subsystem list`: Lists subsystems from the external repository, showing their dependents.

This enables cross-repository subsystem workflows where teams working on multiple repositories can document architectural patterns in a shared external documentation repository while maintaining references in each participating project.

## Success Criteria

1. **Task-aware subsystem discover**: `ve subsystem discover` detects task directory context via `is_task_directory()` and:
   - Creates subsystem in the external repository via `Subsystems.create_subsystem()`
   - Creates `external.yaml` in each project's `docs/subsystems/` directory with proper `created_after` ordering
   - Updates the external subsystem's OVERVIEW.md with dependents list
   - Outputs created paths for both external subsystem and project references

2. **Task-aware subsystem list**: `ve subsystem list` in task directory context:
   - Lists subsystems from the external repository
   - Shows status and dependents for each subsystem
   - Supports the same output format as task-aware chunk/narrative list

3. **SubsystemFrontmatter enhanced**: `SubsystemFrontmatter` model in `models.py` adds a `dependents` field (similar to `NarrativeFrontmatter`) for tracking which projects reference external subsystems.

4. **Utility functions**: New functions added to `task_utils.py`:
   - `create_task_subsystem()` - orchestrates cross-repo subsystem creation
   - `list_task_subsystems()` - lists subsystems with dependents from external repo
   - `add_dependents_to_subsystem()` - update subsystem OVERVIEW.md frontmatter with dependents
   - `TaskSubsystemError` - error class for user-friendly messages

5. **Tests pass**: All existing tests continue to pass, and new tests cover:
   - Task-aware subsystem discover flow
   - Task-aware subsystem listing
   - External.yaml creation for subsystems
   - Error handling for missing repos/configs