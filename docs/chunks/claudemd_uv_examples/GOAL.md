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

Remove `uv run` prefix from `ve` command examples in CLAUDE.md template sections that are rendered for all VE-using projects, not just the vibe-engineer repository itself.

Currently, the orchestrator documentation section in `src/templates/claude/CLAUDE.md.jinja2` uses `uv run ve` in code examples (lines 265-356). This is incorrect guidance for projects that have installed `ve` as a package—only the vibe-engineer source repository needs to run `ve` under `uv` to use the development version.

The template already has conditional sections using `{% if ve_config is defined and ve_config.is_ve_source_repo %}` for VE-source-specific content (like the "Development" section warning about running under UV). The orchestrator examples should use plain `ve` commands since they are not wrapped in this conditional.

Also check the `discover-subsystems.md.jinja2` skill template which has similar unconditional `uv run ve` examples.

## Success Criteria

- All `uv run ve` references in `src/templates/claude/CLAUDE.md.jinja2` that appear outside of `{% if ve_config.is_ve_source_repo %}` blocks are changed to plain `ve` commands
- All `uv run ve` references in `src/templates/commands/discover-subsystems.md.jinja2` are changed to plain `ve` commands (or wrapped in appropriate conditionals if the skill is VE-source-specific)
- Running `uv run ve init` regenerates `CLAUDE.md` with the corrected examples
- The "Development" section retains its `uv run ve` examples since it's already conditionally rendered only for the VE source repo
- Any other skill templates with `uv run ve` are similarly corrected