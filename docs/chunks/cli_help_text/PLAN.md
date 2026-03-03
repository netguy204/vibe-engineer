<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk improves CLI discoverability through three targeted changes:

1. **Enriched command group help text** - Update `@click.group()` decorators across all CLI modules to include one-sentence concept descriptions.

2. **Actionable "not found" error messages** - Wrap artifact lookup failures with suggestions to run list commands.

3. **Document the `chunk start` alias** - Add "(Aliases: start)" to the create command's help text.

All changes are localized to CLI help strings and error message formatting. No changes to command behavior, validation logic, or core functionality.

Per docs/trunk/TESTING_PHILOSOPHY.md: "We verify help exists, not its exact phrasing" - this chunk doesn't require new tests, but any existing tests must continue to pass.

## Sequence

### Step 1: Enrich command group help text

Update the `@click.group()` decorator docstrings in each CLI module to include concept descriptions:

**src/cli/chunk.py** - Line 44-46:
```python
@click.group()
def chunk():
    """Manage chunks - discrete units of implementation work.

    Chunks are the primary work units in Vibe Engineering, each representing
    a focused piece of implementation with a defined goal and success criteria.
    """
    pass
```

**src/cli/narrative.py** - Line 30-32:
```python
@click.group()
def narrative():
    """Manage narratives - multi-chunk initiatives with upfront decomposition.

    Use narratives when work is too large for a single chunk. They decompose
    big ambitions into ordered chunks with a shared context.
    """
    pass
```

**src/cli/subsystem.py** - Line 31-33:
```python
@click.group()
def subsystem():
    """Manage subsystems - documented architectural patterns.

    Subsystems emerge when you notice recurring patterns across chunks.
    They capture invariants and coordinate related code.
    """
    pass
```

**src/cli/investigation.py** - Line 30-32:
```python
@click.group()
def investigation():
    """Manage investigations - exploratory documents for understanding before acting.

    Start an investigation when you need to explore before committing to
    implementation, such as diagnosing issues or validating hypotheses.
    """
    pass
```

**src/cli/friction.py** - Line 13-15:
```python
@click.group()
def friction():
    """Manage friction log - accumulative ledger for pain points.

    Log friction as you encounter it. When patterns emerge (3+ entries),
    consider creating a chunk or investigation to address them.
    """
    pass
```

**src/cli/task.py** - Line 14-16:
```python
@click.group()
def task():
    """Manage task directories - cross-repository work coordination.

    Task directories enable working across multiple repositories with
    shared artifacts stored in an external repository.
    """
    pass
```

**src/cli/orch.py** - Line 19-21:
```python
@click.group()
def orch():
    """Manage orchestrator - parallel chunk execution across worktrees.

    The orchestrator daemon schedules chunks to run in isolated git worktrees,
    enabling parallel agent work with automatic conflict detection.
    """
    pass
```

**src/cli/reviewer.py** - Line 19-21:
```python
@click.group()
def reviewer():
    """Manage reviewer agent - automated decision tracking and review.

    Reviewer agents evaluate chunk implementations against success criteria.
    Curated decisions provide few-shot examples for future reviews.
    """
    pass
```

### Step 2: Add actionable suggestions to "not found" errors

Create a helper function in `src/cli/utils.py` for formatting artifact-not-found errors with suggestions, then use it in CLI modules:

**src/cli/utils.py** - Add helper function:
```python
def format_not_found_error(
    artifact_type: str,
    artifact_id: str,
    list_command: str | None = None,
) -> str:
    """Format a 'not found' error with actionable suggestion.

    Args:
        artifact_type: The type of artifact (e.g., "Chunk", "Narrative")
        artifact_id: The ID that wasn't found
        list_command: Optional list command to suggest (e.g., "ve chunk list")

    Returns:
        Formatted error message with suggestion
    """
    msg = f"{artifact_type} '{artifact_id}' not found"
    if list_command:
        msg += f". Run `{list_command}` to see available {artifact_type.lower()}s"
    return msg
```

Update key "not found" error sites:

**src/cli/chunk.py** - `complete_chunk()` around line 522:
```python
if chunk_name is None:
    from cli.utils import format_not_found_error
    click.echo(f"Error: {format_not_found_error('Chunk', chunk_id, 've chunk list')}", err=True)
    raise SystemExit(1)
```

**src/cli/chunk.py** - `status()` around line 830:
```python
if resolved_id is None:
    from cli.utils import format_not_found_error
    click.echo(f"Error: {format_not_found_error('Chunk', chunk_id, 've chunk list')}", err=True)
    raise SystemExit(1)
```

**src/cli/narrative.py** - `status()` around line 181:
```python
if fm is None:
    from cli.utils import format_not_found_error
    click.echo(f"Error: {format_not_found_error('Narrative', narrative_id, 've narrative list')}", err=True)
    raise SystemExit(1)
```

**src/cli/subsystem.py** - `validate()` around line 167:
```python
if frontmatter is None:
    from cli.utils import format_not_found_error
    click.echo(f"Error: {format_not_found_error('Subsystem', subsystem_id, 've subsystem list')}", err=True)
    raise SystemExit(1)
```

**src/cli/investigation.py** - `status()` around line 177 (error handling for investigations):
```python
# Similar pattern for investigation status lookups
```

### Step 3: Document the `chunk start` alias

The alias is created at line 201 of `src/cli/chunk.py` via `chunk.add_command(create, name="start")`.

Update the `create` command's docstring to mention the alias:

**src/cli/chunk.py** - `create()` docstring around line 59-67:
```python
def create(short_names, project_dir, yes, future, ticket, projects):
    """Create a new chunk (or multiple chunks). (Aliases: start)

    Creates chunks in docs/chunks/. Task context routes to task-scoped storage.

    Single chunk: ve chunk create my_feature [TICKET_ID]
    Multiple chunks: ve chunk create chunk_a chunk_b chunk_c --future [--ticket TICKET_ID]

    When creating multiple chunks, use --ticket flag for ticket ID.
    """
```

### Step 4: Run tests and verify

Run the test suite to ensure no regressions:

```bash
uv run pytest tests/ -v
```

Manually verify help text is visible:
```bash
uv run ve --help
uv run ve chunk --help
uv run ve chunk create --help
```

## Risks and Open Questions

- **Help text length**: Click may truncate long help strings. Keep group-level descriptions to 2-3 lines maximum.
- **Import location**: The `format_not_found_error` helper is added to `cli/utils.py`. This is consistent with other CLI utilities already there.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->