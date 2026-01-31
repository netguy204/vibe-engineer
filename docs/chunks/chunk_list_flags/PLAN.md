<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk renames the `--latest` flag to `--current` and adds a new `--recent` flag to `ve chunk list`. The implementation follows the existing CLI pattern established for `--latest` and `--last-active` flags.

**Strategy:**
1. **Rename `--latest` to `--current`** in the CLI option definition. The underlying `get_current_chunk()` method in `Chunks` class already has the correct semantics—it finds the currently IMPLEMENTING chunk.
2. **Add `--recent` flag** that shows the 10 most recently created ACTIVE chunks. This requires a new method in the `Chunks` class to find recent ACTIVE chunks by creation order.
3. **Update documentation** in the CLAUDE.md template and command templates that reference `--latest`.
4. **Write tests first** per TESTING_PHILOSOPHY.md, then implement to make them pass.

The approach builds on the existing `list_chunks()` method which already returns chunks in causal order (newest first) and the `parse_chunk_frontmatter()` method for filtering by status.

## Sequence

### Step 1: Write failing tests for `--current` flag

Add tests to `tests/test_chunk_list.py` that verify:
- `--current` flag shows the currently IMPLEMENTING chunk (same as old `--latest`)
- `--current` fails when no IMPLEMENTING chunk exists
- `--current` ignores FUTURE chunks
- Help text shows `--current` not `--latest`

These tests will fail because `--current` doesn't exist yet.

Location: `tests/test_chunk_list.py`

### Step 2: Write failing tests for `--recent` flag

Add tests to `tests/test_chunk_list.py` that verify:
- `--recent` flag shows up to 10 ACTIVE chunks in creation order (newest first)
- `--recent` returns only ACTIVE status chunks
- `--recent` fails when no ACTIVE chunks exist
- `--recent` limits output to 10 chunks even if more exist
- `--recent` is mutually exclusive with `--current` and `--last-active`
- Help text shows `--recent` flag with appropriate description

These tests will fail because `--recent` doesn't exist yet.

Location: `tests/test_chunk_list.py`

### Step 3: Add `get_recent_active_chunks()` method to Chunks class

Implement a new method in `src/chunks.py` that:
- Returns up to `limit` (default 10) ACTIVE chunks
- Orders by creation (using existing `list_chunks()` causal ordering)
- Filters to only ACTIVE status

```python
def get_recent_active_chunks(self, limit: int = 10) -> list[str]:
    """Return the most recently created ACTIVE chunks.

    Returns:
        List of chunk directory names, ordered newest first, limited to `limit`.
    """
```

Location: `src/chunks.py`

### Step 4: Rename `--latest` to `--current` in CLI

Update `src/ve.py`:
- Change `@click.option("--latest", ...)` to `@click.option("--current", ...)`
- Update function parameter name from `latest` to `current`
- Update error messages and internal references
- Preserve the behavior (calls `get_current_chunk()`)

Location: `src/ve.py`

### Step 5: Add `--recent` flag to CLI

Update `src/ve.py`:
- Add `@click.option("--recent", is_flag=True, help="Output the 10 most recently created ACTIVE chunks")`
- Add mutual exclusivity check with `--current` and `--last-active`
- Implement the output: call `get_recent_active_chunks()` and format each as `docs/chunks/{name}`

Location: `src/ve.py`

### Step 6: Update task directory handling

Update `_list_task_chunks()` in `src/ve.py` to support:
- Rename `latest` parameter to `current`
- Add `recent` parameter handling for task context

Location: `src/ve.py`

### Step 7: Update CLAUDE.md template

Update `src/templates/claude/CLAUDE.md.jinja2`:
- Change `ve chunk list --latest` to `ve chunk list --current`
- The text says "find the most recently created chunk" which is misleading—update to clarify it shows the currently IMPLEMENTING chunk

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 8: Update command templates

Update all command templates that reference `--latest`:
- `src/templates/commands/chunk-plan.md.jinja2`
- `src/templates/commands/chunk-complete.md.jinja2`
- `src/templates/commands/chunk-implement.md.jinja2`
- `src/templates/commands/chunk-create.md.jinja2`
- `src/templates/commands/chunk-commit.md.jinja2`

Change `--latest` to `--current` in all these files.

Location: `src/templates/commands/*.jinja2`

### Step 9: Run all tests and verify

Run the full test suite to ensure:
- New tests for `--current` and `--recent` pass
- Existing tests still pass (with updates for renamed flag)
- No regressions

```bash
uv run pytest tests/
```

## Risks and Open Questions

- **Backwards compatibility**: Users may have scripts relying on `--latest`. This is a breaking change but the investigation notes "No backwards compatibility needed". Should verify with operator if this is acceptable.
- **Task context complexity**: The `--recent` flag needs to work in task directory mode. May need to aggregate ACTIVE chunks from both external repo and local projects, or just from external repo.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->