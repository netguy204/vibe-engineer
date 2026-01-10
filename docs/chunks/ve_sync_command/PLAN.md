<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `ve sync` command updates `pinned` fields in `external.yaml` files to match the current state of external chunk repositories. The implementation follows the existing patterns established by `ve chunk start` (task-aware chunk creation) and leverages the infrastructure from chunks 0007 and 0008.

**Strategy:**
1. Add a new `sync` command to the CLI under the existing `cli` group (not nested under `chunk` or `task`)
2. Create a `sync.py` module with the core sync logic, following the pattern of `task_utils.py`
3. Detect context (task directory vs single repo) similar to how `ve chunk start` does
4. In task directory mode: iterate projects, find `external.yaml` files, use local worktree to resolve current SHA
5. In single repo mode: find `external.yaml` files, use `git ls-remote` to resolve SHA from remote
6. Apply TDD per docs/trunk/TESTING_PHILOSOPHY.md - write failing tests first for each behavioral requirement

**Key Infrastructure (already exists):**
- `TaskConfig` and `ExternalChunkRef` models in `src/models.py` (chunk 0007)
- `get_current_sha()` and `resolve_ref()` in `src/git_utils.py` (chunk 0008)
- `is_task_directory()`, `load_task_config()`, `load_external_ref()` in `src/task_utils.py` (chunk 0010)

**New functionality needed:**
- `git ls-remote` wrapper for single-repo mode (extends git_utils.py)
- Sync logic that finds all `external.yaml` files and updates them
- CLI command with `--dry-run`, `--project`, and `--chunk` options

**Decision references:**
- Per DEC-002 (git not assumed), the command must work outside git repos when in task directory mode (since resolution happens via local worktrees)
- Per DEC-004 (project-root relative paths), all path references use project root

## Subsystem Considerations

No subsystems are relevant to this chunk. The only existing subsystem (`0001-template_system`) handles template rendering, which is not used by the sync command.

## Sequence

### Step 1: Add `resolve_remote_ref()` to git_utils.py

Add a function to resolve a git ref from a remote repository using `git ls-remote`.

**Location:** `src/git_utils.py`

**Function signature:**
```python
def resolve_remote_ref(repo_url: str, ref: str = "HEAD") -> str:
    """Resolve a git ref from a remote repository.

    Args:
        repo_url: The remote repository URL (or org/repo shorthand)
        ref: The ref to resolve (default: "HEAD" for default branch)

    Returns:
        The full 40-character SHA

    Raises:
        ValueError: If the remote is not accessible or ref doesn't exist
    """
```

**Tests first** (`tests/test_git_utils.py`):
- Test that it returns a valid 40-character SHA for a known public repo
- Test that it raises ValueError for an inaccessible remote
- Test that it raises ValueError for a non-existent ref

### Step 2: Add helper functions to sync.py

Create a new module `src/sync.py` with helper functions for the sync operation.

**Location:** `src/sync.py`

**Functions:**

```python
def find_external_refs(project_path: Path) -> list[Path]:
    """Find all external.yaml files in a project's docs/chunks directory."""

def update_external_yaml(external_yaml_path: Path, new_sha: str) -> bool:
    """Update the pinned field in an external.yaml file.

    Returns True if the file was modified, False if already current.
    """

@dataclass
class SyncResult:
    """Result of syncing a single external reference."""
    chunk_id: str
    old_sha: str
    new_sha: str
    updated: bool
    error: str | None = None
```

**Tests first** (`tests/test_sync.py`):
- `find_external_refs`: returns empty list when no external refs exist
- `find_external_refs`: returns paths to all external.yaml files
- `update_external_yaml`: updates pinned when SHA differs
- `update_external_yaml`: returns False when SHA is already current
- `update_external_yaml`: preserves other fields (repo, chunk, track)

### Step 3: Implement task directory sync logic

Add the core sync logic for task directory mode.

**Location:** `src/sync.py`

**Function:**
```python
def sync_task_directory(
    task_dir: Path,
    dry_run: bool = False,
    project_filter: list[str] | None = None,
    chunk_filter: list[str] | None = None,
) -> list[SyncResult]:
    """Sync external references in task directory mode.

    Iterates all projects, finds external.yaml files, resolves current SHA
    from external chunk repo (local worktree), and updates pinned fields.
    """
```

**Tests first:**
- Updates external.yaml files across multiple projects
- Respects `--dry-run` (reports changes without modifying files)
- Respects `--project` filter (only syncs specified projects)
- Respects `--chunk` filter (only syncs specified chunks)
- Returns results indicating what was updated vs already current
- Handles inaccessible external repo with clear error
- Continues processing other refs if one fails (with error in result)

### Step 4: Implement single repo sync logic

Add the sync logic for single repo mode (uses `git ls-remote`).

**Location:** `src/sync.py`

**Function:**
```python
def sync_single_repo(
    repo_path: Path,
    dry_run: bool = False,
    chunk_filter: list[str] | None = None,
) -> list[SyncResult]:
    """Sync external references in single repo mode.

    Finds external.yaml files, uses git ls-remote to resolve current SHA
    from remote repository, and updates pinned fields.
    """
```

**Tests first:**
- Updates external.yaml using SHA from git ls-remote
- Respects `--dry-run`
- Respects `--chunk` filter
- Handles remote resolution failure with clear error
- Continues processing other refs if one fails

### Step 5: Add CLI command

Add the `ve sync` command to the CLI.

**Location:** `src/ve.py`

**Command structure:**
```
ve sync [--dry-run] [--project NAME]... [--chunk ID]...
```

**Options:**
- `--dry-run`: Show what would be updated without making changes
- `--project NAME`: (task directory only) Sync only specified project(s)
- `--chunk ID`: Sync only specified chunk(s)

**Tests first** (`tests/test_sync_cli.py`):
- CLI outputs formatted results (project/repo, chunk ID, old SHA, new SHA, status)
- CLI shows summary count ("Updated X of Y external references")
- CLI dry-run prefix and "would update" language
- CLI error when `--project` used outside task directory
- CLI error when specified `--chunk` doesn't exist or isn't external
- CLI non-zero exit code when errors occurred

### Step 6: Integration tests

Add integration tests that exercise the full flow.

**Location:** `tests/test_sync_integration.py`

**Tests:**
- End-to-end task directory sync (create task dir, external repo, projects, run sync)
- End-to-end single repo sync (create repo, external ref, run sync against public remote)
- Verify YAML serialization is correct (no extra fields, proper formatting)

---

**BACKREFERENCE COMMENTS**

Add `# Chunk: docs/chunks/0034-ve_sync_command - Sync external references` at the module level for `src/sync.py` and at function level for additions to `src/git_utils.py` and `src/ve.py`.

## Dependencies

- **Chunk 0007 (cross_repo_schemas)**: Provides `TaskConfig`, `ExternalChunkRef` models - already complete
- **Chunk 0008 (git_local_utilities)**: Provides `get_current_sha()` - already complete
- **Chunk 0010 (chunk_create_task_aware)**: Provides `is_task_directory()`, `load_task_config()`, `load_external_ref()`, `resolve_repo_directory()` - already complete

No external libraries needed beyond what's already in the project (pydantic, click, pyyaml).

## Risks and Open Questions

1. **`git ls-remote` for org/repo shorthand**: The `repo` field in `external.yaml` uses GitHub-style `org/repo` format (e.g., `acme/chunks-repo`). The `git ls-remote` command needs a full URL. We'll need to expand this to `https://github.com/{org}/{repo}.git` or similar. This may not work for private repos or non-GitHub hosts without additional configuration.

2. **Network dependency in tests**: Testing `git ls-remote` against real remotes introduces network dependencies. Consider:
   - Use a well-known stable public repo (e.g., a small, stable GitHub repo)
   - Mock subprocess calls for most tests, use real network only for integration tests
   - Accept that some tests may be flaky if GitHub is unreachable

3. **Performance for many external refs**: In a large task directory with many projects and many external refs, syncing could be slow. The current design processes refs sequentially. Could parallelize in future if needed, but not in scope for this chunk.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->