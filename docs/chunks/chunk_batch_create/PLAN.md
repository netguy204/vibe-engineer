<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the `ve chunk create` CLI command to accept multiple chunk names as variadic arguments. The implementation will:

1. **Modify the CLI layer** (`src/ve.py`): Change `short_name` from a single `@click.argument` to a variadic argument accepting multiple values.

2. **Loop over names**: For each chunk name, apply the existing validation and creation logic. Flags like `--future` and `--ticket` apply uniformly to all chunks in the batch.

3. **Preserve single-chunk behavior**: When a single name is provided, behavior is unchanged. The guard preventing multiple IMPLEMENTING chunks is respected (batch creation of IMPLEMENTING chunks is blocked if any IMPLEMENTING chunk exists).

4. **Error handling**: If creation fails for any chunk, report the error and continue with remaining chunks (partial success allowed). Report all created paths at the end.

5. **CLAUDE.md template update**: Document the batch creation capability and add guidance for agents to use Task tool (sub-agents) to refine goals in parallel after batch creation.

**Testing approach** (per `docs/trunk/TESTING_PHILOSOPHY.md`):
- Test batch creation creates all requested chunks
- Test `--future` flag applies to all chunks
- Test error on batch IMPLEMENTING when one already exists
- Test partial success when some names are invalid
- Test output lists all created chunk paths

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow_artifacts
  subsystem's Chunks manager class for chunk creation. The `Chunks.create_chunk()` method
  will be called in a loop for batch creation. No changes to the subsystem patterns needed.

## Sequence

### Step 1: Write failing tests for batch creation

Create tests in `tests/test_chunk_start.py` (or new file `tests/test_chunk_batch_create.py`) that verify:

1. `ve chunk create name1 name2 name3` creates three chunks
2. `--future` flag applies to all chunks in batch
3. `--ticket` flag applies to all chunks in batch
4. Output lists all created paths
5. Batch IMPLEMENTING creation fails when IMPLEMENTING chunk exists
6. Partial success: if one name is invalid, others still created
7. Single name still works (backward compatibility)

Location: `tests/test_chunk_start.py` (add new `TestBatchCreation` class)

### Step 2: Modify CLI argument to accept multiple names

Change the `create` command in `src/ve.py`:

Current:
```python
@click.argument("short_name")
```

New:
```python
@click.argument("short_names", nargs=-1, required=True)
```

Update the function signature to accept `short_names: tuple[str, ...]` and loop over each name.

Location: `src/ve.py#create` (around line 131)

### Step 3: Implement batch creation logic

In the `create` function:

1. Validate all names upfront before creating any chunks
2. For IMPLEMENTING status (no `--future`), check guard once at the start
3. Loop through validated names and create each chunk
4. Collect created paths and any errors
5. Report all results at end

Preserve the existing task-context detection and routing to `_start_task_chunk`.

Location: `src/ve.py#create`

### Step 4: Update `_start_task_chunk` for batch creation

Extend `_start_task_chunk` to handle multiple chunk names in task directory mode.
The function should loop over each name and call `create_task_chunk` for each.

Location: `src/ve.py#_start_task_chunk`

### Step 5: Update CLAUDE.md template with batch creation guidance

Add to `src/templates/claude/CLAUDE.md.jinja2`:

1. Document the batch creation syntax in the "Creating and Submitting FUTURE Chunks" section
2. Add guidance for agents to use Task tool sub-agents to refine goals in parallel after batch creation
3. Example: "After creating multiple chunks with `ve chunk create a b c --future`, spawn sub-agents to refine each GOAL.md in parallel"

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 6: Run tests and verify all pass

Run `uv run pytest tests/test_chunk_start.py -v` to verify:
- New batch creation tests pass
- Existing single-creation tests still pass

### Step 7: Re-render CLAUDE.md and verify

Run `uv run ve init` to re-render the CLAUDE.md from the updated template.
Verify the batch creation documentation appears correctly.

## Dependencies

None - this extends existing functionality with no new dependencies.

## Risks and Open Questions

1. **Ticket ID with batch creation**: Currently `ticket_id` is a second positional argument. With variadic `short_names`, we need to decide how to handle tickets. Options:
   - Make `--ticket` a flag-based option only (simplest, recommended)
   - Apply the same ticket to all chunks (current design assumption)
   - This is a minor breaking change if anyone uses positional ticket_id with batch creation

   **Decision**: Keep `ticket_id` as optional second positional for single-chunk (backward compat), but when multiple names are provided, `--ticket` flag must be used. Alternatively, simplify by making ticket flag-only.

2. **Error handling strategy**: If creating chunk 2 of 3 fails, should we:
   - Stop and report (fail-fast)
   - Continue and report all results at end (partial success)

   **Decision**: Partial success - create all possible chunks and report errors alongside successes.

3. **Cluster size warnings**: Currently emitted after single chunk creation. For batch creation, emit once at end summarizing any clusters that grew large.

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