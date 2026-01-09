# Implementation Plan

## Approach

This chunk completes the template_system consolidation by:

1. **Extending `render_to_directory`** with an `overwrite` parameter and a richer `RenderResult`
   return type that tracks created, skipped, and overwritten files
2. **Migrating `subsystems.py` and `narratives.py`** to import and use `template_system.render_template`
   instead of their local duplicates
3. **Migrating `project.py`** from `shutil.copy`/symlink to template rendering
4. **Renaming templates** in `trunk/` and `commands/` to use `.jinja2` suffix

The approach follows the existing patterns established in chunk 0025-migrate_chunks_template for
migrating `chunks.py`. We use test-driven development per docs/trunk/TESTING_PHILOSOPHY.md.

Key design choices:
- The `RenderResult` dataclass mirrors `project.py`'s existing `InitResult` pattern
- The `overwrite` parameter defaults to `False` for backwards compatibility
- Commands get `overwrite=True` (always update to latest templates), trunk/CLAUDE.md get
  `overwrite=False` (preserve user content)

## Subsystem Considerations

- **docs/subsystems/0001-template_system** (REFACTORING): This chunk IMPLEMENTS the final
  consolidation work, resolving all NON_COMPLIANT code references and transitioning the
  subsystem to STABLE status.

## Sequence

### Step 1: Add RenderResult dataclass to template_system.py

Create a dataclass that tracks the outcome of template rendering:

```python
@dataclass
class RenderResult:
    created: list[pathlib.Path]      # Files that didn't exist and were created
    skipped: list[pathlib.Path]      # Files that existed and were not overwritten
    overwritten: list[pathlib.Path]  # Files that existed and were replaced
```

Location: `src/template_system.py`

### Step 2: Add overwrite parameter to render_to_directory

Modify `render_to_directory` signature:
- Add `overwrite: bool = False` parameter
- Change return type from `list[pathlib.Path]` to `RenderResult`
- Implement logic: if file exists and `overwrite=False`, add to `skipped`;
  if exists and `overwrite=True`, write and add to `overwritten`

Location: `src/template_system.py`

### Step 3: Update chunks.py to use RenderResult

The current `Chunks.create_chunk` calls `render_to_directory` but only uses the return
value to get the created paths. Update to use the new `RenderResult.created` field.

Location: `src/chunks.py`

### Step 4: Write tests for RenderResult and overwrite behavior

Following TDD, write tests that verify:
- `RenderResult` correctly categorizes created/skipped/overwritten files
- `overwrite=False` skips existing files
- `overwrite=True` replaces existing files
- Backwards compatibility: existing tests continue to pass

Location: `tests/test_template_system.py`

### Step 5: Migrate subsystems.py to use template_system

Remove the local `render_template` function from `src/subsystems.py` and:
- Import `render_template` from `template_system`
- Update `Subsystems.create_subsystem` to use the imported function
- The subsystem templates currently don't use the `.jinja2` suffix; rename them

Changes:
- `src/subsystems.py`: Remove local `render_template`, add import
- `src/templates/subsystem/OVERVIEW.md` → `src/templates/subsystem/OVERVIEW.md.jinja2`

### Step 6: Migrate narratives.py to use template_system

Remove the local `render_template` function from `src/narratives.py` and:
- Import `render_template` from `template_system`
- Update `Narratives.create_narrative` to use the imported function
- Rename narrative templates to use `.jinja2` suffix

Changes:
- `src/narratives.py`: Remove local `render_template`, add import
- `src/templates/narrative/OVERVIEW.md` → `src/templates/narrative/OVERVIEW.md.jinja2`

### Step 7: Rename trunk templates to use .jinja2 suffix

Rename all trunk templates:
- `src/templates/trunk/GOAL.md` → `src/templates/trunk/GOAL.md.jinja2`
- `src/templates/trunk/SPEC.md` → `src/templates/trunk/SPEC.md.jinja2`
- `src/templates/trunk/DECISIONS.md` → `src/templates/trunk/DECISIONS.md.jinja2`
- `src/templates/trunk/TESTING_PHILOSOPHY.md` → `src/templates/trunk/TESTING_PHILOSOPHY.md.jinja2`

### Step 8: Rename commands templates to use .jinja2 suffix

Rename all command templates:
- `src/templates/commands/*.md` → `src/templates/commands/*.md.jinja2`

### Step 9: Rename CLAUDE.md template

Rename the root CLAUDE.md template:
- `src/templates/CLAUDE.md` → `src/templates/CLAUDE.md.jinja2`

### Step 10: Migrate project.py _init_trunk to use template rendering

Replace `shutil.copy` in `_init_trunk` with `render_to_directory`:
- Use collection `"trunk"`
- Use `overwrite=False` (preserve user content)
- Map `RenderResult` to `InitResult`

Location: `src/project.py`

### Step 11: Migrate project.py _init_commands to use template rendering

Replace symlink/copy logic in `_init_commands` with `render_to_directory`:
- Use collection `"commands"`
- Use `overwrite=True` (always update to latest templates)
- Remove symlink creation code entirely
- Map `RenderResult` to `InitResult`

Location: `src/project.py`

### Step 12: Migrate project.py _init_claude_md to use template rendering

Replace `shutil.copy` in `_init_claude_md` with `render_template`:
- The CLAUDE.md template is a single file, not a collection directory
- Use `overwrite=False` (preserve user content)
- Handle the single-file case appropriately

Location: `src/project.py`

### Step 13: Update project.py tests

Update `tests/test_project.py` to reflect the new behavior:
- Commands are now rendered files, not symlinks (remove symlink assertions)
- Verify idempotency behavior (trunk skipped, commands overwritten)
- Ensure all existing semantic tests still pass

Location: `tests/test_project.py`

### Step 14: Update subsystem documentation

Update `docs/subsystems/0001-template_system/OVERVIEW.md`:
- Mark all NON_COMPLIANT references as COMPLIANT
- Change status from REFACTORING to STABLE
- Add this chunk to the chunks list
- Update Known Deviations to show all resolved

Location: `docs/subsystems/0001-template_system/OVERVIEW.md`

### Step 15: Run full test suite and verify

Run `pytest tests/` and verify:
- All existing tests pass
- No regressions in CLI behavior
- `ve init` idempotency works as expected

## Risks and Open Questions

1. **CLAUDE.md is a single file, not in a collection subdirectory** - The current template
   structure has `src/templates/CLAUDE.md` at the root, not in a `claude/` subdirectory.
   Need to handle this as a special case in `_init_claude_md` using `render_template`
   directly rather than `render_to_directory`.

2. **Existing tests expect symlinks for commands** - `test_project.py` has tests like
   `test_init_creates_command_symlinks` and `test_init_symlinks_point_to_templates`.
   These will need to be updated to expect regular files instead.

3. **Template context for trunk/commands** - The trunk and command templates currently
   have no dynamic content. We'll pass a `TemplateContext` with no active artifact,
   which makes the `project` variable available for future use but doesn't affect
   current rendering.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->