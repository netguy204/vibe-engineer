<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements the friction log artifact type following the established patterns in the codebase:

1. **Template System Integration** - Create a `FRICTION.md.jinja2` template in `src/templates/trunk/` following the prototype design from `docs/investigations/friction_log_artifact/prototypes/FRICTION.md`. This integrates with `ve init` via the existing `render_to_directory("trunk", ...)` call in `project.py`.

2. **CLI Command Group** - Add a new `friction` command group to `src/ve.py` with three subcommands:
   - `ve friction log` - Append a new friction entry
   - `ve friction list` - Display friction entries with filtering
   - `ve friction analyze` - Group entries by tag and highlight clusters

3. **Business Logic Module** - Create a new `src/friction.py` module containing the `Friction` class with methods for parsing, appending, and querying the friction log. This follows the pattern of `chunks.py`, `narratives.py`, `investigations.py`.

4. **Pydantic Models** - Add friction-related models to `src/models.py`:
   - `FrictionTheme` - Theme identifier and name
   - `FrictionProposedChunk` - Proposed chunk with `addresses` array linking to entry IDs
   - `FrictionFrontmatter` - Parses the frontmatter structure

5. **Test-Driven Development** - Following `docs/trunk/TESTING_PHILOSOPHY.md`:
   - Write failing tests first for Friction class behavior
   - Write failing CLI integration tests
   - Then implement to make tests pass

Key design decisions from the investigation:
- **Prose entries in body** - Entries are markdown prose under `### FXXX: ...` headings
- **Themes in frontmatter** - Categories emerge organically; agent sees existing themes
- **Derived status** - Entry status (OPEN/ADDRESSED/RESOLVED) computed from `proposed_chunks.addresses`
- **Single log per project** - Located at `docs/trunk/FRICTION.md`

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system for rendering `FRICTION.md.jinja2`. Follow the established patterns for trunk templates (`render_to_directory("trunk", ...)` in `project.py`).

## Sequence

### Step 1: Add friction models to models.py

Add Pydantic models for friction log parsing:

```python
class FrictionTheme(BaseModel):
    """A friction theme/category in the frontmatter."""
    id: str  # Short identifier like "code-refs"
    name: str  # Human-readable name like "Code Reference Friction"

class FrictionProposedChunk(BaseModel):
    """A proposed chunk that addresses friction entries."""
    prompt: str
    chunk_directory: str | None = None
    addresses: list[str] = []  # List of F-number IDs like ["F001", "F003"]

class FrictionFrontmatter(BaseModel):
    """Frontmatter schema for FRICTION.md files."""
    themes: list[FrictionTheme] = []
    proposed_chunks: list[FrictionProposedChunk] = []
```

Location: `src/models.py`

**Tests first** (in `tests/test_models.py`):
- Test FrictionTheme validation (id and name required)
- Test FrictionProposedChunk validation (addresses is list of strings)
- Test FrictionFrontmatter parsing

### Step 2: Create FRICTION.md.jinja2 template

Create the friction log template based on the prototype structure:

```markdown
---
themes: []
proposed_chunks: []
---

# Friction Log

<!--
GUIDANCE FOR AGENTS:

When appending a new friction entry:
1. Read existing themes - cluster the new entry into an existing theme if it fits
2. If no theme fits, add a new theme to frontmatter
3. Assign the next sequential F-number ID
4. Use the format: ### FXXX: YYYY-MM-DD [theme-id] Title

Entry status is DERIVED, not stored:
- OPEN: Entry ID not in any proposed_chunks.addresses
- ADDRESSED: Entry ID in proposed_chunks.addresses where chunk_directory is set
- RESOLVED: Entry ID addressed by a chunk that has reached COMPLETE status

When patterns emerge (3+ entries in a theme, or recurring pain):
- Add a proposed_chunk to frontmatter with the entry IDs it would address
- The prompt should describe the work, not just "fix friction"
-->

## Entries

<!-- Friction entries will be appended below -->
```

Location: `src/templates/trunk/FRICTION.md.jinja2`

**Test** (in `tests/test_init.py`):
- Verify `ve init` creates `docs/trunk/FRICTION.md`
- Verify FRICTION.md contains expected structure (frontmatter, guidance comment, Entries heading)

### Step 3: Create friction.py business logic module

Create the Friction class with methods for:
- `parse_frontmatter()` - Parse YAML frontmatter into FrictionFrontmatter model
- `parse_entries()` - Extract entries from body (ID, date, theme, title, content)
- `get_next_entry_id()` - Return next sequential F-number (e.g., "F005")
- `append_entry()` - Add new entry with correct formatting
- `list_entries(status_filter, tags_filter)` - Query entries with filters
- `get_entry_status(entry_id)` - Compute OPEN/ADDRESSED/RESOLVED from proposed_chunks

```python
@dataclass
class FrictionEntry:
    """Parsed friction entry from the log body."""
    id: str  # e.g., "F001"
    date: str  # e.g., "2026-01-12"
    theme_id: str  # e.g., "code-refs"
    title: str
    content: str  # Full markdown content after the heading

class Friction:
    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self.friction_path = project_dir / "docs" / "trunk" / "FRICTION.md"
```

Location: `src/friction.py`

**Tests first** (in `tests/test_friction.py`):
- `test_parse_frontmatter_empty` - New friction log with empty arrays
- `test_parse_frontmatter_with_themes` - Log with themes
- `test_parse_entries_extracts_fields` - Verify entry parsing
- `test_get_next_entry_id_empty` - Returns "F001" for empty log
- `test_get_next_entry_id_sequential` - Returns "F004" when F001-F003 exist
- `test_append_entry_creates_entry` - Entry appended with correct format
- `test_get_entry_status_open` - Entry not in proposed_chunks
- `test_get_entry_status_addressed` - Entry in proposed_chunks with chunk_directory
- `test_list_entries_all` - Returns all entries
- `test_list_entries_filter_status` - Filter by OPEN/ADDRESSED
- `test_list_entries_filter_tags` - Filter by theme tag

### Step 4: Implement `ve friction log` CLI command

Add the friction command group and log subcommand:

```python
@cli.group()
def friction():
    """Friction log commands"""
    pass

@friction.command("log")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--title", prompt="Title", help="Brief title for the friction entry")
@click.option("--description", prompt="Description", help="Detailed description of the friction")
@click.option("--impact", prompt="Impact", type=click.Choice(["low", "medium", "high", "blocking"]), help="Severity of the friction")
@click.option("--theme", prompt="Theme", help="Theme ID (or 'new' to create)")
def log_entry(project_dir, title, description, impact, theme):
    """Log a new friction entry."""
```

The command should:
1. Load existing friction log and parse frontmatter
2. Display existing themes for user reference
3. Handle "new" theme by prompting for theme id and name
4. Generate next F-number ID
5. Append entry in correct format
6. Update frontmatter if new theme added

Location: `src/ve.py`

**Tests first** (in `tests/test_friction_cli.py`):
- `test_friction_log_command_exists` - Help text available
- `test_friction_log_creates_entry` - Entry appears in file
- `test_friction_log_increments_id` - Sequential ID assignment
- `test_friction_log_new_theme` - New theme added to frontmatter
- `test_friction_log_existing_theme` - No frontmatter change for existing theme

### Step 5: Implement `ve friction list` CLI command

```python
@friction.command("list")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--open", "status_open", is_flag=True, help="Show only OPEN entries")
@click.option("--tags", multiple=True, help="Filter by theme tags")
def list_entries(project_dir, status_open, tags):
    """List friction entries."""
```

Output format:
```
F001 [OPEN] [code-refs] Symbolic references become ambiguous
F002 [ADDRESSED] [templates] Rendered files easy to edit by mistake
```

Location: `src/ve.py`

**Tests first** (in `tests/test_friction_cli.py`):
- `test_friction_list_command_exists` - Help text available
- `test_friction_list_shows_all_entries` - Default lists all
- `test_friction_list_open_filter` - --open shows only OPEN
- `test_friction_list_tags_filter` - --tags filters by theme
- `test_friction_list_empty` - "No friction entries found" for empty log

### Step 6: Implement `ve friction analyze` CLI command

```python
@friction.command("analyze")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--tags", multiple=True, help="Filter analysis to specific themes")
def analyze(project_dir, tags):
    """Analyze friction patterns and suggest actions."""
```

Output format:
```
## Friction Analysis

### code-refs (3 entries) ⚠️ Pattern Detected
- F001: Symbolic references become ambiguous
- F003: No validation that code references resolve
- F005: Ambiguous function names in CLI

Consider creating a chunk or investigation to address this pattern.

### templates (2 entries)
- F002: Rendered files easy to edit by mistake
- F004: Template changes not detected by init
```

The ⚠️ indicator appears for themes with 3+ entries.

Location: `src/ve.py`

**Tests first** (in `tests/test_friction_cli.py`):
- `test_friction_analyze_command_exists` - Help text available
- `test_friction_analyze_groups_by_theme` - Entries grouped correctly
- `test_friction_analyze_highlights_clusters` - 3+ entries get indicator
- `test_friction_analyze_tags_filter` - --tags filters analysis
- `test_friction_analyze_empty` - "No friction entries found" for empty log

### Step 7: Add backreference comments and update GOAL.md code_paths

Add backreference comments to new code:
```python
# Chunk: docs/chunks/friction_template_and_cli - Friction log artifact type
```

Update `docs/chunks/friction_template_and_cli/GOAL.md` frontmatter with:
```yaml
code_paths:
  - src/friction.py
  - src/models.py
  - src/ve.py
  - src/templates/trunk/FRICTION.md.jinja2
  - tests/test_friction.py
  - tests/test_friction_cli.py
```

### Step 8: Run full test suite and fix any issues

```bash
uv run pytest tests/
```

Verify:
- All new tests pass
- No regressions in existing tests
- `ve init` creates FRICTION.md
- `ve friction log/list/analyze` work end-to-end

## Dependencies

No external dependencies. Uses existing libraries:
- `click` for CLI
- `pydantic` for validation
- `jinja2` for templates
- `pyyaml` for frontmatter parsing

## Risks and Open Questions

1. **Entry heading format parsing**: The regex for parsing `### FXXX: YYYY-MM-DD [theme-id] Title` needs to be robust to handle edge cases (missing brackets, extra whitespace, etc.). Mitigation: comprehensive test cases for malformed entries.

2. **Multi-line entry content**: Entries span from one heading to the next. Need to correctly capture all content including **Impact** and **Frequency** lines. Mitigation: test with realistic multi-line entries.

3. **Concurrent edits**: If the friction log is edited manually while `ve friction log` runs, changes could be lost. Mitigation: Out of scope for this chunk; document as a known limitation.

4. **Large friction logs**: With many entries, performance of parsing could degrade. Mitigation: Keep it simple for now; optimize later if needed. The investigation suggested archiving RESOLVED entries to a separate file if the log grows large.

## Deviations

<!-- To be populated during implementation -->