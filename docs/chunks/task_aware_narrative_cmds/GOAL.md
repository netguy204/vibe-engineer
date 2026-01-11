---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/task_utils.py
- src/narratives.py
- src/ve.py
- tests/test_task_narrative_create.py
- tests/test_task_narrative_list.py
- tests/test_task_chunk_create.py
- tests/test_task_chunk_list.py
- tests/test_task_models.py
code_references:
  - ref: src/models.py#TaskConfig
    implements: "Renamed external_chunk_repo to external_artifact_repo for generic artifact support"
  - ref: src/models.py#NarrativeFrontmatter
    implements: "Added dependents field for cross-repo narrative references"
  - ref: src/task_utils.py#TaskNarrativeError
    implements: "Error class for task narrative creation with user-friendly messages"
  - ref: src/task_utils.py#add_dependents_to_narrative
    implements: "Update narrative OVERVIEW.md frontmatter with dependents list"
  - ref: src/task_utils.py#create_task_narrative
    implements: "Orchestrate multi-repo narrative creation with external.yaml and dependents"
  - ref: src/task_utils.py#list_task_narratives
    implements: "List narratives from external repo with their dependents"
  - ref: src/ve.py#_create_task_narrative
    implements: "CLI handler for task-aware narrative creation"
  - ref: src/ve.py#_list_task_narratives
    implements: "CLI handler for task-aware narrative listing"
  - ref: src/ve.py#create_narrative
    implements: "CLI command with task directory detection for narrative create"
  - ref: src/ve.py#list_narratives
    implements: "CLI command with task directory detection for narrative list"
  - ref: tests/test_task_narrative_create.py
    implements: "Integration tests for task-aware narrative creation"
  - ref: tests/test_task_narrative_list.py
    implements: "Integration tests for task-aware narrative listing"
narrative: null
subsystems:
- subsystem_id: workflow_artifacts
  relationship: implements
created_after: ["consolidate_ext_ref_utils"]
---

# Chunk Goal

## Minor Goal

Extend `ve narrative create` and `ve narrative list` commands to support task directory context, following the pattern established by chunk task-aware commands. When executed in a task directory (containing `.ve-task.yaml`):

- `ve narrative create`: Creates the narrative in the external repository, then creates `external.yaml` references in each project directory with proper causal ordering.
- `ve narrative list`: Lists narratives from the external repository, showing their dependents.

This enables cross-repository narrative workflows where teams working on multiple repositories can track higher-level initiatives in a shared external documentation repository while maintaining references in each participating project.

## Success Criteria

1. **TaskConfig refactored**: `TaskConfig` model in `models.py` renames `external_chunk_repo` to `external_artifact_repo` for generality. This single field specifies where all external workflow artifacts (chunks, narratives, investigations, subsystems) are stored. All references in `task_utils.py` and tests updated accordingly.

2. **Task-aware narrative create**: `ve narrative create` detects task directory context via `is_task_directory()` and:
   - Creates narrative in the external repository via `Narratives.create_narrative()`
   - Creates `external.yaml` in each project's `docs/narratives/` directory with proper `created_after` ordering
   - Updates the external narrative's OVERVIEW.md with dependents list
   - Outputs created paths for both external narrative and project references

3. **Task-aware narrative list**: `ve narrative list` in task directory context:
   - Lists narratives from the external repository
   - Shows status and dependents for each narrative
   - Supports the same output format as task-aware chunk list

4. **Utility functions**: New functions added to `task_utils.py`:
   - `create_task_narrative()` - orchestrates cross-repo narrative creation
   - `list_task_narratives()` - lists narratives with dependents from external repo
   - `TaskNarrativeError` - error class for user-friendly messages

5. **Tests pass**: All existing tests continue to pass, and new tests cover:
   - Task-aware narrative creation flow
   - Task-aware narrative listing
   - External.yaml creation for narratives
   - Error handling for missing repos/configs

