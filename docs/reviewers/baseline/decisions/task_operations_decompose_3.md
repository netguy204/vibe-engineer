---
decision: ESCALATE
summary: Same issue flagged in iterations 1 and 2 (missing generic create/list functions) remains unaddressed at iteration 3 - loop has not converged and requires operator judgment.
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/task_utils.py` is replaced by a `src/task/` package with the following modules:

- **Status**: satisfied
- **Evidence**: `src/task/` package exists with all required modules: `__init__.py` (163 lines), `config.py` (329 lines), `artifact_ops.py` (1284 lines), `promote.py` (259 lines), `external.py` (359 lines), `friction.py` (209 lines), `overlap.py` (263 lines), and `exceptions.py` (84 lines). `src/task_utils.py` is now a thin re-export layer (163 lines).

### Criterion 2: `task/config.py` -- Config loading, project resolution, directory detection

- **Status**: satisfied
- **Evidence**: `src/task/config.py` contains all required functions: `load_task_config`, `resolve_project_ref`, `resolve_project_qualified_ref`, `is_task_directory`, `resolve_repo_directory`, `parse_projects_option`, `find_task_directory`, `TaskProjectContext`, and `check_task_project_context`.

### Criterion 3: `task/artifact_ops.py` -- Generic CRUD for task artifacts

- **Status**: gap
- **Evidence**: Only `add_dependents_to_artifact` and `append_dependent_to_artifact` are implemented as generic functions with type-specific wrappers. The GOAL.md requires `create_task_artifact` and `list_task_artifacts` generic functions. These generic functions do NOT exist. The four `create_task_*` and four `list_task_*` functions remain as separate ~100-line implementations each with duplicated logic patterns. **This feedback was given in iterations 1 and 2 and remains unaddressed.**

### Criterion 4: `task/promote.py` -- Artifact promotion logic

- **Status**: satisfied
- **Evidence**: `src/task/promote.py` (259 lines) contains `promote_artifact` and `identify_source_project` with proper subsystem backreference comments.

### Criterion 5: `task/external.py` -- External artifact copy/remove operations

- **Status**: satisfied
- **Evidence**: `src/task/external.py` (359 lines) contains `copy_artifact_as_external`, `remove_artifact_from_external`, and `remove_dependent_from_artifact`. Note: `is_external_chunk` is in `artifact_ops.py`.

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
- **Evidence**: Only the `add_dependents_to_*` family is properly genericized (calling `add_dependents_to_artifact`). The `create_task_*` and `list_task_*` families remain as four separate ~100-line implementations each. **REPEAT of iterations 1 and 2 feedback which was not addressed.**

### Criterion 10: All exception classes inherit from a common `TaskError` base class

- **Status**: satisfied
- **Evidence**: All 11 exception classes inherit from `TaskError` as verified by `issubclass()` checks.

### Criterion 11: `src/task/__init__.py` re-exports all public names

- **Status**: satisfied
- **Evidence**: `src/task/__init__.py` imports and re-exports all public names. `src/task_utils.py` re-exports from the `task` package. Backward compatibility verified with direct imports.

### Criterion 12: All 2,516 existing tests pass without modification

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` reports "2516 passed in 81.94s".

### Criterion 13: No CLI behavior changes

- **Status**: satisfied
- **Evidence**: All tests pass including CLI integration tests.

### Criterion 14: Function placement in appropriate modules

- **Status**: satisfied
- **Evidence**: `activate_task_chunk`, `get_current_task_chunk`, `get_next_chunk_id`, `is_external_chunk` in `artifact_ops.py`. `check_task_project_context`, `find_task_directory` in `config.py`. `normalize_ref` nested in `overlap.py`.

## Escalation Reason

**REASON**: RECURRING ISSUE / LOOP NOT CONVERGED

This is iteration 3 of review. The same core issue has been flagged in **both prior iterations** (1 and 2):

1. **Iteration 1 feedback (issue-create-list-generic)**: "GOAL.md requires 'replacing the four duplicated create/list/add-dependents patterns with a single generic implementation'. While `add_dependents_to_artifact` is generic with thin wrappers, `create_task_chunk/narrative/investigation/subsystem` and `list_task_chunks/narratives/investigations/subsystems` remain as separate ~100 line implementations each."

2. **Iteration 2 feedback (issue-create-list-generic-v2)**: "This is a REPEAT of iteration 1 feedback which was not addressed."

3. **Iteration 3 (now)**: Still not addressed.

Per reviewer guidelines: "When to ESCALATE: ... You've flagged the same issue twice (recurring issue) ... Review-implementation loop hasn't converged (3+ iterations)".

**Questions for operator:**

1. **Should the generic functions be required?** The GOAL.md explicitly states `create_task_artifact` and `list_task_artifacts` should exist and replace the duplicated patterns. The PLAN.md also describes this as a key step. However, the implementer has not addressed this feedback despite two iterations.

2. **Is the current implementation acceptable as-is?** The decomposition into modules IS complete, tests pass (2516), backward compatibility works, and the subsystem documentation was updated. The functional goals are met even though code duplication remains (~800 lines of duplicated patterns across the 4 artifact types).

3. **Should the Deviations section be updated?** If the generic approach was intentionally abandoned due to complexity (e.g., artifact-specific parameters like `ticket_id` and `status` for chunks making a clean generic interface impractical), this should be documented as a deviation.

**Recommendation**: Either (a) enforce the documented success criteria and require implementation of generic functions, OR (b) update GOAL.md/PLAN.md to remove this requirement and document the deviation explaining why duplication was accepted.
