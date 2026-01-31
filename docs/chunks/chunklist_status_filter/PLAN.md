<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add status filtering capabilities to `ve chunk list` by extending the existing CLI command with new options. The implementation follows the established Click-based CLI patterns already present in `src/ve.py`.

**Key design decisions:**
- Use `--status` option with `multiple=True` to accept multiple status values
- Add convenience boolean flags (`--future`, `--active`, `--implementing`) that map to corresponding `--status` values
- Filtering is applied post-retrieval: `Chunks.list_chunks()` returns all chunks, then CLI filters by status before display
- Case-insensitive matching for user convenience
- Mutual exclusivity: `--latest` and `--last-active` are for single-chunk output; `--status` filters the list view

**Existing patterns to follow:**
- The CLI already uses `is_flag=True` for boolean options (e.g., `--latest`, `--future`)
- Uses `multiple=True` for options that can be specified multiple times (e.g., `--pattern` in backrefs command)
- Status values defined in `ChunkStatus` enum in `src/models.py`

**Testing strategy:**
- Test-driven development per TESTING_PHILOSOPHY.md
- CLI integration tests using Click's `CliRunner` in a temp project fixture
- Test each filtering option individually and in combination
- Test case-insensitivity
- Test invalid status error messaging
- Test composition with existing flags (`--project-dir`)

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow artifacts subsystem. The `ChunkStatus` enum and `Chunks` class are part of this subsystem. Our implementation will use `ChunkStatus` for status validation and pattern-match against the existing CLI patterns.

## Sequence

### Step 1: Write failing tests for status filtering

Create tests in `tests/test_chunk_list.py` for the new status filtering behavior. Tests should verify:

1. `--status FUTURE` filters to only FUTURE chunks
2. `--status ACTIVE` filters to only ACTIVE chunks
3. `--status IMPLEMENTING` filters to only IMPLEMENTING chunks
4. Case-insensitivity: `--status future` works
5. Multiple statuses: `--status FUTURE --status ACTIVE` shows both
6. Comma-separated: `--status FUTURE,ACTIVE` shows both
7. Invalid status error message lists valid options
8. Convenience flags: `--future`, `--active`, `--implementing`
9. Composition: status filter + `--project-dir` works together
10. Empty result when no chunks match filter

Location: `tests/test_chunk_list.py`

### Step 2: Add status option and convenience flags to CLI

Update the `list_chunks` function in `src/ve.py` to add:
- `--status` option with `multiple=True` for repeatable specification
- `--future` flag as shortcut for `--status FUTURE`
- `--active` flag as shortcut for `--status ACTIVE`
- `--implementing` flag as shortcut for `--status IMPLEMENTING`

Use `click.option` decorators following existing patterns. The status option should accept strings that map to `ChunkStatus` values.

Location: `src/ve.py#list_chunks`

### Step 3: Implement status parsing and validation

Create a helper function to:
1. Parse status values from `--status` option (handling comma-separated values)
2. Merge status values from convenience flags
3. Validate that all provided statuses are valid `ChunkStatus` values (case-insensitive)
4. Return error with valid options list if invalid status provided

This keeps the main `list_chunks` function clean and testable.

Location: `src/ve.py` (new helper function near `list_chunks`)

### Step 4: Implement filtering logic in list_chunks

Modify the list display logic in `list_chunks` to:
1. If status filters are specified, filter `chunk_list` to only include chunks whose status matches one of the filter values
2. For external chunks, they don't have a parseable status - either skip them or treat as "EXTERNAL" (document this decision)
3. Handle the empty result case (all chunks filtered out)

The filtering happens between getting the chunk list and displaying it. The existing loop that formats output already parses frontmatter for status display.

Location: `src/ve.py#list_chunks`

### Step 5: Update help text

Ensure the help text documents:
- The `--status` option with examples
- Case-insensitivity
- Multiple status specification (both `--status X --status Y` and `--status X,Y`)
- Convenience flag shortcuts

Run `ve chunk list --help` to verify.

Location: `src/ve.py` (docstring and option help strings)

### Step 6: Extend to task context

Update `_list_task_chunks` to support the same status filtering. This function handles the cross-repo case. The status filtering logic should be shared or replicated.

Location: `src/ve.py#_list_task_chunks`

### Step 7: Run full test suite

Run `uv run pytest tests/test_chunk_list.py -v` to verify all new tests pass, then run the full test suite `uv run pytest tests/` to ensure no regressions.

## Dependencies

No external dependencies required. All needed infrastructure exists:
- `ChunkStatus` enum is already defined in `src/models.py`
- Click library is already available
- Test fixtures (`runner`, `temp_project`) exist in `tests/conftest.py`

## Risks and Open Questions

1. **External chunk handling**: External chunks (with `external.yaml` but no local `GOAL.md`) don't have a parseable status. Decision: External chunks should be excluded when status filtering is active, since they're references to external artifacts rather than local chunks with a known status.

2. **Flag collision**: The `--future` flag already exists on `chunk start`. For `chunk list`, we're adding a different `--future` flag meaning "filter to FUTURE status". This is contextually different but consistent naming. No collision since they're on different subcommands.

3. **Interaction with `--latest`/`--last-active`**: These flags return a single chunk based on criteria. Status filtering with these flags could:
   - Return error (mutually exclusive) - CHOSEN: These are output mode selectors, not filters
   - Apply filter then select - More complex, unclear use case

   Decision: `--status` and `--latest`/`--last-active` are mutually exclusive since `--latest` and `--last-active` are specialized single-chunk selectors, not list filters.

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