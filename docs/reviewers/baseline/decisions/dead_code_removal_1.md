---
decision: FEEDBACK
summary: Two of five success criteria not satisfied - task_utils.py still exists and 15 imports remain in tests/test_artifact_remove_external.py
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: The function `_start_task_chunk` no longer exists in `src/cli/chunk.py`. Grep for `_start_task_chunk[^s]` returns zero matches across the codebase.

- **Status**: satisfied
- **Evidence**: Grep for `def _start_task_chunk[^s]` in `src/` returns zero matches. Only `_start_task_chunks` (plural, batch handler) exists at line 218 of `src/cli/chunk.py`. The single-chunk handler has been removed.

### Criterion 2: The function `validate_combined_chunk_name` no longer exists in `src/cli/utils.py`. All call sites that previously used it now use `validate_short_name` directly. Grep for `validate_combined_chunk_name` returns zero matches.

- **Status**: satisfied
- **Evidence**: Grep for `validate_combined_chunk_name` in `src/` returns zero matches. The function has been removed from `src/cli/utils.py`. Only `validate_short_name` remains (line 18).

### Criterion 3: The file `src/task_utils.py` is deleted. All imports that previously referenced `task_utils` now import directly from `task`, `task.config`, `task.artifact_ops`, `task.promote`, `task.external`, `task.friction`, `task.overlap`, `task.exceptions`, or `external_refs` as appropriate.

- **Status**: gap
- **Evidence**: `src/task_utils.py` still exists (163 lines). The file remains as a re-export shim. `ls -la src/task_utils.py` shows the file is present and has not been deleted.

### Criterion 4: No import of `task_utils` appears anywhere in `src/` or `tests/`. Grep for `from task_utils import|import task_utils` returns zero matches.

- **Status**: gap
- **Evidence**: Grep finds 15 imports from `task_utils` in `tests/test_artifact_remove_external.py` (lines 31, 78, 125, 157, 198, 241, 258, 273, 299, 349, 399, 442, 481, 542, 633). These test functions import `copy_artifact_as_external`, `remove_artifact_from_external`, and `TaskRemoveExternalError` from `task_utils` instead of from `task` or `task.external`.

### Criterion 5: All existing tests pass (`uv run pytest tests/`) with no regressions.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/` completes with 2631 tests passed. However, this is because `task_utils.py` still exists as a working shim - the tests would fail if the shim were deleted without first migrating the imports.

## Feedback Items

### Issue 1: task_utils.py shim not deleted

- **id**: issue-tu-exists
- **location**: `src/task_utils.py`
- **concern**: The file still exists (163 lines). The GOAL.md success criteria explicitly states "The file `src/task_utils.py` is deleted."
- **suggestion**: After migrating all imports in tests/test_artifact_remove_external.py to import from `task` or `task.external`, delete `src/task_utils.py`.
- **severity**: functional
- **confidence**: high

### Issue 2: 15 unmigrated imports in test file

- **id**: issue-tu-imports
- **location**: `tests/test_artifact_remove_external.py` (lines 31, 78, 125, 157, 198, 241, 258, 273, 299, 349, 399, 442, 481, 542, 633)
- **concern**: These test functions still import `copy_artifact_as_external`, `remove_artifact_from_external`, and `TaskRemoveExternalError` from `task_utils` instead of from `task` or `task.external`.
- **suggestion**: Replace each `from task_utils import copy_artifact_as_external, remove_artifact_from_external` with `from task import copy_artifact_as_external, remove_artifact_from_external` (or `from task.external import ...`). Similarly for `TaskRemoveExternalError`.
- **severity**: functional
- **confidence**: high
