<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only change to the CLAUDE.md Jinja2 template. The goal is to add a prominent warning that prevents agents from bypassing the template system by manually creating artifact files (GOAL.md, PLAN.md, OVERVIEW.md).

**Strategy**: Add a new section to `src/templates/claude/CLAUDE.md.jinja2` called "Creating Artifacts" that:
1. Explicitly prohibits manual creation of artifact files
2. Lists the commands to use instead
3. Explains why this matters (templates contain required frontmatter and structure)

**Placement**: The new section should appear after "Available Commands" and before "Getting Started", since it provides critical context for using those commands correctly.

**Testing approach**: Per TESTING_PHILOSOPHY.md, we don't test template prose content. The verification is:
1. Run `uv run ve init` to regenerate CLAUDE.md
2. Visually confirm the new guidance appears in the rendered output

This chunk USES the template_system subsystem (STABLE) - we're adding content to an existing template, following the established rendering workflow.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system by modifying `src/templates/claude/CLAUDE.md.jinja2`. The subsystem is STABLE, so we follow its established patterns:
  - Templates use `.jinja2` suffix
  - Templates are rendered via `ve init` (which uses `render_template`)
  - No custom Jinja2 logic required - just static markdown content

## Sequence

### Step 1: Add "Creating Artifacts" section to CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` to add a new section between "Available Commands" and "Getting Started".

The section should include:
1. A clear **CRITICAL** warning that agents must never manually create artifact files
2. A table mapping artifact types to their creation commands:
   - Chunks → `ve chunk create` or `/chunk-create`
   - Investigations → `ve investigation create` or `/investigation-create`
   - Narratives → `ve narrative create` or `/narrative-create`
   - Subsystems → `ve subsystem create` or `/subsystem-discover`
3. A brief explanation of why this matters (templates contain required frontmatter, structure, and schema guidance)

Location: `src/templates/claude/CLAUDE.md.jinja2` (insert after line ~208, after the "Available Commands" section)

### Step 2: Regenerate CLAUDE.md and verify

Run `uv run ve init` to regenerate the CLAUDE.md file from the updated template.

Verify the new "Creating Artifacts" section appears in the rendered `CLAUDE.md` between "Available Commands" and "Getting Started".

**Note**: No code backreferences needed for this chunk - it only modifies template content, not code logic.

## Dependencies

None. The template file exists and the template system is STABLE.

## Risks and Open Questions

- **Section placement**: The plan places the new section after "Available Commands" and before "Getting Started". This seems logical (know the commands → know how to use them → get started), but could alternatively go earlier in the document for more prominence. The chosen placement keeps the "Getting Started" section as the natural entry point for new agents.

## Deviations

*To be populated during implementation.*