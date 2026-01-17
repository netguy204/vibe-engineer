<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk rewrites the narrative CLI commands (`create`, `list`, `compact`) to use scratchpad
storage (`~/.vibe/scratchpad/`) instead of in-repo `docs/narratives/`. The work builds on the
scratchpad storage infrastructure from `scratchpad_storage` chunk.

**Strategy:**

1. **Modify `ve.py` narrative command group** to route to scratchpad storage via
   `ScratchpadNarratives` class instead of the in-repo `Narratives` class.

2. **Add task context detection** using the existing `is_task_directory()` pattern to route
   to `~/.vibe/scratchpad/task:[name]/narratives/` when in task context.

3. **Update the `/narrative-create` skill template** to work with scratchpad paths.

4. **Handle compact command**: The `compact` command creates a narrative that references
   existing chunks. Since chunks are also moving to scratchpad, this remains internally
   consistent - it just operates on scratchpad narratives referencing scratchpad chunks.

5. **Remove in-repo narrative support**: Per success criteria, commands should no longer
   create/read from `docs/narratives/`. The existing `Narratives` class remains for any
   legacy in-repo usage but the CLI commands are rewired.

**Key design decision:** This follows DEC-002 (git not assumed) by moving narratives to a
user-global location outside any git repository.

**Test-driven approach per TESTING_PHILOSOPHY.md:**
- Write failing tests first for each command (create, list) with scratchpad storage
- Test project context routing to `~/.vibe/scratchpad/[project]/narratives/`
- Test task context routing to `~/.vibe/scratchpad/task:[name]/narratives/`

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS scratchpad
  narrative commands as part of the workflow artifacts pattern. The existing
  `ScratchpadNarratives` class in `src/scratchpad.py` already follows the manager
  class pattern established by the subsystem (enumerate, create, parse_frontmatter).

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system
  for rendering narrative OVERVIEW.md files. The `scratchpad_narrative/OVERVIEW.md.jinja2`
  template already exists from the `scratchpad_storage` chunk.

## Sequence

### Step 1: Write failing tests for `ve narrative create` with scratchpad

Create tests in `tests/test_narrative_scratchpad.py` that verify:
- `ve narrative create my_narrative` in project context creates
  `~/.vibe/scratchpad/[project]/narratives/my_narrative/OVERVIEW.md`
- Frontmatter contains expected fields (status: DRAFTING, created_at)
- Output shows the scratchpad path (not docs/narratives/)

Use `tmp_path` fixture for the scratchpad root to avoid polluting the real
`~/.vibe/scratchpad/` directory.

Location: `tests/test_narrative_scratchpad.py`

### Step 2: Write failing tests for `ve narrative list` with scratchpad

Add tests to verify:
- `ve narrative list` shows narratives from `~/.vibe/scratchpad/[project]/narratives/`
- Output format includes status and path
- Empty list case handled gracefully

Location: `tests/test_narrative_scratchpad.py`

### Step 3: Write failing tests for task context routing

Add tests to verify:
- In task context, `ve narrative create foo` creates in `~/.vibe/scratchpad/task:[name]/narratives/`
- In task context, `ve narrative list` lists from task scratchpad
- Task name is detected from `.ve-task.yaml` in the directory

Location: `tests/test_narrative_scratchpad.py`

### Step 4: Implement `ve narrative create` with scratchpad storage

Modify `src/ve.py` `create_narrative()` command:
1. Remove task directory check (the old cross-repo mode)
2. Detect task context from `.ve-task.yaml` to get task name
3. Create `Scratchpad` instance with default root
4. Use `scratchpad.resolve_context()` to get context path
5. Create `ScratchpadNarratives` manager
6. Call `narratives.create_narrative(short_name)`
7. Output the scratchpad path

Add backreference comment:
```python
# Chunk: docs/chunks/scratchpad_narrative_commands - Scratchpad narrative commands
```

Location: `src/ve.py`

### Step 5: Implement `ve narrative list` with scratchpad storage

Modify `src/ve.py` `list_narratives()` command:
1. Remove task directory check (the old cross-repo mode)
2. Create `Scratchpad` instance and resolve context
3. Create `ScratchpadNarratives` manager
4. Call `narratives.list_narratives()` for ordered list
5. Output each narrative with status and path

Location: `src/ve.py`

### Step 6: Handle `ve narrative compact` for scratchpad

The compact command consolidates chunks into a narrative. In the scratchpad model:
- Source chunks are in scratchpad
- Target narrative is created in scratchpad
- References between them use scratchpad paths

Modify to:
1. Create the narrative in scratchpad via `ScratchpadNarratives.create_narrative()`
2. Update to reference the source chunk short_names
3. Output the scratchpad narrative path

Note: The compact command's chunk-to-narrative backreference update functionality
may need to be simplified or removed since scratchpad chunks don't have code_references.

Location: `src/ve.py`

### Step 7: Update `/narrative-create` skill template

Modify `src/templates/commands/narrative-create.md.jinja2`:
1. Update step 2 to show scratchpad path in example
2. Remove task context conditional (scratchpad handles both cases uniformly)
3. Update step 3 path references

Location: `src/templates/commands/narrative-create.md.jinja2`

### Step 8: Remove legacy in-repo narrative code paths

Clean up `src/ve.py`:
1. Remove `_create_task_narrative()` helper (task mode now uses scratchpad)
2. Remove `_list_task_narratives()` helper
3. Remove imports for task narrative utilities that are no longer needed

The `Narratives` class in `src/narratives.py` can remain for any internal usage
but the CLI no longer routes to it.

Location: `src/ve.py`

### Step 9: Run tests and verify all pass

Execute the test suite to ensure:
1. New scratchpad narrative tests pass
2. Existing tests that don't touch narrative commands still pass
3. No regressions in other functionality

Command: `uv run pytest tests/test_narrative_scratchpad.py -v`
Command: `uv run pytest tests/ -v` (full suite)

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments to help future agents trace code
back to the documentation that motivated it:

```python
# Chunk: docs/chunks/scratchpad_narrative_commands - Scratchpad narrative commands
# Narrative: docs/narratives/global_scratchpad - User-global scratchpad for flow artifacts
```

## Dependencies

- **`scratchpad_storage` chunk (ACTIVE)**: Provides the `Scratchpad`, `ScratchpadNarratives`,
  and `ScratchpadNarrativeFrontmatter` classes that this chunk uses. Already implemented.

- **Existing scratchpad narrative template**: `src/templates/scratchpad_narrative/OVERVIEW.md.jinja2`
  already exists from the storage chunk.

## Risks and Open Questions

1. **Compact command complexity**: The `ve narrative compact` command does more than
   just create a narrative - it consolidates chunks, updates their frontmatter to
   reference the narrative, and identifies files with backreferences to update.
   In the scratchpad model, scratchpad chunks don't have code_references, so the
   backreference update functionality is not applicable. Decision: Simplify or
   remove the compact command for scratchpad, or keep it but skip the backreference
   parts.

2. **Status and update-refs commands**: The existing narrative status and update-refs
   commands work with in-repo narratives. These may need to be updated or may be
   out of scope if we're focusing only on create/list/compact.

3. **Existing tests**: Tests in `tests/test_narratives.py` test the in-repo narrative
   system. We need to either update these to use scratchpad or leave them as legacy
   tests while adding new scratchpad-specific tests.

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