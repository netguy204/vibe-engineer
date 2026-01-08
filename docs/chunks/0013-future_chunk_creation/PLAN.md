# Implementation Plan

## Approach

We'll extend the existing chunk management system to support a `FUTURE` status for chunks. This involves:

1. **Template changes**: Update the GOAL.md template to document the new `FUTURE` status and accept a `status` template variable
2. **Core logic changes**: Modify `Chunks` class to support creating chunks with different statuses and finding the current IMPLEMENTING chunk
3. **CLI changes**: Add `--future` flag to `ve chunk start`, update `ve chunk list` output, and add `ve chunk activate` command
4. **Skill changes**: Update `/chunk-create` skill to intelligently use `--future` when appropriate

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first, then implement.

## Sequence

### Step 1: Add FUTURE status to template documentation

Update `src/templates/chunk/GOAL.md` to:
- Add `FUTURE` to the STATUS VALUES comment
- Change the hardcoded `status: IMPLEMENTING` to use a Jinja template variable `{{ status | default('IMPLEMENTING') }}`

This ensures the template documents the new status and supports parameterized status values.

Location: `src/templates/chunk/GOAL.md`

### Step 2: Write tests for `Chunks.create_chunk()` with status parameter

Write failing tests that verify:
- `create_chunk()` accepts an optional `status` parameter
- When `status="FUTURE"`, the created GOAL.md has `status: FUTURE`
- Default behavior (no status param) still creates with `status: IMPLEMENTING`

Location: `tests/test_chunks.py`

### Step 3: Implement status parameter in `Chunks.create_chunk()`

Modify `Chunks.create_chunk()` to:
- Accept an optional `status` parameter (default: `"IMPLEMENTING"`)
- Pass `status` to the template render context

Location: `src/chunks.py`

### Step 4: Write tests for `Chunks.get_current_chunk()`

Write failing tests that verify:
- `get_current_chunk()` returns the highest-numbered chunk with status `IMPLEMENTING`
- Returns `None` when no `IMPLEMENTING` chunks exist (even if FUTURE/ACTIVE chunks exist)
- Ignores `FUTURE`, `ACTIVE`, `SUPERSEDED`, and `HISTORICAL` chunks

Location: `tests/test_chunks.py`

### Step 5: Implement `Chunks.get_current_chunk()`

Add new method that:
- Iterates through chunks in descending numeric order
- Parses each chunk's frontmatter
- Returns the first chunk with `status: IMPLEMENTING`
- Returns `None` if no implementing chunk found

Location: `src/chunks.py`

### Step 6: Write tests for `ve chunk start --future`

Write failing CLI tests that verify:
- `ve chunk start --future <name>` creates a chunk with status `FUTURE`
- The command outputs the created path normally
- Without `--future`, chunks still have status `IMPLEMENTING`

Location: `tests/test_chunk_start.py`

### Step 7: Implement `--future` flag on `ve chunk start`

Add `--future` flag to the `start` command:
- When set, pass `status="FUTURE"` to `chunks.create_chunk()`
- Default behavior unchanged

Location: `src/ve.py`

### Step 8: Write tests for updated `ve chunk list` output

Write failing tests that verify:
- `ve chunk list` output includes status for each chunk
- Format: `docs/chunks/<name> [STATUS]`
- `--latest` flag now uses `get_current_chunk()` to find the IMPLEMENTING chunk

Location: `tests/test_chunk_list.py`

### Step 9: Implement updated `ve chunk list` output

Modify the `list_chunks` CLI command to:
- Parse frontmatter for each chunk to get status
- Display status in brackets after the path
- Update `--latest` to use `get_current_chunk()` instead of `get_latest_chunk()`

Location: `src/ve.py`

### Step 10: Refactor frontmatter modification into reusable utility

Extract the frontmatter modification logic from `add_dependents_to_chunk()` in `src/task_utils.py:177-214` into a generic utility function:

```python
def update_frontmatter_field(goal_path: Path, field: str, value: Any) -> None:
    """Update a single field in GOAL.md frontmatter."""
```

Then refactor `add_dependents_to_chunk()` to use this utility. This enables reuse for status updates.

Location: `src/task_utils.py` (or consider moving to a shared `frontmatter.py` module)

### Step 11: Write tests for `ve chunk activate`

Write failing tests that verify:
- `ve chunk activate <id>` changes a FUTURE chunk to IMPLEMENTING
- Command fails with error if another chunk is already IMPLEMENTING
- Command fails with error if target chunk is not FUTURE
- Command fails with error if chunk doesn't exist

Location: `tests/test_chunk_activate.py` (new file)

### Step 12: Implement `ve chunk activate`

Add new CLI command that:
- Resolves chunk_id to chunk name
- Checks if there's already an IMPLEMENTING chunk (error if so)
- Verifies target chunk has status FUTURE
- Uses `update_frontmatter_field()` to set `status: IMPLEMENTING`

Location: `src/ve.py`, `src/chunks.py` (add `activate_chunk()` method)

### Step 13: Update `/chunk-create` skill

Modify `src/templates/commands/chunk-create.md` to:
- Check if there's a current IMPLEMENTING chunk using `ve chunk list --latest`
- If an IMPLEMENTING chunk exists, default to using `--future`
- Analyze the user's prompt for signals like "later", "next", "after this" to inform the decision
- Document this behavior in the skill instructions

Location: `src/templates/commands/chunk-create.md`

### Step 14: Validate with existing tests

Run full test suite to ensure no regressions:
- `pytest tests/`
- Fix any broken tests

## Risks and Open Questions

- **Cross-repo mode**: The `_start_task_chunk` path in `ve.py` also needs to support `--future`. Need to verify `create_task_chunk` in `task_utils.py` can accept a status parameter.

## Deviations

<!-- To be filled during implementation -->