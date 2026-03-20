

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Apply the same project-root resolution pattern used by `orch` and `board` commands (see `board_cursor_root_resolution` and `orch_daemon_root_resolution` chunks). The root cause is that every entity CLI command defaults `--project-dir` to `"."` (CWD) instead of resolving the actual project root. When called from a subdirectory or a different project, the `Entities` instance writes to the wrong `.entities/` directory — journals silently land in a phantom location.

The fix:
1. Change all entity command `--project-dir` options from `default="."` to `default=None`
2. Add a `resolve_entity_project_dir()` helper that delegates to the existing `resolve_project_root()` from `src/board/storage.py`
3. Apply resolution at the top of each command before constructing `Entities`
4. Add a test that verifies journal files exist on disk after shutdown (the core missing assertion)
5. Add a test that verifies resolution from a subdirectory

This follows DEC-002 (git not assumed) — the resolution chain tries `.ve-task.yaml` then `.git` then falls back to CWD, which works in both git and non-git projects.

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write the failing subdirectory test first, then fix the code.

## Subsystem Considerations

No subsystems are directly relevant. The project-root resolution logic lives in `src/board/storage.py` and is reused by convention rather than governed by a subsystem.

## Sequence

### Step 1: Write failing test — journals exist on disk after shutdown

Add a test to `tests/test_entity_shutdown_cli.py` that asserts journal files physically exist in `memories/journal/` after `ve entity shutdown` completes with memories input. The existing `test_shutdown_skips_consolidation_few_memories` test checks CLI output strings but never verifies files on disk — this is the gap.

The test should:
- Create an entity at `tmp_path`
- Run shutdown with 2 memories (below consolidation threshold)
- Assert `len(list(journal_dir.glob("*.md"))) == 2`

This test should pass (it exercises the `--project-dir` happy path). It establishes the assertion pattern for Step 2.

Location: `tests/test_entity_shutdown_cli.py`

### Step 2: Write failing test — shutdown from subdirectory resolves project root

Add a test that creates an entity at the project root (`tmp_path`), then invokes `ve entity shutdown` from a subdirectory of `tmp_path` **without** passing `--project-dir`. This simulates the reported bug: a steward running from a different CWD.

The test should:
- Create an entity at `tmp_path` (the project root)
- Create a `.git` directory at `tmp_path` (so `resolve_project_root` can find it)
- Create a subdirectory `tmp_path / "subdir"`
- Use `monkeypatch.chdir(tmp_path / "subdir")` to change CWD
- Run `ve entity shutdown testbot --memories-file ...` without `--project-dir`
- Assert exit code 0
- Assert journal files exist at `tmp_path / ".entities" / "testbot" / "memories" / "journal"`
- Assert journal files do NOT exist at `tmp_path / "subdir" / ".entities"`

This test will fail because the current code defaults to `"."` which resolves to `subdir/`.

Location: `tests/test_entity_shutdown_cli.py`

### Step 3: Add `resolve_entity_project_dir()` helper

Create a resolution helper in `src/cli/entity.py` following the exact pattern from `src/cli/orch.py::resolve_orch_project_dir()`:

```python
# Chunk: docs/chunks/entity_shutdown_silent_failure - Entity CLI root resolution
def resolve_entity_project_dir(explicit_dir: pathlib.Path | None) -> pathlib.Path:
    """Resolve the project directory for entity commands.

    When --project-dir is not provided (None), walks up from CWD to find
    the project root using the same chain as board/orch commands:
    .ve-task.yaml → .git → CWD fallback.
    """
    from board.storage import resolve_project_root
    return resolve_project_root(explicit_dir)
```

Location: `src/cli/entity.py`

### Step 4: Fix all entity commands to use resolution

Update every entity subcommand in `src/cli/entity.py`:

1. Change `--project-dir` default from `"."` to `None` in all 6 commands: `create`, `list`, `startup`, `recall`, `touch`, `shutdown`
2. Add `project_dir = resolve_entity_project_dir(project_dir)` as the first line of each command function body

Commands affected (line numbers approximate):
- `create` (line 31): `default="."` → `default=None`
- `list` (line 50): `default="."` → `default=None`
- `startup` (line 74): `default="."` → `default=None`
- `recall` (line 97): `default="."` → `default=None`
- `touch` (line 132): `default="."` → `default=None`
- `shutdown` (line 161): `default="."` → `default=None`

Also remove `exists=True` from the `--project-dir` option type for the `default=None` case (Click validates `exists=True` against `None`, so use `exists=True` only when a value is provided — or just drop it since `resolve_project_root` handles non-existent paths).

Location: `src/cli/entity.py`

### Step 5: Verify tests pass

Run the full entity test suite:
```bash
uv run pytest tests/test_entity_shutdown_cli.py tests/test_entity_cli.py -v
```

The failing test from Step 2 should now pass. All existing tests should continue to pass since they explicitly provide `--project-dir`.

### Step 6: Add backreference comment

Add a chunk backreference at the top of the `resolve_entity_project_dir` function and in the module-level comments of `src/cli/entity.py`.

Location: `src/cli/entity.py`

## Risks and Open Questions

- **`exists=True` with `default=None`**: Click's `Path(exists=True)` will reject `None` unless we handle it. The orch commands use `click.Path(exists=True, path_type=pathlib.Path)` with `default=None` and it works because Click only validates when a value is provided. Verify this during implementation.
- **Other entity callers**: If `run_consolidation()` in `src/entity_shutdown.py` is called from contexts other than the CLI (e.g., directly from a skill), those callers already pass an explicit `project_dir` so they are unaffected.
- **Consolidation deletion**: Investigation confirmed consolidation only deletes journals after successful API consolidation — it is NOT the cause of the missing files. The fix is purely in path resolution.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->