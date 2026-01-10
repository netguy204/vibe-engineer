---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/template_system.py
- tests/test_template_system.py
code_references:
- ref: src/template_system.py#ActiveChunk
  implements: Chunk context dataclass with short_name, id, goal_path, plan_path properties
- ref: src/template_system.py#ActiveNarrative
  implements: Narrative context dataclass with short_name, id, overview_path properties
- ref: src/template_system.py#ActiveSubsystem
  implements: Subsystem context dataclass with short_name, id, overview_path properties
- ref: src/template_system.py#TemplateContext
  implements: Project context holder ensuring only one active artifact at a time
- ref: src/template_system.py#list_templates
  implements: Template enumeration helper excluding partials and hidden files
- ref: src/template_system.py#get_environment
  implements: Cached Jinja2 Environment creation per collection
- ref: src/template_system.py#render_template
  implements: Core template rendering with context injection
- ref: src/template_system.py#render_to_directory
  implements: Batch rendering with .jinja2 suffix stripping
- ref: tests/test_template_system.py
  implements: Comprehensive test suite for template system
narrative: null
subsystems:
- subsystem_id: template_system
  relationship: implements
created_after:
- subsystem_impact_resolution
---

# Chunk Goal

## Minor Goal

Create the canonical `src/template_system.py` module that provides a unified
template rendering system for the entire codebase. This foundational work
eliminates the three duplicate `render_template` functions across
`src/chunks.py`, `src/subsystems.py`, and `src/narratives.py`, and establishes
the infrastructure for all future template work.

This chunk is the first step in the template_system subsystem consolidation.
All subsequent migration chunks (chunks, subsystems, narratives, project.py)
depend on this module existing.

## Success Criteria

1. **New module exists**: `src/template_system.py` is created with:
   - A configured Jinja2 `Environment` with include support
   - A `render_template(collection, template_name, **context)` function
   - A `render_to_directory(collection, dest_dir, **context)` function
   - Template enumeration helpers (e.g., `list_templates(collection)`)

2. **Project context object**: A `TemplateContext` class (or similar) that provides
   the base context for all templates:
   - `project.active_chunk` - Non-null when rendering in chunk context, with:
     - `short_name` - The chunk's short name (e.g., "canonical_template_module")
     - `id` - The full chunk ID (e.g., "0023-canonical_template_module")
     - `goal_path` - Convenience property for path to GOAL.md
     - `plan_path` - Convenience property for path to PLAN.md
   - `project.active_narrative` - Non-null when rendering in narrative context, with:
     - `short_name` - The narrative's short name
     - `id` - The full narrative ID (e.g., "0002-feature_name")
     - `overview_path` - Convenience property for path to OVERVIEW.md
   - `project.active_subsystem` - Non-null when rendering in subsystem context, with:
     - `short_name` - The subsystem's short name
     - `id` - The full subsystem ID (e.g., "0001-template_system")
     - `overview_path` - Convenience property for path to OVERVIEW.md

   Only one of these three will be non-null at render time. Templates can assume
   the attribute matching their context is populated.

3. **Include mechanism works**: Templates can use `{% include %}` to include
   partials from a `partials/` subdirectory within their collection

4. **Suffix convention established**: Template files use `.jinja2` suffix;
   `render_to_directory` strips this suffix when writing output files

5. **Collection structure**: Each subdirectory of `src/templates/` is a collection
   (chunk, subsystem, narrative, commands, trunk). The module discovers and
   validates collections automatically.

6. **Tests pass**: Unit tests verify:
   - Template rendering with context variables
   - Project context object with active_chunk/narrative/subsystem
   - Include resolution within collection boundaries
   - Suffix stripping behavior
   - Error handling for missing templates

7. **No existing behavior changed**: This chunk creates the new module but does
   NOT migrate existing code to use it. The duplicate `render_template` functions
   remain until subsequent chunks migrate them. Template files are NOT renamed
   to `.jinja2` in this chunk—that happens during migration chunks.