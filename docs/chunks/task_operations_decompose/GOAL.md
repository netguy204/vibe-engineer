---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/task_utils.py
- src/task/__init__.py
- src/task/config.py
- src/task/artifact_ops.py
- src/task/promote.py
- src/task/external.py
- src/task/friction.py
- src/task/overlap.py
- src/task/exceptions.py
code_references:
  # Package structure and re-exports
  - ref: src/task/__init__.py
    implements: "Package re-exports for backward compatibility with task_utils imports"
  - ref: src/task_utils.py
    implements: "Thin re-export shim preserving backward compatibility"

  # Exception hierarchy
  - ref: src/task/exceptions.py#TaskError
    implements: "Base exception class for all task operations"
  - ref: src/task/exceptions.py#TaskChunkError
    implements: "Chunk-specific task error"
  - ref: src/task/exceptions.py#TaskNarrativeError
    implements: "Narrative-specific task error"
  - ref: src/task/exceptions.py#TaskInvestigationError
    implements: "Investigation-specific task error"
  - ref: src/task/exceptions.py#TaskSubsystemError
    implements: "Subsystem-specific task error"
  - ref: src/task/exceptions.py#TaskPromoteError
    implements: "Artifact promotion error"
  - ref: src/task/exceptions.py#TaskCopyExternalError
    implements: "External copy operation error"
  - ref: src/task/exceptions.py#TaskRemoveExternalError
    implements: "External removal operation error"
  - ref: src/task/exceptions.py#TaskFrictionError
    implements: "Friction logging error"
  - ref: src/task/exceptions.py#TaskOverlapError
    implements: "Overlap detection error"
  - ref: src/task/exceptions.py#TaskActivateError
    implements: "Chunk activation error"

  # Config module
  - ref: src/task/config.py#is_task_directory
    implements: "Task directory detection via .ve-task.yaml"
  - ref: src/task/config.py#load_task_config
    implements: "Task configuration loading and validation"
  - ref: src/task/config.py#resolve_repo_directory
    implements: "Org/repo reference resolution to filesystem path"
  - ref: src/task/config.py#parse_projects_option
    implements: "--projects CLI option parsing"
  - ref: src/task/config.py#resolve_project_ref
    implements: "Flexible project reference resolution"
  - ref: src/task/config.py#resolve_project_qualified_ref
    implements: "Project-qualified code reference parsing"
  - ref: src/task/config.py#find_task_directory
    implements: "Walk-up task directory discovery"
  - ref: src/task/config.py#TaskProjectContext
    implements: "Task project context dataclass"
  - ref: src/task/config.py#check_task_project_context
    implements: "Task project context detection"

  # Artifact operations module
  - ref: src/task/artifact_ops.py#add_dependents_to_artifact
    implements: "Generic artifact dependents update"
  - ref: src/task/artifact_ops.py#append_dependent_to_artifact
    implements: "Idempotent dependent entry append"
  - ref: src/task/artifact_ops.py#add_dependents_to_chunk
    implements: "Chunk-specific dependents wrapper"
  - ref: src/task/artifact_ops.py#add_dependents_to_narrative
    implements: "Narrative-specific dependents wrapper"
  - ref: src/task/artifact_ops.py#add_dependents_to_investigation
    implements: "Investigation-specific dependents wrapper"
  - ref: src/task/artifact_ops.py#add_dependents_to_subsystem
    implements: "Subsystem-specific dependents wrapper"
  - ref: src/task/artifact_ops.py#create_task_chunk
    implements: "Multi-repo chunk creation orchestration"
  - ref: src/task/artifact_ops.py#create_task_narrative
    implements: "Multi-repo narrative creation orchestration"
  - ref: src/task/artifact_ops.py#create_task_investigation
    implements: "Multi-repo investigation creation orchestration"
  - ref: src/task/artifact_ops.py#create_task_subsystem
    implements: "Multi-repo subsystem creation orchestration"
  - ref: src/task/artifact_ops.py#list_task_chunks
    implements: "Task-level chunk listing with dependents"
  - ref: src/task/artifact_ops.py#list_task_narratives
    implements: "Task-level narrative listing with dependents"
  - ref: src/task/artifact_ops.py#list_task_investigations
    implements: "Task-level investigation listing with dependents"
  - ref: src/task/artifact_ops.py#list_task_subsystems
    implements: "Task-level subsystem listing with dependents"
  - ref: src/task/artifact_ops.py#get_current_task_chunk
    implements: "Current IMPLEMENTING chunk retrieval"
  - ref: src/task/artifact_ops.py#get_next_chunk_id
    implements: "Legacy sequential chunk ID calculation"
  - ref: src/task/artifact_ops.py#list_task_artifacts_grouped
    implements: "Grouped artifact listing by location"
  - ref: src/task/artifact_ops.py#list_task_proposed_chunks
    implements: "Proposed chunk collection from artifacts"
  - ref: src/task/artifact_ops.py#is_external_chunk
    implements: "External chunk detection convenience wrapper"
  - ref: src/task/artifact_ops.py#activate_task_chunk
    implements: "FUTURE chunk activation in task context"

  # Promote module
  - ref: src/task/promote.py#identify_source_project
    implements: "Source project identification for promotion"
  - ref: src/task/promote.py#promote_artifact
    implements: "Artifact promotion to external repository"

  # External module
  - ref: src/task/external.py#copy_artifact_as_external
    implements: "External artifact copy to project"
  - ref: src/task/external.py#remove_artifact_from_external
    implements: "External reference removal from project"
  - ref: src/task/external.py#remove_dependent_from_artifact
    implements: "Dependent entry removal from frontmatter"

  # Friction module
  - ref: src/task/friction.py#create_task_friction_entry
    implements: "Multi-repo friction entry creation"
  - ref: src/task/friction.py#add_external_friction_source
    implements: "External friction source reference addition"

  # Overlap module
  - ref: src/task/overlap.py#TaskOverlapResult
    implements: "Overlap detection result dataclass"
  - ref: src/task/overlap.py#find_task_overlapping_chunks
    implements: "Cross-repo chunk overlap detection"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_prune_consolidate
- chunk_validator_extract
- cli_formatters_extract
- frontmatter_import_consolidate
- models_subpackage
- orch_client_context
- project_artifact_registry
- remove_legacy_prefix
- scheduler_decompose
---

# Chunk Goal

## Minor Goal

Decompose `src/task_utils.py` (2,629 lines, 37 public functions, 10+ exception classes) into a focused `src/task/` package with cohesive modules. This file has become a dumping ground for all task-related operations spanning at least six distinct responsibilities: config loading, artifact CRUD, promotion, external operations, friction management, and overlap detection. The "utils" name itself signals the lack of a coherent organizing principle.

This decomposition directly supports the project's goal of maintaining healthy, comprehensible documentation and code over time. Every CLI command module depends on `task_utils.py`, making it a bottleneck for understanding and change. Agents working on any feature must parse thousands of lines to find the relevant operation, and changes to one responsibility risk breaking unrelated ones.

The core structural problems are:

1. **Duplicated artifact operations**: The create/list/add-dependents patterns are repeated nearly identically for chunks, narratives, investigations, and subsystems (four parallel implementations of `create_task_*`, `list_task_*`, `add_dependents_to_*`). These should be consolidated into generic artifact operations parameterized by artifact type.

2. **Scattered exception classes**: Ten exception classes (`TaskChunkError`, `TaskNarrativeError`, `TaskInvestigationError`, `TaskSubsystemError`, `TaskPromoteError`, `TaskArtifactListError`, `TaskCopyExternalError`, `TaskRemoveExternalError`, `TaskFrictionError`, `TaskOverlapError`) plus `TaskActivateError` have no shared base class, making consistent error handling impossible.

3. **Unrelated responsibilities in one module**: Config resolution, artifact promotion, external artifact management, friction logging, and overlap detection share no state or abstraction but are forced into a single file.

Splitting this file will make individual responsibilities discoverable, reduce cognitive load for agents, and enable independent evolution of each concern.

## Success Criteria

- `src/task_utils.py` is replaced by a `src/task/` package with the following modules:
  - `task/config.py` -- Config loading, project resolution, directory detection (currently ~230 lines: `load_task_config`, `resolve_project_ref`, `resolve_project_qualified_ref`, `is_task_directory`, `resolve_repo_directory`, `parse_projects_option`)
  - `task/artifact_ops.py` -- Artifact CRUD operations for task context (`create_task_chunk`, `create_task_narrative`, `create_task_investigation`, `create_task_subsystem`, `list_task_chunks`, `list_task_narratives`, `list_task_investigations`, `list_task_subsystems`, `add_dependents_to_artifact`, `append_dependent_to_artifact`, `list_task_artifacts_grouped`, `list_task_proposed_chunks`)
  - `task/promote.py` -- Artifact promotion logic (currently ~430 lines: `promote_artifact`, `identify_source_project`)
  - `task/external.py` -- External artifact copy/remove operations (currently ~340 lines: `copy_artifact_as_external`, `remove_artifact_from_external`, `remove_dependent_from_artifact`, `is_external_chunk`)
  - `task/friction.py` -- Friction entry operations (currently ~200 lines: `create_task_friction_entry`, `add_external_friction_source`)
  - `task/overlap.py` -- Overlap detection (currently ~240 lines: `find_task_overlapping_chunks`, `TaskOverlapResult`)
  - `task/exceptions.py` -- All exception classes consolidated under a `TaskError` base class
- The `add_dependents_to_*` family is consolidated into a generic `add_dependents_to_artifact()` with type-specific wrappers for backward compatibility
- All exception classes inherit from a common `TaskError` base class
- `src/task/__init__.py` re-exports all public names so that existing `from task_utils import ...` patterns continue to work during the transition period
- All 2,516 existing tests pass without modification (or with only import-path updates)
- No CLI behavior changes -- all commands produce identical output before and after
- `activate_task_chunk`, `get_current_task_chunk`, `get_next_chunk_id`, `check_task_project_context`, `find_task_directory`, and `normalize_ref` are placed in the most cohesive module (config or artifact_ops as appropriate)