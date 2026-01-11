<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The current `ve task init` implementation accepts `--external` and `--project` arguments
and stores them directly in `.ve-task.yaml`. The goal is to resolve local directory names
to `org/repo` format by inspecting git remotes before writing to the config.

**Strategy:**
1. Add a new function `get_github_org_repo(path)` to `git_utils.py` that extracts the
   `org/repo` from a git repository's remote URL (typically `origin`)
2. Modify `TaskInit` to resolve local directory paths to `org/repo` format before storing
3. Keep backwards compatibility: if the input already looks like `org/repo`, use it directly

**Key Implementation Details:**

- **Remote URL parsing**: Git remotes can have multiple formats:
  - `https://github.com/org/repo.git`
  - `git@github.com:org/repo.git`
  - `ssh://git@github.com/org/repo.git`
  - We'll extract `org/repo` using regex patterns

- **Worktree support**: The `git config --get remote.origin.url` command works for both
  regular clones and worktrees (worktrees share the parent repo's config)

- **Resolution flow**:
  1. If input contains `/` and looks like `org/repo`, treat as direct reference (existing behavior)
  2. If input is a plain directory name, resolve to filesystem path
  3. Extract `org/repo` from the resolved directory's git remote
  4. Store the resolved `org/repo` in `.ve-task.yaml`

**Building on existing code:**
- `git_utils.py`: Already has `is_git_repository()` - will add `get_github_org_repo()`
- `task_init.py`: Has `_resolve_repo_path()` for directory resolution - will add
  remote-to-org/repo resolution
- `conftest.py`: Has `make_ve_initialized_git_repo()` - will need to add remote setup

Per DEC-004, all file references in documentation use project-root-relative paths.

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The work touches:
- `git_utils.py` - general git utilities, not part of a formal subsystem
- `task_init.py` - task initialization logic, not part of a formal subsystem

## Sequence

### Step 1: Add test helper for git repos with remotes

Update `tests/conftest.py` to add a helper function `make_ve_initialized_git_repo_with_remote()`
that creates a VE-initialized git repo with a configured `origin` remote URL.

This helper is needed because the existing `make_ve_initialized_git_repo()` doesn't set up
any remotes, and we need remotes to test the `org/repo` resolution.

The helper should accept a `remote_url` parameter (e.g., `https://github.com/btaylor/dotter.git`).

Location: `tests/conftest.py`

### Step 2: Write tests for `get_github_org_repo()`

Write tests in `tests/test_git_utils.py` for a new function `get_github_org_repo(path)`:

Test cases:
- HTTPS URL: `https://github.com/org/repo.git` → `org/repo`
- HTTPS URL without .git: `https://github.com/org/repo` → `org/repo`
- SSH URL: `git@github.com:org/repo.git` → `org/repo`
- SSH URL without .git: `git@github.com:org/repo` → `org/repo`
- SSH protocol URL: `ssh://git@github.com/org/repo.git` → `org/repo`
- No remote configured → raises `ValueError`
- Not a git repository → raises `ValueError`
- Works for git worktrees (uses parent repo's remote)

Location: `tests/test_git_utils.py`

### Step 3: Implement `get_github_org_repo()`

Add `get_github_org_repo(path: Path) -> str` to `src/git_utils.py`:

1. Run `git config --get remote.origin.url` to get the remote URL
2. Parse the URL to extract `org/repo` using regex:
   - Pattern for HTTPS: `github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$`
   - Pattern for SSH: `git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$`
3. Return `org/repo` string
4. Raise `ValueError` with clear message if:
   - Path is not a git repository
   - No `origin` remote is configured
   - Remote URL doesn't match expected patterns

Location: `src/git_utils.py`

### Step 4: Write tests for local path resolution in TaskInit

Add tests to `tests/test_task_init.py` for the new resolution behavior:

Test cases:
- Plain directory name (`dotter`) resolves to `org/repo` from its git remote
- Existing `org/repo` format input is still accepted (backwards compatibility)
- Error when directory has no git remote
- Works with git worktrees
- Multiple projects all get resolved correctly

Location: `tests/test_task_init.py`

### Step 5: Add `_resolve_to_org_repo()` function to TaskInit

Add a private function `_resolve_to_org_repo(cwd: Path, repo_ref: str) -> str` to
`src/task_init.py` that:

1. First resolves the directory path using existing `_resolve_repo_path()`
2. If the path exists and is a git repo, extracts `org/repo` from its remote
3. Returns the `org/repo` string

This function bridges directory resolution and git remote inspection.

Location: `src/task_init.py`

### Step 6: Update TaskInit to use resolved org/repo values

Modify `TaskInit` class in `src/task_init.py`:

1. In `__init__` or a new method, resolve all inputs to `org/repo` format:
   - For `external`: resolve to `org/repo`
   - For each `project`: resolve to `org/repo`
2. Store the resolved values for use in `validate()` and `execute()`
3. Update `validate()` to use resolved paths for validation
4. Update `execute()` to write resolved `org/repo` values to `.ve-task.yaml`

The key insight: we resolve once upfront, then use the resolved values everywhere.

Location: `src/task_init.py`

### Step 7: Update validation error messages

Ensure validation errors show both the original input and what it resolved to
(if resolution succeeded but validation failed), for better user debugging.

Example: "Directory 'dotter' (resolved to btaylor/dotter) is not a Vibe Engineer project"

Location: `src/task_init.py`

### Step 8: Run full test suite

Run `uv run pytest tests/` to ensure:
- All new tests pass
- All existing tests still pass
- No regressions in behavior

## Dependencies

No external dependencies. All required infrastructure already exists:
- `git_utils.py` with `is_git_repository()` function
- `task_init.py` with `_resolve_repo_path()` and `TaskInit` class
- Test helpers in `conftest.py`

## Risks and Open Questions

**Risks:**

1. **Non-GitHub remotes**: The implementation assumes GitHub URLs. Users with GitLab,
   Bitbucket, or self-hosted Git servers won't get automatic resolution. This is
   acceptable for MVP - we can add support for other hosts later if needed.

2. **Multiple remotes**: If a repo has multiple remotes (e.g., `origin` and `upstream`),
   we always use `origin`. This is the common case and matches user expectations.

3. **Remote URL format edge cases**: There may be unusual remote URL formats we haven't
   considered (e.g., local file paths, unusual SSH configurations). The implementation
   should fail gracefully with a clear error message.

**Open Questions:**

1. **What if the user specifies `org/repo` but the directory exists?** Current plan:
   if input contains `/`, treat it as an `org/repo` reference (existing behavior).
   We could alternatively check if it's a directory first and resolve from remote.
   Decision: Keep existing behavior for backwards compatibility.

2. **Should we support non-origin remotes?** Decision: No, stick with `origin` for
   simplicity. Users who need different remotes can specify `org/repo` directly.

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