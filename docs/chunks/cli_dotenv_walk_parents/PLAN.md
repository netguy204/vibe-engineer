

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Refactor `load_dotenv_from_project_root()` in `src/cli/dotenv_loader.py` to walk up parent directories from the resolved project root until a `.env` file is found or the filesystem root is reached. The function currently checks only the project root; we'll extract a helper `_find_dotenv_walking_parents(start: Path) -> Path | None` that implements the walk, keeping the public API and error-handling semantics identical.

The resolution order (first found wins) naturally gives project-level `.env` precedence over home-directory `.env` because the walk starts at the project root and moves outward. Existing env vars still take precedence via the `key not in os.environ` guard (no change needed there).

Tests follow TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write failing tests first for each success criterion, then implement.

## Subsystem Considerations

No existing subsystems are directly relevant. This chunk modifies a small, self-contained loader module that doesn't touch validation, template rendering, workflow artifacts, or orchestration.

## Sequence

### Step 1: Write failing tests for parent-walking behavior

Add new tests to `tests/test_dotenv_loader.py` that cover each success criterion:

1. **`test_finds_env_in_parent_directory`** — Create a directory tree where `.env` exists in a grandparent but not in the project root. Assert the grandparent's `.env` is loaded.

2. **`test_project_root_env_wins_over_parent`** — Create `.env` in both project root and a parent directory. Assert only the project root's values are used (first-found-wins).

3. **`test_walk_terminates_at_filesystem_root`** — Create a project root with no `.env` anywhere in its ancestry. Assert no error is raised and no variables are set. (Verifies no infinite loop.)

4. **`test_existing_env_vars_still_win`** — Set an env var, create a parent `.env` with the same key. Assert the pre-existing value is preserved (no-override semantics unchanged).

5. **`test_home_dir_env_loaded`** — Simulate a home directory `.env` by creating a nested structure where `.env` only exists at the top. Run from a deeply nested project root. Assert the top-level `.env` is loaded.

All tests should fail initially because the current implementation only checks the project root.

Location: `tests/test_dotenv_loader.py`

### Step 2: Extract `_find_dotenv_walking_parents` helper

Add a private helper function to `src/cli/dotenv_loader.py`:

```python
def _find_dotenv_walking_parents(start: Path) -> Path | None:
    """Walk from start up to filesystem root, return first .env found."""
    current = start.resolve()
    while True:
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:  # filesystem root
            return None
        current = parent
```

This is a pure function with no side effects — easy to reason about and test in isolation.

Location: `src/cli/dotenv_loader.py`

### Step 3: Refactor `load_dotenv_from_project_root` to use the helper

Replace the direct `.env` check in `load_dotenv_from_project_root()` with a call to `_find_dotenv_walking_parents(root)`. The function body changes from:

```python
dotenv_path = Path(root) / ".env"
if not dotenv_path.is_file():
    return
```

to:

```python
dotenv_path = _find_dotenv_walking_parents(Path(root))
if dotenv_path is None:
    return
```

Everything else stays the same: `dotenv_values()`, the `key not in os.environ` guard, and the bare `except Exception` wrapper.

Update the module-level backreference comment to include this chunk:
```python
# Chunk: docs/chunks/cli_dotenv_loading
# Chunk: docs/chunks/cli_dotenv_walk_parents - Walk parent dirs for .env
```

Location: `src/cli/dotenv_loader.py`

### Step 4: Run tests and verify all pass

Run `uv run pytest tests/test_dotenv_loader.py -v` and confirm:
- All new tests pass
- All existing tests still pass (no regressions)

### Step 5: Update `code_paths` in GOAL.md frontmatter

Set `code_paths` in `docs/chunks/cli_dotenv_walk_parents/GOAL.md` to:
```yaml
code_paths:
  - src/cli/dotenv_loader.py
  - tests/test_dotenv_loader.py
```

## Dependencies

- **`cli_dotenv_loading` chunk** (ACTIVE): Provides the existing `load_dotenv_from_project_root()` function and `python-dotenv` dependency that this chunk extends.

## Risks and Open Questions

- **Symlink loops**: `Path.resolve()` on `start` should collapse symlinks, and `parent == current` terminates the walk at `/`. No additional protection needed unless symlinks create cycles that `resolve()` doesn't flatten (unlikely on modern OSes).
- **Permission errors**: `is_file()` on a directory the user can't read may raise `PermissionError`. The existing bare `except Exception` in `load_dotenv_from_project_root` already handles this — the walk will bail out to the silent-return path.
- **Performance**: Walking to `/` adds at most ~20 `stat` calls (typical directory depth). Negligible at CLI startup.

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