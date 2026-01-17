# Implementation Plan

## Approach

Follow the same architectural patterns established by the chunk commands:

1. **CLI Layer (`src/ve.py`)**: Add a `narrative` command group with a `create` subcommand. Reuse the existing `validate_short_name()` function since narratives share the same naming constraints as chunks.

2. **Business Logic (`src/narratives.py`)**: Create a new module mirroring `chunks.py` structure. The `Narratives` class will handle directory enumeration, ID generation, and template expansion.

3. **Project Integration (`src/project.py`)**: Update `_init_trunk()` (or add a new `_init_narratives()` method) to create `docs/narratives/` during project initialization.

4. **Template Expansion**: Use the same jinja2-based `render_template()` approach from `chunks.py`. The template at `src/templates/narrative/OVERVIEW.md` will be copied with variable expansion (even though no variables exist yet).

This follows DEC-001 (uvx-based CLI) by keeping all functionality accessible via the `ve` command.

## Sequence

### Step 1: Update `ve init` to create `docs/narratives/`

Modify `src/project.py` to add a `_init_narratives()` method that creates the `docs/narratives/` directory during initialization. Update the `init()` method to call this new method.

Location: `src/project.py`

Verification: Run existing `ve init` tests plus add a new test verifying the narratives directory is created.

### Step 2: Create the `Narratives` class

Create `src/narratives.py` with:
- `Narratives.__init__(project_dir)` - initialize with project directory
- `Narratives.narratives_dir` property - returns `docs/narratives/` path
- `Narratives.enumerate_narratives()` - list narrative directory names
- `Narratives.num_narratives` property - count of narratives
- `Narratives.create_narrative(short_name)` - create a new narrative directory

The `create_narrative()` method should:
1. Ensure `docs/narratives/` exists (fallback for pre-existing projects)
2. Calculate next sequence number (4-digit zero-padded)
3. Create `docs/narratives/{NNNN}-{short_name}/`
4. Copy and expand templates from `src/templates/narrative/`

Location: `src/narratives.py`

### Step 3: Add `ve narrative create` command

Add the CLI layer in `src/ve.py`:
- Create `@cli.group()` decorated `narrative()` function
- Add `@narrative.command()` decorated `create()` function
- Accept `short_name` argument and `--project-dir` option
- Validate short_name using existing `validate_short_name()` function
- Normalize to lowercase
- Call `Narratives.create_narrative()` and report the created path

Location: `src/ve.py`

### Step 4: Add tests for `ve init` narratives directory

Add tests to `tests/test_init.py`:
- Verify `docs/narratives/` directory is created by `ve init`
- Verify idempotency (second run doesn't fail if directory exists)

Location: `tests/test_init.py`

### Step 5: Add tests for `Narratives` class

Create `tests/test_narratives.py` with tests for:
- `enumerate_narratives()` returns empty list for new project
- `num_narratives` property returns correct count
- `create_narrative()` creates directory with correct naming
- `create_narrative()` copies template files
- Sequence numbers increment correctly
- `docs/narratives/` is auto-created if missing

Location: `tests/test_narratives.py`

### Step 6: Add tests for `ve narrative create` command

Create `tests/test_narrative_create.py` with tests for:
- Command exists and shows help
- Creates narrative with valid short_name
- Validates short_name (spaces, invalid chars, length)
- Normalizes to lowercase
- Reports created path
- Auto-creates `docs/narratives/` if missing

Location: `tests/test_narrative_create.py`

### Step 7: Verify all tests pass

Run the full test suite to ensure:
- All existing tests continue to pass
- All new tests pass
- No regressions introduced

## Dependencies

None. All required infrastructure exists:
- Template at `src/templates/narrative/OVERVIEW.md` ✓
- jinja2 for template rendering ✓
- click for CLI ✓
- Existing patterns in `chunks.py` and `ve.py` to follow ✓

## Risks and Open Questions

- **Idempotent skipped count**: The existing `test_init_command_idempotent` test asserts "10 files skipped". Adding `docs/narratives/` might not affect this count since it's a directory, not a file, but should verify.

- **Template variable expansion**: The GOAL.md specifies "Template expansion runs even though no variables currently exist (future-proofing)". This requires using jinja2 render even with no variables, which matches the chunks pattern.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->