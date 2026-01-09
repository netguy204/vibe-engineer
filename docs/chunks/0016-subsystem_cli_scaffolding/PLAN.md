<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds CLI scaffolding for subsystem documentation, following the patterns established by `ve narrative` and `ve chunk` commands. The implementation builds on:

- **Existing `Subsystems` class** (src/subsystems.py): Already provides `enumerate_subsystems()`, `is_subsystem_dir()`, and `parse_subsystem_frontmatter()` from chunk 0014
- **Existing `SubsystemFrontmatter` model** (src/models.py): Defines the frontmatter schema with status enum
- **Existing `validate_identifier` function** (src/validation.py): Reused for shortname validation
- **Narrative/Chunk CLI patterns** (src/ve.py): Mirror the `ve narrative create` and `ve chunk list` command structure

The approach:
1. Extend `Subsystems` class with `create_subsystem()` and `find_by_shortname()` methods
2. Add `ve subsystem` command group to CLI with `discover` and `list` subcommands
3. Create minimal template at `src/templates/subsystem/OVERVIEW.md`
4. Write tests first per docs/trunk/TESTING_PHILOSOPHY.md

Per DEC-001, all functionality is accessible via the CLI.

## Sequence

### Step 1: Write failing tests for `Subsystems.create_subsystem()`

Location: tests/test_subsystems.py

Add tests for the `create_subsystem()` method:
- Creates `docs/subsystems/{NNNN}-{shortname}/OVERVIEW.md`
- First subsystem gets `0001-` prefix
- Subsequent subsystems increment correctly (e.g., `0002-`, `0003-`)
- Returns path to created directory
- Creates `docs/subsystems/` directory if it doesn't exist

### Step 2: Write failing tests for `Subsystems.find_by_shortname()`

Location: tests/test_subsystems.py

Add tests for finding existing subsystems by shortname:
- Returns subsystem directory name if shortname exists (e.g., "validation" → "0001-validation")
- Returns None if shortname doesn't exist
- Handles multiple subsystems correctly

### Step 3: Implement `Subsystems.create_subsystem()` and `find_by_shortname()`

Location: src/subsystems.py

Add methods to the `Subsystems` class:

```python
def find_by_shortname(self, shortname: str) -> str | None:
    """Find subsystem directory by shortname.

    Returns directory name (e.g., "0001-validation") if found, None otherwise.
    """

def create_subsystem(self, shortname: str) -> pathlib.Path:
    """Create a new subsystem directory with OVERVIEW.md template.

    Returns path to created directory.
    """
```

Follow the pattern from `Narratives.create_narrative()` for template rendering.

### Step 4: Create minimal subsystem OVERVIEW.md template

Location: src/templates/subsystem/OVERVIEW.md

Create a minimal template with:
- Frontmatter with `status: DISCOVERING`
- Empty `chunks: []` and `code_references: []`
- Section headers only (Intent, Scope, Invariants, Implementation Locations, Chunk Relationships)
- No agent guidance comments (that's chunk 3's responsibility)

Template uses Jinja2 variables: `{{ short_name }}`

### Step 5: Write failing CLI tests for `ve subsystem list`

Location: tests/test_subsystem_list.py (new file)

Test cases:
- With no subsystems: outputs "No subsystems found" to stderr, exits with code 1
- With subsystems: outputs `docs/subsystems/{dir} [{STATUS}]` for each, sorted
- Verifies output format matches `ve chunk list` behavior

### Step 6: Write failing CLI tests for `ve subsystem discover`

Location: tests/test_subsystem_discover.py (new file)

Test cases:
- Valid shortname creates directory and outputs path
- Invalid shortname (via `validate_identifier`) errors with message
- Duplicate shortname errors with "Subsystem 'X' already exists at docs/subsystems/NNNN-X"
- Shortname is normalized to lowercase

### Step 7: Implement `ve subsystem` command group with `list` subcommand

Location: src/ve.py

Add:
```python
@cli.group()
def subsystem():
    """Subsystem commands"""
    pass

@subsystem.command("list")
@click.option("--project-dir", ...)
def list_subsystems(project_dir):
    ...
```

Follow the pattern from `ve chunk list` for:
- Empty state handling (stderr + exit code 1)
- Output format with status in brackets

### Step 8: Implement `ve subsystem discover` subcommand

Location: src/ve.py

Add:
```python
@subsystem.command()
@click.argument("shortname")
@click.option("--project-dir", ...)
def discover(shortname, project_dir):
    ...
```

Implementation:
1. Validate shortname with `validate_identifier`
2. Normalize to lowercase
3. Check for duplicates with `Subsystems.find_by_shortname()`
4. Create subsystem with `Subsystems.create_subsystem()`
5. Output created path

### Step 9: Verify all tests pass

Run full test suite to ensure no regressions and all new tests pass.

## Dependencies

- **Chunk 0014** (ACTIVE): Provides `SubsystemFrontmatter`, `SubsystemStatus`, and base `Subsystems` class methods

## Risks and Open Questions

- **Template directory structure**: Need to verify `src/templates/subsystem/` follows the same pattern as `src/templates/narrative/` and `src/templates/chunk/` for Jinja2 template loading
- **Sequence number calculation**: The current `Narratives.create_narrative()` uses `num_narratives + 1` which counts all directories. For robustness, should we parse the highest existing number like `Chunks.list_chunks()` does? (Decision: follow existing narrative pattern for consistency; can be improved in a future chunk if needed)

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->