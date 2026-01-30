---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
  - src/templates/commands/partials/auto-generated-header.md.jinja2
  - src/template_system.py
  - .ve-config.yaml
  - CLAUDE.md
code_references:
  - ref: src/template_system.py#VeConfig
    implements: "Simplified VE config dataclass (removed is_ve_source_repo flag)"
  - ref: src/template_system.py#load_ve_config
    implements: "Config loader (no longer reads is_ve_source_repo)"
  - ref: src/templates/commands/partials/auto-generated-header.md.jinja2
    implements: "Unconditional auto-generated header for command templates"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Language-agnostic CLAUDE.md template (no Development or Template Editing sections)"
narrative: null
investigation: null
subsystems:
  - subsystem_id: template_system
    relationship: implements
friction_entries: []
bug_type: null
created_after: ["chunk_last_active"]
---

# Chunk Goal

## Minor Goal

Remove the `is_ve_source_repo` configuration option entirely and simplify the
template system so all projects are treated identically.

Currently:
1. `is_ve_source_repo` in `.ve-config.yaml` enables conditional template rendering
2. The CLAUDE.md template has conditional blocks for vibe-engineer-specific
   content (Development section, Template Editing Workflow)
3. The auto-generated header on command files only renders when `is_ve_source_repo`
   is true
4. The "Development" section with Python/UV/pytest guidance renders for all projects

Changes needed:
1. **Auto-generated headers**: Should ALWAYS render on command files, not just
   in vibe-engineer. Agents in any host project shouldn't edit those files
   either - they'd be overwritten on the next `ve init`.
2. **Development/testing guidance**: Remove entirely from VE-managed content.
   This is host project responsibility, not VE's.
3. **Template editing workflow**: Move outside VE-managed markers in vibe-engineer's
   own CLAUDE.md - it's project-specific documentation.
4. **`is_ve_source_repo` config**: Remove entirely from VeConfig and templates.

## Success Criteria

1. Remove `is_ve_source_repo` from `VeConfig` class in `src/template_system.py`
2. Remove `is_ve_source_repo` from `.ve-config.yaml`
3. Update `src/templates/commands/partials/auto-generated-header.md.jinja2` to
   always render (remove the conditional)
4. Remove the "Development" section from `src/templates/claude/CLAUDE.md.jinja2`
5. Remove all `is_ve_source_repo` conditionals from CLAUDE.md template
6. Move vibe-engineer's project-specific documentation (UV commands, template
   editing workflow) outside the `<!-- VE:MANAGED:START/END -->` markers in
   this repository's CLAUDE.md
7. Running `ve init` in any project produces identical VE-managed content