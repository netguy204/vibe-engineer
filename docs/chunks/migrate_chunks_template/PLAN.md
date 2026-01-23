# Implementation Plan

## Approach

This is a consolidation chunk that eliminates one of three duplicate
`render_template` functions identified in the template_system subsystem's Known
Deviations. The approach is straightforward:

1. Rename chunk templates to use the `.jinja2` suffix convention
2. Replace the local `render_template` with imports from `template_system`
3. Update `Chunks::create_chunk` to use `render_to_directory`
4. Remove the unused `jinja2` import
5. Update chunk templates to use the standardized `project.active_chunk.*` context
6. Update `create_chunk` to pass `ActiveChunk` via `TemplateContext`

The implementation must preserve exact output behavior—existing tests verify
that created chunks have correct directory names, frontmatter content, and
template variable substitution. These tests serve as the regression suite.

## Subsystem Considerations

- **docs/subsystems/0001-template_system** (REFACTORING): This chunk IMPLEMENTS
  the subsystem by migrating `chunks.py` to use the canonical template module.

The subsystem is in REFACTORING status, meaning we should bring touched code
into compliance. After this chunk:
- `src/chunks.py#render_template` will be removed (was NON_COMPLIANT)
- `src/chunks.py#Chunks::create_chunk` will use `template_system.render_to_directory`
  (becomes COMPLIANT)

## Sequence

### Step 1: Rename chunk templates to use `.jinja2` suffix

Rename the template files to include the `.jinja2` suffix per the subsystem's
hard invariant #2.

Location: `src/templates/chunk/`

Files to rename:
- `GOAL.md` → `GOAL.md.jinja2`
- `PLAN.md` → `PLAN.md.jinja2`

### Step 2: Update `Chunks::create_chunk` to use `template_system`

Modify `src/chunks.py` to:
1. Import `render_to_directory` from `template_system`
2. Remove the local `render_template` function
3. Remove the `jinja2` import
4. Replace the template rendering loop with a single `render_to_directory` call

The current implementation iterates over `template_dir.glob("chunk/*.md")` and
renders each template individually. The new implementation uses
`render_to_directory("chunk", chunk_path, ...)` which:
- Enumerates templates via `list_templates("chunk")`
- Renders each through the configured Jinja2 Environment
- Strips the `.jinja2` suffix from output filenames
- Writes files to the destination directory

Location: `src/chunks.py`

### Step 3: Update tests that reference template filenames

The test `test_works_with_real_chunk_templates` in `test_template_system.py`
asserts that `list_templates("chunk")` returns `"GOAL.md"` and `"PLAN.md"`.
After renaming, it should return `"GOAL.md.jinja2"` and `"PLAN.md.jinja2"`.

Location: `tests/test_template_system.py`

### Step 4: Run tests and verify behavior

Run the full test suite to verify:
- Existing chunk creation tests pass (output files still named correctly)
- Template system tests pass with renamed templates
- No regressions in other tests

Command: `pytest tests/`

### Step 5: Manual verification

Run `ve chunk start test_chunk` to verify the end-to-end workflow still works.

### Step 6: Update chunk templates to use standardized context

Update the chunk templates to reference data through `project.active_chunk.*`
instead of raw kwargs. This follows the template_system's canonical pattern.

Location: `src/templates/chunk/`

Changes:
- `{{ chunk_directory }}` → `{{ project.active_chunk.id }}`
- Keep `{{ status }}` and `{{ ticket_id }}` as kwargs (creation-time parameters)

### Step 7: Update `create_chunk` to use `TemplateContext`

Modify `src/chunks.py#Chunks::create_chunk` to:
1. Import `ActiveChunk` and `TemplateContext` from `template_system`
2. Create an `ActiveChunk` instance with the chunk's metadata
3. Wrap it in a `TemplateContext`
4. Pass the context to `render_to_directory`

This ensures chunk templates access data through the standardized context
pattern, achieving full compliance with the template_system subsystem.

### Step 8: Run tests and manual verification

Re-run the test suite and manual verification to confirm the refactored
context-based approach produces identical output.

## Risks and Open Questions

1. **Template variable compatibility**: The canonical `render_template` accepts
   `context: TemplateContext` as a named parameter, while the current code
   passes all variables as kwargs. Need to verify kwargs are passed through
   correctly (they are—`render_to_directory` accepts `**kwargs` and forwards
   them to `render_template`).

2. **Glob pattern change**: Current code uses `template_dir.glob("chunk/*.md")`
   which won't match `.jinja2` files. The migration to `render_to_directory`
   sidesteps this since it uses `list_templates()` internally.

## Deviations

- **Steps 6-8 added during implementation**: The original plan only migrated to
  using `render_to_directory` with raw kwargs, which technically worked but
  didn't follow the template_system's canonical pattern of using `TemplateContext`
  with `ActiveChunk`. Steps 6-8 were added to achieve full compliance with the
  subsystem's intended design.