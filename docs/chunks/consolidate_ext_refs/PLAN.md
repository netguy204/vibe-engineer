<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk performs a refactoring that:

1. **Moves `ArtifactType` from `artifact_ordering.py` to `models.py`** - The enum is
   needed by the new `ExternalArtifactRef` model. Moving it avoids circular imports
   since `models.py` is lower in the import hierarchy.

2. **Creates `ExternalArtifactRef` to replace `ExternalChunkRef`** - The new model
   adds `artifact_type` and renames `chunk` to `artifact_id` to be type-agnostic.

3. **Updates all call sites** - Since no external.yaml files exist yet, this is a
   clean replacement with no backward compatibility concerns.

The approach follows TDD per TESTING_PHILOSOPHY.md: write failing tests first for
the new model validation behavior, then implement the model, then update call sites.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS the
  consolidated external reference model as the first step in resolving the
  "External References Only for Chunks" deviation. The subsystem is in REFACTORING
  status, so opportunistic improvements are appropriate.

## Sequence

### Step 1: Move ArtifactType to models.py

Move the `ArtifactType` StrEnum from `src/artifact_ordering.py` to `src/models.py`.

In `src/models.py`:
- Add the `ArtifactType` enum near the other status enums (after `ChunkStatus`)
- Add backreference comment linking to this chunk

In `src/artifact_ordering.py`:
- Remove the `ArtifactType` class definition
- Add import: `from models import ArtifactType`
- Update the module-level backreference comment to mention this chunk

Location: `src/models.py`, `src/artifact_ordering.py`

### Step 2: Write failing tests for ExternalArtifactRef

Add tests to `tests/test_task_models.py` in a new `TestExternalArtifactRef` class:

- `test_external_artifact_ref_requires_artifact_type` - Rejects missing artifact_type
- `test_external_artifact_ref_rejects_invalid_artifact_type` - Rejects unknown type
- `test_external_artifact_ref_requires_artifact_id` - Rejects missing artifact_id
- `test_external_artifact_ref_rejects_invalid_artifact_id` - Rejects invalid ID format
- `test_external_artifact_ref_valid_chunk` - Accepts valid chunk reference
- `test_external_artifact_ref_valid_narrative` - Accepts valid narrative reference
- `test_external_artifact_ref_valid_investigation` - Accepts valid investigation reference
- `test_external_artifact_ref_valid_subsystem` - Accepts valid subsystem reference

Run tests: `uv run pytest tests/test_task_models.py -v` - tests should fail.

Location: `tests/test_task_models.py`

### Step 3: Implement ExternalArtifactRef model

Create `ExternalArtifactRef` in `src/models.py`:

```python
# Chunk: docs/chunks/consolidate_ext_refs - Generic external artifact reference
class ExternalArtifactRef(BaseModel):
    """Reference to a workflow artifact in another repository.

    Used for external.yaml files that reference artifacts (chunks, narratives,
    investigations, subsystems) in an external repository.
    """

    artifact_type: ArtifactType
    artifact_id: str  # Short name of the referenced artifact
    repo: str  # GitHub-style org/repo format
    track: str | None = None  # Branch to follow (optional)
    pinned: str | None = None  # 40-char SHA (optional)
    created_after: list[str] = []  # Local causal ordering

    # Validators for repo, artifact_id, pinned (same as ExternalChunkRef)
```

Use the same validators as `ExternalChunkRef`:
- `repo` uses `_require_valid_repo_ref()`
- `artifact_id` uses `_require_valid_dir_name()`
- `pinned` validates 40-char hex SHA

Run tests: `uv run pytest tests/test_task_models.py -v` - tests should pass.

Location: `src/models.py`

### Step 4: Remove ExternalChunkRef and update imports

Remove `ExternalChunkRef` from `src/models.py`.

Update `ChunkDependent` to use `ExternalArtifactRef`:
```python
class ChunkDependent(BaseModel):
    dependents: list[ExternalArtifactRef] = []
```

Update `ChunkFrontmatter` to use `ExternalArtifactRef`:
```python
dependents: list[ExternalArtifactRef] = []  # For cross-repo chunks
```

Location: `src/models.py`

### Step 5: Update task_utils.py

Update `src/task_utils.py`:

1. Update import:
   ```python
   from models import TaskConfig, ExternalArtifactRef, ArtifactType
   ```

2. Update `load_external_ref()`:
   - Change return type to `ExternalArtifactRef`
   - Update docstring
   - The function body stays the same (Pydantic handles validation)

3. Update `create_external_yaml()`:
   - Add `artifact_type: ArtifactType` parameter (default `ArtifactType.CHUNK`)
   - Update the data dict to use `artifact_type` and `artifact_id` keys instead of `chunk`

4. Update `create_task_chunk()`:
   - Pass `artifact_type=ArtifactType.CHUNK` to `create_external_yaml()`
   - Update the dependents dict to use `artifact_type` and `artifact_id`

5. Update `list_task_chunks()`:
   - Update the comment about `ExternalArtifactRef` objects

Location: `src/task_utils.py`

### Step 6: Update other imports

Update files that import `ArtifactType` from `artifact_ordering`:

- `src/chunks.py`: Keep import from `artifact_ordering` (re-exports)
- `src/investigations.py`: Keep import from `artifact_ordering`
- `src/subsystems.py`: Keep import from `artifact_ordering`
- `src/narratives.py`: Keep import from `artifact_ordering`
- `src/ve.py`: Keep import from `artifact_ordering`
- `tests/test_artifact_ordering.py`: Keep import from `artifact_ordering`

Note: `artifact_ordering.py` re-exports `ArtifactType` after importing from models,
so existing imports from `artifact_ordering` continue to work.

Location: No changes needed if we re-export from artifact_ordering.

### Step 7: Update tests

Update `tests/test_task_models.py`:
- Remove `TestExternalChunkRef` class (or rename to TestExternalArtifactRef)
- Update imports to use `ExternalArtifactRef`
- Update `TestChunkDependent` to use `ExternalArtifactRef` format

Update `tests/test_task_utils.py`:
- Update imports to use `ExternalArtifactRef`
- Update `test_load_external_ref_*` tests to use new model format
- Update any tests that create external.yaml files

Update `tests/test_chunks.py`:
- Update any tests that use `ExternalChunkRef` in GOAL.md frontmatter

Run full test suite: `uv run pytest tests/ -v`

Location: `tests/test_task_models.py`, `tests/test_task_utils.py`, `tests/test_chunks.py`

### Step 8: Update subsystem documentation

Update `docs/subsystems/workflow_artifacts/OVERVIEW.md`:

1. Update the External References section to mention `ExternalArtifactRef`
2. Add this chunk to the `chunks` frontmatter list
3. Update the code_references to mention the new model

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

## Dependencies

None. This chunk builds on existing infrastructure (models.py, artifact_ordering.py)
without requiring additional setup.

## Risks and Open Questions

- **Circular import risk**: Moving `ArtifactType` to `models.py` should be safe since
  `models.py` doesn't import from `artifact_ordering.py`. Verify by running tests
  after Step 1.

- **Field naming in external.yaml**: The new model uses `artifact_type` and `artifact_id`
  fields. Since no external.yaml files exist yet, this is not a breaking change.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION -->