---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/chunks.py
  - src/templates/chunk/GOAL.md.jinja2
  - src/templates/chunk/PLAN.md.jinja2
  - tests/test_template_system.py
code_references:
  - ref: src/chunks.py#Chunks::create_chunk
    implements: "Uses template_system.render_to_directory with ActiveChunk and TemplateContext"
  - ref: src/templates/chunk/GOAL.md.jinja2
    implements: "Chunk GOAL.md template with .jinja2 suffix (renamed from GOAL.md)"
  - ref: src/templates/chunk/PLAN.md.jinja2
    implements: "Chunk PLAN.md template with .jinja2 suffix (renamed from PLAN.md)"
  - ref: tests/test_template_system.py#TestIntegration::test_works_with_real_chunk_templates
    implements: "Verifies chunk templates use .jinja2 suffix"
narrative: null
subsystems:
  - subsystem_id: "0001-template_system"
    relationship: implements
---

# Chunk Goal

## Minor Goal

Migrate `src/chunks.py` from its local `render_template` function to use the
canonical `template_system` module. This is the first of four consolidation
chunks to eliminate duplicate template rendering code and enable include
support across all template collections.

This advances the template_system subsystem from REFACTORING toward STABLE by
reducing NON_COMPLIANT code references. After this chunk, `chunks.py` will use
the shared Jinja2 Environment with include support instead of creating bare
`jinja2.Template` instances.

## Success Criteria

- `src/chunks.py` imports `render_template` (or `render_to_directory`) from
  `template_system` instead of defining its own
- The local `render_template` function in `chunks.py` is deleted
- `Chunks::create_chunk` uses the canonical template system functions
- The import of `jinja2` in `chunks.py` is removed (no longer needed)
- Chunk templates in `src/templates/chunk/` are renamed to include the `.jinja2`
  suffix (e.g., `GOAL.md` → `GOAL.md.jinja2`) per the subsystem's hard invariant
- All existing tests pass
- `ve chunk start` command continues to work correctly (manual verification)