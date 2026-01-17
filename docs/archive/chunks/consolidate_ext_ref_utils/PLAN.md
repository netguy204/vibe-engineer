<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk creates a new `src/external_refs.py` module that consolidates external
artifact reference utilities. The approach is:

1. **Create new module with generic utilities** - Build `src/external_refs.py` with
   type-agnostic functions that work for any artifact type.

2. **Move functions from task_utils.py** - The existing `is_external_chunk`,
   `load_external_ref`, and `create_external_yaml` functions move to the new module.
   The chunk-specific `is_external_chunk` becomes `is_external_artifact`.

3. **Update all callers directly** - Since there are no external users of this CLI,
   we update import sites directly rather than maintaining re-exports:
   - `src/sync.py` - imports from `external_refs`
   - `src/external_resolve.py` - imports from `external_refs`
   - `src/task_utils.py` - imports from `external_refs`
   - `src/artifact_ordering.py` - uses shared constants from `external_refs`

4. **TDD approach** - Per TESTING_PHILOSOPHY.md, write tests first for the new
   generic utilities, then implement to make them pass.

The design leverages the existing `_ARTIFACT_MAIN_FILE` mapping in `artifact_ordering.py`
which already knows the main document for each artifact type (GOAL.md for chunks,
OVERVIEW.md for others).

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS
  external reference utilities for the workflow_artifacts subsystem. Since the
  subsystem is in REFACTORING status, we will opportunistically improve code we touch
  to follow subsystem patterns.

The subsystem's "External Reference Consolidation" section (items #5-7) describes
this work. This chunk addresses item #5 specifically.

## Sequence

### Step 1: Write tests for new external_refs module

Create `tests/test_external_refs.py` with failing tests for:

- `is_external_artifact(path, artifact_type)` - Tests for each artifact type
  - Chunk: external.yaml without GOAL.md → True
  - Narrative: external.yaml without OVERVIEW.md → True
  - Investigation: external.yaml without OVERVIEW.md → True
  - Subsystem: external.yaml without OVERVIEW.md → True
  - Local artifact with main file → False
  - Empty directory → False

- `detect_artifact_type_from_path(path)` - Tests for path detection
  - `docs/chunks/foo/` → CHUNK
  - `docs/narratives/bar/` → NARRATIVE
  - `docs/investigations/baz/` → INVESTIGATION
  - `docs/subsystems/qux/` → SUBSYSTEM
  - Invalid path → raises ValueError

- `get_main_file_for_type(artifact_type)` - Simple utility tests
  - Returns "GOAL.md" for CHUNK
  - Returns "OVERVIEW.md" for others

Location: `tests/test_external_refs.py`

### Step 2: Create external_refs module with core utilities

Create `src/external_refs.py` with:

```python
# Constants
ARTIFACT_MAIN_FILE: dict[ArtifactType, str]
ARTIFACT_DIR_NAME: dict[ArtifactType, str]

# Functions
def get_main_file_for_type(artifact_type: ArtifactType) -> str
def is_external_artifact(path: Path, artifact_type: ArtifactType) -> bool
def detect_artifact_type_from_path(path: Path) -> ArtifactType
```

Include module-level backreference comment linking to this chunk and the
workflow_artifacts subsystem.

Location: `src/external_refs.py`

### Step 3: Migrate load_external_ref to external_refs module

Move `load_external_ref` from `task_utils.py` to `external_refs.py`. The function
already returns `ExternalArtifactRef` which is type-agnostic.

Add test coverage for loading external refs with different artifact types.

Location: `src/external_refs.py`

### Step 4: Migrate create_external_yaml to external_refs module

Move `create_external_yaml` from `task_utils.py` to `external_refs.py`. The function
already supports all artifact types via the `artifact_type` parameter.

No additional tests needed - existing tests in `test_task_utils.py` cover this.

Location: `src/external_refs.py`

### Step 5: Update task_utils.py

Update `task_utils.py` to:
- Remove `is_external_chunk`, `load_external_ref`, `create_external_yaml` definitions
- Import `create_external_yaml`, `load_external_ref` from `external_refs`
- Import `is_external_artifact` and use with `ArtifactType.CHUNK` where needed

Location: `src/task_utils.py`

### Step 6: Update sync.py and external_resolve.py

Update import sites to use `external_refs`:
- `src/sync.py` - change imports from `task_utils` to `external_refs`
- `src/external_resolve.py` - change imports from `task_utils` to `external_refs`

Both currently use `is_external_chunk` - replace with
`is_external_artifact(path, ArtifactType.CHUNK)`.

Location: `src/sync.py`, `src/external_resolve.py`

### Step 7: Update artifact_ordering.py to use external_refs

Replace the inline external detection logic in `_enumerate_artifacts` with a call
to `is_external_artifact`. Remove duplicate `_ARTIFACT_MAIN_FILE` constant and
import from `external_refs`.

Update these functions:
- `_enumerate_artifacts` - Use `is_external_artifact(item, artifact_type)`
- `_build_index_for_type` - Use imported constants

Location: `src/artifact_ordering.py`

### Step 8: Update test imports

Update test files to import from the correct locations:
- `tests/test_task_utils.py` - update imports for moved functions
- Any other tests that import these functions

Location: `tests/test_task_utils.py`

### Step 9: Update GOAL.md with code_paths

Add the files we touched to the chunk's GOAL.md frontmatter:
- `src/external_refs.py`
- `src/task_utils.py`
- `src/sync.py`
- `src/external_resolve.py`
- `src/artifact_ordering.py`
- `tests/test_external_refs.py`

Location: `docs/chunks/consolidate_ext_ref_utils/GOAL.md`

### Step 10: Update subsystem documentation

Update `docs/subsystems/workflow_artifacts/OVERVIEW.md`:
- Mark proposed chunk #5 as completed with `chunk_directory: consolidate_ext_ref_utils`
- Add code reference for `src/external_refs.py`
- Update "External References" section to reference the new module

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

### Step 11: Run tests and verify

Run the full test suite to verify:
- All new tests pass
- All existing tests pass (backward compatibility)
- No import errors

```bash
uv run pytest tests/
```

## Dependencies

- **chunk consolidate_ext_refs**: Must be complete (provides `ExternalArtifactRef` model
  and `ArtifactType` enum in `models.py`). Status: ACTIVE ✓

## Risks and Open Questions

1. **Circular imports**: The new `external_refs.py` needs to import `ArtifactType` from
   `models.py`, and `artifact_ordering.py` will import from `external_refs.py`. Need to
   verify no circular import chains are created.

2. **Test organization**: Tests in `test_task_utils.py` currently test `load_external_ref`
   and `create_external_yaml`. Decision: Update imports in test file to use `external_refs`
   directly, or keep tests where they are if the functions are still accessible via
   `task_utils` imports.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->