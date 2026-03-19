

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Detect the empty-repo condition early — at daemon startup — and raise a clear, actionable `DaemonError` before the daemon forks. This gives the CLI layer (`src/cli/orch.py`) its normal error-handling path: print the message to stderr and exit 1 with no stack trace.

The detection happens in `src/orchestrator/git_utils.py` via a new `repo_has_commits()` helper, which is called from `start_daemon()` in `src/orchestrator/daemon.py` before the fork. The error message tells the user exactly what to do: make an initial commit.

This approach keeps the fix localised to the orchestrator's git layer and daemon startup, requires no new dependencies, and follows the existing error-propagation pattern (GitError → DaemonError → CLI echo).

## Subsystem Considerations

- **docs/subsystems/orchestrator**: This chunk USES the orchestrator subsystem. The fix adds an early guard to the daemon startup path and a helper to the orchestrator's shared git utilities module. It follows the existing GitError → DaemonError propagation pattern.

## Sequence

### Step 1: Add `repo_has_commits()` to `src/orchestrator/git_utils.py`

Add a new function that checks whether a git repository has any commits:

```python
def repo_has_commits(repo_dir: Path) -> bool:
```

Implementation: Run `git rev-parse HEAD` and return `True` if it succeeds (exit code 0), `False` if it fails. This is the simplest reliable check — `HEAD` only resolves when at least one commit exists.

Location: `src/orchestrator/git_utils.py`, after `get_current_branch()`.

### Step 2: Write failing tests for `repo_has_commits()`

Add tests to `tests/test_git_utils.py` (the existing orchestrator git utils test file doesn't exist — these tests live alongside the non-orchestrator `git_utils` tests, but `repo_has_commits` is in the orchestrator module). Create a small test class in a new file or add to the existing orchestrator worktree test file.

Better: add a new test class in `tests/test_orchestrator_git_utils.py`:

- `test_repo_has_commits_returns_true_after_initial_commit` — create a git repo, make a commit, assert `True`
- `test_repo_has_commits_returns_false_for_empty_repo` — `git init` only, assert `False`

### Step 3: Guard daemon startup against empty repos

In `src/orchestrator/daemon.py`, inside `start_daemon()`, add an early check **before the fork** (after detecting task context, before the fork at line ~418). In single-repo mode only:

```python
if not task_info.is_task_context:
    from orchestrator.git_utils import repo_has_commits
    if not repo_has_commits(project_dir):
        raise DaemonError(
            "Cannot start orchestrator: repository has no commits. "
            "Make an initial commit first (e.g., `git commit --allow-empty -m 'Initial commit'`)."
        )
```

This runs in the parent process, so the error propagates naturally to the CLI layer, which prints it to stderr and exits 1 — no stack trace, no git internals.

### Step 4: Write failing test for daemon empty-repo guard

Add a test to `tests/test_orchestrator_daemon.py` (or a new focused test file if the daemon tests are structured differently):

- `test_start_daemon_raises_on_empty_repo` — create a `git init`-only repo, call `start_daemon()`, assert it raises `DaemonError` with a message containing "no commits" and "initial commit".

This test must NOT require actually forking a daemon — the error should be raised before the fork.

### Step 5: Write a CLI integration test

Add a test to `tests/test_orchestrator_cli.py` or `tests/test_orchestrator_cli_core.py`:

- `test_start_in_empty_repo_shows_actionable_error` — use Click's `CliRunner` to invoke `ve orch start` in an empty git repo. Assert exit code 1, assert the output contains a user-friendly message about making an initial commit, and assert no stack trace / git fatal error in the output.

### Step 6: Update `get_current_branch()` error message (opportunistic)

While we're in `git_utils.py`, improve the error message in `get_current_branch()` to wrap the raw git stderr with a more descriptive message when the failure is specifically due to an empty repo (no HEAD). This provides defense-in-depth if `get_current_branch()` is ever called outside the guarded daemon path:

```python
if result.returncode != 0:
    if "unknown revision" in result.stderr or "bad default revision" in result.stderr:
        raise GitError(
            "Cannot determine current branch: repository has no commits. "
            "Make an initial commit first."
        )
    raise GitError(f"Failed to get current branch: {result.stderr}")
```

### Step 7: Update GOAL.md code_paths

Update `docs/chunks/orch_empty_repo_handling/GOAL.md` frontmatter `code_paths` to list:
- `src/orchestrator/git_utils.py`
- `src/orchestrator/daemon.py`

Add backreference comments to the new/modified functions:
```python
# Chunk: docs/chunks/orch_empty_repo_handling - Empty repo detection
```

## Dependencies

No new dependencies. Uses only `subprocess` (stdlib) and the existing `GitError`/`DaemonError` exception hierarchy.

## Risks and Open Questions

- **Task context mode**: In multi-repo (task context) mode, the base branch is determined per-repo during worktree creation, not at daemon startup. The guard only applies to single-repo mode. An empty repo in a task context would fail later during worktree creation — this is out of scope for this chunk but noted for awareness.
- **Race condition**: Theoretically a user could make an initial commit between the check and the fork. This is harmless — the check is advisory, not a lock.

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