# Implementation Plan

## Approach

This chunk removes dead code identified during the architecture review. The approach is:

1. **Delete unused function** (`_start_task_chunk`): Simple removal - the function is defined but never called.

2. **Consolidate redundant validation** (`validate_combined_chunk_name`): Replace call site with `validate_short_name`, delete the function.

3. **Migrate `task_utils.py` imports**: Update all 26 import sites in `src/` and `tests/` to import directly from `task` package or `external_refs`, then delete the shim.

This is pure refactoring - no behavior changes. All existing tests must pass after each step.

Per docs/trunk/TESTING_PHILOSOPHY.md, this work doesn't require new tests because:
- We're removing dead code (nothing to test)
- Import path changes are validated by running the existing test suite
- The removed function was never called, so no behavior is being lost

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk removes the backward-compatibility shim `src/task_utils.py` mentioned in the subsystem overview. After removal, the subsystem documentation should be updated to remove references to this file. However, since the subsystem is DOCUMENTED (not REFACTORING), this is optional cleanup.

## Sequence

### Step 1: Delete `_start_task_chunk` function

Remove the unused function from `src/cli/chunk.py`.

**Location**: `src/cli/chunk.py`, lines 220-253

**Verification**: Run `uv run pytest tests/test_chunk_start.py` to ensure chunk creation still works via the batch handler.

### Step 2: Replace `validate_combined_chunk_name` call site

In `src/cli/chunk.py:125`, the code calls:
```python
errors.extend(validate_combined_chunk_name(name.lower(), ticket_id))
```

This is redundant because `validate_short_name` (called on line 124) already validates the 31-character limit via `validate_identifier`. The only difference is `validate_combined_chunk_name` accepts a `ticket_id` parameter that it explicitly ignores (line 47: `combined_name = short_name`).

**Action**:
1. Remove the call to `validate_combined_chunk_name` at line 125
2. Remove `validate_combined_chunk_name` from the import statement at line 39
3. Delete the `validate_combined_chunk_name` function from `src/cli/utils.py` (lines 30-54)

**Verification**: Run `uv run pytest tests/test_chunk_start.py` to ensure validation still works.

### Step 3: Catalog all `task_utils` import sites

Examine each of the 26 import sites in `src/` and `tests/` to determine the correct replacement import path.

The `task_utils.py` re-exports from two sources:
- `external_refs`: `is_external_artifact`, `load_external_ref`, `create_external_yaml`, `normalize_artifact_path`, `ARTIFACT_MAIN_FILE`, `ARTIFACT_DIR_NAME`
- `task`: All task-related symbols (exceptions, config, artifact_ops, promote, external, friction, overlap)

For each import site, determine which symbols are used and from which source they should be imported.

### Step 4: Migrate imports in `src/` files (14 files)

Update imports in the following files to import directly from `task` or `external_refs`:

1. `src/task/__init__.py` - Imports from `task_utils` to get `external_refs` symbols; switch to direct import
2. `src/orchestrator/models.py` - Check which symbols are used
3. `src/external_resolve.py` - Check which symbols are used
4. `src/cli/utils.py` - Uses `TaskProjectContext`, `is_task_directory`; switch to `from task import`
5. `src/cluster_analysis.py` - Check which symbols are used
6. `src/cli/narrative.py` - Check which symbols are used
7. `src/cli/subsystem.py` - Check which symbols are used
8. `src/cli/investigation.py` - Check which symbols are used
9. `src/cli/external.py` - Check which symbols are used
10. `src/cli/friction.py` - Check which symbols are used
11. `src/cli/artifact.py` - Check which symbols are used
12. `src/cli/chunk.py` - Uses task-related imports; switch to `from task import`
13. `src/chunk_validation.py` - Check which symbols are used
14. `src/chunks.py` - Check which symbols are used

**Verification**: Run `uv run pytest tests/` after each file to catch import errors early.

### Step 5: Migrate imports in `tests/` files (12 files)

Update imports in the following test files:

1. `tests/test_task_narrative_create.py`
2. `tests/test_task_subsystem_discover.py`
3. `tests/test_task_utils.py` - May need to import from both `task` and `external_refs`
4. `tests/test_task_context_cmds.py`
5. `tests/test_task_init.py`
6. `tests/test_task_investigation_create.py`
7. `tests/test_task_chunk_create.py`
8. `tests/test_external_resolve.py`
9. `tests/test_chunk_list_proposed.py`
10. `tests/test_artifact_promote.py`
11. `tests/test_artifact_remove_external.py`
12. `tests/test_artifact_copy_external.py`

**Verification**: Run full test suite after all migrations.

### Step 6: Delete `src/task_utils.py`

Remove the now-unused re-export shim.

**Verification**:
- `grep -r "from task_utils import\|import task_utils" src/ tests/` returns zero matches
- `uv run pytest tests/` passes
- `uv run ve chunk list` works (smoke test)

### Step 7: Update cross_repo_operations subsystem documentation (optional)

Remove mention of `src/task_utils.py` from `docs/subsystems/cross_repo_operations/OVERVIEW.md` line 182.

## Risks and Open Questions

1. **Import ordering**: Some files may have circular import concerns. If encountered, use lazy imports or restructure as needed.

2. **Test isolation**: Tests that mock `task_utils` imports will need their mock targets updated. This should be mechanical but may require attention.

3. **External tools**: If any external tools or scripts import from `task_utils`, they will break. This is acceptable - the module docstring has warned about deprecation, and direct imports from `task` are the documented replacement.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->