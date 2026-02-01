---
status: SUPERSEDED
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
- src/templates/commands/chunk-plan.md.jinja2
- src/templates/commands/partials/auto-generated-header.md.jinja2
code_references: []
narrative: null
investigation: template_drift
subsystems: []
created_after: ["restore_template_content", "template_drift_prevention"]
superseded_by: "Commit a465762 (refactor: remove chunk/narrative backreferences, simplify subsystems)"
---

# Chunk Goal

## Minor Goal

Add Jinja backreference comments to source templates for traceability. This mirrors the code backreference pattern (e.g., `# Chunk: docs/chunks/foo`) but uses Jinja comment syntax (`{# Chunk: docs/chunks/foo #}`).

These comments:
- Are visible only in source templates (stripped during rendering)
- Help future agents understand why template sections exist
- Provide traceability from template content back to the chunks that added it

This addresses a finding from the template_drift investigation: when agents modify rendered files without knowing they're derived from templates, having backreferences in the source templates makes the provenance clear to anyone reading the template source.

## Success Criteria

- Key template sections have `{# Chunk: ... #}` comments identifying which chunk added them
- Comments follow the same format as code backreferences: `{# Chunk: docs/chunks/<directory> - <brief description> #}`
- At minimum, add backreferences to:
  - The auto-generated header mechanism (added by template_drift_prevention)
  - The proposed_chunks documentation (restored by restore_template_content)
  - The Template Editing Workflow section (added by template_drift_prevention)
- Tests pass
- Templates render correctly (comments stripped from output)