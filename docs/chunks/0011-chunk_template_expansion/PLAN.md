<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the template rendering context in `create_chunk()` to include the chunk directory name. This is a minimal change:

1. Compute the chunk directory name (e.g., `0011-chunk_template_expansion`) from the already-computed path
2. Pass it as `chunk_directory` to the Jinja2 template renderer
3. Update the PLAN.md template to use `{{ chunk_directory }}` in the reference comment

This follows DEC-004 (markdown references relative to project root) by enabling templates to produce paths like `docs/chunks/0011-chunk_template_expansion/GOAL.md` instead of placeholder syntax.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md:
- Write tests first that verify rendered templates contain the expected chunk directory
- Tests should assert on the actual file contents, not just that files exist

## Sequence

### Step 1: Write test for chunk_directory in rendered templates

Add a test to `tests/test_chunks.py` that:
- Creates a chunk via `Chunks.create_chunk()`
- Reads the generated PLAN.md file
- Asserts that the rendered content contains the actual chunk directory name (e.g., `docs/chunks/0001-feature/GOAL.md`)
- Asserts it does NOT contain the placeholder text `NNNN-name`

This test will fail initially because the template variable doesn't exist yet.

Location: `tests/test_chunks.py`

### Step 2: Expand template context with chunk_directory

Modify `Chunks.create_chunk()` in `src/chunks.py` to:
- Extract the chunk directory name from the computed `chunk_path` using `chunk_path.name`
- Pass `chunk_directory=chunk_path.name` to `render_template()`

Location: `src/chunks.py:89-95`

### Step 3: Update PLAN.md template to use chunk_directory

Replace the placeholder `docs/chunks/NNNN-name/GOAL.md` in `src/templates/chunk/PLAN.md` with `docs/chunks/{{ chunk_directory }}/GOAL.md`.

Location: `src/templates/chunk/PLAN.md:23`

### Step 4: Review GOAL.md template for self-references

Examine `src/templates/chunk/GOAL.md` for any self-referential text that could benefit from `{{ chunk_directory }}`. Currently, the template does not appear to have any such references, but verify and update if needed.

Location: `src/templates/chunk/GOAL.md`

### Step 5: Run tests and verify

Run `pytest tests/` to confirm:
- The new test passes
- All existing tests still pass

## Risks and Open Questions

- **Template compatibility**: The existing template variables (`ticket_id`, `short_name`, `next_chunk_id`) must remain available. The change only adds a new variable, so this should be safe.
- **Cross-repo chunks**: Future work may involve chunks in external repositories where the path prefix differs. This chunk only addresses the local case; cross-repo path handling is out of scope.

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