<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends the causal ordering system to include external chunk references.
The core insight from the `artifact_sequence_numbering` investigation is that external
chunks store their position in the *external repo's* causal chain in their GOAL.md,
but when referenced locally via `external.yaml`, we need to track their position in
the *local* causal chain separately.

**Strategy:**

1. Add `created_after: list[str]` field to the `ExternalChunkRef` Pydantic model
2. Update `_enumerate_artifacts()` to detect external chunk directories
3. Add a new helper to parse `created_after` from plain YAML (external.yaml)
4. Update `_build_index_for_type()` to include external chunks in ordering
5. Update `create_external_yaml()` to populate `created_after` with current tips
6. Add tests covering external chunk scenarios

**Key files to modify:**
- `src/models.py` - Add `created_after` field to `ExternalChunkRef`
- `src/artifact_ordering.py` - Update enumeration and index building
- `src/task_utils.py` - Update `create_external_yaml()` to set `created_after`
- `tests/test_artifact_ordering.py` - Add external chunk tests

**Pattern alignment:**
- Follow existing `_parse_created_after()` pattern for reading the field
- Use `is_external_chunk()` from `task_utils.py` to detect external refs
- External chunks use "EXTERNAL" pseudo-status for tip eligibility (always eligible)

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS the causal
  ordering system by extending it to handle external chunk references. The subsystem
  documents `ArtifactIndex` and the `created_after` field semantics.

## Sequence

### Step 1: Add `created_after` field to ExternalChunkRef model

Update `src/models.py` to add the `created_after` field to `ExternalChunkRef`:

```python
class ExternalChunkRef(BaseModel):
    repo: str
    chunk: str
    track: str | None = None
    pinned: str | None = None
    created_after: list[str] = []  # Local causal ordering
```

The field defaults to empty list for backward compatibility with existing external.yaml
files that don't have the field.

Location: `src/models.py` (ExternalChunkRef class, ~line 248)

Add backreference:
```python
# Chunk: docs/chunks/external_chunk_causal - Local causal ordering for external refs
```

### Step 2: Add helper to parse created_after from plain YAML

Create `_parse_yaml_created_after()` in `src/artifact_ordering.py` to read
`created_after` from a plain YAML file (not markdown frontmatter):

```python
def _parse_yaml_created_after(file_path: Path) -> list[str]:
    """Parse created_after from a plain YAML file (e.g., external.yaml)."""
    if not file_path.exists():
        return []
    try:
        data = yaml.safe_load(file_path.read_text())
        if not data:
            return []
        created_after = data.get("created_after", [])
        if created_after is None:
            return []
        if isinstance(created_after, str):
            return [created_after]
        if isinstance(created_after, list):
            return created_after
        return []
    except (yaml.YAMLError, OSError):
        return []
```

Location: `src/artifact_ordering.py` (near `_parse_created_after`, ~line 138)

### Step 3: Update `_enumerate_artifacts` to include external chunks

Modify `_enumerate_artifacts()` to also detect directories with `external.yaml`
(when `GOAL.md` doesn't exist). Only applies to chunks (ArtifactType.CHUNK):

```python
def _enumerate_artifacts(artifact_dir: Path, artifact_type: ArtifactType) -> set[str]:
    if not artifact_dir.exists():
        return set()

    main_file = _ARTIFACT_MAIN_FILE[artifact_type]
    result = set()

    for item in artifact_dir.iterdir():
        if not item.is_dir():
            continue
        main_path = item / main_file
        external_path = item / "external.yaml"

        if main_path.exists():
            # Local artifact
            result.add(item.name)
        elif artifact_type == ArtifactType.CHUNK and external_path.exists():
            # External chunk reference
            result.add(item.name)

    return result
```

Location: `src/artifact_ordering.py` (function `_enumerate_artifacts`, ~line 84)

### Step 4: Update `_build_index_for_type` to handle external chunks

Modify `_build_index_for_type()` to:
1. Detect external chunks when reading dependencies
2. Read `created_after` from `external.yaml` for external chunks
3. Treat external chunks as having "EXTERNAL" pseudo-status (always tip-eligible)

The key changes are in the loop that builds the dependency graph:

```python
for artifact_name in artifacts:
    main_path = artifact_dir / artifact_name / main_file
    external_path = artifact_dir / artifact_name / "external.yaml"

    if main_path.exists():
        # Local artifact
        created_after = _parse_created_after(main_path)
        status = _parse_status(main_path)
    elif external_path.exists():
        # External chunk reference
        created_after = _parse_yaml_created_after(external_path)
        status = "EXTERNAL"  # Always tip-eligible
    else:
        # Should not happen given _enumerate_artifacts logic
        created_after = []
        status = None

    deps[artifact_name] = created_after
    statuses[artifact_name] = status
```

For tip eligibility, add "EXTERNAL" to the eligible statuses for chunks:

```python
_TIP_ELIGIBLE_STATUSES: dict[ArtifactType, set[str] | None] = {
    ArtifactType.CHUNK: {"ACTIVE", "IMPLEMENTING", "EXTERNAL"},
    # ... other types unchanged
}
```

Location: `src/artifact_ordering.py` (function `_build_index_for_type`, ~line 279)

### Step 5: Update `get_ancestors` to handle external chunks

The `get_ancestors()` method also needs to handle external chunks when building
the dependency graph:

```python
for name in artifacts:
    main_path = artifact_dir / name / main_file
    external_path = artifact_dir / name / "external.yaml"

    if main_path.exists():
        created_after = _parse_created_after(main_path)
    elif external_path.exists():
        created_after = _parse_yaml_created_after(external_path)
    else:
        created_after = []

    deps[name] = created_after
```

Location: `src/artifact_ordering.py` (function `get_ancestors`, ~line 406)

### Step 6: Update `create_external_yaml` to populate created_after

Modify `create_external_yaml()` in `src/task_utils.py` to:
1. Accept an optional `created_after` parameter
2. Include it in the YAML output

```python
def create_external_yaml(
    project_path: Path,
    short_name: str,
    external_repo_ref: str,
    external_chunk_id: str,
    pinned_sha: str,
    track: str = "main",
    created_after: list[str] | None = None,
) -> Path:
    chunk_dir = project_path / "docs" / "chunks" / short_name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    external_yaml_path = chunk_dir / "external.yaml"
    data = {
        "repo": external_repo_ref,
        "chunk": external_chunk_id,
        "track": track,
        "pinned": pinned_sha,
    }
    if created_after:
        data["created_after"] = created_after

    with open(external_yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return external_yaml_path
```

Location: `src/task_utils.py` (function `create_external_yaml`, ~line 162)

### Step 7: Update `create_task_chunk` to pass current tips

Modify `create_task_chunk()` to find current tips and pass them to
`create_external_yaml()`:

```python
from artifact_ordering import ArtifactIndex, ArtifactType

# ... in create_task_chunk(), before the project loop:

# 5-6. For each project: create external.yaml with causal ordering
for project_ref in config.projects:
    # ... existing path resolution ...

    # Get current tips for this project's causal ordering
    try:
        index = ArtifactIndex(project_path)
        tips = index.find_tips(ArtifactType.CHUNK)
    except Exception:
        tips = []

    # Create external.yaml with created_after
    external_yaml_path = create_external_yaml(
        project_path=project_path,
        short_name=project_chunk_id,
        external_repo_ref=config.external_chunk_repo,
        external_chunk_id=external_chunk_id,
        pinned_sha=pinned_sha,
        created_after=tips,
    )
    # ... rest unchanged
```

Location: `src/task_utils.py` (function `create_task_chunk`, ~line 276)

### Step 8: Add tests for external chunk ordering

Add a new test class `TestExternalChunkOrdering` in `tests/test_artifact_ordering.py`:

```python
class TestExternalChunkOrdering:
    """Tests for external chunk handling in causal ordering."""

    def _create_external_chunk(
        self,
        chunks_dir: Path,
        name: str,
        repo: str = "org/external-repo",
        chunk: str = "external_chunk_name",
        created_after: list[str] | None = None,
    ):
        """Helper to create an external chunk reference."""
        chunk_dir = chunks_dir / name
        chunk_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "repo": repo,
            "chunk": chunk,
            "track": "main",
            "pinned": "a" * 40,
        }
        if created_after:
            data["created_after"] = created_after

        with open(chunk_dir / "external.yaml", "w") as f:
            yaml.dump(data, f)

    def test_external_chunks_included_in_enumeration(self, tmp_path):
        """External chunks are included when enumerating artifacts."""
        ...

    def test_external_chunks_included_in_ordered_list(self, tmp_path):
        """External chunks appear in get_ordered() output."""
        ...

    def test_external_chunk_can_be_tip(self, tmp_path):
        """External chunk with no dependents is identified as tip."""
        ...

    def test_mixed_local_and_external_ordering(self, tmp_path):
        """Local and external chunks are correctly ordered together."""
        ...

    def test_external_chunk_created_after_respected(self, tmp_path):
        """External chunk's created_after field is used for ordering."""
        ...

    def test_staleness_detects_external_yaml_changes(self, tmp_path):
        """Adding/removing external chunks triggers index rebuild."""
        ...

    def test_external_chunks_always_tip_eligible(self, tmp_path):
        """External chunks are always eligible to be tips (no status filtering)."""
        ...
```

Location: `tests/test_artifact_ordering.py` (new class at end of file)

### Step 9: Update tests for task_utils external.yaml creation

Add/update tests in `tests/test_task_utils.py` to verify `created_after` is written:

```python
def test_create_external_yaml_with_created_after(tmp_path):
    """create_external_yaml includes created_after when provided."""
    project_path = tmp_path / "project"
    (project_path / "docs" / "chunks").mkdir(parents=True)

    result = create_external_yaml(
        project_path=project_path,
        short_name="test_chunk",
        external_repo_ref="org/repo",
        external_chunk_id="ext_chunk",
        pinned_sha="a" * 40,
        created_after=["previous_chunk"],
    )

    with open(result) as f:
        data = yaml.safe_load(f)

    assert data["created_after"] == ["previous_chunk"]

def test_create_external_yaml_without_created_after(tmp_path):
    """create_external_yaml omits created_after when not provided."""
    # ... test that created_after key is absent when not provided
```

Location: `tests/test_task_utils.py`

### Step 10: Run tests and verify

1. Run `uv run pytest tests/test_artifact_ordering.py -v`
2. Run `uv run pytest tests/test_task_utils.py -v`
3. Run full test suite: `uv run pytest tests/`

## Dependencies

- Requires `artifact_ordering_index` chunk (implements ArtifactIndex) - already complete
- Requires `created_after_field` chunk (adds field to frontmatter models) - already complete
- Requires `populate_created_after` chunk (sets created_after on artifact creation) - already complete

## Risks and Open Questions

1. **Backward compatibility**: Existing external.yaml files won't have `created_after`.
   The code handles this by defaulting to empty list, which makes them roots in the
   causal graph. This is acceptable - they'll still appear in listings, just won't
   be correctly ordered relative to other chunks.

2. **Performance**: Adding external chunk detection adds an extra file existence check
   per directory. Since this is IO-bound and directories are small (typically <100),
   impact should be negligible.

3. **Status filtering edge case**: External chunks have no status field. The solution
   uses "EXTERNAL" as a pseudo-status that's always tip-eligible. Alternative would
   be to always include external chunks in tips regardless of status filtering.

4. **`ve sync` integration**: The GOAL.md mentions `ve sync` should update `created_after`.
   This is deferred - the current implementation sets `created_after` at creation time.
   Updating on sync would require tracking which tips existed when the reference was
   created vs now, which adds complexity. Can be addressed in a follow-up chunk if needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
