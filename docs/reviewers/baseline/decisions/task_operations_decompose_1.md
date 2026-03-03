---
decision: FEEDBACK
summary: Package decomposition is complete and tests pass, but GOAL.md success criterion for generic `create_task_artifact` and `list_task_artifacts` functions was not implemented - type-specific functions remain as separate implementations rather than thin wrappers around generic functions.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/task_utils.py` is replaced by a `src/task/` package with the following modules:

- **Status**: satisfied
- **Evidence**: `src/task/` package exists with `__init__.py`, `config.py`, `artifact_ops.py`, `promote.py`, `external.py`, `friction.py`, `overlap.py`, and `exceptions.py`. `src/task_utils.py` is now a thin re-export layer (163 lines down from 2629 lines).

### Criterion 2: `task/config.py` -- Config loading, project resolution, directory detection

- **Status**: satisfied
- **Evidence**: `src/task/config.py` contains `load_task_config`, `resolve_project_ref`, `resolve_project_qualified_ref`, `is_task_directory`, `resolve_repo_directory`, `parse_projects_option`, `find_task_directory`, `TaskProjectContext`, and `check_task_project_context` (329 lines).

### Criterion 3: `task/artifact_ops.py` -- Generic CRUD for task artifacts

- **Status**: gap
- **Evidence**: `add_dependents_to_artifact` and `append_dependent_to_artifact` are implemented as generic functions. However, `create_task_artifact` and `list_task_artifacts` generic functions do NOT exist - the type-specific functions (`create_task_chunk`, `create_task_narrative`, etc.) are NOT thin wrappers around generic implementations but remain as four separate ~100 line implementations each. This does not match the GOAL.md requirement: "replacing the four duplicated create/list/add-dependents patterns with a single generic implementation".

### Criterion 4: `task/promote.py` -- Artifact promotion logic

- **Status**: satisfied
- **Evidence**: `src/task/promote.py` contains `promote_artifact` and `identify_source_project` (259 lines).

### Criterion 5: `task/external.py` -- External artifact copy/remove operations

- **Status**: satisfied
- **Evidence**: `src/task/external.py` contains `copy_artifact_as_external`, `remove_artifact_from_external`, and `remove_dependent_from_artifact` (359 lines). Note: `is_external_chunk` is in `artifact_ops.py` not `external.py`.

### Criterion 6: `task/friction.py` -- Friction entry operations

- **Status**: satisfied
- **Evidence**: `src/task/friction.py` contains `create_task_friction_entry` and `add_external_friction_source` (209 lines).

### Criterion 7: `task/overlap.py` -- Overlap detection

- **Status**: satisfied
- **Evidence**: `src/task/overlap.py` contains `TaskOverlapResult` dataclass and `find_task_overlapping_chunks` (263 lines).

### Criterion 8: `task/exceptions.py` -- All exception classes consolidated under a `TaskError` base class

- **Status**: satisfied
- **Evidence**: `src/task/exceptions.py` defines `TaskError` base class and 11 subclasses (84 lines).

### Criterion 9: The four artifact-type-specific function families are replaced by generic implementations

- **Status**: gap
- **Evidence**: Only `add_dependents_to_artifact` is implemented as a generic function with thin type-specific wrappers calling it. The `create_task_*` and `list_task_*` families remain as four separate implementations (each ~100 lines) rather than being refactored into generic `create_task_artifact(artifact_type, ...)` and `list_task_artifacts(artifact_type, ...)` with thin wrappers.

### Criterion 10: All exception classes inherit from a common `TaskError` base class

- **Status**: satisfied
- **Evidence**: All 11 exception classes (`TaskChunkError`, `TaskNarrativeError`, `TaskInvestigationError`, `TaskSubsystemError`, `TaskPromoteError`, `TaskArtifactListError`, `TaskCopyExternalError`, `TaskRemoveExternalError`, `TaskFrictionError`, `TaskOverlapError`, `TaskActivateError`) inherit from `TaskError`.

### Criterion 11: `src/task/__init__.py` re-exports all public names

- **Status**: satisfied
- **Evidence**: `src/task/__init__.py` imports and re-exports all public names from submodules via `__all__` (163 lines). `src/task_utils.py` re-exports from `task` package.

### Criterion 12: All 2,516 existing tests pass without modification

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` reports "2516 passed in 120.18s".

### Criterion 13: No CLI behavior changes

- **Status**: satisfied
- **Evidence**: All tests pass, including CLI integration tests. No API changes.

### Criterion 14: Function placement in appropriate modules

- **Status**: satisfied
- **Evidence**: `activate_task_chunk`, `get_current_task_chunk`, `get_next_chunk_id` are in `artifact_ops.py`. `check_task_project_context`, `find_task_directory` are in `config.py`. `normalize_ref` remains as a nested function in `overlap.py` (GOAL.md noted it "can be module-level" but didn't require it).

## Feedback Items

### Issue 1: Generic create/list functions not implemented

- **ID**: issue-create-list-generic
- **Location**: src/task/artifact_ops.py
- **Concern**: GOAL.md requires "replacing the four duplicated create/list/add-dependents patterns with a single generic implementation". While `add_dependents_to_artifact` is generic with thin wrappers, `create_task_chunk/narrative/investigation/subsystem` and `list_task_chunks/narratives/investigations/subsystems` remain as separate ~100 line implementations each, duplicating similar logic.
- **Suggestion**: Implement `create_task_artifact(task_dir, artifact_type, short_name, **kwargs)` and `list_task_artifacts(task_dir, artifact_type)` as generic functions. Then rewrite the four type-specific functions as thin wrappers (similar to how `add_dependents_to_chunk` calls `add_dependents_to_artifact`).
- **Severity**: functional
- **Confidence**: high

### Issue 2: Deviations section not populated

- **ID**: issue-deviations-empty
- **Location**: docs/chunks/task_operations_decompose/PLAN.md
- **Concern**: The Deviations section is empty despite the implementation diverging from the plan by not creating generic `create_task_artifact` and `list_task_artifacts` functions. This deviation should be documented.
- **Suggestion**: Add a deviation note explaining why the generic functions were not implemented (e.g., if the complexity of artifact-specific parameters made generalization impractical).
- **Severity**: style
- **Confidence**: high
