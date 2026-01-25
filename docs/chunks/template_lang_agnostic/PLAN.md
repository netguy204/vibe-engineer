# Implementation Plan

## Approach

The strategy is straightforward: remove the `is_ve_source_repo` conditional infrastructure
entirely and make templates language-agnostic by:

1. **Always render auto-generated headers on slash commands** - The header tells agents not
   to edit files that will be overwritten on `ve init`. This applies in any project, not
   just vibe-engineer itself.

2. **Remove the Development section from VE-managed content** - Development instructions
   (test commands, package managers) are host project responsibilities. VE shouldn't
   prescribe these.

3. **Move vibe-engineer-specific content outside the VE:MANAGED markers** - The Template
   Editing Workflow and UV command guidance are specific to this repository and should
   live after the `<!-- VE:MANAGED:END -->` marker in CLAUDE.md.

4. **Remove `is_ve_source_repo` from config and code** - Once templates no longer use the
   flag, remove it from `VeConfig`, `.ve-config.yaml`, and all tests.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk modifies the template system.
  The subsystem is STABLE, so changes should be minimal and deliberate. The changes
  here simplify the system by removing a conditional path, which aligns with the
  subsystem's intent of unified template rendering.

  After implementation, update the subsystem's code_references to remove the
  `is_ve_source_repo` documentation from the VeConfig reference.

## Sequence

### Step 1: Update the auto-generated header partial to always render

Remove the `is_ve_source_repo` conditional from
`src/templates/commands/partials/auto-generated-header.md.jinja2`.

The header should always render, warning agents in any host project not to edit
the file.

**Before:**
```jinja2
{# Only render in ve source repository #}
{% if ve_config is defined and ve_config.is_ve_source_repo %}
<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
...
-->

{% endif %}
```

**After:**
```jinja2
<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/{{ source_template }}
Edit the source template, then run `ve init` to regenerate.
-->

```

Location: `src/templates/commands/partials/auto-generated-header.md.jinja2`

### Step 2: Remove the Development section from CLAUDE.md template

Delete the "## Development" section entirely from the CLAUDE.md.jinja2 template.
This section currently says "This project uses UV for package management. Run
tests with `uv run pytest tests/`." followed by a conditional block about using
UV for the `ve` command.

Development/testing guidance is the host project's responsibility. VE should not
prescribe it.

Location: `src/templates/claude/CLAUDE.md.jinja2` (lines 413-431)

### Step 3: Remove the Template Editing Workflow section from CLAUDE.md template

Delete the conditional "## Template Editing Workflow" section from CLAUDE.md.jinja2.

This content will be moved to vibe-engineer's CLAUDE.md outside the managed markers
(Step 5).

Location: `src/templates/claude/CLAUDE.md.jinja2` (lines 432-456)

### Step 4: Remove the auto-generated header from CLAUDE.md template

Remove the conditional auto-generated header at the top of CLAUDE.md.jinja2.

The VE:MANAGED markers already serve this purpose for CLAUDE.md - agents know
not to edit content inside those markers. Adding a header above the markers
is redundant.

Location: `src/templates/claude/CLAUDE.md.jinja2` (lines 1-9)

### Step 5: Add project-specific content to vibe-engineer's CLAUDE.md

After the `<!-- VE:MANAGED:END -->` marker in CLAUDE.md, add the vibe-engineer-specific
documentation:

1. **Development section** - UV package management, `uv run ve` guidance
2. **Template Editing Workflow section** - Instructions for editing templates

This content lives outside the managed section, so it won't be overwritten by
`ve init` and is specific to this repository.

Location: `CLAUDE.md` (after the VE:MANAGED:END marker)

Note: This requires a two-step approach:
- First, run `ve init` to render the cleaned-up template
- Then manually add the project-specific content after the marker

### Step 6: Remove `is_ve_source_repo` from VeConfig

Update `src/template_system.py`:

1. Remove the `is_ve_source_repo` attribute from the `VeConfig` dataclass
2. Remove `is_ve_source_repo` from the `as_dict()` method
3. Remove the `is_ve_source_repo` parsing from `load_ve_config()`
4. Update the docstring to remove `is_ve_source_repo` documentation

Location: `src/template_system.py` (VeConfig class and load_ve_config function)

### Step 7: Remove `is_ve_source_repo` from .ve-config.yaml

Delete the `is_ve_source_repo: true` line from `.ve-config.yaml`.

Location: `.ve-config.yaml`

### Step 8: Update tests for VeConfig

Update `tests/test_template_system.py`:

1. Remove `TestVeConfig::test_default_is_ve_source_repo_false`
2. Remove `TestVeConfig::test_is_ve_source_repo_true`
3. Update `TestVeConfig::test_as_dict` to remove `is_ve_source_repo` assertion
4. Update `TestVeConfig::test_load_ve_config_missing_file` to not check `is_ve_source_repo`
5. Remove `test_load_ve_config_reads_is_ve_source_repo_true`
6. Remove `test_load_ve_config_reads_is_ve_source_repo_false`
7. Update `test_load_ve_config_missing_key` (currently checks missing `is_ve_source_repo`)
8. Update `test_load_ve_config_empty_file` to not check `is_ve_source_repo`

Update or remove `TestVeConfigInTemplates`:
1. Update tests that check for auto-generated header behavior (now unconditional)
2. Remove tests for Template Editing Workflow section (no longer in template)
3. Remove tests for `is_ve_source_repo`-conditional UV guidance

Location: `tests/test_template_system.py`

### Step 9: Update subsystem documentation

Update `docs/subsystems/template_system/OVERVIEW.md`:

1. Update the VeConfig code reference to reflect the simplified dataclass
   (remove "with is_ve_source_repo flag" from description)

Location: `docs/subsystems/template_system/OVERVIEW.md`

### Step 10: Verify changes

Run `ve init` to regenerate the CLAUDE.md and command files, then verify:

1. All command files in `.claude/commands/` have auto-generated headers
2. CLAUDE.md no longer has the Development or Template Editing Workflow sections
   inside the VE:MANAGED markers
3. Tests pass with `uv run pytest tests/test_template_system.py -v`

## Dependencies

None. This chunk simplifies existing code without introducing new dependencies.

## Risks and Open Questions

1. **Existing host projects using vibe-engineer** - After this change, running
   `ve init` in any project will add auto-generated headers to command files.
   This is a breaking change in that sense, but the headers are correct behavior
   and should not cause issues.

2. **VE-managed content shrinking** - The VE:MANAGED section will now be smaller
   (no Development section). Projects that previously had this content rendered
   will see it disappear on the next `ve init`. However, this is correct - that
   content was never appropriate for VE to prescribe.

## Deviations

*To be populated during implementation.*