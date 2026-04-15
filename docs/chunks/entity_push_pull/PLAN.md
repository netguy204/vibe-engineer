

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Three new CLI commands (`ve entity push`, `ve entity pull`, `ve entity set-origin`) plus backing
library functions in `entity_repo.py`. Each command operates on the entity's own git repo at
`.entities/<name>/` — not the parent project's repo.

The library layer (`entity_repo.py`) handles all git subprocess logic and raises clean
`ValueError` / `RuntimeError` exceptions. The CLI layer (`src/cli/entity.py`) converts those
exceptions into `click.ClickException` and prints human-readable output. This mirrors the pattern
established by `attach_entity` / `detach_entity`.

Git operations needed:
- **push**: `git push origin <branch>` — straightforward, capture output for reporting commit count
- **pull**: `git fetch origin` + divergence check (`git rev-list`) + `git merge --ff-only` on clean fast-forward
- **set-origin**: `git remote set-url origin <url>` (or `git remote add origin <url>` if none exists)

TDD per TESTING_PHILOSOPHY.md:
- Write failing tests for each library function first (covering success and error paths)
- Write failing CLI tests (exit codes, output messages, side effects)
- Then implement to make them pass

## Subsystem Considerations

No relevant subsystems documented. This chunk introduces new git operations on entity submodule repos
using the same subprocess-based approach already established in `entity_repo.py` (`_run_git`,
`_run_git_output`). No deviation from existing patterns.

## Sequence

### Step 1: Write failing unit tests for `entity_repo` push/pull/set-origin functions

Create `tests/test_entity_push_pull.py`. Use the `make_entity_origin` helper pattern from
`test_entity_submodule.py` (create entity repo + bare clone as origin) to set up a realistic git
environment. Each test calls the not-yet-existing library functions, verifying they fail before
implementation.

Tests to write:

**push_entity:**
- `test_push_sends_commits_to_origin` — commit a file to the entity repo, call `push_entity`, then
  clone the origin fresh and verify the commit appears
- `test_push_warns_uncommitted_changes_returns_warning` — write an untracked file but don't commit;
  `push_entity` should succeed (push only pushes committed state) but return a warning flag or
  message
- `test_push_raises_if_no_remote` — entity with no remote configured raises `RuntimeError`
- `test_push_raises_if_not_entity_repo` — non-existent path raises `ValueError`

**pull_entity:**
- `test_pull_fast_forward_advances_local_branch` — push a commit from another clone to origin;
  `pull_entity` should apply it so HEAD is updated
- `test_pull_fast_forward_returns_merged_commits` — `pull_entity` result includes the number of new
  commits merged
- `test_pull_already_up_to_date` — no new commits on origin; `pull_entity` reports up-to-date
- `test_pull_diverged_raises_merge_needed` — origin and local have diverged (both have commits the
  other lacks); `pull_entity` raises `MergeNeededError` without modifying local branch
- `test_pull_raises_if_no_remote` — entity with no remote raises `RuntimeError`

**set_entity_origin:**
- `test_set_origin_configures_remote` — after `set_entity_origin`, `git remote get-url origin`
  returns the new URL
- `test_set_origin_replaces_existing_remote` — call twice with different URLs; second URL wins
- `test_set_origin_raises_if_not_entity_repo` — invalid path raises `ValueError`

Location: `tests/test_entity_push_pull.py`

### Step 2: Add `MergeNeededError` to `entity_repo.py`

Define a custom exception class at the top of `entity_repo.py` so the CLI can catch it
specifically and print the correct user-facing message (suggest `ve entity merge`). This is
scaffolding with no meaningful behavior, so no dedicated test needed — it will be exercised by the
pull tests above.

```python
# Chunk: docs/chunks/entity_push_pull - Custom exception for diverged histories
class MergeNeededError(RuntimeError):
    """Raised when pull cannot fast-forward because histories have diverged."""
    pass
```

Location: `src/entity_repo.py`

### Step 3: Implement `push_entity` in `entity_repo.py`

Add the `push_entity` function that:
1. Resolves the entity path: `project_dir / ".entities" / name` if given project+name, or
   accepts a direct entity path. Accept `entity_path: Path` directly (cleaner for tests).
2. Validates the path is an entity repo via `is_entity_repo(entity_path)`.
3. Checks for a configured remote: `git remote get-url origin` — raises `RuntimeError` if absent.
4. Checks for uncommitted changes via `git status --porcelain`. If present, returns a result
   dataclass with `has_uncommitted=True` (warn the caller; don't block the push).
5. Determines current branch: `git rev-parse --abbrev-ref HEAD`.
6. Runs `git push origin <branch>` using `_run_git`.
7. Counts commits pushed: `git rev-list origin/<branch>..HEAD` before push gives the ahead count.
   Capture this before pushing and return it in the result.

Return type — a small dataclass `PushResult(commits_pushed: int, has_uncommitted: bool)`.

```python
# Chunk: docs/chunks/entity_push_pull - Push entity repo to remote origin
def push_entity(entity_path: Path) -> PushResult: ...
```

Location: `src/entity_repo.py`

### Step 4: Implement `pull_entity` in `entity_repo.py`

Add the `pull_entity` function that:
1. Validates entity path via `is_entity_repo`.
2. Checks for a configured remote; raises `RuntimeError` if absent.
3. Runs `git fetch origin` to download remote state.
4. Determines current branch: `git rev-parse --abbrev-ref HEAD`.
5. Checks divergence:
   - `git rev-list HEAD..origin/<branch>` → commits on origin not in local (need to merge in)
   - `git rev-list origin/<branch>..HEAD` → commits in local not on origin (local is ahead)
   - If both are non-empty: raise `MergeNeededError` with a descriptive message
6. If local-only commits (ahead case): report already diverged (raise `MergeNeededError`)
7. If nothing new (up-to-date): return `PullResult(commits_merged=0, up_to_date=True)`
8. If fast-forward possible (origin has new commits, local does not): run
   `git merge --ff-only origin/<branch>` and return `PullResult(commits_merged=N, up_to_date=False)`

Return type — `PullResult(commits_merged: int, up_to_date: bool)`.

```python
# Chunk: docs/chunks/entity_push_pull - Pull entity repo from remote origin
def pull_entity(entity_path: Path) -> PullResult: ...
```

Location: `src/entity_repo.py`

### Step 5: Implement `set_entity_origin` in `entity_repo.py`

Add the `set_entity_origin` function that:
1. Validates entity path via `is_entity_repo`.
2. Checks if a remote named `origin` already exists: `git remote` and check output.
3. If exists: `git remote set-url origin <url>`.
4. If not: `git remote add origin <url>`.
5. Validates the URL is non-empty (basic sanity check; no strict URL format validation — the
   investigation notes local paths and GitHub HTTPS/SSH all need to work).

```python
# Chunk: docs/chunks/entity_push_pull - Set or update entity repo remote origin
def set_entity_origin(entity_path: Path, url: str) -> None: ...
```

Location: `src/entity_repo.py`

### Step 6: Run unit tests — verify they pass

```bash
uv run pytest tests/test_entity_push_pull.py -v
```

All tests from Step 1 should now pass. Fix any implementation issues before moving to CLI.

### Step 7: Write failing CLI integration tests

Create `tests/test_entity_push_pull_cli.py`. Use Click's `CliRunner` to invoke commands via the
`entity` CLI group. Each test should verify exit codes, output content, and side effects.

Tests to write (using the `runner.invoke(entity, [...])` pattern from existing CLI tests):

**`ve entity push <name>`:**
- `test_push_cli_succeeds_reports_commit_count` — attach entity to project, make a commit, run
  `push`, verify exit 0 and output contains number of commits or success message
- `test_push_cli_warns_uncommitted_changes` — push with dirty working tree, verify warning in
  output but still exits 0
- `test_push_cli_error_no_remote` — push entity with no remote, verify exit non-zero and error
  message mentions "remote" or "origin"
- `test_push_cli_error_entity_not_found` — push nonexistent entity, verify exit non-zero

**`ve entity pull <name>`:**
- `test_pull_cli_fast_forward_reports_commits_merged` — push commits to origin from another clone,
  run pull, verify output reports new commits merged
- `test_pull_cli_already_up_to_date` — no new commits, verify output says up-to-date
- `test_pull_cli_diverged_warns_merge_needed` — create diverged history, verify exit non-zero and
  output suggests `ve entity merge`
- `test_pull_cli_error_no_remote` — pull entity with no remote, verify exit non-zero

**`ve entity set-origin <name> <url>`:**
- `test_set_origin_cli_configures_remote` — run set-origin, then check git remote, verify URL set
- `test_set_origin_cli_replaces_existing_remote` — run twice with different URLs, verify second wins
- `test_set_origin_cli_error_entity_not_found` — nonexistent entity, verify exit non-zero

Location: `tests/test_entity_push_pull_cli.py`

### Step 8: Add `push`, `pull`, `set-origin` commands to `src/cli/entity.py`

Add three Click commands to the `entity` group. Follow the exact pattern of `attach` / `detach`:
- `--project-dir` option on each command
- Call `resolve_entity_project_dir`
- Resolve entity path: `project_dir / ".entities" / name`
- Call library function, convert `ValueError` / `RuntimeError` / `MergeNeededError` to
  `click.ClickException`
- Print user-facing output with `click.echo`

**`ve entity push <name>`:**
```python
# Chunk: docs/chunks/entity_push_pull - CLI push command
@entity.command("push")
@click.argument("name")
@click.option("--project-dir", ...)
def push(name: str, project_dir: ...) -> None:
    """Push entity commits to remote origin."""
```
Output:
- If uncommitted changes: `Warning: entity has uncommitted changes — these will not be pushed`
- Success: `Pushed <N> commit(s) to origin` or `Already up to date` (if 0 to push)

**`ve entity pull <name>`:**
```python
# Chunk: docs/chunks/entity_push_pull - CLI pull command
@entity.command("pull")
@click.argument("name")
@click.option("--project-dir", ...)
def pull(name: str, project_dir: ...) -> None:
    """Fetch and merge entity commits from remote origin."""
```
Output:
- Fast-forward: `Merged <N> new commit(s) from origin`
- Up-to-date: `Already up to date`
- `MergeNeededError`: exit non-zero, message: `Histories have diverged. Use 've entity merge' to resolve.`

**`ve entity set-origin <name> <url>`:**
```python
# Chunk: docs/chunks/entity_push_pull - CLI set-origin command
@entity.command("set-origin")
@click.argument("name")
@click.argument("url")
@click.option("--project-dir", ...)
def set_origin(name: str, url: str, project_dir: ...) -> None:
    """Set or update the remote origin URL for an entity."""
```
Output: `Set origin for '<name>' to <url>`

Location: `src/cli/entity.py`

### Step 9: Run CLI tests — verify they pass

```bash
uv run pytest tests/test_entity_push_pull_cli.py -v
```

Fix any issues. Then run the full test suite to catch regressions:

```bash
uv run pytest tests/ -v
```

### Step 10: Update `GOAL.md` `code_paths`

The chunk GOAL.md currently lists:
```yaml
code_paths:
- src/cli/entity.py
- src/entity_repo.py
```

These are correct. Add test paths:
```yaml
code_paths:
- src/cli/entity.py
- src/entity_repo.py
- tests/test_entity_push_pull.py
- tests/test_entity_push_pull_cli.py
```

## Dependencies

- `entity_attach_detach` chunk must be complete (it is — listed in `depends_on`). The
  `attach_entity`, `is_entity_repo`, `_run_git`, `_run_git_output` helpers it provides are
  the foundation this chunk builds on.

## Risks and Open Questions

- **`git push` output parsing**: Git writes push summary to stderr (not stdout). The commit count
  is more reliably computed before push via `git rev-list origin/<branch>..HEAD` than by parsing
  post-push output. This approach avoids parsing fragile git output.

- **Detached HEAD in worktrees**: Per the investigation (H2), entity submodules start in detached
  HEAD when initialized in worktrees. `push_entity` and `pull_entity` get the current branch via
  `git rev-parse --abbrev-ref HEAD` — this returns `HEAD` when detached, which would cause `git
  push origin HEAD` to fail. The plan uses this to detect the detached case and raise a clear error
  (`"Entity is in detached HEAD state — checkout a branch first"`). Worktree HEAD checkout is
  handled by `entity_worktree_support` (a later chunk); this chunk just needs to handle it
  gracefully.

- **Entity path vs project+name**: Library functions accept `entity_path: Path` directly rather
  than `(project_dir, name)`. This is simpler for testing (no need for full project setup) and
  consistent with `is_entity_repo` which also takes a Path. The CLI layer performs the
  `project_dir / ".entities" / name` resolution.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->
