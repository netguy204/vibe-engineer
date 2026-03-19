

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extract the root resolution logic from `resolve_board_root` in `src/board/storage.py` into a shared `resolve_project_root` utility, then modify all `ve orch` CLI commands to use it instead of defaulting `--project-dir` to `"."`.

The key insight is that `resolve_board_root` already implements the exact resolution chain needed (`.ve-task.yaml` → `.git` → CWD fallback, per DEC-002). Rather than duplicating this, we extract the shared algorithm so both board and orch commands use the same resolution.

The change is primarily in `src/cli/orch.py`: each command's `--project-dir` option currently defaults to `"."` and has `exists=True` validation. We need to change the default to `None` and resolve it at the start of each command handler using the shared utility. When `--project-dir` is explicitly provided, it's used as-is (matching the board pattern).

Testing follows TESTING_PHILOSOPHY.md: we test the shared utility's resolution behavior (unit tests) and verify representative orch CLI commands work from subdirectories (CLI integration tests).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a missing feature in the orchestrator subsystem — CLI root resolution. The subsystem's invariant "CLI commands are thin wrappers around HTTP calls" is preserved; we're fixing how the CLI locates the daemon, not adding business logic to the CLI layer.

## Sequence

### Step 1: Extract `resolve_project_root` into a shared utility

Create a new function `resolve_project_root` in `src/board/storage.py` (alongside the existing helpers `find_git_root` and `find_task_directory`) that contains the core resolution algorithm currently inside `resolve_board_root`. Then refactor `resolve_board_root` to delegate to it.

The new function signature:

```python
# Chunk: docs/chunks/orch_daemon_root_resolution - Shared project root resolution
def resolve_project_root(explicit_root: Path | None = None) -> Path:
    """Resolve the project root for daemon/state file lookup.

    Priority chain:
    1. Explicit root (operator override) — returned as-is
    2. Walk up for .ve-task.yaml — task directory is the root
    3. Walk up for .git — git root is the project root
    4. Fall back to CWD (preserves DEC-002: git not assumed)
    """
```

`resolve_board_root` becomes a thin alias:

```python
def resolve_board_root(explicit_root: Path | None = None) -> Path:
    return resolve_project_root(explicit_root)
```

Location: `src/board/storage.py`

**Why keep it in `board/storage.py`?** The helper functions `find_git_root` and `find_task_directory` (imported from `task.config`) are already here. Moving everything to a new module would be a larger refactor with no immediate payoff. The function name `resolve_project_root` makes it clear this is a general-purpose utility despite its location.

### Step 2: Write failing tests for `resolve_project_root`

Add tests in `tests/test_board_storage.py` (where `resolve_board_root` tests already live) to verify:

1. `resolve_project_root` with an explicit root returns it as-is
2. `resolve_project_root` from a subdirectory with `.ve-task.yaml` ancestor finds the task root
3. `resolve_project_root` from a subdirectory with `.git` ancestor finds the git root
4. `resolve_project_root` with no markers falls back to CWD
5. Task marker takes priority over git marker

These mirror the existing `resolve_board_root` tests but verify the extracted function directly.

Location: `tests/test_board_storage.py`

### Step 3: Make tests pass by implementing `resolve_project_root`

Implement the function per Step 1. Ensure existing `resolve_board_root` tests still pass since it delegates to the new function.

Location: `src/board/storage.py`

### Step 4: Create `resolve_orch_project_dir` helper in `src/cli/orch.py`

Add a small helper at the top of `src/cli/orch.py` that wraps `resolve_project_root` for use by orch commands:

```python
# Chunk: docs/chunks/orch_daemon_root_resolution - Orch CLI root resolution
def resolve_orch_project_dir(explicit_dir: pathlib.Path | None) -> pathlib.Path:
    """Resolve the project directory for orchestrator commands.

    When --project-dir is not provided (None), walks up from CWD to find
    the project root using the same chain as board commands:
    .ve-task.yaml → .git → CWD fallback.
    """
    from board.storage import resolve_project_root
    return resolve_project_root(explicit_dir)
```

Location: `src/cli/orch.py`

### Step 5: Update all `--project-dir` options in orch commands

For every command in `src/cli/orch.py` (26 occurrences), change:

```python
# Before:
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")

# After:
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=None)
```

And at the top of each command handler, add:

```python
project_dir = resolve_orch_project_dir(project_dir)
```

When `--project-dir` is `None` (not provided), `resolve_orch_project_dir` walks up to find the root. When explicitly provided, it's used as-is.

**Note on `exists=True`**: Keep `exists=True` for the explicit case (Click validates the user-provided path). When `default=None`, Click skips validation of the default, which is correct — the resolved path will be validated by the resolution chain itself (it always returns an existing directory).

Location: `src/cli/orch.py`

### Step 6: Write CLI integration tests for orch root resolution

Add a new test file `tests/test_orchestrator_root_resolution.py` that verifies orch commands resolve the daemon from subdirectories. Test representative commands (not all 26 — that would be testing Click plumbing):

1. **`ve orch status` from subdirectory**: Set up a project with `.git` at the root, `cd` into a subdirectory, invoke `orch status`. Verify it looks for daemon state at the git root, not CWD. (This test can mock `get_daemon_status` to verify the correct path is passed.)

2. **`ve orch ps` from subdirectory**: Similar — mock `create_client` to verify it receives the resolved root path.

3. **`ve orch start` from subdirectory**: Mock `start_daemon` and verify the resolved root is passed.

4. **Task directory takes priority**: Set up both `.ve-task.yaml` and `.git`, verify task root is used.

5. **Explicit `--project-dir` overrides resolution**: Provide `--project-dir /some/path`, verify that path is used regardless of CWD.

Location: `tests/test_orchestrator_root_resolution.py`

### Step 7: Update `code_paths` in GOAL.md

Update the chunk's GOAL.md frontmatter with the files touched:

```yaml
code_paths:
  - src/board/storage.py
  - src/cli/orch.py
  - tests/test_board_storage.py
  - tests/test_orchestrator_root_resolution.py
```

## Dependencies

- `board_cursor_root_resolution` chunk (ACTIVE) — shipped the `resolve_board_root` function and helpers (`find_git_root`, `find_task_directory`) that this chunk extracts into a shared utility. No code changes needed in that chunk; we build on its output.

## Risks and Open Questions

- **`exists=True` with `default=None`**: Click's `Path` type with `exists=True` validates that the path exists. When the default is `None`, Click should skip validation (no path to validate). Verified this works with Click's implementation — `None` bypasses type processing. If this causes issues, the fallback is to remove `exists=True` and validate explicitly in the resolution helper.

- **Circular import risk**: `src/cli/orch.py` importing from `src/board/storage.py` creates a new dependency edge. Since both are leaf modules (CLI layer importing from domain layer), this should be safe. The import is deferred (inside the helper function) to avoid import-time cycles.

- **26 command handlers to update**: The mechanical nature of updating all 26 `--project-dir` options is low-risk but tedious. Missing one would leave that command broken from subdirectories. The integration tests in Step 6 cover representative commands; a `grep` check during review can catch any missed occurrences.

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