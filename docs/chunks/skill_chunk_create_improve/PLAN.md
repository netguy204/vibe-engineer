

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk modifies a single file: `src/templates/commands/chunk-create.md.jinja2`.
The changes are purely to the skill template prose — no Python code, no CLI logic,
no tests needed (per docs/trunk/TESTING_PHILOSOPHY.md: "We verify templates render
without error and files are created, but don't assert on template prose").

The two improvements are:

1. **Skill description (line 2)** — Rewrite the `description:` frontmatter to include
   trigger phrases that match how operators naturally ask for chunk creation. Currently
   it says "Create a new chunk of work and refine its goal." which misses phrases like
   "start new work", "chunk this", "make a chunk for X".

2. **Context capture instructions (step 4)** — Expand the GOAL.md refinement step to
   explicitly instruct the creating agent to extract and embed conversation context
   that would be lost when handing off to an implementing agent in a separate session.

The template system (docs/subsystems/template_system) renders this Jinja2 template
into `.claude/commands/chunk-create.md` via `ve init`. Our changes stay within the
template source per the template editing workflow in CLAUDE.md.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system.
  We edit the Jinja2 source template and rely on `ve init` to render it. No
  deviations from the subsystem's patterns are introduced.

## Sequence

### Step 1: Improve the skill description for discoverability

Location: `src/templates/commands/chunk-create.md.jinja2`, line 2 (the `description:` field)

Current description:
```
description: Create a new chunk of work and refine its goal.
```

Replace with a description that includes trigger phrases operators naturally use.
The description should trigger on phrases like:
- "create a chunk"
- "start new work" / "start a new chunk"
- "chunk this work" / "chunk this"
- "make a chunk for X"
- "define a piece of work"
- "break this into a chunk"

New description (draft):
```
description: Create a new chunk of work and refine its goal. Use when the operator wants to start new work, chunk something, define a piece of work, or break work into a chunk.
```

The description field is used by the skill matching system to decide when to
trigger. Including verb phrases that operators use ("start new work", "chunk this")
improves recall without hurting precision.

### Step 2: Add context capture guidance to the GOAL.md refinement step

Location: `src/templates/commands/chunk-create.md.jinja2`, step 4 (currently lines 59-62)

Current step 4:
```
4. Refine the contents of <chunk directory>/GOAL.md given the piece of work that
   the user has described, ask them any questions required to complete the
   template and cohesively and thoroughly define the goal of what they're trying
   to accomplish.
```

Expand this step to instruct the creating agent to capture conversation context
that would otherwise be lost. The implementing agent will work in a separate
session without access to the conversation that spawned the chunk.

New step 4 should include explicit guidance to embed:

- **Specific file paths and function names** referenced in the conversation
- **Error messages or reproduction steps** for bugs
- **Design decisions and rejected alternatives** discussed
- **Code patterns or snippets** that illustrate the desired behavior
- **Operator preferences or constraints** mentioned verbally
- **Links to related artifacts** (chunks, investigations, subsystems, narratives)

The key insight: anything the creating agent "just knows" from conversation
context must be written into the GOAL.md, because the implementing agent will
have zero conversation context. The goal should be **self-contained** — an agent
reading only the GOAL.md should have everything needed to plan and implement.

### Step 3: Verify rendering

Run `uv run ve init` to re-render the template and confirm the output at
`.claude/commands/chunk-create.md` looks correct. Spot-check that:
- The description field renders properly
- The new step 4 guidance is present
- No existing functionality is broken (naming, frontmatter steps, etc.)
- The Jinja2 template syntax is valid (no render errors)

## Dependencies

None. This chunk modifies only the chunk-create skill template.

## Risks and Open Questions

- **Description length**: The skill description field may have a practical length
  limit where matching quality degrades. If the expanded description causes issues,
  fall back to a shorter version with the most impactful trigger phrases.
- **Over-prescription in step 4**: Too many sub-bullets in the context capture
  guidance could make the step feel overwhelming. Balance thoroughness with
  readability — the guidance should feel like a natural checklist, not an essay.

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