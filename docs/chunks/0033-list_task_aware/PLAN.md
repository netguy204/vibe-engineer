# Implementation Plan

## Approach

Follow the pattern established by `ve chunk start` for task-aware operations (chunk 0010). The `list_chunks` command in `src/ve.py` will detect if it's running in a task directory via `is_task_directory()`. If so, it delegates to task-aware logic that operates on the external chunk repository; otherwise, it uses existing single-repo behavior unchanged.

Key patterns from existing code:
- `is_task_directory(path)` and `load_task_config(path)` from `src/task_utils.py`
- `resolve_repo_directory(task_dir, repo_ref)` to map org/repo to filesystem path
- `Chunks` class for listing and parsing chunks in a repository

The implementation will add a new helper function in `task_utils.py` to list chunks with their dependents from the external repo, keeping the CLI command (`src/ve.py`) thin.

Tests follow the existing task-aware testing patterns from `tests/test_task_chunk_create.py`, using the `setup_task_directory` helper to create realistic task directory fixtures.

## Sequence

### Step 1: Write failing tests for task-aware list

Create `tests/test_task_chunk_list.py` with tests that verify:
1. Listing chunks from external repo when in task directory
2. Dependents are displayed for each chunk
3. `--latest` returns implementing chunk from external repo
4. Error handling for inaccessible external repo

Use the `setup_task_directory` helper pattern from `test_task_chunk_create.py`.

Location: `tests/test_task_chunk_list.py`

### Step 2: Add helper function to list task-aware chunks

Create `list_task_chunks(task_dir: Path) -> list[dict]` in `src/task_utils.py` that:
1. Loads task config via `load_task_config()`
2. Resolves external repo path via `resolve_repo_directory()`
3. Creates a `Chunks` instance for the external repo
4. For each chunk, parses frontmatter to get status and dependents
5. Returns a list of dicts with `{name, status, dependents}`

Add backreference comment: `# Chunk: docs/chunks/0033-list_task_aware - Task-aware chunk listing`

Location: `src/task_utils.py`

### Step 3: Add helper to get current task chunk

Create `get_current_task_chunk(task_dir: Path) -> str | None` in `src/task_utils.py` that:
1. Loads task config and resolves external repo
2. Creates a `Chunks` instance for the external repo
3. Returns `chunks.get_current_chunk()` result

This is the task-aware equivalent of `Chunks.get_current_chunk()`.

Location: `src/task_utils.py`

### Step 4: Update list_chunks CLI command

Modify the `list_chunks` function in `src/ve.py` to:
1. Check `is_task_directory(project_dir)` at the start
2. If in task directory, call task-aware helpers instead of single-repo logic
3. Format output to show dependents (indented under each chunk)
4. Handle errors with `TaskChunkError` pattern

The output format for task-aware mode:
```
docs/chunks/0002-auth_validation [IMPLEMENTING]
  dependents: acme/service-a (0005), acme/service-b (0009)
docs/chunks/0001-auth_token [ACTIVE]
  dependents: acme/service-a (0003), acme/service-b (0007)
```

Update backreference comment to include this chunk.

Location: `src/ve.py`

### Step 5: Add tests for single-repo behavior unchanged

Add a test in `tests/test_task_chunk_list.py` that verifies single-repo behavior (outside task directory) remains identical to current implementation.

Location: `tests/test_task_chunk_list.py`

### Step 6: Run full test suite and fix issues

Run `uv run pytest tests/` to verify:
- All new tests pass
- All existing tests still pass
- No regressions in single-repo behavior

## Dependencies

This chunk depends on infrastructure from:
- **Chunk 0007 (cross_repo_schemas)** - `TaskConfig`, `ExternalChunkRef` models
- **Chunk 0008 (git_local_utilities)** - Not directly used, but related infrastructure
- **Chunk 0009 (task_init)** - `.ve-task.yaml` file format
- **Chunk 0010 (chunk_create_task_aware)** - `is_task_directory()`, `load_task_config()`, `resolve_repo_directory()`, `TaskChunkError`

All dependencies are already complete (ACTIVE status).

## Risks and Open Questions

- **Dependents parsing**: Need to parse `dependents` from chunk frontmatter. The existing `parse_chunk_frontmatter()` returns a dict, which should include `dependents` if present. Need to verify the exact YAML structure matches what `ve chunk start` creates.

- **Output format**: The proposed output format shows dependents on an indented line. This is a reasonable UX but differs from the single-repo output. Verify this doesn't break scripts that parse `ve chunk list` output (unlikely since this only applies in task directory context).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->