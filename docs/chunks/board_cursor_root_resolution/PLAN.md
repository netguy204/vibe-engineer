

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a `resolve_board_root()` function that automatically determines the correct
project root for cursor storage, then wire it into the three CLI commands that
accept `--project-root` (`watch`, `watch-multi`, `ack`).

The resolution algorithm prioritizes:
1. **Explicit `--project-root` flag** — if the operator provides it, use it as-is (preserves backward compat)
2. **Walk up for `.ve-task.yaml`** — reuse `find_task_directory()` from `src/task/config.py`
3. **Walk up for `.git`** — add a new `find_git_root()` helper (pure filesystem walk, no subprocess — check for `.git` directory/file existence)
4. **Fall back to CWD** — current behavior, preserves DEC-002 (git not assumed)

The key design choice is to make the `--project-root` Click default `None` instead
of `"."`, then resolve `None` into a concrete path via the new function. This means
the `exists=True` constraint on `--project-root` is only validated when the operator
explicitly passes the flag, while automatic resolution handles the common case.

Per DEC-002, git is not assumed — the `.git` walk is a best-effort fallback, and
the CWD fallback ensures the command works outside both task and git contexts.

Tests follow the testing philosophy: TDD with semantic assertions verifying that
cursor files land at the resolved root regardless of CWD.

## Subsystem Considerations

No existing subsystems are directly relevant to this change. The board system is
self-contained and this chunk touches only board CLI/storage code plus a small
utility function. The `cross_repo_operations` subsystem provides `find_task_directory()`
which we reuse but don't modify.

## Sequence

### Step 1: Add `find_git_root()` to `src/board/storage.py`

Add a pure-filesystem function that walks parent directories looking for `.git`
(can be a directory or file — git worktrees use a `.git` file). No subprocess
calls needed; simple path existence check.

```python
def find_git_root(start_path: Path) -> Path | None:
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    if (current / ".git").exists():
        return current
    return None
```

Location: `src/board/storage.py`

### Step 2: Add `resolve_board_root()` to `src/board/storage.py`

This is the core resolution function implementing the priority chain:

1. If `explicit_root` is not None, return it (operator override via `--project-root`)
2. Call `find_task_directory(cwd)` — if found, return that path
3. Call `find_git_root(cwd)` — if found, return that path
4. Return `cwd` (fallback preserves current behavior)

Import `find_task_directory` from `task.config`. The function signature:

```python
def resolve_board_root(explicit_root: Path | None = None) -> Path:
```

Add backreference: `# Chunk: docs/chunks/board_cursor_root_resolution`

Location: `src/board/storage.py`

### Step 3: Write tests for `find_git_root()` and `resolve_board_root()`

Write tests in `tests/test_board_storage.py` that verify:

- `find_git_root()` finds `.git` directory from a subdirectory
- `find_git_root()` finds `.git` file (worktree scenario) from a subdirectory
- `find_git_root()` returns `None` when no `.git` exists in the tree
- `resolve_board_root()` with explicit root returns the explicit root
- `resolve_board_root()` prefers `.ve-task.yaml` over `.git`
- `resolve_board_root()` falls back to `.git` root when no task yaml
- `resolve_board_root()` falls back to CWD when neither marker exists

Use `tmp_path`, `monkeypatch.chdir()` to control CWD, and create `.git`
directories / `.ve-task.yaml` files in the fixture tree.

Location: `tests/test_board_storage.py`

### Step 4: Modify CLI commands to use `resolve_board_root()`

For each of the three commands (`watch_cmd`, `watch_multi_cmd`, `ack_cmd`):

1. Change `--project-root` default from `"."` to `None` and remove `exists=True`
   (auto-resolved paths don't need Click's exists check; the function handles it)
2. At the top of the command body, call `resolve_board_root(project_root)` to
   get the resolved path
3. Use the resolved path for all subsequent `load_cursor()` / `save_cursor()` calls

The type annotation on the parameter changes from `Path` to `Path | None`.

Add backreference: `# Chunk: docs/chunks/board_cursor_root_resolution`

Location: `src/cli/board.py`

### Step 5: Add import of `resolve_board_root` to `src/cli/board.py`

Add `resolve_board_root` to the existing imports from `board.storage`.

Location: `src/cli/board.py`

### Step 6: Write CLI integration tests

Add tests in `tests/test_board_cli.py` that verify the end-to-end behavior:

- `ve board ack <channel>` from a subdirectory writes the cursor to the project
  root's `.ve/board/cursors/` (not the subdirectory's)
- `ve board ack <channel>` with explicit `--project-root` still uses the
  explicit path
- Verify that running ack from both project root and a subdirectory produces
  the same cursor file

These tests use Click's `CliRunner` with `monkeypatch.chdir()` for CWD control,
and set up a git repo fixture (or `.ve-task.yaml`) at the root of `tmp_path`.

Location: `tests/test_board_cli.py`

### Step 7: Update GOAL.md code_paths

Update the chunk's `code_paths` frontmatter to list the files touched:

```yaml
code_paths:
  - src/board/storage.py
  - src/cli/board.py
  - tests/test_board_storage.py
  - tests/test_board_cli.py
```

Location: `docs/chunks/board_cursor_root_resolution/GOAL.md`

## Dependencies

No new dependencies. Uses existing `find_task_directory()` from `src/task/config.py`.

## Risks and Open Questions

- **Removing `exists=True` from `--project-root`**: Currently Click validates the
  path exists when the flag is provided. By changing the default to `None`, we lose
  Click's built-in validation for the explicit-override case. Mitigation: add a
  manual `Path.exists()` check at the top of the command when `project_root` is not
  None, raising `click.BadParameter` if invalid.
- **Circular import risk**: `src/board/storage.py` importing from `src/task/config.py`.
  Both are leaf modules so this should be safe, but worth verifying. If circular,
  use a local import inside `resolve_board_root()`.

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