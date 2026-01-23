<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk fixes a mismatch between documentation examples and validator requirements
for code references in task context. The approach addresses three areas:

1. **Template fix**: Update the template examples to use correct `org/repo::` format
   and add guidance about where to find project names.

2. **Template expansion**: Pass project names from task context when rendering
   chunk templates, so examples are dynamically populated with real project names
   from `.ve-task.yaml`.

3. **Validator improvement**: Enhance error messages in `SymbolicReference.validate_ref()`
   and surface those errors in `parse_chunk_frontmatter()` instead of silently
   returning `None`.

The implementation follows these existing patterns:
- Template rendering via `template_system.py` with `TaskContext` for task-specific context
- Pydantic model validation in `models.py` with field validators
- Frontmatter parsing in `chunks.py` with YAML extraction

Per TESTING_PHILOSOPHY.md, tests will:
- Be written first (TDD approach) for the validator improvement
- Assert semantic behavior (error messages contain expected content)
- Cover boundary cases (invalid formats, empty values)

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template
  subsystem for rendering chunk templates with task context. The subsystem is
  STABLE, so we follow its patterns exactly.

## Sequence

### Step 1: Improve validator error messages

Enhance `SymbolicReference.validate_ref()` in `src/models.py` to provide explicit
error messages when the project qualifier is not in `org/repo` format:

- Current behavior: Calls `_require_valid_repo_ref(project, "project qualifier")` which
  raises generic errors
- New behavior: Wrap the call to provide a more contextual message that includes:
  - The actual invalid value received (e.g., "got 'pybusiness'")
  - The expected format (e.g., "must be in 'org/repo' format")
  - An example (e.g., "e.g., 'acme/project::path'")

Location: `src/models.py#SymbolicReference::validate_ref`

### Step 2: Surface validation errors in frontmatter parsing

Update `parse_chunk_frontmatter()` in `src/chunks.py` to surface validation error
details instead of silently returning `None`:

Current behavior:
```python
except (yaml.YAMLError, ValidationError):
    return None
```

New behavior: Store the validation error and provide a method to access it, or
alternatively, create a variant that returns an error result. For now, the simpler
approach is to log/capture the actual error in a way that chunk-complete can access.

After analysis: The cleanest approach is to add a new method `parse_chunk_frontmatter_with_errors()`
that returns `tuple[ChunkFrontmatter | None, list[str]]` where the second element
contains error messages. This preserves backward compatibility.

Location: `src/chunks.py#Chunks::parse_chunk_frontmatter`

### Step 3: Update template examples to use full org/repo format

Modify `src/templates/chunk/GOAL.md.jinja2` lines 53-72 to:

1. Change the task_context examples from short names (`dotter::`, `vibe-engineer::`)
   to full org/repo format (use placeholder `acme/dotter::`, `acme/vibe-engineer::`)
2. Add guidance comment telling agents where to find project names:
   "See `.ve-task.yaml` projects list for org/repo names"
3. Keep the non-task-context examples unchanged (they don't need project qualifiers)

Location: `src/templates/chunk/GOAL.md.jinja2`

### Step 4: Add projects to template rendering context

Update chunk template rendering to pass project names from task context:

1. In `src/task_init.py` or where chunks are created in task context, pass the
   projects list from `TaskContext` to the template
2. Use Jinja2 to dynamically generate examples using actual project names from
   the task config

Currently, chunk creation in task context goes through:
- `src/ve.py#_start_task_chunk` → `src/task_utils.py#create_task_chunk`

The `create_task_chunk` function creates the chunk in the external repo via
`chunks.create_chunk()`. The template is rendered by `render_to_directory()`.

To pass task context to chunk templates:
1. Add `task_context` and `projects` as optional kwargs to `Chunks.create_chunk()`
2. Pass these through to `render_to_directory()`
3. Update the template to use `{% if projects %}` to generate dynamic examples

Location: `src/chunks.py#Chunks::create_chunk`, `src/task_utils.py#create_task_chunk`

### Step 5: Write tests for validator improvement

Add tests to `tests/test_models.py` for the improved error messages:

1. Test that short project names like `pybusiness::` produce an error mentioning
   "org/repo" format
2. Test that the error message includes the actual invalid value
3. Test that valid full `org/repo::` format still works

Location: `tests/test_models.py#TestSymbolicReferenceWithProjectQualification`

### Step 6: Write tests for frontmatter parsing with errors

Add tests to `tests/test_chunks.py` for the new error surfacing:

1. Test that invalid code_references produce specific error messages
2. Test that the error includes the validation failure reason
3. Test that valid frontmatter still parses correctly

Location: `tests/test_chunks.py` or create new file `tests/test_chunk_validation.py`

### Step 7: Write tests for template expansion

Add tests for template rendering with task context:

1. Test that chunk template renders with projects list
2. Test that examples use actual project names when projects are provided
3. Test that examples use generic placeholders when no task context

Location: `tests/test_template_system.py` or `tests/test_task_chunk_create.py`

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

```python
# Chunk: docs/chunks/coderef_format_prompting - Improved org/repo format error messages
```

## Dependencies

- `docs/chunks/taskdir_context_cmds` (ACTIVE) - This chunk builds on the task-context
  awareness established there. It is marked as `created_after` in the GOAL.md.

## Risks and Open Questions

1. **Backward compatibility**: Changing `parse_chunk_frontmatter()` signature could
   break callers. Mitigation: Add new method rather than changing existing one.

2. **Template rendering performance**: Passing extra context shouldn't materially
   affect performance, but worth monitoring.

3. **Error message verbosity**: Need to balance helpful detail vs. overwhelming
   output. The error should be concise but include the key information (what was
   wrong, what was expected).

4. **Jinja2 template complexity**: Dynamic example generation adds template logic.
   Keep it simple with a straightforward `{% for project in projects %}` pattern.

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