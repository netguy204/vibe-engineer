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
  - file: src/models.py
    ranges:
      - lines: "16-36"
        implements: "TaskConfig schema with external_chunk_repo and projects fields"
      - lines: "39-55"
        implements: "ExternalChunkRef schema with project and chunk fields"
      - lines: "58-61"
        implements: "ChunkDependent schema with dependents list"
  - file: src/validation.py
    ranges:
      - lines: "6-37"
        implements: "Shared validate_identifier for directory name validation"
  - file: src/task_utils.py
    ranges:
      - lines: "10-12"
        implements: "is_task_directory utility function"
      - lines: "15-22"
        implements: "is_external_chunk utility function"
      - lines: "25-45"
        implements: "load_task_config utility function"
      - lines: "48-68"
        implements: "load_external_ref utility function"
  - file: tests/test_task_models.py
    ranges:
      - lines: "9-64"
        implements: "TaskConfig validation tests"
      - lines: "67-102"
        implements: "ExternalChunkRef validation tests"
      - lines: "105-148"
        implements: "ChunkDependent validation tests"
  - file: tests/test_task_utils.py
    ranges:
      - lines: "12-88"
        implements: "Utility function tests"
  - file: tests/test_chunks.py
    ranges:
      - lines: "97-140"
        implements: "Frontmatter dependents parsing tests"
narrative: 0001-cross_repo_chunks
---

# Chunk Goal

## Minor Goal

Introduce Pydantic models and utility functions to support cross-repository chunk management. This directly advances the trunk GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

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
