---
decision: FEEDBACK
summary: Prior iteration feedback not addressed - generic create/list functions still missing, type-specific implementations remain duplicated, deviation not documented.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/task_utils.py` is replaced by a `src/task/` package with the following modules:

- **Status**: satisfied
- **Evidence**: `src/task/` package exists with all required modules: `__init__.py`, `config.py`, `artifact_ops.py`, `promote.py`, `external.py`, `friction.py`, `overlap.py`, and `exceptions.py`. `src/task_utils.py` is now a thin re-export layer (163 lines, down from 2,629 lines).

### Criterion 2: `task/config.py` -- Config loading, project resolution, directory detection

- **Status**: satisfied
- **Evidence**: `src/task/config.py` (329 lines) contains all required functions: `load_task_config`, `resolve_project_ref`, `resolve_project_qualified_ref`, `is_task_directory`, `resolve_repo_directory`, `parse_projects_option`, `find_task_directory`, `TaskProjectContext`, and `check_task_project_context`.

### Criterion 3: `task/artifact_ops.py` -- Generic CRUD for task artifacts

- **Status**: gap
- **Evidence**: Only `add_dependents_to_artifact` and `append_dependent_to_artifact` are implemented as generic functions with type-specific wrappers. However, the GOAL.md explicitly requires "replacing the four duplicated create/list/add-dependents patterns with a single generic implementation" including `create_task_artifact` and `list_task_artifacts`. These generic functions do NOT exist. The four `create_task_*` and four `list_task_*` functions remain as separate ~100-line implementations each with duplicated logic patterns. This was flagged in iteration 1 feedback and has NOT been addressed.

### Criterion 4: `task/promote.py` -- Artifact promotion logic

- **Status**: satisfied
- **Evidence**: `src/task/promote.py` (259 lines) contains `promote_artifact` and `identify_source_project` with proper subsystem backreference comments.

### Criterion 5: `task/external.py` -- External artifact copy/remove operations

- **Status**: satisfied
- **Evidence**: `src/task/external.py` (359 lines) contains `copy_artifact_as_external`, `remove_artifact_from_external`, and `remove_dependent_from_artifact`. Note: `is_external_chunk` is in `artifact_ops.py` rather than `external.py` (minor placement divergence from GOAL.md listing).

### Criterion 6: `task/friction.py` -- Friction entry operations

- **Status**: satisfied
- **Evidence**: `src/task/friction.py` (209 lines) contains `create_task_friction_entry` and `add_external_friction_source`.

### Criterion 7: `task/overlap.py` -- Overlap detection

- **Status**: satisfied
- **Evidence**: `src/task/overlap.py` (263 lines) contains `TaskOverlapResult` dataclass and `find_task_overlapping_chunks`.

### Criterion 8: `task/exceptions.py` -- All exception classes consolidated under a `TaskError` base class

- **Status**: satisfied
- **Evidence**: `src/task/exceptions.py` (84 lines) defines `TaskError` base class and 11 subclasses that all inherit from it.

### Criterion 9: The four artifact-type-specific function families are replaced by generic implementations

- **Status**: gap
- **Evidence**: Only the `add_dependents_to_*` family is properly genericized (calling `add_dependents_to_artifact`). The `create_task_*` and `list_task_*` families remain as four separate ~100-line implementations each. This is a REPEAT of iteration 1 feedback which was not addressed.

### Criterion 10: All exception classes inherit from a common `TaskError` base class

- **Status**: satisfied
- **Evidence**: All 11 exception classes (`TaskChunkError`, `TaskNarrativeError`, `TaskInvestigationError`, `TaskSubsystemError`, `TaskPromoteError`, `TaskArtifactListError`, `TaskCopyExternalError`, `TaskRemoveExternalError`, `TaskFrictionError`, `TaskOverlapError`, `TaskActivateError`) inherit from `TaskError` in `src/task/exceptions.py`.

### Criterion 11: `src/task/__init__.py` re-exports all public names

- **Status**: satisfied
- **Evidence**: `src/task/__init__.py` (163 lines) imports and re-exports all public names from submodules via `__all__`. `src/task_utils.py` re-exports from the `task` package for backward compatibility.

### Criterion 12: All 2,516 existing tests pass without modification

- **Status**: satisfied
- **Evidence**: Running `uv run pytest tests/` reports "2516 passed in 111.43s".

### Criterion 13: No CLI behavior changes

- **Status**: satisfied
- **Evidence**: All tests pass including CLI integration tests. The re-export pattern preserves API compatibility.

### Criterion 14: Function placement in appropriate modules

- **Status**: satisfied
- **Evidence**: `activate_task_chunk`, `get_current_task_chunk`, `get_next_chunk_id`, `is_external_chunk` are in `artifact_ops.py`. `check_task_project_context`, `find_task_directory` are in `config.py`. `normalize_ref` remains as a nested function in `overlap.py` (GOAL.md noted it "can be module-level" but didn't require it).

## Feedback Items

### Issue 1: Generic create/list functions not implemented (REPEAT from iteration 1)

- **ID**: issue-create-list-generic-v2
- **Location**: src/task/artifact_ops.py
- **Concern**: GOAL.md explicitly requires "replacing the four duplicated create/list/add-dependents patterns with a single generic implementation parameterized by artifact type (`create_task_artifact`, `list_task_artifacts`, ...)". This feedback was given in iteration 1 but was NOT addressed. The four `create_task_*` functions and four `list_task_*` functions remain as separate ~100-line implementations with duplicated patterns.
- **Suggestion**: Implement generic `create_task_artifact(task_dir, artifact_type, short_name, **kwargs)` and `list_task_artifacts(task_dir, artifact_type)` functions. Then convert the type-specific functions to thin wrappers that call the generic implementation (as was done for `add_dependents_to_*`). The helper function `_get_manager_for_type()` already exists and can be used for this purpose.
- **Severity**: functional
- **Confidence**: high

### Issue 2: Deviations section not populated (REPEAT from iteration 1)

- **ID**: issue-deviations-empty-v2
- **Location**: docs/chunks/task_operations_decompose/PLAN.md (Deviations section at end of file)
- **Concern**: The Deviations section remains empty despite the implementation diverging significantly from the plan. If the generic functions were intentionally not implemented due to complexity (e.g., artifact-specific parameters like `ticket_id` and `status` for chunks), this should be documented as a deviation per PLAN.md instructions.
- **Suggestion**: Either (a) implement the generic functions as originally planned, OR (b) document the deviation explaining why the generic approach was not taken (e.g., "Step 3: Generic create_task_artifact was not implemented because artifact-specific parameters (ticket_id, status for chunks) made a clean generic interface impractical. The duplication was accepted to preserve type-specific signatures.").
- **Severity**: style
- **Confidence**: high

