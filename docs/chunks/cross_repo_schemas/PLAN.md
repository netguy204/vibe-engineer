# Implementation Plan

## Approach

Extend `src/models.py` with new Pydantic models for cross-repository chunk management. These models establish validation schemas for:

1. **TaskConfig** - validates `.ve-task.yaml` files that coordinate cross-repo work
2. **ExternalChunkRef** - validates `external.yaml` files that point to remote chunks
3. **ChunkDependent** - validates entries in the new `dependents` frontmatter field

Build utility functions in a new `src/task_utils.py` module that use these models for detection and loading.

Per DEC-002, we don't assume Git—these schemas work in any directory structure where `.ve-task.yaml` exists at the coordination root.

**Testing approach:** Following `docs/trunk/TESTING_PHILOSOPHY.md`, write failing tests first that assert semantic properties (schema accepts valid data, rejects invalid data, utility functions correctly detect structures).

## Sequence

### Step 1: Write failing tests for TaskConfig schema

Create `tests/test_task_models.py` with tests that will fail until the model exists:

- `test_task_config_valid_minimal` - accepts `{"external_chunk_repo": "chunks", "projects": ["repo1"]}`
- `test_task_config_valid_multiple_projects` - accepts multiple projects in list
- `test_task_config_rejects_empty_projects` - rejects `{"external_chunk_repo": "chunks", "projects": []}`
- `test_task_config_rejects_invalid_dir_chars` - rejects directory names with spaces, special chars
- `test_task_config_rejects_long_dir_name` - rejects directory names >= 32 chars

Location: `tests/test_task_models.py`

### Step 2: Implement TaskConfig Pydantic model

Add to `src/models.py`:

```python
class TaskConfig(BaseModel):
    """Schema for .ve-task.yaml files."""
    external_chunk_repo: str
    projects: list[str]
```

Add validators:
- `projects` must be non-empty
- All directory names (external_chunk_repo and each project) must match pattern `^[a-zA-Z0-9_-]{1,31}$`

Run tests from Step 1 until all pass.

Location: `src/models.py`

### Step 3: Write failing tests for ExternalChunkRef schema

Add to `tests/test_task_models.py`:

- `test_external_ref_valid_full` - accepts `{"repo": "org/repo", "chunk": "0001-feature", "track": "develop", "pinned": "abc1234"}`
- `test_external_ref_valid_minimal` - accepts without `track` (defaults to "main")
- `test_external_ref_default_track_is_main` - verifies default
- `test_external_ref_rejects_short_sha` - rejects `pinned` < 7 chars
- `test_external_ref_rejects_non_hex_sha` - rejects non-hex characters in `pinned`

Location: `tests/test_task_models.py`

### Step 4: Implement ExternalChunkRef Pydantic model

Add to `src/models.py`:

```python
class ExternalChunkRef(BaseModel):
    """Schema for external.yaml files."""
    repo: str
    chunk: str
    track: str = "main"
    pinned: str
```

Add validator:
- `pinned` must be >= 7 chars and match `^[0-9a-fA-F]+$`

Run tests from Step 3 until all pass.

Location: `src/models.py`

### Step 5: Write failing tests for ChunkDependent schema

Add to `tests/test_task_models.py`:

- `test_chunk_dependent_valid` - accepts `{"repo": "other-project", "local_chunk": "0002-integration"}`
- `test_chunk_dependent_missing_repo` - rejects missing `repo`
- `test_chunk_dependent_missing_local_chunk` - rejects missing `local_chunk`

Location: `tests/test_task_models.py`

### Step 6: Implement ChunkDependent Pydantic model

Add to `src/models.py`:

```python
class ChunkDependent(BaseModel):
    """A dependent chunk in another repository."""
    repo: str
    local_chunk: str
```

Run tests from Step 5 until all pass.

Location: `src/models.py`

### Step 7: Write failing tests for utility functions

Create `tests/test_task_utils.py`:

- `test_is_task_directory_true` - returns True when `.ve-task.yaml` exists
- `test_is_task_directory_false` - returns False when `.ve-task.yaml` absent
- `test_is_external_chunk_true` - returns True when `external.yaml` exists (and no GOAL.md)
- `test_is_external_chunk_false_normal_chunk` - returns False when GOAL.md exists
- `test_is_external_chunk_false_empty` - returns False when neither exists
- `test_load_task_config_valid` - loads and returns TaskConfig from valid YAML
- `test_load_task_config_invalid` - raises ValidationError for invalid YAML
- `test_load_task_config_missing` - raises FileNotFoundError when file missing
- `test_load_external_ref_valid` - loads and returns ExternalChunkRef from valid YAML
- `test_load_external_ref_invalid` - raises ValidationError for invalid YAML

Location: `tests/test_task_utils.py`

### Step 8: Implement utility functions

Create `src/task_utils.py`:

```python
def is_task_directory(path: Path) -> bool:
    """Detect presence of .ve-task.yaml."""

def is_external_chunk(chunk_path: Path) -> bool:
    """Detect presence of external.yaml instead of GOAL.md."""

def load_task_config(path: Path) -> TaskConfig:
    """Load and validate .ve-task.yaml."""

def load_external_ref(chunk_path: Path) -> ExternalChunkRef:
    """Load and validate external.yaml."""
```

Run tests from Step 7 until all pass.

Location: `src/task_utils.py`

### Step 9: Verify existing frontmatter parsing handles dependents

Add tests to `tests/test_chunks.py`:

- `test_parse_frontmatter_with_dependents` - existing `parse_chunk_frontmatter` returns dependents field when present
- `test_parse_frontmatter_without_dependents` - existing chunks without dependents continue to work

The existing `parse_chunk_frontmatter` in `src/chunks.py` should already handle this since it returns the raw YAML dict. Verify with tests.

Location: `tests/test_chunks.py`

### Step 10: Export all new models from models.py

Ensure `src/models.py` exports:
- `TaskConfig`
- `ExternalChunkRef`
- `ChunkDependent`

Update `__all__` if present, or verify imports work correctly.

Location: `src/models.py`

## Risks and Open Questions

- **URL validation for `repo` field**: The GOAL.md mentions "URL or org/repo shorthand" but doesn't specify validation rules. This chunk implements the schema without strict URL validation—later chunks can add validation when the sync command needs to interpret these values.

- **SHA validation strictness**: Using `^[0-9a-fA-F]+$` pattern with 7+ char minimum. Git SHAs are 40 chars but abbreviated SHAs (7+) are common. If stricter validation needed, can be adjusted.

## Deviations

<!-- Populate during implementation -->