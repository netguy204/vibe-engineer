---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/task_utils.py
- src/ve.py
- tests/test_task_investigation_create.py
- tests/test_task_investigation_list.py
code_references:
  - ref: src/models.py#InvestigationFrontmatter
    implements: "Added dependents field for cross-repo investigation tracking"
  - ref: src/task_utils.py#TaskInvestigationError
    implements: "Error class for task investigation operations with user-friendly messages"
  - ref: src/task_utils.py#add_dependents_to_investigation
    implements: "Helper to update investigation OVERVIEW.md frontmatter with dependents list"
  - ref: src/task_utils.py#create_task_investigation
    implements: "Orchestrates multi-repo investigation creation with external.yaml and dependents"
  - ref: src/task_utils.py#list_task_investigations
    implements: "Lists investigations from external repo with their dependents"
  - ref: src/ve.py#create_investigation
    implements: "CLI command extended with task directory detection"
  - ref: src/ve.py#_create_task_investigation
    implements: "Handler for task directory investigation creation"
  - ref: src/ve.py#list_investigations
    implements: "CLI command extended with task directory detection"
  - ref: src/ve.py#_list_task_investigations
    implements: "Handler for task directory investigation listing"
  - ref: tests/test_task_investigation_create.py
    implements: "Integration tests for task-aware investigation creation"
  - ref: tests/test_task_investigation_list.py
    implements: "Integration tests for task-aware investigation listing"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["external_resolve_all_types", "sync_all_workflows", "task_aware_narrative_cmds"]
---

# Chunk Goal

## Minor Goal

Extend `ve investigation create` and `ve investigation list` commands to support task directory context, following the pattern established by chunk and narrative task-aware commands. When executed in a task directory (containing `.ve-task.yaml`):

- `ve investigation create`: Creates the investigation in the external repository, then creates `external.yaml` references in each project directory with proper causal ordering.
- `ve investigation list`: Lists investigations from the external repository, showing their dependents.

This enables cross-repository investigation workflows where teams working on multiple repositories can track diagnostic or exploratory work in a shared external documentation repository while maintaining references in each participating project.

## Success Criteria

1. **Task-aware investigation create**: `ve investigation create` detects task directory context via `is_task_directory()` and:
   - Creates investigation in the external repository via `Investigations.create_investigation()`
   - Creates `external.yaml` in each project's `docs/investigations/` directory with proper `created_after` ordering
   - Updates the external investigation's OVERVIEW.md with dependents list
   - Outputs created paths for both external investigation and project references

2. **Task-aware investigation list**: `ve investigation list` in task directory context:
   - Lists investigations from the external repository
   - Shows status and dependents for each investigation
   - Supports the same output format as task-aware chunk/narrative list

3. **Utility functions**: New functions added to `task_utils.py`:
   - `create_task_investigation()` - orchestrates cross-repo investigation creation
   - `list_task_investigations()` - lists investigations with dependents from external repo
   - `TaskInvestigationError` - error class for user-friendly messages

4. **Model updates**: `InvestigationFrontmatter` in `models.py` updated:
   - Add `dependents: list[InvestigationDependent]` field to track which projects reference this investigation
   - `InvestigationDependent` model with `project_path` and `artifact_id` fields (following `NarrativeDependent` pattern)

5. **Tests pass**: All existing tests continue to pass, and new tests cover:
   - Task-aware investigation creation flow
   - Task-aware investigation listing
   - External.yaml creation for investigations
   - Error handling for missing repos/configs

