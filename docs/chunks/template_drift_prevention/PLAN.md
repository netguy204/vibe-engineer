<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This implementation introduces configuration-driven conditional template rendering. The approach:

1. **Configuration file**: Create `.ve-config.yaml` at repository root with `is_ve_source_repo: true` flag
2. **Config loading**: Add a `load_ve_config()` function to read the config during template rendering
3. **Pass config to templates**: Thread the config through the template system so templates can access `is_ve_source_repo`
4. **Conditional headers**: Add Jinja2 conditionals to templates that render auto-generated warnings when the flag is true
5. **Workflow documentation**: Add a conditional section to CLAUDE.md explaining template editing workflow

The implementation builds on the existing `template_system.py` module and extends `render_template` / `render_to_directory` to accept and pass through project configuration.

## Subsystem Considerations

- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the template subsystem for rendering. We extend the subsystem by adding project configuration context to template rendering.

## Sequence

### Step 1: Create .ve-config.yaml in ve source repository

Create the configuration file at the repository root with:

```yaml
# VE Project Configuration
# This file identifies project-level settings for vibe-engineer tooling.

# Set to true in the vibe-engineer source repository.
# When true, rendered templates include auto-generated headers warning
# against direct editing.
is_ve_source_repo: true
```

Location: `.ve-config.yaml` (repository root)

### Step 2: Add config loading to template system

Add a function to load and parse `.ve-config.yaml`:

```python
def load_ve_config(project_dir: pathlib.Path) -> dict:
    """Load .ve-config.yaml from project root, returning empty dict if absent."""
```

Extend `render_template` and `render_to_directory` to accept an optional `ve_config` dict and pass it to templates.

Location: `src/template_system.py`

### Step 3: Update project.py to pass config to template rendering

Modify `_init_commands()` and `_init_claude_md()` to load the ve config and pass it to template rendering functions.

Location: `src/project.py`

### Step 4: Add auto-generated header partial template

Create a reusable partial that renders the auto-generated warning header:

```jinja2
{# Only render in ve source repository #}
{% if ve_config.is_ve_source_repo %}
<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: {{ source_template }}
Edit the source template, then run `ve project init` to regenerate.
-->

{% endif %}
```

Location: `src/templates/commands/partials/auto-generated-header.md.jinja2`

### Step 5: Add header to command templates

Update command templates to include the auto-generated header partial at the top (after frontmatter).

Location: `src/templates/commands/*.jinja2`

### Step 6: Add header and workflow section to CLAUDE.md template

1. Add the auto-generated header at the top
2. Add a conditional "Template Editing Workflow" section explaining:
   - Which files are rendered from templates
   - The source template locations
   - How to edit (modify template, re-render with `ve project init`)

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 7: Re-render templates in ve source repository

Run `ve project init` to regenerate all rendered files with the new headers.

### Step 8: Write tests

Add tests for:
- `load_ve_config()` with file present/absent
- Template rendering with `is_ve_source_repo: true` includes header
- Template rendering with `is_ve_source_repo: false` or absent omits header

Location: `tests/test_template_system.py`

## Dependencies

- PyYAML for parsing `.ve-config.yaml` (already a dependency via ruamel.yaml or standard yaml)

## Risks and Open Questions

- **YAML library choice**: Need to verify which YAML library is available (ruamel.yaml vs PyYAML). Will check pyproject.toml.

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