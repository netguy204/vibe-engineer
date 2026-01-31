<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends the `proposed_chunks` schema in both narrative and investigation templates to support a `depends_on` field. The field uses index-based references, allowing agents to express dependencies between proposed chunks before they are created as actual chunks.

The approach follows the pattern already demonstrated in the `explicit_chunk_deps` narrative's OVERVIEW.md, which uses `depends_on: [0, 2]` syntax to reference prompts at indices 0 and 2 in the same `proposed_chunks` array.

Key design decisions:
- **Index-based references**: Since proposed chunks don't have directory names yet (they're just prompts), we use array indices as stable identifiers within a single proposed_chunks array
- **Zero-based indexing**: Matches standard programming conventions
- **Schema documentation in templates**: The templates contain extensive comment blocks explaining each field; we add `depends_on` documentation to these blocks

The work is purely template editing - no runtime code changes. This is a schema extension that chunk #3 (explicit_deps_chunk_propagate) will consume when translating proposed_chunks into actual chunks.

No tests are needed because:
1. Template content verification is explicitly out of scope per TESTING_PHILOSOPHY.md ("We verify templates render without error and files are created, but don't assert on template prose")
2. The change adds documentation to existing comment blocks - no runtime behavior changes
3. Existing tests for `ve init` and template rendering already ensure templates are syntactically valid

## Subsystem Considerations

No subsystems are affected. This chunk modifies only template documentation comments, not runtime code patterns.

## Sequence

### Step 1: Update the narrative template's PROPOSED_CHUNKS schema

**File:** `src/templates/narrative/OVERVIEW.md.jinja2`

Add documentation for the `depends_on` field to the PROPOSED_CHUNKS schema section in the comment block. The documentation should explain:

- **What it is:** An optional array of integer indices referencing other prompts in the same `proposed_chunks` array
- **Format:** Zero-based integer indices (e.g., `depends_on: [0, 2]` means "this prompt depends on prompts at indices 0 and 2")
- **When to use:** When chunks have implementation dependencies that affect execution order
- **How it flows:** At chunk-create time, index references are translated to chunk directory names

Location: Add after the existing prompt/chunk_directory field documentation in the PROPOSED_CHUNKS comment block.

### Step 2: Update the investigation template's PROPOSED_CHUNKS schema

**File:** `src/templates/investigation/OVERVIEW.md.jinja2`

Add the same `depends_on` field documentation to the investigation template's PROPOSED_CHUNKS schema section. Investigations use the same proposed_chunks format as narratives, so the documentation should be consistent.

Location: Add after the existing prompt/chunk_directory field documentation in the PROPOSED_CHUNKS comment block.

### Step 3: Verify templates render correctly

Run `uv run ve init` to regenerate templates and verify no syntax errors.

Run the existing test suite to confirm templates still render correctly:
```bash
uv run pytest tests/ -v
```

No new tests are needed per TESTING_PHILOSOPHY.md (template prose is not tested), but existing tests must continue to pass.

## Dependencies

None. This chunk has no dependencies on other chunks in the narrative - it can be implemented independently. Per the narrative's proposed_chunks, this chunk (index 1) has `depends_on: []`.

## Risks and Open Questions

**Low risk.** This is a documentation-only change with no runtime behavior.

**Open questions resolved by design:**
- **Why indices instead of names?** Proposed chunks don't have directory names yet - they're just prompts. Index references are stable within a single array and get translated to chunk names during `/chunk-create`.
- **What about circular dependencies?** The index-based system inherently prevents forward references (a prompt cannot depend on a higher-index prompt that doesn't exist yet). Circular dependencies are impossible within a single array.

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