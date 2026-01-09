# Implementation Plan

## Approach

This chunk follows established patterns from `src/narratives.py` and `src/subsystems.py` to implement investigation management. The strategy is:

1. **Add `InvestigationStatus` enum to `src/models.py`** - Define the four states: `ONGOING`, `SOLVED`, `NOTED`, `DEFERRED`

2. **Create `src/investigations.py`** - Implement an `Investigations` class following the patterns from `Narratives` and `Subsystems`:
   - `enumerate_investigations()` - List investigation directory names
   - `create_investigation(short_name)` - Create investigation directory with sequential `{NNNN}-{short_name}` numbering
   - `parse_investigation_frontmatter(investigation_id)` - Parse and validate OVERVIEW.md frontmatter

3. **Add CLI commands to `src/ve.py`** - Add `ve investigation create` and `ve investigation list` commands following the patterns of existing narrative and subsystem commands

4. **Create slash command template** - Create `src/templates/commands/investigation-create.md.jinja2` following patterns from `narrative-create.md.jinja2` and `subsystem-discover.md.jinja2`, with scale assessment logic

5. **Test-driven development** - Write tests first per docs/trunk/TESTING_PHILOSOPHY.md, following patterns from `test_subsystems.py`, `test_subsystem_list.py`, and `test_subsystem_discover.py`

The implementation uses existing utilities:
- `validate_identifier` from `src/validation.py` for input validation
- `render_to_directory` from `src/template_system.py` for template rendering
- The existing investigation template at `src/templates/investigation/OVERVIEW.md.jinja2`

Per DEC-001, all functionality is accessible via the `ve` CLI.

## Sequence

### Step 1: Add InvestigationStatus enum to models.py

Add the `InvestigationStatus` enum to `src/models.py` with values:
- `ONGOING` - Investigation in progress
- `SOLVED` - Investigation led to action; chunks were proposed/created
- `NOTED` - Findings documented but no action required
- `DEFERRED` - Investigation paused; may be revisited later

**Tests first**: Add tests to `tests/test_models.py` that verify:
- All four status values exist and are accessible
- The enum is a `StrEnum` for serialization compatibility

Location: `src/models.py`

### Step 2: Add InvestigationFrontmatter model to models.py

Create a Pydantic model for investigation frontmatter validation:
- `status: InvestigationStatus`
- `trigger: str | None`
- `proposed_chunks: list[dict]` (each with `prompt` and optional `chunk_directory`)

**Tests first**: Add tests to `tests/test_models.py` that verify:
- Valid frontmatter parses successfully
- Invalid status values are rejected
- Missing required fields are rejected

Location: `src/models.py`

### Step 3: Create Investigations class skeleton

Create `src/investigations.py` with the `Investigations` class:
- `__init__(self, project_dir)` - Store project directory
- `investigations_dir` property - Return `project_dir / "docs" / "investigations"`
- `enumerate_investigations()` - List investigation directory names (empty list if none exist)
- `num_investigations` property - Return count

**Tests first**: Create `tests/test_investigations.py` with tests that verify:
- Empty project returns empty list
- Property returns correct path

Location: `src/investigations.py`

### Step 4: Implement create_investigation method

Add the `create_investigation(short_name)` method:
- Ensure investigations directory exists
- Calculate next sequence number (4-digit zero-padded)
- Create investigation directory with `{NNNN}-{short_name}` pattern
- Use `render_to_directory` to render the investigation template
- Return the created path

This requires adding `ActiveInvestigation` dataclass to `src/template_system.py` and updating `TemplateContext` to support it.

**Tests first**: Add tests to `tests/test_investigations.py` that verify:
- Creates directory at expected path
- Creates OVERVIEW.md file
- Sequential numbering works correctly
- Returns correct path

Location: `src/investigations.py`, `src/template_system.py`

### Step 5: Implement parse_investigation_frontmatter method

Add the `parse_investigation_frontmatter(investigation_id)` method:
- Read OVERVIEW.md from investigation directory
- Extract YAML frontmatter between `---` markers
- Validate against `InvestigationFrontmatter` model
- Return parsed frontmatter or `None` if invalid/missing

**Tests first**: Add tests to `tests/test_investigations.py` that verify:
- Valid frontmatter parses correctly
- Returns None for non-existent investigation
- Returns None for malformed frontmatter

Location: `src/investigations.py`

### Step 6: Add CLI investigation group and create command

Add to `src/ve.py`:
- `@cli.group() def investigation():` - Command group
- `@investigation.command() def create(short_name, project_dir):` - Create command
  - Validate short_name using existing `validate_short_name`
  - Normalize to lowercase
  - Create investigation via `Investigations.create_investigation`
  - Output "Created {relative_path}"

**Tests first**: Create `tests/test_investigation_create.py` with tests that verify:
- Help shows correct usage
- Valid shortname creates directory and outputs path
- Invalid shortname errors with message
- Shortname normalized to lowercase
- Sequential numbering works
- `--project-dir` option works

Location: `src/ve.py`

### Step 7: Add CLI investigation list command

Add to `src/ve.py`:
- `@investigation.command("list") def list_investigations(state, project_dir):` - List command
  - If no investigations: output "No investigations found" to stderr, exit 1
  - Without filter: output all investigations with status tags
  - With `--state` filter: output only investigations matching that state

**Tests first**: Create `tests/test_investigation_list.py` with tests that verify:
- Help shows correct usage
- Empty project exits with error and message
- Single investigation outputs path with status
- Multiple investigations sorted correctly
- `--state` filter works correctly
- Invalid state errors with message
- Format includes status brackets

Location: `src/ve.py`

### Step 8: Create investigation-create slash command template

Create `src/templates/commands/investigation-create.md.jinja2`:
- Include common tips partial
- Scale assessment section that evaluates operator's description:
  - **Investigation warranted signals**: unclear root cause, multiple hypotheses, spans systems, architectural implications, exploration across sessions
  - **Chunk sufficient signals**: single hypothesis, obvious fix, localized change, no architectural decision
- If simple: explain why, offer `/chunk-create` with suggested description, allow override
- If investigation-worthy: derive short name, run `ve investigation create`, guide population of Trigger, Success Criteria, and initial hypotheses

**Tests first**: Add test to `tests/test_template_system.py` that verifies:
- Template renders without error
- Template file exists and is valid Jinja2

Location: `src/templates/commands/investigation-create.md.jinja2`

## Dependencies

- **Chunk 0027-investigation_template** (status: ACTIVE) - The investigation OVERVIEW.md template exists at `src/templates/investigation/OVERVIEW.md.jinja2`
- No external libraries to add - uses existing dependencies

## Risks and Open Questions

- **Frontmatter model complexity**: The `proposed_chunks` field has a nested structure. Need to decide if this requires a dedicated Pydantic model or if `list[dict]` with runtime validation is sufficient. Starting with the simpler approach.

- **Filter state validation**: For `ve investigation list --state`, invalid state values should error clearly. Need to ensure the error message lists valid states.

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