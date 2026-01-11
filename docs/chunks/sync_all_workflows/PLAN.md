<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the existing sync functionality to iterate over all workflow artifact types instead of just chunks. The key changes are:

1. **Generalize `find_external_refs()`**: Accept an optional `artifact_types` parameter. Default to all types. Use `ARTIFACT_DIR_NAME` from `external_refs.py` to find the correct directory for each type.

2. **Add artifact type to `SyncResult`**: Include `artifact_type` field so output can distinguish between chunk, narrative, investigation, and subsystem syncs.

3. **Update sync functions**: Both `sync_task_directory()` and `sync_single_repo()` will iterate all artifact types, using the generalized finder.

4. **Extend CLI filtering**: Keep `--chunk` for backward compatibility, add `--artifact` option for general filtering by `type:name` pattern.

This builds on the `external_refs.py` utilities created by chunk `consolidate_ext_ref_utils`, using `ARTIFACT_DIR_NAME` and `is_external_artifact()` which already support all artifact types.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the
  subsystem's External Reference Consolidation item #6 ("Extend ve sync to all
  workflow types"). The subsystem is in REFACTORING status, so opportunistic
  improvement applies—we should follow subsystem patterns consistently.

## Sequence

### Step 1: Write failing tests for `find_external_refs` generalization

Add tests to `tests/test_sync.py` verifying:
- `find_external_refs()` finds external.yaml in `docs/narratives/` directories
- `find_external_refs()` finds external.yaml in `docs/investigations/` directories
- `find_external_refs()` finds external.yaml in `docs/subsystems/` directories
- `find_external_refs()` returns all external refs across all artifact types when no filter specified
- `find_external_refs()` can filter by artifact type

Location: `tests/test_sync.py`

### Step 2: Generalize `find_external_refs()` function

Update `find_external_refs()` in `src/sync.py` to:
- Accept optional `artifact_types: list[ArtifactType] | None` parameter (default: all types)
- Import `ARTIFACT_DIR_NAME` from `external_refs.py` to iterate artifact directories
- Use `is_external_artifact()` with the appropriate artifact type for each directory
- Return a list of tuples `(external_yaml_path, artifact_type)` instead of just paths

Location: `src/sync.py`

### Step 3: Write failing tests for `SyncResult` artifact type field

Add tests verifying `SyncResult` includes artifact type:
- `SyncResult.artifact_type` field exists and is populated
- Output displays artifact type prefix (e.g., `narrative:my_narrative`)

Location: `tests/test_sync.py`

### Step 4: Add artifact_type field to SyncResult

Update `SyncResult` dataclass in `src/sync.py`:
- Add `artifact_type: ArtifactType` field
- Rename `chunk_id` to `artifact_id` for clarity (with deprecation path if needed)

Location: `src/sync.py`

### Step 5: Write failing tests for sync functions with all artifact types

Add tests verifying:
- `sync_task_directory()` processes external refs from all artifact type directories
- `sync_single_repo()` processes external refs from all artifact type directories
- Results include appropriate artifact type for each synced reference

Location: `tests/test_sync.py`

### Step 6: Update `sync_task_directory()` to process all artifact types

Modify the function to:
- Call generalized `find_external_refs()` for all artifact types
- Populate `artifact_type` in `SyncResult`
- Update the chunk_id/artifact_id to use format `{artifact_type.value}:{name}` in task dir mode

Location: `src/sync.py`

### Step 7: Update `sync_single_repo()` to process all artifact types

Modify the function to:
- Call generalized `find_external_refs()` for all artifact types
- Populate `artifact_type` in `SyncResult`
- Update the chunk_id/artifact_id to use format `{artifact_type.value}:{name}` in single repo mode

Location: `src/sync.py`

### Step 8: Write failing tests for CLI filtering

Add tests for CLI options:
- `--artifact type:name` filters by artifact type and name
- `--chunk` backward compatibility continues to work (filters to chunk type only)
- Both filters work correctly together

Location: `tests/test_sync_cli.py`

### Step 9: Extend CLI with `--artifact` option

Update `sync` command in `src/ve.py`:
- Add `--artifact` option accepting `type:name` or just `name` patterns
- Keep `--chunk` option for backward compatibility (internally converts to `--artifact chunk:name`)
- Update `_sync_task_directory()` and `_sync_single_repo()` helper functions to pass artifact filters
- Update `_display_sync_results()` to show artifact type in output

Location: `src/ve.py`

### Step 10: Update sync function signatures for artifact filtering

Update both sync functions in `src/sync.py`:
- Replace `chunk_filter` parameter with `artifact_filter: dict[ArtifactType, list[str]] | None`
- Or simpler: accept `artifact_filter: list[tuple[ArtifactType, str]] | None`
- Backward compatibility: if only names provided (no type), match across all types

Location: `src/sync.py`

### Step 11: Run all tests and fix any issues

Run `uv run pytest tests/` to verify:
- All new tests pass
- All existing tests continue to pass
- No regressions in sync behavior

Location: All test files

### Step 12: Update module docstring and add backreferences

Update `src/sync.py`:
- Update module docstring to reflect support for all workflow artifact types
- Add chunk backreference comment for this chunk

Location: `src/sync.py`

## Dependencies

- **consolidate_ext_ref_utils** (complete) - Provides `ARTIFACT_DIR_NAME`, `is_external_artifact()`,
  `load_external_ref()` in `src/external_refs.py`
- **consolidate_ext_refs** (complete) - Provides `ExternalArtifactRef` model with `artifact_type` field

## Risks and Open Questions

- **API backward compatibility**: The `SyncResult.chunk_id` field is used by existing code.
  May need to keep both `chunk_id` (deprecated) and new `artifact_id` field, or use a single
  field with different formatting. Decision: Use `artifact_id` as the primary field name,
  deprecate `chunk_id` if callers exist outside our codebase.

- **CLI option design**: The `--chunk` option exists for filtering. Options considered:
  1. Keep `--chunk` and add `--narrative`, `--investigation`, `--subsystem` separately
  2. Add single `--artifact type:name` option and deprecate `--chunk`
  3. Keep `--chunk` as alias for `--artifact chunk:name`

  Decision: Option 3 - add `--artifact` as the general mechanism, keep `--chunk` for backward
  compatibility as a convenience alias.

- **Return type change for `find_external_refs()`**: Returning tuples instead of just paths
  changes the function signature. All callers within the codebase need updating, but since
  `sync.py` is the only consumer, this is low risk.

## Deviations

<!-- Populated during implementation -->