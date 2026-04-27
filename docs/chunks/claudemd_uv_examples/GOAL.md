---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/claude/CLAUDE.md.jinja2
  - src/templates/commands/discover-subsystems.md.jinja2
code_references:
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Orchestrator examples using plain ve commands for installed package usage"
  - ref: src/templates/commands/discover-subsystems.md.jinja2
    implements: "Migration CLI examples using plain ve commands"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
created_after: ["claudemd_external_prompt"]
---

# Chunk Goal

## Minor Goal

CLAUDE.md template sections rendered for all VE-using projects use plain `ve` command examples, not `uv run ve`. Only the vibe-engineer source repository needs to invoke `ve` under `uv` to exercise the development version, so unconditional `uv run ve` examples would mislead projects that have installed `ve` as a package.

The template uses `{% if ve_config is defined and ve_config.is_ve_source_repo %}` blocks to gate VE-source-specific content (e.g., the "Development" section warning about running under UV). Code examples outside those conditional blocks — including the orchestrator documentation section in `src/templates/claude/CLAUDE.md.jinja2` and the migration CLI examples in `src/templates/commands/discover-subsystems.md.jinja2` — use plain `ve` commands.

## Success Criteria

- All `uv run ve` references in `src/templates/claude/CLAUDE.md.jinja2` that appear outside of `{% if ve_config.is_ve_source_repo %}` blocks are changed to plain `ve` commands
- All `uv run ve` references in `src/templates/commands/discover-subsystems.md.jinja2` are changed to plain `ve` commands (or wrapped in appropriate conditionals if the skill is VE-source-specific)
- Running `uv run ve init` regenerates `CLAUDE.md` with the corrected examples
- The "Development" section retains its `uv run ve` examples since it's already conditionally rendered only for the VE source repo
- Any other skill templates with `uv run ve` are similarly corrected