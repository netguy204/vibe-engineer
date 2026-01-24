# Implementation Plan

## Approach

Enhance `ve external resolve` to provide agents with everything they need in a single command:
1. The artifact's main content (GOAL.md or OVERVIEW.md) - already exists
2. **The local filesystem path to the artifact** - new
3. **A directory listing of the artifact's contents** - new
4. **Context indication** (task directory vs single repo mode) - new

**Key insight - resolution priority**:

The critical constraint is: always show the latest state, but never destroy user work.

1. **In task mode**: Check if the artifact exists in a local worktree first. If it does,
   use that path directly - even if it has uncommitted changes. The worktree IS the
   source of truth for the user's current work, including work not yet pushed.

2. **Cache fallback**: When using the cache (single repo mode, or artifact not in any
   local worktree), fetch and reset to latest before returning. The cache has no user
   work to preserve.

This two-tier approach handles the "before it's been pushed" case correctly - in task
mode, an agent working on an artifact that hasn't been pushed will see the local
worktree state.

**Resolution flow**:
```
resolve(artifact_id):
    if is_task_directory():
        # Check local worktrees first
        for project in task_config.projects:
            if artifact exists in project worktree:
                return worktree path  # User's local state, possibly uncommitted
        # Not in any worktree - fall through to cache

    # Cache mode: fetch and reset to ensure latest
    ensure_cached_and_updated(repo)
    return cache path
```

**Bare clone → regular clone**: The cache currently uses bare clones (no working tree).
To provide filesystem paths, we need regular clones. The `ensure_cached()` function will
be updated to:
- Clone as regular repo (not `--bare`)
- On subsequent calls: fetch and reset to origin/HEAD to ensure latest

**Testing approach**: Per `docs/trunk/TESTING_PHILOSOPHY.md`:
- Add tests for new output fields (local_path, directory listing, context indicator)
- Test both task directory and single repo modes
- Test edge cases (empty directories, missing secondary files)

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk IMPLEMENTS changes
  to the external resolution capability. The subsystem's invariant 6 ("External resolution
  works in both task and single-repo mode") must be preserved. Since the subsystem is
  DOCUMENTED (not REFACTORING), we update only what's necessary for this chunk's goals.

## Sequence

### Step 1: Update repo_cache.py to use regular clones with fetch+reset

Change the cache from bare clones to regular clones, and ensure it always reflects
the latest remote state.

Location: `src/repo_cache.py`

Changes to `ensure_cached()`:
- For new clones: Use `git clone` (not `--bare`)
- For existing repos: `git fetch --all` then `git reset --hard origin/HEAD`
- Handle migration: If existing cache is a bare clone (has no working tree), delete
  and re-clone. Detect via `git rev-parse --is-bare-repository`.

Add new function:
```python
def get_repo_path(repo: str) -> Path:
    """Return filesystem path to cached repo working tree.

    Does NOT fetch/reset - call ensure_cached() first if you need latest.
    """
    return repo_to_cache_path(repo)
```

Existing `get_file_at_ref()` and `resolve_ref()` continue to work (git commands work
in regular repos too).

Acceptance: `ensure_cached()` creates/updates regular clones; cached repos have
working trees that reflect origin/HEAD.

### Step 2: Add list_directory_at_ref function to repo_cache

Add ability to list files in a directory at a specific ref.

Location: `src/repo_cache.py`

Add new function:
```python
def list_directory_at_ref(repo: str, ref: str, dir_path: str) -> list[str]:
    """List files in a directory at a specific ref using git ls-tree.

    Args:
        repo: Repository identifier in org/repo format
        ref: Git ref (SHA, branch, tag)
        dir_path: Path to the directory within the repository

    Returns:
        List of filenames in the directory (not full paths)

    Raises:
        ValueError: If the directory cannot be listed
    """
```

Implementation uses `git ls-tree --name-only {ref} {dir_path}/` to list contents.

Acceptance: Can list directory contents at any ref in cached repos.

### Step 3: Extend ResolveResult dataclass

Add fields for local path and directory contents.

Location: `src/external_resolve.py`

Changes to `ResolveResult`:
```python
@dataclass
class ResolveResult:
    """Result of resolving an external artifact reference."""
    repo: str
    artifact_type: ArtifactType
    artifact_id: str
    track: str
    resolved_sha: str
    main_content: str | None
    secondary_content: str | None
    local_path: Path | None  # NEW: filesystem path to artifact directory
    directory_contents: list[str] | None  # NEW: files in the artifact directory
    context_mode: str  # NEW: "task_directory" or "single_repo"
```

Acceptance: ResolveResult has new fields; existing code still works.

### Step 4: Update resolve_artifact_task_directory to populate new fields

Populate local_path and directory_contents in task directory mode using the local
worktree directly (no fetch/reset - the worktree is the user's source of truth).

Location: `src/external_resolve.py#resolve_artifact_task_directory`

Changes:
- After resolving `external_artifact_dir`, store it as `local_path`
- List directory contents via `pathlib.Path.iterdir()` on the worktree path
- Set `context_mode="task_directory"`
- Return updated ResolveResult with new fields populated

**Important**: Do NOT fetch or reset the worktree. The user may have uncommitted changes
or work not yet pushed. The worktree represents the user's current state, which is
exactly what agents need when working in task mode.

Acceptance: Task directory resolution includes local path and directory listing from
the actual worktree (including uncommitted files).

### Step 5: Update resolve_artifact_single_repo to populate new fields

Populate local_path and directory_contents in single repo mode. Unlike task mode,
here we MUST fetch+reset to ensure we're showing the latest remote state.

Location: `src/external_resolve.py#resolve_artifact_single_repo`

Changes:
- Call `repo_cache.ensure_cached(ref.repo)` early (this now does fetch+reset)
- Use `repo_cache.get_repo_path(ref.repo)` to get cache path
- Construct `local_path` as `cache_path / "docs" / dir_name / ref.artifact_id`
- List directory contents via `pathlib.Path.iterdir()` on `local_path` (working tree
  is guaranteed current after ensure_cached)
- Set `context_mode="single_repo (via cache)"`
- Return updated ResolveResult with new fields populated

**Important**: The call to `ensure_cached()` guarantees the working tree reflects
origin/HEAD. This is safe because the cache has no user work to preserve - it's
purely a mirror of the remote.

Note: We could also use `repo_cache.list_directory_at_ref()` for directory contents,
but since `ensure_cached()` already updated the working tree, reading from the
filesystem is simpler and faster.

Acceptance: Single repo resolution includes local path and directory listing
reflecting the latest remote state.

### Step 6: Update CLI output format in _display_resolve_result

Enhance the CLI output to match the proposed format in GOAL.md.

Location: `src/ve.py#_display_resolve_result`

Changes to output format:
```
Artifact: {artifact_id} ({artifact_type})
Context: {context_mode} (via external.yaml)
Path: {local_path}
Contents:
  {file1}
  {file2}
  ...

--- {main_file} ---
{main_content}

--- {secondary_file} ---  (if applicable)
{secondary_content}
```

Changes:
- Add "Context:" line showing which mode was used
- Add "Path:" line with the local filesystem path
- Add "Contents:" section with indented file listing
- Preserve existing content output logic (--main-only, --secondary-only flags)

Acceptance: CLI output matches the example in GOAL.md.

### Step 7: Add tests for new output fields

Add tests verifying the new output fields.

Location: `tests/test_external_resolve.py` and `tests/test_external_resolve_cli.py`

New tests in `test_external_resolve.py`:
- `test_resolve_result_includes_local_path_task_mode`: Verify local_path populated in task mode
- `test_resolve_result_includes_local_path_single_repo`: Verify local_path populated in single repo mode
- `test_resolve_result_includes_directory_contents`: Verify directory listing populated
- `test_resolve_result_context_mode`: Verify context_mode field is set correctly
- `test_task_mode_shows_uncommitted_changes`: **Critical** - Create a file in the worktree
  without committing, verify it appears in directory_contents and can be read. This
  validates the two-tier priority (worktree over cache)

New tests in `test_external_resolve_cli.py`:
- `test_output_includes_path`: Verify "Path:" appears in CLI output
- `test_output_includes_directory_listing`: Verify "Contents:" and file list appear
- `test_output_includes_context_indicator`: Verify "Context:" appears

Acceptance: Tests pass and cover new functionality.

### Step 8: Update repo_cache tests

Update tests for the new repo_cache functionality.

Location: `tests/test_repo_cache.py` (create if doesn't exist)

New tests:
- `test_ensure_cached_creates_working_tree`: Verify clones have working trees
- `test_list_directory_at_ref`: Test directory listing function
- `test_get_repo_path`: Test path retrieval

Acceptance: repo_cache tests pass.

### Step 9: Update cross_repo_operations subsystem docs

Document the enhanced resolve output capability.

Location: `docs/subsystems/cross_repo_operations/OVERVIEW.md`

Changes:
- Update "External resolution" scope item to mention path and directory listing
- No invariant changes needed (existing invariant 6 already covers dual-mode resolution)
- Add `src/repo_cache.py#list_directory_at_ref` to code_references if it's a new public API

Acceptance: Subsystem docs reflect new capability.

### Step 10: Run full test suite

Verify all changes work together.

```bash
uv run pytest tests/
```

Fix any regressions or failures.

Acceptance: All tests pass.

---

**BACKREFERENCE COMMENTS**

Files being modified already have appropriate subsystem backreferences:
- `src/external_resolve.py` has `# Subsystem: docs/subsystems/cross_repo_operations`
- `src/repo_cache.py` has `# Subsystem: docs/subsystems/cross_repo_operations`

After implementation, add this chunk backreference to the module docstrings:
- `src/external_resolve.py`: `# Chunk: docs/chunks/external_resolve_enhance`
- `src/repo_cache.py`: `# Chunk: docs/chunks/external_resolve_enhance`

## Risks and Open Questions

1. **Bare clone migration**: Existing bare clones in `~/.ve/cache/repos/` won't have
   working trees. **Mitigation**: Have `ensure_cached()` detect bare clones via
   `git rev-parse --is-bare-repository` and delete+re-clone if needed.

2. **Disk space**: Regular clones use more disk space than bare clones. For small/medium
   repos this is negligible. For very large repos (multi-GB), this could matter.
   **Mitigation**: This is internal caching for developer tooling, not production systems.

3. **Network dependency in single repo mode**: `ensure_cached()` now always fetches,
   meaning single repo mode requires network access. **Mitigation**: This is acceptable -
   the point of single repo mode is to access remote content. If offline access is
   needed, use task directory mode with local worktrees.

4. **Reset destroys local cache changes**: If someone manually modifies the cache
   (unlikely but possible), `git reset --hard` will destroy those changes.
   **Mitigation**: The cache is explicitly internal tooling - users shouldn't modify it.
   Document this if needed.

5. **Context indicator naming**: Using "task_directory" vs "single_repo (via cache)" to
   make it clear to agents which path they're looking at. The cache path is a local
   mirror, while the task directory path is the user's actual work.

6. **Path format**: On Windows, paths use backslashes. The output should use native
   path separators. Python's `Path` handles this automatically.

7. **Two-tier priority correctness**: In task mode, we check worktrees first before
   falling back to cache. This is critical - the worktree may have work not yet pushed.
   **Verification**: Add test case where worktree has uncommitted changes and verify
   those are visible in the resolved content.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
