---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
  - src/models.py
  - src/task_utils.py
  - src/ve.py
  - tests/test_task_chunk_create.py
  - tests/test_task_models.py
code_references:
  - file: src/models.py
    ranges:
      - lines: 18-46
        implements: "_require_valid_repo_ref() validator for GitHub org/repo format"
      - lines: 49-50
        implements: "SHA_PATTERN regex for 40-char hex SHA validation"
      - lines: 53-77
        implements: "TaskConfig model with org/repo format validation for external_chunk_repo and projects"
      - lines: 79-113
        implements: "ExternalChunkRef unified model for both external.yaml and dependents list"
      - lines: 115-118
        implements: "ChunkDependent model for chunk GOAL.md frontmatter with dependents"
  - file: src/task_utils.py
    ranges:
      - lines: 18-58
        implements: "resolve_repo_directory() to resolve org/repo reference to filesystem path"
      - lines: 117-134
        implements: "get_next_chunk_id() to calculate next sequential chunk ID for a project"
      - lines: 137-174
        implements: "create_external_yaml() to write external.yaml in project's chunk directory"
      - lines: 177-214
        implements: "add_dependents_to_chunk() to update GOAL.md frontmatter with dependents"
      - lines: 217-220
        implements: "TaskChunkError exception class for user-friendly error messages"
      - lines: 223-317
        implements: "create_task_chunk() orchestrator for multi-repo chunk creation"
  - file: src/ve.py
    ranges:
      - lines: "11"
        implements: "Import of task-aware functions (is_task_directory, create_task_chunk, TaskChunkError)"
      - lines: 75-78
        implements: "Task directory detection and branching in chunk start command"
      - lines: 98-113
        implements: "_start_task_chunk() CLI handler for cross-repo mode output"
  - file: tests/test_task_chunk_create.py
    ranges:
      - lines: 1-307
        implements: "Integration tests for task-aware chunk creation"
  - file: tests/test_task_models.py
    ranges:
      - lines: 1-195
        implements: "Unit tests for TaskConfig, ExternalChunkRef, and ChunkDependent models"
  - file: tests/test_task_utils.py
    ranges:
      - lines: 1-382
        implements: "Unit tests for task utility functions"
narrative: 0001-cross_repo_chunks
---

<!--
DO NOT DELETE THIS COMMENT until the chunk complete command is run.
This describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- IMPLEMENTING: This chunk is in the process of being implemented.
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only

PARENT_CHUNK:
- null for new work
- chunk directory name (e.g., "006-segment-compaction") for corrections or modifications

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Populated after implementation, before PR
- Maps specific line ranges to what they implement
- Example:
  code_references:
    - file: src/segment/writer.rs
      ranges:
        - lines: 45-120
          implements: "SegmentWriter struct and core write loop"
        - lines: 122-145
          implements: "fsync durability guarantees"

NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name.
- When setting this field during /chunk-create, also update the narrative's OVERVIEW.md
  frontmatter to add this chunk to its `chunks` array with the prompt and chunk_directory.
-->

# Chunk Goal

## Minor Goal

Extend `ve chunk create <short-name>` to support cross-repository work when run from a task directory. This directly advances the trunk GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

When working in a task directory containing multiple git worktrees, the user needs to create chunks that live in the external chunk repository but are referenced from all participating projects. This chunk enables that workflow with a single command.

This chunk depends on:
- **Chunk 7 (cross_repo_schemas)** - Pydantic models for TaskConfig, ExternalChunkRef, ChunkDependent
- **Chunk 8 (git_local_utilities)** - `get_current_sha()` function for populating `pinned` fields
- **Chunk 9 (task_init)** - `ve task init` command that creates `.ve-task.yaml`

## Success Criteria

### 1. Unified ExternalChunkRef Schema

The `ExternalChunkRef` model is unified to handle both use cases:
- **external.yaml files** in participating repos (with versioning)
- **dependents list** in external chunk GOAL.md frontmatter (without versioning)

All repository references use GitHub's `org/repo` format:

```yaml
# external.yaml example
repo: acme/chunks           # GitHub-style org/repo identifier
chunk: 0001-auth_token      # Chunk ID in the external repo
track: main                 # Branch to follow (defaults to "main")
pinned: a1b2c3d4e5f6...     # SHA at time of creation (full 40-char)
```

```yaml
# dependents list in GOAL.md frontmatter
dependents:
  - repo: acme/service-a
    chunk: 0003-auth_token
  - repo: acme/service-b
    chunk: 0007-auth_token
```

The unified `ExternalChunkRef` model:
- `repo: str` - validates as `org/repo` format (exactly one slash)
- `chunk: str` - validates as directory name (the chunk ID)
- `track: str | None = None` - branch to follow (optional, used in external.yaml)
- `pinned: str | None = None` - validated as 40-character hex SHA (optional, used in external.yaml)

**Directory resolution**: Given `org/repo`, resolve to directory path:
1. First try: `task_dir/{repo}/` (e.g., `task_dir/chunks/`)
2. If not found, try: `task_dir/{org}/{repo}/` (e.g., `task_dir/acme/chunks/`)

### 2. Task-Aware Chunk Creation

When `ve chunk create <short-name>` (or `ve chunk start`) detects it's running from a task directory (via `is_task_directory()`):

1. **Create chunk in external repo**: Use existing `Chunks.create_chunk()` against the external chunk repository path
2. **Add dependents metadata**: After creating the chunk, update its GOAL.md frontmatter to include `dependents` entries for each project
3. **Create external.yaml in each project**: For each project in the task config:
   - Determine next sequential chunk ID for that project
   - Create `docs/chunks/<id>-<short_name>/external.yaml` with:
     - `repo`: external chunk repo identifier (`org/repo` format from task config)
     - `chunk`: the chunk ID created in step 1
     - `track`: "main" (default)
     - `pinned`: current HEAD SHA of the external chunk repo
4. **Report all created paths**: Output each path created (one in external repo, one per project)

### 3. Preserved Single-Repo Behavior

When not in a task directory, `ve chunk create` behaves exactly as before:
- Creates chunk in the current project's `docs/chunks/`
- No external.yaml files are created
- No dependents metadata is added

### 4. Error Handling

- If any project directory is not accessible, fail with clear error
- If external chunk repo is not accessible, fail with clear error
- If SHA resolution fails, fail with clear error
- All errors should indicate which specific operation failed

### 5. Tests

Unit tests validate:
- Task-aware detection works correctly
- External repo chunk creation includes dependents metadata
- External.yaml files have correct content in each project
- Next sequential ID is calculated correctly per project
- Pinned SHA is correctly resolved from external repo HEAD
- Single-repo behavior is unchanged
- Error cases produce helpful messages