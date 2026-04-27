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

The template system treats all projects identically — there is no
`is_ve_source_repo` config flag, and no conditional rendering keyed on
"is this the VE source repo?".

Specifically:
1. `.ve-config.yaml` carries no `is_ve_source_repo` field, and `VeConfig`
   in `src/template_system.py` has no such attribute.
2. The CLAUDE.md template (`src/templates/claude/CLAUDE.md.jinja2`) contains
   no vibe-engineer-specific conditional blocks. Python/UV/pytest "Development"
   guidance is host-project responsibility, not VE-managed content.
3. The auto-generated header partial
   (`src/templates/commands/partials/auto-generated-header.md.jinja2`)
   renders unconditionally on every command file in every host project, so
   agents in any project see the "do not edit, regenerate via `ve init`"
   warning.
4. Vibe-engineer's own project-specific documentation (UV commands, template
   editing workflow) lives outside the `<!-- VE:MANAGED:START/END -->` markers
   in this repository's CLAUDE.md, where `ve init` will not overwrite it.

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