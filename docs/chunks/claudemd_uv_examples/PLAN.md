<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a straightforward text replacement in Jinja2 template files. The template already demonstrates the correct pattern—it uses `{% if ve_config is defined and ve_config.is_ve_source_repo %}` to conditionally render VE-source-specific content. The "Development" section (lines 408-423) correctly uses this pattern.

The fix involves:
1. Changing `uv run ve` to `ve` in all examples that are rendered for ALL VE-using projects (not just the vibe-engineer source repo)
2. Leaving the examples inside the `is_ve_source_repo` conditional block unchanged

No tests are needed since this is purely documentation content. Verification will be done by regenerating CLAUDE.md and confirming the output.

## Subsystem Considerations

No subsystems are relevant to this documentation-only change.

## Sequence

### Step 1: Fix CLAUDE.md.jinja2 orchestrator examples

In `src/templates/claude/CLAUDE.md.jinja2`, change all `uv run ve` occurrences in the orchestrator documentation section (lines 265-356) to plain `ve` commands.

Specific locations to change:
- Line 265: `uv run ve chunk create my_chunk --future` → `ve chunk create my_chunk --future`
- Line 274: `uv run ve orch inject my_chunk` → `ve orch inject my_chunk`
- Line 288: `uv run ve orch work-unit delete my_chunk` → `ve orch work-unit delete my_chunk`
- Line 289: `uv run ve orch inject my_chunk` → `ve orch inject my_chunk`
- Line 297: `uv run ve orch attention` → `ve orch attention`
- Line 303: `uv run ve orch answer my_chunk "The answer to the question"` → `ve orch answer my_chunk "The answer to the question"`
- Line 309: `uv run ve orch resolve my_chunk --verdict INDEPENDENT` → `ve orch resolve my_chunk --verdict INDEPENDENT`
- Line 355: `uv run ve orch start` → `ve orch start`
- Line 356: `uv run ve orch inject my_chunk` → `ve orch inject my_chunk`

**Important**: Do NOT change lines 414-415 which are inside the `{% if ve_config.is_ve_source_repo %}` block—those should remain as `uv run ve` since they're specifically for the VE source repo.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 2: Fix discover-subsystems.md.jinja2 examples

In `src/templates/commands/discover-subsystems.md.jinja2`, change the `uv run ve` occurrences to plain `ve` commands.

Specific locations to change:
- Line 30: `uv run ve migration status subsystem_discovery` → `ve migration status subsystem_discovery`
- Line 82: `uv run ve migration create subsystem_discovery` → `ve migration create subsystem_discovery`

Location: `src/templates/commands/discover-subsystems.md.jinja2`

### Step 3: Regenerate CLAUDE.md and verify

Run `uv run ve init` to regenerate the CLAUDE.md file from the template.

Verify:
- The orchestrator examples in the generated CLAUDE.md use plain `ve` commands
- The "Development" section still shows `uv run ve` examples (since it's conditionally rendered only for VE source repo)

### Step 4: Search for any remaining occurrences

Search all template files for any remaining `uv run ve` occurrences outside of `is_ve_source_repo` blocks to ensure completeness.

## Dependencies

None. This is a standalone documentation fix.

## Risks and Open Questions

None. The change is straightforward text replacement with clear boundaries.

## Deviations

(To be populated during implementation if any deviations occur)