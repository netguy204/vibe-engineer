---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/models.py
- src/task_utils.py
- src/external_refs.py
- src/ve.py
- tests/test_task_chunk_create.py
- tests/test_task_models.py
code_references:
- ref: src/models.py#_require_valid_repo_ref
  implements: Validator for GitHub org/repo format
- ref: src/models.py#TaskConfig
  implements: Model with org/repo format validation for external_artifact_repo and projects
- ref: src/models.py#ExternalArtifactRef
  implements: Unified model for both external.yaml and dependents list (replaced ExternalChunkRef)
- ref: src/models.py#ChunkDependent
  implements: Model for chunk GOAL.md frontmatter with dependents
- ref: src/task_utils.py#resolve_repo_directory
  implements: Resolves org/repo reference to filesystem path
- ref: src/task_utils.py#get_next_chunk_id
  implements: Calculates next sequential chunk ID for a project
- ref: src/external_refs.py#create_external_yaml
  implements: Writes external.yaml in project's chunk directory
- ref: src/task_utils.py#add_dependents_to_chunk
  implements: Updates GOAL.md frontmatter with dependents
- ref: src/task_utils.py#TaskChunkError
  implements: Exception class for user-friendly error messages
- ref: src/task_utils.py#create_task_chunk
  implements: Orchestrator for multi-repo chunk creation
- ref: src/ve.py#_start_task_chunk
  implements: CLI handler for cross-repo mode output
- ref: tests/test_task_chunk_create.py
  implements: Integration tests for task-aware chunk creation
- ref: tests/test_task_models.py
  implements: Unit tests for TaskConfig, ExternalArtifactRef, ChunkDependent
- ref: tests/test_task_utils.py
  implements: Unit tests for task utility functions
narrative: cross_repo_chunks
created_after:
- task_init
---

# Chunk Goal

## Minor Goal

Extend `ve chunk create <short-name>` to support cross-repository work when run from a task directory. This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

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