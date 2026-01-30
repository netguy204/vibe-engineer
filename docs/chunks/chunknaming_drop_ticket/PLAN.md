<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a targeted refactoring that removes ticket ID embedding from chunk directory names while preserving ticket association in frontmatter. The change is surgical:

1. **Remove ticket ID from directory naming** - Modify `Chunks.create_chunk()` to ignore `ticket_id` when building the directory path (while still passing it to the template for frontmatter).

2. **Update collision detection** - Modify `Chunks.find_duplicates()` to only check `short_name` since ticket IDs will no longer be in directory names.

3. **Update combined name validation** - The `validate_combined_chunk_name()` function in `ve.py` needs to validate just the short_name since ticket IDs won't add to directory length.

4. **Update slash command template** - Modify `/chunk-create` template to reflect that ticket IDs only affect frontmatter, not directory names.

5. **Preserve backward compatibility** - Existing chunks with ticket suffixes (e.g., `my_feature-VE-001`) continue to work through `extract_short_name()` and `resolve_chunk_id()`.

The approach follows DEC-002 (git not assumed) and the workflow_artifacts subsystem patterns.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (DOCUMENTED): This chunk modifies the chunk creation workflow, which is core to this subsystem. Changes should preserve existing lifecycle semantics (FUTURE → IMPLEMENTING → ACTIVE).

- **docs/subsystems/cluster_analysis** (DOCUMENTED): This chunk USES the cluster analysis subsystem patterns. The chunk naming change aligns with the subsystem's guidance that prefixes should be domain concepts (not ticket IDs).

## Sequence

### Step 1: Write failing tests for new directory naming behavior

Write tests that verify:
- `ve chunk create my_chunk PROJ-123` creates `docs/chunks/my_chunk/` (not `my_chunk-PROJ-123/`)
- The `ticket` field in GOAL.md frontmatter is still populated with `PROJ-123`
- `find_duplicates()` detects collision when creating `my_chunk` twice (ignoring ticket differences)

Location: tests/test_chunks.py

### Step 2: Modify Chunks.create_chunk() to not use ticket_id in directory name

Change the directory name construction in `create_chunk()` to use only `short_name`:

```python
# Before (lines 251-254):
if ticket_id:
    chunk_path = self.chunk_dir / f"{short_name}-{ticket_id}"
else:
    chunk_path = self.chunk_dir / short_name

# After:
chunk_path = self.chunk_dir / short_name
```

Keep passing `ticket_id` to `render_to_directory()` so the `ticket:` frontmatter field is still populated.

Location: src/chunks.py#Chunks::create_chunk

### Step 3: Modify Chunks.find_duplicates() to ignore ticket_id

Change `find_duplicates()` to only match on `short_name`, ignoring the `ticket_id` parameter:

```python
# Before (lines 105-116):
if ticket_id:
    target_short = f"{short_name}-{ticket_id}"
else:
    target_short = short_name

# After:
target_short = short_name
```

Keep the `ticket_id` parameter in the function signature for backward compatibility but don't use it.

Location: src/chunks.py#Chunks::find_duplicates

### Step 4: Update validate_combined_chunk_name() in ve.py

Since ticket IDs no longer affect directory names, validation should only check `short_name` length:

```python
# Before (lines 82-91):
if ticket_id:
    combined_name = f"{short_name}-{ticket_id}"
else:
    combined_name = short_name

# After:
combined_name = short_name  # ticket_id no longer affects directory name
```

Consider: Should this function be removed entirely since it's now redundant with `validate_short_name()`? Keep it for clarity but simplify.

Location: src/ve.py#validate_combined_chunk_name

### Step 5: Update /chunk-create command template

Modify the template to reflect that ticket IDs affect only frontmatter, not directory names:

- Step 2: Remove the `<ticket number>` placeholder from the `ve chunk create` command example
- Update step 3 to clarify the directory is created at `docs/chunks/<shortname>/` regardless of ticket

Location: src/templates/commands/chunk-create.md.jinja2

### Step 6: Update test assertions to expect new directory naming

Update existing tests in `tests/test_chunks.py` to expect the new naming:
- `test_create_chunk_creates_directory`: `"my_feature"` not `"my_feature-VE-001"`
- `test_num_chunks_increments`: Similar updates
- `test_single_chunk_returns_list_with_one_item`: `"feature"` not `"feature-VE-001"`
- All other tests that assert on directory names with ticket IDs

Location: tests/test_chunks.py

### Step 7: Run full test suite and fix any remaining assertions

```bash
uv run pytest tests/
```

Fix any remaining test failures related to ticket ID in directory names.

### Step 8: Verify backward compatibility

Ensure existing chunks with ticket suffixes (e.g., `my_feature-VE-001`) continue to work:
- `extract_short_name("my_feature-VE-001")` should still return `"my_feature-VE-001"` (full name for non-legacy format)
- `resolve_chunk_id("my_feature-VE-001")` should still resolve correctly

Write a test confirming legacy chunks are readable.

## Dependencies

- **validation_chunk_name** (ACTIVE): This chunk created the combined name validation logic that we're simplifying.

## Risks and Open Questions

1. **Backward compatibility scope**: The `extract_short_name()` function handles legacy `{NNNN}-{name}` format but not `{name}-{TICKET}` format. Existing chunks with ticket suffixes might be treated differently after this change.

   **Mitigation**: Test that existing chunks like `my_feature-VE-001` continue to resolve correctly. The current `extract_short_name()` will return the full name for non-legacy patterns, which is correct behavior.

2. **Task context (cross-repo) mode**: `create_task_chunk()` in `task_utils.py` also uses `ticket_id` in the chunk name. This needs to be updated too.

   **Mitigation**: Include `task_utils.py` in the implementation scope and ensure tests cover task context mode.

3. **Collision behavior change**: Currently `create_chunk("VE-001", "foo")` and `create_chunk("VE-002", "foo")` would create two different directories. After this change, the second call would fail as a duplicate.

   **Impact**: This is the **intended behavior** - the ticket ID should not be a uniqueness factor for chunk naming. Operators wanting to create multiple chunks for different tickets should use distinct short names.

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