<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a documentation-only change to the CLAUDE.md Jinja2 template. The approach is straightforward:

1. Add a brief "Learning Philosophy" section to the CLAUDE.md template
2. Place it after the "Getting Started" section where it flows naturally
3. Keep it concise (~10-12 lines) per the success criteria
4. Verify the template renders correctly with `ve init`

The content draws from the investigation's learning philosophy prototype (`docs/investigations/task_agent_experience/prototypes/LEARNING_PHILOSOPHY.md`), distilled to the essential message:
- Chunks first (immediate gratification)
- Larger artifacts discovered when needed (narratives, subsystems, investigations)
- Tasks for multi-project work
- Orchestration for parallel workflows

No code changes, no new tests required—this is purely documentation content. The existing template rendering tests in the codebase already cover that templates render without error (per TESTING_PHILOSOPHY.md: "We verify templates render without error and files are created, but don't assert on template prose").

## Subsystem Considerations

No subsystems are relevant to this chunk. This is a documentation-only change that doesn't touch any code patterns or architectural subsystems.

## Sequence

### Step 1: Add "Learning Philosophy" section to CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` to add a new "Learning Philosophy" section after the "Getting Started" section.

**Content to add** (approximately 10-12 lines):

```markdown
## Learning Philosophy

You don't need to learn everything upfront. Vibe engineering is designed to meet you where you are:

1. **Start with chunks** - The create → plan → implement → complete cycle gives immediate, tangible progress. Most work lives here.
2. **Discover larger artifacts when needed** - Narratives emerge when work is too big for one chunk. Subsystems emerge when you keep touching the same patterns. Investigations emerge when you need to understand before acting.
3. **Graduate to tasks for multi-project work** - When work spans repositories, the same patterns apply at a larger scale.
4. **Use orchestration for parallel workflows** - When managing multiple concurrent workstreams, the orchestrator (`ve orch`) automates scheduling, attention routing, and conflict detection.

The documentation teaches itself: follow backreferences in code to discover the chunks and subsystems that govern it. Each artifact type is discovered when the current level becomes insufficient.
```

**Location**: `src/templates/claude/CLAUDE.md.jinja2`, after line 131 (the "Getting Started" section)

**Backreference comment**: Add a Jinja comment before the section:
```jinja2
{# Chunk: docs/chunks/learning_philosophy_docs - Learning philosophy section #}
```

### Step 2: Regenerate CLAUDE.md and verify

Run `uv run ve init` to regenerate CLAUDE.md from the template.

Verify:
- The command succeeds without errors
- CLAUDE.md contains the new "Learning Philosophy" section
- The section appears after "Getting Started"
- The content is ~10-12 lines as specified

## Dependencies

No dependencies. The CLAUDE.md template already exists and is functional.

## Risks and Open Questions

- **Placement**: The plan places the section after "Getting Started". An alternative would be a new subsection within "Getting Started". The current approach (separate section) is cleaner and matches the existing document structure.

- **Orchestration mention**: The GOAL.md mentions orchestration (`ve orch`) for parallel workflows. This feature may not be fully documented yet—the mention is forward-looking and sets expectations without requiring the feature to exist.

## Deviations

_To be populated during implementation._