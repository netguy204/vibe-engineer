

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `python-dotenv` as a dependency and call `dotenv_values()` early in the CLI
startup to load variables from a `.env` file located at the resolved project
root. The loading uses the existing `resolve_project_root()` function from
`src/board/storage.py` which implements the `.ve-task.yaml` → `.git` → CWD
resolution chain (respecting DEC-002: git not assumed).

The dotenv loading happens in the Click group's callback (the `cli()` function
in `src/cli/__init__.py`), which runs before any subcommand. We use
`dotenv_values()` to read the file and then manually set only variables that
aren't already in `os.environ`, ensuring existing environment variables always
take precedence (no override behavior).

We extract the dotenv loading into a standalone helper function in a new module
`src/cli/dotenv_loader.py` to keep the concern isolated and independently
testable.

Tests follow the project's testing philosophy: unit tests for the loader
function (dotenv parsing, precedence, missing file), and a CLI integration test
to verify end-to-end behavior via Click's CliRunner.

## Sequence

### Step 1: Add `python-dotenv` dependency

Add `python-dotenv>=1.0.0` to the `dependencies` list in `pyproject.toml`.

Location: `pyproject.toml`

### Step 2: Create the dotenv loader helper

Create `src/cli/dotenv_loader.py` with a `load_dotenv_from_project_root()`
function that:

1. Calls `resolve_project_root()` to find the project root
2. Constructs the path `<root>/.env`
3. If the file doesn't exist, returns silently (no error)
4. Reads variables using `dotenv_values(dotenv_path)`
5. For each variable, sets it in `os.environ` only if not already present

The function takes no arguments (uses CWD-based resolution) and returns nothing.
Errors from dotenv parsing should be caught and silently ignored to avoid
breaking CLI startup.

Add a backreference comment: `# Chunk: docs/chunks/cli_dotenv_loading`

Location: `src/cli/dotenv_loader.py`

### Step 3: Wire dotenv loading into CLI startup

Modify the `cli()` Click group in `src/cli/__init__.py` to invoke
`load_dotenv_from_project_root()` in a callback that runs before subcommands.

Convert the `cli` function from a pass-through to one that calls the loader:

```python
@click.group()
def cli():
    """Vibe Engineer"""
    load_dotenv_from_project_root()
```

Location: `src/cli/__init__.py`

### Step 4: Write unit tests for the dotenv loader

Create `tests/test_dotenv_loader.py` with tests:

1. **Loads `.env` from project root** — Create a temp directory with `.git` and
   a `.env` file containing `TEST_VAR=hello`. Call the loader from within that
   directory. Assert `os.environ["TEST_VAR"] == "hello"`. Clean up after.

2. **Existing env vars take precedence** — Set `EXISTING_VAR=original` in
   `os.environ`, create `.env` with `EXISTING_VAR=overridden`. Call loader.
   Assert `os.environ["EXISTING_VAR"] == "original"`.

3. **Missing `.env` is silently ignored** — Create a temp directory with `.git`
   but no `.env`. Call loader. Assert no exception raised.

4. **Works from subdirectory** — Create temp dir with `.git` and `.env` at root.
   `cd` into a subdirectory. Call loader. Assert the variable is loaded (proving
   root resolution walks up).

Each test should use `monkeypatch` to manage `os.environ` changes and CWD
changes, avoiding test pollution.

Location: `tests/test_dotenv_loader.py`

### Step 5: Write CLI integration test

Add a test that invokes a `ve` subcommand via Click's `CliRunner` with a `.env`
file present, verifying the variable is available during command execution. This
can be done by using a simple subcommand that echoes an env var, or by
checking that a command that needs `ANTHROPIC_API_KEY` doesn't fail when the key
is in `.env`.

Location: `tests/test_dotenv_loader.py`

## Dependencies

- `python-dotenv>=1.0.0` — new external dependency for `.env` file parsing
- Existing `resolve_project_root()` in `src/board/storage.py`

## Risks and Open Questions

- **Performance**: `resolve_project_root()` walks up the directory tree on every
  CLI invocation. This is already done by other commands, so the incremental
  cost is just the dotenv file read — negligible.
- **Dotenv format edge cases**: `python-dotenv` handles quoting, multiline
  values, and comments. We rely on its parsing behavior and don't need to
  reimplement.
- **Recursive resolution**: If the project root is different from CWD, the
  `.env` file must be at the project root, not CWD. This is the intended
  behavior per the goal, but may surprise users who expect CWD `.env` loading.

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
