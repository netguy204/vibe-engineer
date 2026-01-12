<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The existing GOAL.md template (`src/templates/chunk/GOAL.md.jinja2`) documents most frontmatter fields in a comment block (STATUS, PARENT_CHUNK, CODE_PATHS, CODE_REFERENCES, etc.), but **`created_after` has no documentation at all**. This explains why agents misunderstand its semantics.

The fix is to add a `CREATED_AFTER` documentation section to the comment block, following the same format as other fields. The documentation must:

1. Explain what `created_after` actually is: the "tips" of the chunk DAG when this chunk was created (chunks with no dependents yet)
2. Clarify that tips must be ACTIVE chunks (shipped work), not FUTURE chunks
3. Warn against the common anti-pattern of confusing this with implementation dependencies
4. Point to where implementation dependencies *should* be tracked (investigation/narrative ordering, design docs)

No code changes are needed - this is purely a template documentation update. No new tests are required since this doesn't change behavior, only agent guidance.


## Sequence

### Step 1: Add CREATED_AFTER documentation block to GOAL.md template

Add a new `CREATED_AFTER:` section to the comment block in `src/templates/chunk/GOAL.md.jinja2`, following the same format as existing field documentation (STATUS, PARENT_CHUNK, etc.).

The documentation should include:
- **What it is**: List of chunk directory names representing the "tips" of the chunk DAG at creation time
- **What tips are**: ACTIVE chunks that have no dependents yet (no other chunk references them in their `created_after`)
- **Auto-populated**: This field is automatically populated by `ve chunk create` - agents should not modify it
- **Key constraint**: Tips must be ACTIVE (shipped) chunks, never FUTURE chunks
- **Common mistake**: Warning against confusing `created_after` with implementation dependencies
- **Where to track dependencies**: Point to investigation `proposed_chunks` ordering, narrative chunk sequencing, and design documents

Location: src/templates/chunk/GOAL.md.jinja2

### Step 2: Regenerate rendered files

Run `uv run ve init` to propagate the template changes to any rendered GOAL.md files (primarily affecting the template itself, not existing chunks).

### Step 3: Verify the change

1. Confirm the new documentation appears in the template
2. Create a test chunk to verify the rendered GOAL.md includes the new documentation


## Risks and Open Questions

- The documentation length may make the comment block quite long. The balance between thoroughness and readability is subjective - will aim for concise but complete.

## Deviations

<!-- Populate during implementation -->