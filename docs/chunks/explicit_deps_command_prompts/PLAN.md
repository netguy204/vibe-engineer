<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The dependency chunks (`explicit_deps_goal_docs` and `explicit_deps_template_docs`) have already
updated the template files with comprehensive documentation of the null vs empty semantics:

- `src/templates/chunk/GOAL.md.jinja2` - Documents `depends_on` semantics in the DEPENDS_ON section
- `src/templates/narrative/OVERVIEW.md.jinja2` - Documents `depends_on` in proposed_chunks schema
- `src/templates/investigation/OVERVIEW.md.jinja2` - Documents `depends_on` in proposed_chunks schema

This chunk updates the **command prompts** that guide agents through creating these artifacts. The key
insight is that command prompts need to teach agents **when** to use each form, not just document
what they mean (the templates already do that).

Strategy:
1. Update `/chunk-create` prompt to teach agents the distinction when populating `depends_on`
2. Update `/narrative-create` prompt to explain the semantics for `proposed_chunks.depends_on`
3. Check other commands that reference `depends_on` for consistency (investigation-create already
   defers to chunk-create, so it may not need changes)

Per TESTING_PHILOSOPHY.md, we don't test template prose content. Verification is:
- Templates render without error (`uv run ve init`)
- The documentation is present and readable

<!-- No subsystems are relevant to this chunk - it only modifies documentation/prompts -->

## Sequence

### Step 1: Update `/chunk-create` command prompt

Add documentation to `src/templates/commands/chunk-create.md.jinja2` that teaches agents
the `depends_on` null vs empty semantics. The current prompt already has step 5 about
checking narratives/investigations for dependencies, but it doesn't explain when to
leave the field as `null` vs setting it to `[]`.

Add a new step (or augment step 5) that explains:

1. **When to set `depends_on: []`**: The agent has analyzed the chunk and determined it
   has no implementation dependencies on other chunks in the same batch. This bypasses
   the orchestrator's conflict oracle.

2. **When to leave `depends_on` as `null` or omit it**: The agent hasn't analyzed
   dependencies yet, or the analysis is uncertain. This triggers oracle consultation.

3. **When to set `depends_on: ["chunk_a", ...]`**: The agent knows specific chunks
   that must complete before this one.

The key teaching moment: the default template value of `depends_on: []` is an
**explicit assertion of independence**, not a placeholder to be filled in later.

Location: `src/templates/commands/chunk-create.md.jinja2`

### Step 2: Update `/narrative-create` command prompt

Add documentation to `src/templates/commands/narrative-create.md.jinja2` that explains
the `depends_on` semantics for entries in the `proposed_chunks` array.

The current prompt is minimal (only 3 steps). Add guidance about:

1. When populating `proposed_chunks` entries, the `depends_on` field follows the same
   null vs empty semantics as chunk GOAL.md.

2. Index-based dependencies (`[0, 2]`) are converted to chunk directory names at
   chunk-create time.

3. If the agent doesn't know dependencies between proposed chunks, **omit the field**
   rather than using `[]`. Using `[]` asserts independence.

Location: `src/templates/commands/narrative-create.md.jinja2`

### Step 3: Check `/investigation-create` for consistency

Review `src/templates/commands/investigation-create.md.jinja2` to determine if it needs
updates. Based on initial review, it delegates chunk creation to `/chunk-create`, so it
may not need direct `depends_on` documentation. However, it does mention "Proposed Chunks"
in Phase 2A step 6, which might benefit from a note about the semantics.

If changes are needed, add similar guidance as Step 2.

Location: `src/templates/commands/investigation-create.md.jinja2`

### Step 4: Verify templates render correctly

Run `uv run ve init` to regenerate rendered command files and verify no syntax errors.

Location: Project root

### Step 5: Update code_paths in GOAL.md

Add the modified template files to the `code_paths` frontmatter field in the chunk's
GOAL.md for traceability.

Location: `docs/chunks/explicit_deps_command_prompts/GOAL.md`

## Dependencies

This chunk depends on:

- **explicit_deps_goal_docs** (ACTIVE): Updated `src/templates/chunk/GOAL.md.jinja2` with the
  semantics table. This chunk's command prompts reference that documentation.

- **explicit_deps_template_docs** (ACTIVE): Updated `src/templates/narrative/OVERVIEW.md.jinja2`
  and `src/templates/investigation/OVERVIEW.md.jinja2` with the semantics table. This chunk's
  command prompts reference that documentation.

Both dependencies are satisfied (status: ACTIVE).

## Risks and Open Questions

- **Prompt length**: Adding detailed `depends_on` guidance increases command prompt length.
  The chunk-create prompt is already substantial. Keeping the new content concise is important.

- **Redundancy with templates**: The templates now contain the semantics table. The command
  prompts should teach **when to use each form** without duplicating the full semantics
  documentation. Reference the templates rather than repeating everything.

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