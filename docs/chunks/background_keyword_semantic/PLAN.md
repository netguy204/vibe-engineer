<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only chunk that adds guidance to CLAUDE.md about the "background" keyword semantic. The implementation involves:

1. **Adding a new subsection to the "Working with the Orchestrator" section** in `src/templates/claude/CLAUDE.md.jinja2` that documents when and how agents should use the background workflow.

2. **Adding guidance to the chunk GOAL.md template** (`src/templates/chunk/GOAL.md.jinja2`) reminding agents that FUTURE chunks created via the background workflow require operator review before commit/inject.

Per DEC-005 (Commands do not prescribe git operations), the documentation will describe the workflow without mandating specific git commit strategies.

The templates are part of the `template_system` subsystem (STABLE), so this chunk follows its patterns for template location and will trigger a re-render via `ve init` to verify output.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template_system subsystem. All template modifications follow the established patterns:
  - Templates are in `src/templates/` with `.jinja2` suffix
  - Changes are verified by running `ve init` to re-render
  - CLAUDE.md has Jinja2 chunk backreference comments

## Sequence

### Step 1: Add "Background Keyword" subsection to CLAUDE.md template

Add a new subsection titled "### The 'Background' Keyword" after the "Proactive Orchestrator Support" subsection in `src/templates/claude/CLAUDE.md.jinja2`.

The subsection should document:

1. **Trigger phrases** that indicate background workflow:
   - "do this in the background"
   - "handle this in the background"
   - "run this in the background"
   - "in the background"

2. **Expected agent behavior**:
   - Create FUTURE chunk (not IMPLEMENTING)
   - Refine GOAL.md with operator
   - Present goal for operator review and **wait for approval**
   - Commit the chunk only after approval
   - Inject into orchestrator
   - Continue with other work or confirm completion

3. **Contrast with default behavior**:
   - Without "background": Create IMPLEMENTING chunk, work on it immediately
   - With "background": Create FUTURE chunk, inject into orchestrator, move on

Location: `src/templates/claude/CLAUDE.md.jinja2` (after line 283, the "Proactive Orchestrator Support" subsection)

Add a chunk backreference comment before the new section following the pattern of other sections:
```jinja2
{# Chunk: docs/chunks/background_keyword_semantic - Background keyword documentation #}
```

### Step 2: Add FUTURE chunk guidance to GOAL.md template

Add guidance to the chunk GOAL.md template (`src/templates/chunk/GOAL.md.jinja2`) in the STATUS VALUES comment block, after the FUTURE status description.

The guidance should remind agents:
- FUTURE chunks created via "background" keyword require operator review
- Do not commit or inject until the operator approves the GOAL.md
- This ensures the operator stays in the loop for backgrounded work

Location: `src/templates/chunk/GOAL.md.jinja2` (around line 28-29, after the FUTURE status value description)

### Step 3: Re-render templates and verify

Run `ve init` to re-render CLAUDE.md from the updated template. Verify:
- The new "Background Keyword" subsection appears in CLAUDE.md
- The rendered file maintains proper formatting
- No existing content is disrupted

### Step 4: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter with the files being modified:
- `src/templates/claude/CLAUDE.md.jinja2`
- `src/templates/chunk/GOAL.md.jinja2`

## Risks and Open Questions

1. **Phrase coverage**: The documented trigger phrases may not cover all natural language variations operators use. The current list is based on the goal description; if operators consistently use other phrasings, future work may need to expand the list.

2. **Operator workflow interruption**: Requiring approval before commit/inject adds a pause to the workflow. This is intentional (per the goal), but could feel slow if the operator expects immediate backgrounding.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->