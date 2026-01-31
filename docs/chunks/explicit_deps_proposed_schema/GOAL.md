---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/narrative/OVERVIEW.md.jinja2
  - src/templates/investigation/OVERVIEW.md.jinja2
code_references:
  - ref: src/templates/narrative/OVERVIEW.md.jinja2
    implements: "PROPOSED_CHUNKS schema documentation with depends_on field for narratives"
  - ref: src/templates/investigation/OVERVIEW.md.jinja2
    implements: "PROPOSED_CHUNKS schema documentation with depends_on field for investigations"
narrative: explicit_chunk_deps
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after:
- orch_task_worktrees
depends_on: []
---

# Chunk Goal

## Minor Goal

Extend the `proposed_chunks` schema in narrative and investigation templates to support a `depends_on` field that uses index-based references to other prompts in the same array. This enables agents to express inter-chunk dependencies at the planning stage, before any chunks are created.

Currently, dependencies between proposed chunks can only be described informally in prose. By adding a structured `depends_on` field that references other prompts by their array index (e.g., `depends_on: [0, 2]` means "this prompt depends on prompts at indices 0 and 2"), agents can declare ordering constraints that will later be translated into chunk-level dependencies during `/chunk-create`.

This is the second step in the explicit_chunk_deps narrative, providing the schema foundation that chunk #3 (dependency propagation during chunk-create) will consume.

## Success Criteria

1. **Narrative template updated**: `src/templates/narrative/OVERVIEW.md.jinja2` includes `depends_on` field documentation in the `PROPOSED_CHUNKS` schema comment, explaining:
   - The field is an array of integer indices
   - Indices refer to other prompts in the same `proposed_chunks` array
   - Example usage: `depends_on: [0, 2]`

2. **Investigation template updated**: `src/templates/investigation/OVERVIEW.md.jinja2` includes the same `depends_on` field documentation in its `PROPOSED_CHUNKS` schema comment

3. **Existing narrative shows the pattern**: The `explicit_chunk_deps` narrative's OVERVIEW.md already demonstrates the pattern (it uses `depends_on` in its proposed_chunks). Templates should document what the narrative already models.

4. **Schema documentation is clear**: A reader of the template can understand:
   - What `depends_on` means (explicit ordering constraints)
   - How to specify dependencies (array of zero-based indices)
   - When to use it (when chunks have implementation dependencies)

