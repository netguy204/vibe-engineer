# Implementation Plan

## Approach

This is a straightforward import consolidation refactor. The strategy is:

1. **Update imports at call sites**: Change five modules from importing `update_frontmatter_field` from `task_utils` to importing directly from `frontmatter`.
2. **Remove the re-export**: Delete the re-export lines from `task_utils.py`.
3. **Update test imports**: The test file `tests/test_task_utils.py` imports this function from `task_utils`; these tests should be moved or updated to import from `frontmatter`.
4. **Verify**: Run the full test suite to ensure no regressions.

This follows the pattern already established by `src/artifact_manager.py` (line 271), which correctly imports directly from `frontmatter`.

No new architectural decisions are required. This is a mechanical consolidation of import paths to reduce indirection.

## Subsystem Considerations

No subsystems are relevant. This is a pure import path consolidation with no architectural pattern changes.

## Sequence

### Step 1: Update import in `src/orchestrator/scheduler.py`

Change the top-level import from:
```python
from task_utils import update_frontmatter_field
```
to:
```python
from frontmatter import update_frontmatter_field
```

Location: `src/orchestrator/scheduler.py` line 33

### Step 2: Update import in `src/chunks.py` (first occurrence)

Change the local import inside `activate_chunk()` from:
```python
from task_utils import update_frontmatter_field
```
to:
```python
from frontmatter import update_frontmatter_field
```

Location: `src/chunks.py` line 317

### Step 3: Update import in `src/chunks.py` (second occurrence)

Change the local import inside `update_status()` from:
```python
from task_utils import update_frontmatter_field
```
to:
```python
from frontmatter import update_frontmatter_field
```

Location: `src/chunks.py` line 1221

### Step 4: Update import in `src/consolidation.py`

Change the local import inside `consolidate_chunks_to_narrative()` from:
```python
from task_utils import update_frontmatter_field
```
to:
```python
from frontmatter import update_frontmatter_field
```

Location: `src/consolidation.py` line 55

### Step 5: Update import in `src/cli/chunk.py`

Change the local import inside `complete_chunk()` from:
```python
from task_utils import update_frontmatter_field
```
to:
```python
from frontmatter import update_frontmatter_field
```

Location: `src/cli/chunk.py` line 638

### Step 6: Remove re-export from `src/task_utils.py`

Delete the comment and import lines:
```python
# Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
# Re-export update_frontmatter_field from the shared module for API compatibility
from frontmatter import update_frontmatter_field
```

Location: `src/task_utils.py` lines 301-303

### Step 7: Update test imports in `tests/test_task_utils.py`

The test file imports `update_frontmatter_field` from `task_utils` (line 18). Since this function is tested thoroughly in `tests/test_frontmatter.py` already (class `TestUpdateFrontmatterField` starting at line 335), we have two options:

**Option A (Preferred)**: Remove the `TestUpdateFrontmatterField` class from `tests/test_task_utils.py` entirely. The tests are duplicates of what's already covered in `tests/test_frontmatter.py`.

**Option B**: Update the import to `from frontmatter import update_frontmatter_field` and keep the tests. However, this creates redundant testing.

Given the goal of consolidation, Option A is cleaner. The import statement at line 18 should also be updated to remove `update_frontmatter_field` from the import list.

### Step 8: Verify no remaining imports from task_utils

Run grep to confirm zero results for:
```bash
grep -r "from task_utils import update_frontmatter_field" src/
```

### Step 9: Run full test suite

Execute `uv run pytest tests/` to verify no regressions. All existing tests should pass.

## Dependencies

None. This chunk is independent per the narrative's design (`depends_on: []`). The `frontmatter.py` module already exists with the canonical `update_frontmatter_field` implementation.

## Risks and Open Questions

**Low risk**: This is a mechanical refactor. The function signature and behavior remain unchanged; only the import path changes.

**Potential concern**: If any external tooling or dynamic imports reference `task_utils.update_frontmatter_field`, they would break. However:
- The codebase grep shows all usages are explicit static imports
- The re-export was marked "for API compatibility" but the only consumer is internal code
- No external packages depend on this

## Deviations

<!-- Populated during implementation -->