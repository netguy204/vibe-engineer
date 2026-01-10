---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/repo_cache.py
  - src/external_resolve.py
  - src/sync.py
  - src/ve.py
  - tests/test_repo_cache.py
  - tests/test_external_resolve.py
  - tests/test_external_resolve_cli.py
  - tests/test_sync.py
code_references:
  - ref: src/repo_cache.py
    implements: "Repository cache infrastructure for single-repo mode operations"
  - ref: src/repo_cache.py#get_cache_dir
    implements: "Cache location management at ~/.ve/cache/repos/"
  - ref: src/repo_cache.py#ensure_cached
    implements: "Clone repo if not cached, fetch if cached"
  - ref: src/repo_cache.py#get_file_at_ref
    implements: "Read file content at specific git ref using git show"
  - ref: src/repo_cache.py#resolve_ref
    implements: "Resolve git ref to SHA using rev-parse"
  - ref: src/external_resolve.py
    implements: "External chunk resolution logic for both modes"
  - ref: src/external_resolve.py#ResolveResult
    implements: "Result dataclass with repo, chunk ID, track, SHA, and content"
  - ref: src/external_resolve.py#resolve_task_directory
    implements: "Task directory mode resolution using local worktrees"
  - ref: src/external_resolve.py#resolve_single_repo
    implements: "Single repo mode resolution using repo cache"
  - ref: src/sync.py#sync_single_repo
    implements: "Updated to use repo_cache.resolve_ref instead of git ls-remote"
  - ref: src/ve.py#external
    implements: "External command group"
  - ref: src/ve.py#resolve
    implements: "ve external resolve CLI command with --at-pinned, --goal-only, --plan-only, --project options"
  - ref: src/ve.py#_display_resolve_result
    implements: "Output formatting for resolve command"
  - ref: tests/test_repo_cache.py
    implements: "Unit tests for repo cache module"
  - ref: tests/test_external_resolve.py
    implements: "Unit tests for external resolve module"
  - ref: tests/test_external_resolve_cli.py
    implements: "CLI integration tests for ve external resolve"
narrative: 0001-cross_repo_chunks
subsystems: []
created_after: ["0034-ve_sync_command"]
---

# Chunk Goal

## Minor Goal

Implement the `ve external resolve <local-chunk-id>` command to display an external chunk's content, and introduce a local repo cache for single-repo mode operations. This directly advances docs/trunk/GOAL.md's required property: "It must be possible to perform the workflow outside the context of a Git repository."

When working with cross-repo chunks, developers need to see the content of external chunks without manually navigating to the external repository. The `ve external resolve` command reads the `external.yaml` reference, locates the external chunk, and displays its GOAL.md and PLAN.md content.

This chunk also introduces a **repo cache** (`~/.ve/cache/repos/`) that maintains full clones of external repositories. This cache is used by single-repo mode operations (both `ve external resolve` and `ve sync`) instead of transient `git ls-remote` calls. Benefits:
- Faster repeated operations (no network round-trip after initial clone)
- Enables `--at-pinned` to access any historical SHA
- Consistent behavior between task directory and single-repo modes

This chunk builds on:
- **0007-cross_repo_schemas**: Provides `ExternalChunkRef` model and `load_external_ref` utility
- **0008-git_local_utilities**: Provides `get_current_sha` for SHA resolution
- **0034-ve_sync_command**: Establishes patterns for task directory vs single repo mode (will be updated to use cache)

## Success Criteria

1. **Repo cache infrastructure** (`src/repo_cache.py`):

   - **Cache location**: `~/.ve/cache/repos/` with subdirectories named by repo (e.g., `acme/acme-chunks` → `~/.ve/cache/repos/acme/acme-chunks/`)
   - **`ensure_cached(repo: str) -> Path`**: Clone repo if not cached, fetch if cached. Returns path to cached repo.
   - **`get_file_at_ref(repo: str, ref: str, file_path: str) -> str`**: Get file content at a specific ref. Uses `git show ref:path`. If ref is not found locally, fetches first then retries.
   - **`resolve_ref(repo: str, ref: str) -> str`**: Resolve a ref to a SHA. Uses `git rev-parse`. Fetches if ref not found locally.

2. **`ve external resolve <local-chunk-id>` command** is implemented with two operational modes:

   **Task directory mode** (when `.ve-task.yaml` is present):
   - Accept a local chunk ID (e.g., `0002-auth_token_format`) or qualified `project:chunk` format
   - Locate the corresponding `external.yaml` in the appropriate project
   - Resolve the external chunk location in the external chunk repo worktree
   - Display GOAL.md and PLAN.md content from the external chunk directory
   - By default, show content at current HEAD of the external repo

   **Single repo mode** (when no `.ve-task.yaml` is present):
   - Accept a local chunk ID
   - Locate the `external.yaml` in `docs/chunks/<chunk-id>/`
   - Use repo cache to clone/fetch the external repo
   - Display GOAL.md and PLAN.md content from the external chunk

3. **Command-line options**:

   - **`--at-pinned`**: Show content at the SHA recorded in the `pinned` field instead of current HEAD. This enables archaeological queries—seeing what the external chunk looked like when a particular commit was made.

   - **`--goal-only`**: Show only GOAL.md content (skip PLAN.md)

   - **`--plan-only`**: Show only PLAN.md content (skip PLAN.md)

   - **`--project <name>`** (task directory mode only): Specify which project's external reference to use when the same chunk ID exists in multiple projects. Error if used outside task directory context.

4. **Output format** includes metadata and content:
   - Header showing external ref metadata: repo, chunk ID, track branch
   - Shows resolved SHA (current HEAD or pinned SHA if `--at-pinned`)
   - Separator between GOAL.md and PLAN.md sections
   - Clear indication if PLAN.md doesn't exist
   - Markdown content is displayed as-is (no special rendering)

5. **Update `ve sync` single-repo mode** to use repo cache:
   - Replace `git ls-remote` calls with `repo_cache.resolve_ref()`
   - This provides consistent behavior and enables future operations on cached repos

6. **Error handling** is robust:
   - Clear error if local chunk ID doesn't exist
   - Clear error if local chunk is not an external reference (no external.yaml)
   - Clear error if external chunk repo is inaccessible (clone/fetch fails)
   - Clear error if external chunk doesn't exist in the external repo
   - Clear error if `--at-pinned` is used but `pinned` is null
   - Clear error if `--project` is used outside task directory context
   - Clear error if chunk ID is ambiguous (exists in multiple projects) without `--project`

7. **Unit tests** validate:
   - Repo cache: clone on first access, fetch on subsequent access
   - Repo cache: `get_file_at_ref` with existing and missing refs
   - Task directory mode: resolves external chunk from local worktree
   - Single repo mode: resolves external chunk via cache
   - `--at-pinned` shows content at pinned SHA
   - `--goal-only` and `--plan-only` filter output
   - `--project` disambiguates in task directory mode
   - `ve sync` single-repo mode uses cache instead of ls-remote
   - Error cases: non-existent chunk, not an external ref, inaccessible repo
   - Missing PLAN.md is handled gracefully
