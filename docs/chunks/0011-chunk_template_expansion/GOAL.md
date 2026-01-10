---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/templates/chunk/PLAN.md.jinja2
  - tests/test_chunks.py
code_references:
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Template rendering with chunk_directory variable"
  - ref: src/templates/chunk/PLAN.md.jinja2
    implements: "Jinja2 template using chunk_directory for GOAL.md path reference"
  - ref: tests/test_chunks.py#TestChunkDirectoryInTemplates
    implements: "Tests for chunk_directory in rendered templates"
created_after: ["0010-chunk_create_task_aware"]
---

# Chunk Goal

## Minor Goal

Expand chunk templates with the full chunk directory name so that cross-references between chunk documents can use proper project-root-relative paths per DEC-004. Currently, the PLAN.md template contains awkward placeholder syntax like `docs/chunks/NNNN-name/GOAL.md` because it doesn't have access to the actual chunk directory name at render time.

This improves the developer experience by ensuring generated chunk documents contain accurate, navigable references from the moment they're created.

## Success Criteria

1. **Template context expanded**: `create_chunk()` in `src/chunks.py` passes a `chunk_directory` variable (e.g., `0011-chunk_template_expansion`) to the Jinja2 template renderer

2. **PLAN.md template updated**: The reference to the chunk's GOAL.md uses `{{ chunk_directory }}` to produce a proper path like `docs/chunks/0011-chunk_template_expansion/GOAL.md` instead of the placeholder `docs/chunks/NNNN-name/GOAL.md`

3. **GOAL.md template updated**: Any self-referential comments or examples that mention the chunk directory use the `{{ chunk_directory }}` variable

4. **Existing functionality preserved**: Chunks continue to be created correctly with all existing template variables (`ticket_id`, `short_name`, `next_chunk_id`) still available

5. **Tests pass**: Existing chunk creation tests continue to pass, with any new assertions for the expanded context