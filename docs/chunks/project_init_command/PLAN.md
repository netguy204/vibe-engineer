# Implementation Plan

## Approach

Follow the existing code patterns established in the project:
- CLI commands in `ve.py` as thin wrappers using Click
- Business logic in separate modules (following the `chunks.py` pattern)
- Templates stored in `src/templates/` and accessed via `pathlib`

The init command will be implemented via a new `Project` class in `src/project.py`. The `Project` class represents a vibe engineering project and provides:
- An `init()` method for initialization
- A `chunks` property that returns a `Chunks` instance for the project

This creates a clean hierarchy: `Project` owns project-level concerns, and `Chunks` (accessed via `project.chunks`) handles chunk-specific operations. The CLI commands can instantiate a `Project` and access whatever they need through it.

Per DEC-001, this remains accessible via `uvx` with no additional dependencies beyond what's already declared (jinja2, click).

Per DEC-002, the init command does not assume git - it simply creates directories and files/symlinks in the target project directory.

## Sequence

### Step 1: Create the CLAUDE.md template

Create `src/templates/CLAUDE.md` with content that explains the vibe engineering workflow to agents:
- Purpose of `docs/trunk/` and its documents (GOAL.md, SPEC.md, DECISIONS.md, TESTING_PHILOSOPHY.md)
- The chunks model and `docs/chunks/` directory structure
- How to navigate chunk history and understand implementation decisions
- Available slash commands for chunk management

Location: `src/templates/CLAUDE.md`

### Step 2: Create the Project class

Create `src/project.py` with a `Project` class:
- Constructor takes `project_dir` (Path)
- Stores reference to `template_dir` (same pattern as `chunks.py`)
- Provides a `chunks` property that returns a lazily-instantiated `Chunks` instance
- Will hold initialization methods (added in subsequent steps)

Location: `src/project.py`

### Step 3: Implement trunk document initialization

Add method `_init_trunk()` to Project:
- Creates `docs/trunk/` directory if it doesn't exist
- For each template in `src/templates/trunk/`:
  - If destination file exists, skip it and record as skipped
  - Otherwise, copy the file and record as created
- Returns a result object with created/skipped lists

Location: `src/project.py`

### Step 4: Implement Claude commands setup

Add method `_init_commands()` to Project:
- Creates `.claude/commands/` directory if it doesn't exist
- For each `.md` file in `src/templates/commands/`:
  - If destination symlink/file exists, skip it and record as skipped
  - Otherwise, attempt to create symlink to the template file
  - If symlink fails (Windows without dev mode), fall back to file copy and record warning
- Returns a result object with created/skipped/warnings lists

Location: `src/project.py`

### Step 5: Implement CLAUDE.md creation

Add method `_init_claude_md()` to Project:
- If `CLAUDE.md` exists at project root, skip and record as skipped
- Otherwise, copy from `src/templates/CLAUDE.md` and record as created
- Returns a result object with created/skipped status

Location: `src/project.py`

### Step 6: Implement the orchestrating init method

Add public method `init()` to Project that:
- Calls `_init_trunk()`, `_init_commands()`, `_init_claude_md()` in sequence
- Aggregates all results
- Returns combined result object for the CLI to display

Location: `src/project.py`

### Step 7: Wire up the CLI command

Update the existing `init` command in `ve.py`:
- Accept `--project-dir` option (default: current directory)
- Instantiate `Project` with the project directory
- Call `init()` and display results:
  - Print each created file/directory
  - Print summary of skipped items if any
  - Print warnings if symlink fallback occurred

Location: `src/ve.py`

### Step 8: Manual verification

Test the implementation:
- Run `ve init` in a fresh directory - verify all files created
- Run `ve init` again - verify idempotency (all skipped)
- Verify symlinks in `.claude/commands/` point to correct template locations
- Verify an agent can understand the workflow from reading `CLAUDE.md`

## Risks and Open Questions

- **Symlink behavior on Windows**: The GOAL specifies falling back to copying files if symlinks fail. Need to catch the appropriate exception (`OSError` with `errno.EPERM` or `errno.ENOTSUP`).

- **Template discovery**: Need to reliably find `src/templates/` when running via `uvx`. The existing `chunks.py` uses `pathlib.Path(__file__).parent / "templates"` which should work.

- **CLAUDE.md content quality**: The template needs to be good enough for an uninitiated agent to understand the workflow. May need iteration based on actual agent testing.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->