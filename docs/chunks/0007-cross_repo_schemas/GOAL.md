---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/task_utils.py
  - src/validation.py
  - tests/test_task_models.py
  - tests/test_task_utils.py
  - tests/test_chunks.py
code_references:
  - ref: src/models.py#TaskConfig
    implements: "Schema with external_chunk_repo and projects fields"
  - ref: src/models.py#ExternalChunkRef
    implements: "Schema for chunk references between repos"
  - ref: src/models.py#ChunkDependent
    implements: "Schema for chunk GOAL.md dependents list"
  - ref: src/validation.py#validate_identifier
    implements: "Shared directory name validation"
  - ref: src/task_utils.py#is_task_directory
    implements: "Detects task directory presence"
  - ref: src/task_utils.py#is_external_chunk
    implements: "Detects external chunk presence"
  - ref: src/task_utils.py#load_task_config
    implements: "Loads and validates .ve-task.yaml"
  - ref: src/task_utils.py#load_external_ref
    implements: "Loads and validates external.yaml"
  - ref: tests/test_task_models.py
    implements: "Validation tests for TaskConfig, ExternalChunkRef, ChunkDependent"
  - ref: tests/test_task_utils.py
    implements: "Utility function tests"
  - ref: tests/test_chunks.py
    implements: "Frontmatter dependents parsing tests"
narrative: 0001-cross_repo_chunks
---

# Chunk Goal

## Minor Goal

Introduce Pydantic models and utility functions to support cross-repository chunk management. This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

When engineering work spans multiple repositories, chunks need to live outside any single repo while still maintaining versioning and archaeological properties. This chunk establishes the foundational data models that all subsequent cross-repo functionality depends on.

This chunk defines schemas for:
1. **Task directories** (`.ve-task.yaml`) - coordination points for cross-repo work
2. **External chunk references** (`external.yaml`) - how participating repos point to shared chunks
3. **Extended chunk frontmatter** - the `dependents` field for bidirectional traversal

These schemas enable later chunks to implement task-aware commands (`ve task init`, `ve chunk create`, `ve sync`, etc.) with proper validation.

## Success Criteria

1. **`.ve-task.yaml` schema** is implemented as a Pydantic model with:
   - `external_chunk_repo: str` - directory name of the external chunk repository worktree
   - `projects: list[str]` - list of participating repository worktree directories
   - Validation: non-empty project list, directory names use existing validators (alphanumeric, underscore, hyphen only; no spaces; < 32 chars)

2. **`external.yaml` schema** is implemented as a Pydantic model with:
   - `repo: str` - external chunk repository (URL or org/repo shorthand)
   - `chunk: str` - chunk identifier in the remote repository
   - `track: str` - branch to follow (optional, defaults to `main`)
   - `pinned: str` - SHA at last sync (validated as 7+ character hex string)

3. **Extended chunk GOAL.md frontmatter** supports optional `dependents` field:
   - Each dependent has `repo: str` and `local_chunk: str`
   - Existing chunk frontmatter parsing continues to work for chunks without dependents

4. **Utility functions** are implemented:
   - `is_task_directory(path) -> bool` - detects presence of `.ve-task.yaml`
   - `is_external_chunk(chunk_path) -> bool` - detects presence of `external.yaml` instead of `GOAL.md`
   - `load_task_config(path) -> TaskConfig` - loads and validates `.ve-task.yaml`
   - `load_external_ref(chunk_path) -> ExternalChunkRef` - loads and validates `external.yaml`

5. All models have appropriate docstrings and are exported from `src/models.py`

6. Unit tests validate:
   - Schema validation accepts well-formed data
   - Schema validation rejects malformed data (short SHA < 7 chars, non-hex SHA, empty project list, invalid directory name chars, etc.)
   - `track` defaults to `main` when not provided
   - Utility functions correctly detect task directories and external chunks
