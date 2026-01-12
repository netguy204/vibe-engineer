<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add documentation for the Friction Log artifact type to the CLAUDE.md.jinja2 template. The content will be placed in the artifact documentation hierarchy alongside Chunks, Narratives, Subsystems, and Investigations.

Key aspects:
1. **Mirror existing documentation patterns**: Follow the structure used for other artifact types (location, file format, status values, when to use)
2. **Emphasize unique characteristics**: Friction logs differ from other artifacts in being accumulative ledgers with entry-level (not artifact-level) lifecycle
3. **Reference the canonical location**: `docs/trunk/FRICTION.md`
4. **Document the slash command**: `/friction-log` for quick capture
5. **Explain the bidirectional linking**: How chunks reference friction via `friction_entries`

This is documentation-only work - no tests needed since CLAUDE.md content is verified by `ve init` regeneration.

## Subsystem Considerations

No subsystems are directly relevant. This chunk adds documentation to the template system but doesn't modify template rendering behavior.

## Sequence

### Step 1: Add Friction Log section to CLAUDE.md.jinja2

Add a new section `## Friction Log (\`docs/trunk/FRICTION.md\`)` to the template. Position it after the "Investigations" section to maintain the artifact hierarchy flow (from work units to exploratory artifacts to accumulative artifacts).

Content to document:
- **What friction logs are**: Accumulative ledgers for capturing pain points over time
- **How they differ from other artifacts**:
  - Indefinite lifespan (not bounded like investigations or chunks)
  - Many entries per artifact (ledger, not document)
  - No artifact-level status (always "active")
- **Entry structure**: `### FXXX: YYYY-MM-DD [theme-id] Title`
- **Themes**: Categories that emerge organically as entries accumulate
- **Entry lifecycle**: OPEN → ADDRESSED → RESOLVED (derived from proposed_chunks links)
- **How friction spawns work**: When patterns emerge, add proposed_chunks with addresses linking to entry IDs

Location: `src/templates/claude/CLAUDE.md.jinja2`

Add a Jinja chunk backreference comment: `{# Chunk: docs/chunks/friction_claude_docs - Friction log documentation #}`

### Step 2: Update "When to use each artifact type" guidance

Extend the existing guidance block that explains when to use investigations vs chunks vs narratives. Add friction logs to this list:

- **Friction Log**: When you encounter a pain point that doesn't need immediate action but should be remembered. Captures friction over time; patterns emerge organically.

This helps agents choose the right artifact type for their situation.

Location: Within the Investigations section of `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Add /friction-log to Available Commands

Add the friction log command to the "Available Commands" section:

- `/friction-log` - Capture a friction point for later pattern analysis

Location: `src/templates/claude/CLAUDE.md.jinja2` in the Available Commands list

### Step 4: Document friction_entries in Chunk Frontmatter References

Extend the "Chunk Frontmatter References" section to mention the `friction_entries` field:

- **friction_entries**: Links to friction log entries this chunk addresses (provides "why did we do this work?" traceability)

This documents the bidirectional link from chunks back to friction.

Location: `src/templates/claude/CLAUDE.md.jinja2` in the Chunk Frontmatter References subsection

### Step 5: Regenerate CLAUDE.md and verify

Run `uv run ve init` to regenerate CLAUDE.md from the updated template. Verify:
1. The Friction Log section appears in the rendered output
2. Section ordering is correct (after Investigations)
3. `/friction-log` appears in Available Commands
4. `friction_entries` appears in Chunk Frontmatter References

## Dependencies

- **friction_template_and_cli** (ACTIVE): The friction log artifact must exist before we document it. This chunk is complete.

## Risks and Open Questions

- **friction_entries not yet implemented**: The `friction_chunk_linking` chunk that adds `friction_entries` to the chunk template is still FUTURE. We'll document the field in CLAUDE.md regardless, since the investigation has already designed it and documentation can precede implementation. If the field design changes during implementation, CLAUDE.md would need updating.

## Deviations

<!-- Populate during implementation -->