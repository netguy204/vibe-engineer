# Implementation Plan

## Approach

This chunk introduces **repo cache infrastructure** to enable efficient single-repo mode operations for external chunks, then builds the `ve external resolve` command on top of it.

**Strategy:**
1. Create `src/repo_cache.py` module with cache management functions that clone/fetch external repos to `~/.ve/cache/repos/`
2. Implement the `ve external resolve` command using the same two-mode pattern established in `ve sync` (task directory mode vs single-repo mode)
3. Update `ve sync`'s single-repo mode to use the repo cache instead of transient `git ls-remote` calls

**Patterns we build on:**
- **Task directory detection** from `src/task_utils.py#is_task_directory` and `load_task_config`
- **External ref loading** from `src/task_utils.py#load_external_ref`
- **Git utilities** from `src/git_utils.py` (will extend with cache-aware operations)
- **CLI patterns** from `src/ve.py` including two-mode commands (`sync`), project/chunk filtering, and error handling
- **Test patterns** from `tests/test_sync.py` including task directory fixtures and monkeypatching

**Testing approach per TESTING_PHILOSOPHY.md:**
- Write failing tests first for cache operations and resolve command
- Focus on semantic assertions (file exists, content matches, error raised)
- Test both modes (task directory and single-repo) with appropriate fixtures

## Sequence

### Step 1: Create repo_cache.py with cache infrastructure

Create `src/repo_cache.py` with functions for managing the local repo cache at `~/.ve/cache/repos/`.

**Functions to implement:**

```python
def get_cache_dir() -> Path:
    """Return ~/.ve/cache/repos/, creating if needed."""

def repo_to_cache_path(repo: str) -> Path:
    """Convert org/repo to cache path (~/.ve/cache/repos/org/repo)."""

def ensure_cached(repo: str) -> Path:
    """Clone repo if not cached, fetch if cached. Return path to cached repo."""

def get_file_at_ref(repo: str, ref: str, file_path: str) -> str:
    """Get file content at a specific ref using git show. Fetches if ref not found."""

def resolve_ref(repo: str, ref: str) -> str:
    """Resolve a ref to SHA. Fetches if ref not found locally."""
```

**Key behaviors:**
- Cache location: `~/.ve/cache/repos/{org}/{repo}/`
- `ensure_cached` clones with `git clone --bare` for space efficiency on first access, `git fetch --all` on subsequent access
- `get_file_at_ref` uses `git show {ref}:{path}` on the bare repo
- `resolve_ref` uses `git rev-parse {ref}`, fetches if ref unknown
- All functions raise `ValueError` with clear error messages on failure

Location: `src/repo_cache.py`

### Step 2: Write tests for repo_cache module

Create `tests/test_repo_cache.py` with tests for cache infrastructure.

**Test cases:**
- `test_get_cache_dir_creates_directory` - verifies cache dir is created
- `test_repo_to_cache_path_converts_correctly` - org/repo → path conversion
- `test_ensure_cached_clones_on_first_access` - bare clone created
- `test_ensure_cached_fetches_on_subsequent_access` - fetch runs on existing
- `test_get_file_at_ref_returns_content` - reads file from ref
- `test_get_file_at_ref_fetches_if_ref_missing` - fetches then retries
- `test_get_file_at_ref_error_on_missing_file` - clear error for bad path
- `test_resolve_ref_returns_sha` - resolves branch/tag to SHA
- `test_resolve_ref_fetches_if_unknown` - fetches then retries
- `test_error_on_inaccessible_repo` - clear error when clone fails

Use monkeypatching for `subprocess.run` calls to avoid network access in tests.

Location: `tests/test_repo_cache.py`

### Step 3: Create external_resolve.py module

Create `src/external_resolve.py` with the core resolve logic, separate from CLI.

**Functions to implement:**

```python
@dataclass
class ResolveResult:
    """Result of resolving an external chunk."""
    repo: str
    external_chunk_id: str
    track: str
    resolved_sha: str
    goal_content: str | None
    plan_content: str | None

def resolve_task_directory(
    task_dir: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
    project_filter: str | None = None,
) -> ResolveResult:
    """Resolve external chunk in task directory mode."""

def resolve_single_repo(
    repo_path: Path,
    local_chunk_id: str,
    at_pinned: bool = False,
) -> ResolveResult:
    """Resolve external chunk in single repo mode using cache."""
```

**Task directory mode logic:**
1. If `project_filter` specified, look in that project only; else scan all projects
2. Find chunk directories matching `local_chunk_id` pattern
3. If >1 match and no `project_filter`, raise error for ambiguity
4. Load `external.yaml` from the matched chunk directory
5. Resolve external repo path via `resolve_repo_directory`
6. Determine SHA: if `at_pinned`, use `pinned` from external.yaml; else use HEAD
7. Read GOAL.md and PLAN.md from external chunk directory at that SHA
8. Return `ResolveResult`

**Single repo mode logic:**
1. Find chunk directory `docs/chunks/{local_chunk_id}/`
2. Load `external.yaml`
3. Use repo cache: `ensure_cached(ref.repo)`
4. Determine SHA: if `at_pinned`, use `pinned`; else resolve `ref.track` to SHA
5. Use `get_file_at_ref` to read GOAL.md and PLAN.md
6. Return `ResolveResult`

Location: `src/external_resolve.py`

### Step 4: Write tests for external_resolve module

Create `tests/test_external_resolve.py` with tests for both modes.

**Test cases for task directory mode:**
- `test_resolves_from_local_worktree` - reads from external repo worktree
- `test_at_pinned_reads_historical_state` - uses pinned SHA
- `test_project_filter_selects_correct_project` - disambiguates multi-project
- `test_error_on_ambiguous_chunk` - error when chunk in multiple projects
- `test_error_on_nonexistent_chunk` - clear error for bad chunk ID
- `test_error_on_non_external_chunk` - error if chunk has GOAL.md (not external)

**Test cases for single repo mode:**
- `test_resolves_via_cache` - uses repo cache
- `test_at_pinned_uses_pinned_sha` - respects pinned SHA
- `test_error_when_pinned_null_and_at_pinned` - error if `--at-pinned` but no pinned value
- `test_handles_missing_plan_md` - gracefully handles no PLAN.md

Location: `tests/test_external_resolve.py`

### Step 5: Add `ve external resolve` CLI command

Add the `external` command group and `resolve` subcommand to `src/ve.py`.

**Command signature:**
```
ve external resolve <local-chunk-id> [--at-pinned] [--goal-only] [--plan-only] [--project <name>]
```

**Options:**
- `--at-pinned`: Use pinned SHA instead of current HEAD
- `--goal-only`: Show only GOAL.md content
- `--plan-only`: Show only PLAN.md content
- `--project <name>`: Specify project for disambiguation (task directory only)

**Output format:**
```
External Chunk Reference
========================
Repository: acme/acme-chunks
Chunk: 0001-auth_token_format
Track: main
SHA: a1b2c3d4e5f6...

--- GOAL.md ---
[content]

--- PLAN.md ---
[content]
```

If PLAN.md doesn't exist, show: `--- PLAN.md ---\n(not found)`

**Error handling:**
- Exit 1 with clear message for all error cases from GOAL.md
- `--project` outside task directory: "Error: --project can only be used in task directory context"

Location: `src/ve.py`

### Step 6: Write CLI tests for `ve external resolve`

Create `tests/test_external_resolve_cli.py` with CLI integration tests.

**Test cases:**
- `test_resolve_task_directory_mode` - resolves and displays content
- `test_resolve_single_repo_mode` - resolves via cache
- `test_at_pinned_flag` - shows content at pinned SHA
- `test_goal_only_flag` - shows only GOAL.md
- `test_plan_only_flag` - shows only PLAN.md
- `test_project_filter_in_task_directory` - disambiguates correctly
- `test_project_flag_error_outside_task_directory` - error message
- `test_error_nonexistent_chunk` - exit code 1, clear message
- `test_error_not_external_chunk` - exit code 1, clear message
- `test_error_missing_pinned_with_at_pinned` - exit code 1, clear message

Location: `tests/test_external_resolve_cli.py`

### Step 7: Update `ve sync` single-repo mode to use repo cache

Modify `src/sync.py#sync_single_repo` to use `repo_cache.resolve_ref()` instead of `git_utils.resolve_remote_ref()`.

**Changes:**
1. Import `repo_cache`
2. Replace `resolve_remote_ref(ref.repo, track)` with `repo_cache.resolve_ref(ref.repo, track)`
3. This provides consistent behavior and enables future operations on cached repos

**Benefit:** After this change, single-repo mode benefits from:
- Faster repeated operations (no network round-trip after initial clone)
- Consistent behavior with task directory mode
- Cached repos available for other operations

Location: `src/sync.py`

### Step 8: Update sync tests for cache usage

Update `tests/test_sync.py` to verify single-repo mode uses cache.

**Changes:**
- Update existing tests that mock `resolve_remote_ref` to mock `repo_cache.resolve_ref` instead
- Add test: `test_single_repo_uses_cache` - verifies cache is used

Location: `tests/test_sync.py`

### Step 9: Update GOAL.md code_paths

Update the chunk's frontmatter with the files touched:

```yaml
code_paths:
  - src/repo_cache.py
  - src/external_resolve.py
  - src/sync.py
  - src/ve.py
  - tests/test_repo_cache.py
  - tests/test_external_resolve.py
  - tests/test_external_resolve_cli.py
  - tests/test_sync.py
```

Location: `docs/chunks/0035-external_resolve/GOAL.md`

## Dependencies

- **0007-cross_repo_schemas**: Provides `ExternalChunkRef` model and validators (complete)
- **0008-git_local_utilities**: Provides `get_current_sha`, `resolve_ref` (complete)
- **0034-ve_sync_command**: Establishes patterns for task directory vs single repo mode (complete)

No new external libraries needed. All functionality uses stdlib `subprocess` for git operations.

## Risks and Open Questions

1. **Bare clone vs full clone**: Using `git clone --bare` saves disk space but requires different commands for file access (`git show ref:path` instead of checkout). This is the correct choice for a cache that only needs to read content.

2. **Fetch frequency**: The current design fetches on every `ensure_cached` call if the repo exists. For very frequent operations, this could add latency. However, for typical VE usage (occasional resolve/sync), this is acceptable. Future optimization could add a TTL for fetch freshness.

3. **Cache location**: Using `~/.ve/cache/repos/` follows XDG conventions loosely. On Windows, this might need adjustment, but Python's `Path.home()` handles cross-platform home directory resolution.

4. **Concurrent access**: If multiple processes access the cache simultaneously, git operations should handle this safely (git has internal locking). No explicit locking is implemented.

5. **Error messages**: Git errors can be cryptic. The implementation should catch subprocess errors and translate them to user-friendly messages.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->