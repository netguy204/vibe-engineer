<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This implementation follows the established pattern of `--latest` flag handling, adding a
parallel `--last-active` flag with similar structure. The key difference is the filter criteria:
- `--latest` finds the first IMPLEMENTING chunk in causal order
- `--last-active` finds the ACTIVE tip chunk with the most recent GOAL.md mtime

The implementation has three components:
1. **New `get_last_active_chunk()` method in Chunks class** - Core logic using existing
   `ArtifactIndex.find_tips()` and chunk status filtering
2. **CLI flag and handler** - Add `--last-active` flag to `ve chunk list` with mutual exclusivity
3. **Template update** - Modify chunk-commit template to fall back to `--last-active`

The existing `ArtifactIndex.find_tips()` already filters for tip-eligible statuses (ACTIVE,
IMPLEMENTING, EXTERNAL for chunks), so we filter the returned tips to ACTIVE-only and select
by GOAL.md mtime.

Testing follows TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first, then
implement the minimum code to make them pass.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts**: This chunk USES the workflow artifact lifecycle
  patterns. The Chunks class already has subsystem backreferences, and this implementation
  follows the existing pattern of status-based filtering (similar to `get_current_chunk()`).

## Sequence

### Step 1: Write failing tests for `get_last_active_chunk()`

Add tests to `tests/test_chunks.py` for the new method before implementing it:

1. Test that the method returns the ACTIVE tip chunk with most recent GOAL.md mtime
2. Test that it returns the most recent among multiple ACTIVE tips
3. Test that ACTIVE chunks that are NOT tips (referenced by another chunk's `created_after`) are excluded
4. Test that it returns None when no ACTIVE chunks exist
5. Test that IMPLEMENTING chunks are ignored (not returned)

Location: `tests/test_chunks.py`

### Step 2: Implement `get_last_active_chunk()` method

Add a new method to the `Chunks` class following the pattern of `get_current_chunk()`:

```python
def get_last_active_chunk(self) -> str | None:
    """Return the most recently completed ACTIVE tip chunk.

    This finds the ACTIVE chunk that:
    1. Has ACTIVE status
    2. Is a "tip" in the causal ordering (not in any other chunk's created_after)
    3. Has the most recent GOAL.md mtime among qualifying chunks

    Returns:
        The chunk directory name if an ACTIVE tip exists, None otherwise.
    """
```

The implementation:
1. Get all tips from `ArtifactIndex.find_tips(ArtifactType.CHUNK)`
2. Filter tips to only ACTIVE status using `parse_chunk_frontmatter()`
3. If no ACTIVE tips, return None
4. Get GOAL.md mtime for each ACTIVE tip
5. Return the chunk name with the most recent mtime

Location: `src/chunks.py`, after `get_current_chunk()` method (around line 163)

### Step 3: Write failing CLI tests for `--last-active` flag

Add tests to `tests/test_chunk_list.py`:

1. Test `--last-active` returns ACTIVE tip chunk
2. Test `--last-active` fails when no ACTIVE tips exist (exit code 1, error message)
3. Test `--last-active` and `--latest` are mutually exclusive
4. Test `--help` shows the new flag

Location: `tests/test_chunk_list.py`

### Step 4: Add `--last-active` flag to CLI

Update the `list_chunks` CLI command in `src/ve.py`:

1. Add new option: `@click.option("--last-active", is_flag=True, help="Output only the most recently completed ACTIVE chunk")`
2. Add mutual exclusivity check for `--latest` and `--last-active`
3. Add handler branch for `--last-active` that calls `chunks.get_last_active_chunk()`
4. Output format: `docs/chunks/{chunk_name}` (same as `--latest`)
5. Error handling: "No active tip chunk found" to stderr, exit code 1

Location: `src/ve.py`, lines 188-227

### Step 5: Update `_list_task_chunks()` helper for cross-repo mode

Update the helper function to accept and handle the `last_active` parameter:

1. Update function signature: `def _list_task_chunks(latest: bool, last_active: bool, task_dir: pathlib.Path)`
2. Add handling for `last_active=True` case (similar to `latest` handling)
3. Update the call site in `list_chunks()` to pass the new parameter

Note: This may require adding a corresponding function in `task_utils.py` similar to
`get_current_task_chunk()`, or extending that function with a status filter parameter.

Location: `src/ve.py`, lines 316-330

### Step 6: Update chunk-commit template to use fallback

Modify the template to try `--last-active` when `--latest` returns nothing:

```jinja2
- Current chunk: !`ve chunk list --latest || ve chunk list --last-active`
```

Or use a conditional approach with shell scripting:

```jinja2
- Current chunk: !`ve chunk list --latest 2>/dev/null || ve chunk list --last-active 2>/dev/null || echo "(no active chunk)"`
```

Location: `src/templates/commands/chunk-commit.md.jinja2`, line 12

### Step 7: Verify all tests pass and run manual testing

1. Run the full test suite: `uv run pytest tests/`
2. Manual testing workflow:
   - Create a chunk with `ve chunk start test-chunk`
   - Verify `ve chunk list --latest` returns the chunk
   - Run `ve chunk complete` to mark it ACTIVE
   - Verify `ve chunk list --latest` now returns nothing (or error)
   - Verify `ve chunk list --last-active` returns the completed chunk

Add backreference comment to the new method:
```python
# Chunk: docs/chunks/chunk_last_active - Last active chunk lookup
```

## Dependencies

None. All required infrastructure already exists:
- `ArtifactIndex.find_tips()` for tip detection
- `Chunks.parse_chunk_frontmatter()` for status filtering
- Click CLI framework for mutual exclusivity handling

## Risks and Open Questions

1. **Task directory (cross-repo) support**: The `_list_task_chunks()` helper needs updating,
   and `task_utils.py` may need a new function or extended function signature. This is lower
   priority since the primary use case (chunk-commit) is single-repo, but should be implemented
   for consistency.

2. **mtime reliability**: File modification time is used to select among multiple ACTIVE tips.
   This could be affected by file operations that touch GOAL.md without meaningful changes
   (e.g., `touch`), but this is an edge case and the two-part filter (tip AND mtime) reduces
   false positives.

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