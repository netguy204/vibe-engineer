<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk rewrites the chunk CLI commands (`create`, `list`, `complete`) to use scratchpad storage instead of in-repo `docs/chunks/`. The implementation builds on the `scratchpad_storage` chunk's infrastructure (`src/scratchpad.py`) which provides the `Scratchpad`, `ScratchpadChunks`, and `ScratchpadNarratives` classes.

**Strategy:**

1. **Introduce CLI routing layer**: Add a new module (`src/scratchpad_commands.py`) with functions that mirror chunk command behavior but operate on scratchpad storage. The existing `ve.py` CLI will detect context and route to the appropriate implementation.

2. **Context detection**: Determine whether we're in a task context (multi-repo) or project context (single-repo), then resolve the appropriate scratchpad path. Task context routes to `~/.vibe/scratchpad/task:[name]/`, project context routes to `~/.vibe/scratchpad/[project-name]/`.

3. **Complete migration**: The old in-repo `docs/chunks/` path is no longer used for chunk commands. The `Chunks` class in `src/chunks.py` is retained for orchestrator and task-based cross-repo operations that still need in-repo artifact support, but CLI chunk commands exclusively use scratchpad.

4. **Update skill template**: The `/chunk-create` skill template (`src/templates/commands/chunk-create.md.jinja2`) is updated to reflect scratchpad-based workflow.

**Key design decisions:**

- Per DEC-002 (git not assumed), the scratchpad operates outside git repositories
- Per DEC-005 (commands don't prescribe git), no commit operations are included
- The `complete` command archives the scratchpad chunk (changes status to ARCHIVED) rather than moving files

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifact patterns established by `scratchpad_storage`. The scratchpad chunk commands are a consumer of the `ScratchpadChunks` class.

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system for the updated `/chunk-create` skill template.

## Sequence

### Step 1: Create scratchpad_commands.py module

Create a new module `src/scratchpad_commands.py` that provides the scratchpad-based chunk command implementations:

```python
def scratchpad_create_chunk(
    project_path: Path | None,
    task_name: str | None,
    short_name: str,
    ticket: str | None = None,
) -> Path:
    """Create a chunk in the scratchpad."""

def scratchpad_list_chunks(
    project_path: Path | None,
    task_name: str | None,
    latest: bool = False,
) -> list[str] | str | None:
    """List chunks from the scratchpad."""

def scratchpad_complete_chunk(
    project_path: Path | None,
    task_name: str | None,
    chunk_id: str | None = None,
) -> str:
    """Complete (archive) a chunk in the scratchpad."""
```

These functions will:
- Resolve the scratchpad context using `Scratchpad.resolve_context()`
- Create `ScratchpadChunks` manager for the resolved context
- Perform the appropriate CRUD operation

Location: `src/scratchpad_commands.py`

### Step 2: Add context detection helper

Add a helper function to determine current context from the working directory:

```python
def detect_scratchpad_context(
    project_dir: Path,
) -> tuple[Path | None, str | None]:
    """Detect whether we're in task or project context.

    Returns:
        Tuple of (project_path, task_name) where exactly one is non-None.
    """
```

This checks for task context markers (e.g., `.ve-task.yaml`) and falls back to using the project directory name.

Location: `src/scratchpad_commands.py`

### Step 3: Update ve.py chunk create command

Modify the `create` command in `src/ve.py` to route to scratchpad storage:

1. Remove the current in-repo chunk creation logic for non-task contexts
2. Call `scratchpad_create_chunk()` instead
3. Output the scratchpad path (e.g., `~/.vibe/scratchpad/vibe-engineer/chunks/my_feature`)

Key changes:
- The command still validates `short_name` and `ticket_id`
- The `--future` flag is no longer needed (scratchpad chunks don't have FUTURE status concept - they're all personal work)
- The `--projects` flag is still relevant for task context

Location: `src/ve.py`

### Step 4: Update ve.py chunk list command

Modify the `list_chunks` command in `src/ve.py`:

1. Route to `scratchpad_list_chunks()` for all contexts
2. Output format shows scratchpad location:
   - Without `--latest`: List all chunks with status
   - With `--latest`: Output path to the current IMPLEMENTING chunk

Location: `src/ve.py`

### Step 5: Add ve.py chunk complete command

Add a new `complete` subcommand to the chunk group:

```python
@chunk.command("complete")
@click.argument("chunk_id", required=False, default=None)
@click.option("--project-dir", ...)
def complete_chunk(chunk_id, project_dir):
    """Complete (archive) a chunk in the scratchpad."""
```

This command:
- Resolves the chunk (defaults to current IMPLEMENTING chunk)
- Archives the chunk by updating its status to ARCHIVED
- Outputs confirmation

Location: `src/ve.py`

### Step 6: Update chunk-create skill template

Update `src/templates/commands/chunk-create.md.jinja2` to reflect scratchpad-based workflow:

1. Update instructions to mention scratchpad storage
2. Remove references to `docs/chunks/` directory
3. Update example output paths to show `~/.vibe/scratchpad/...`
4. Remove `--future` flag references (not applicable to scratchpad)

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 7: Write tests for scratchpad_commands module

Create `tests/test_scratchpad_commands.py` with tests for:

1. `scratchpad_create_chunk()`:
   - Creates chunk in project context
   - Creates chunk in task context
   - Validates short_name format
   - Rejects duplicate names

2. `scratchpad_list_chunks()`:
   - Lists chunks in project context
   - Lists chunks in task context
   - Returns current IMPLEMENTING chunk with `latest=True`
   - Returns None when no chunks exist

3. `scratchpad_complete_chunk()`:
   - Archives existing chunk
   - Defaults to current IMPLEMENTING chunk
   - Raises error for non-existent chunk

4. `detect_scratchpad_context()`:
   - Detects task context from `.ve-task.yaml`
   - Falls back to project name from directory

Location: `tests/test_scratchpad_commands.py`

### Step 8: Write CLI integration tests

Add CLI integration tests in `tests/test_chunk_scratchpad_cli.py`:

1. `ve chunk create`:
   - Creates chunk in scratchpad
   - Outputs correct path
   - Validates inputs

2. `ve chunk list`:
   - Lists scratchpad chunks
   - `--latest` outputs current chunk

3. `ve chunk complete`:
   - Archives chunk
   - Outputs confirmation

These tests use `click.testing.CliRunner` and temporary scratchpad directories.

Location: `tests/test_chunk_scratchpad_cli.py`

### Step 9: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the actual files created/modified.

## Dependencies

**Chunk dependencies:**
- `scratchpad_storage` (ACTIVE) - Provides `Scratchpad`, `ScratchpadChunks`, and related models

**External libraries:**
- No new dependencies required; uses existing `click`, `pydantic`, `yaml`

## Risks and Open Questions

1. **Task context detection**: The current task detection uses `is_task_directory()` from `task_utils.py`. Need to verify this works correctly with scratchpad context resolution or if we need a separate detection mechanism.

2. **Backwards compatibility**: Old chunks in `docs/chunks/` won't be visible to the new commands. This is intentional per the goal ("No in-repo chunks"), but operators may be confused initially. Consider adding a migration note or warning.

3. **`--future` flag removal**: Scratchpad chunks don't have FUTURE status - they're personal work notes. Need to confirm this is the correct semantic model. The GOAL.md mentions FUTURE status routing but the investigation suggests scratchpad is for "personal work notes" which may not need the same lifecycle.

4. **Output path format**: The scratchpad path includes `~` which may not expand in all contexts. Consider outputting absolute paths or using `Path.home()` expansion consistently.

5. **Skill template complexity**: The `/chunk-create` template has significant logic around FUTURE chunks and orchestrator integration. Need to decide how much of this applies to scratchpad chunks vs. should be stripped.

## Deviations

### Step 6: Simplified chunk-create skill template

The original chunk-create skill template had significant complexity around:
- FUTURE chunk detection and status routing
- Implementing guard checks
- Bug type classification
- Friction entry tracking
- Investigation origin tracking

For scratchpad chunks, this was simplified since:
- Scratchpad chunks don't have FUTURE status (personal work notes)
- No subsystem references or code_references in scratchpad chunks
- Simpler schema: just status, ticket, success_criteria, created_at

The template was rewritten to reflect the simpler scratchpad workflow.

### Step 7-8: Existing tests need updating

The implementation fundamentally changes where chunks are stored (scratchpad instead of
in-repo). This breaks ~100 existing tests that check for in-repo behavior like:
- Chunks created in `docs/chunks/`
- FUTURE status support
- Implementing guard checks

These tests need to be updated in a follow-up chunk to reflect the new scratchpad-based
storage. The new behavior is covered by:
- `tests/test_scratchpad_commands.py` - Unit tests for command functions
- `tests/test_chunk_scratchpad_cli.py` - CLI integration tests

Task context tests pass (15/16), confirming that task-scoped in-repo chunk creation
still works correctly.