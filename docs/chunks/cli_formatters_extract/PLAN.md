<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a pure refactor that extracts duplicated code into a shared module. The approach is:

1. **Create `src/cli/formatters.py`** with the shared formatting functions
2. **Update all four CLI modules** to import from the new module
3. **Delete the duplicate implementations** from the original files
4. **Verify output remains byte-identical** using the existing test suite

No behavioral changes are intended. All existing tests must pass with no modifications.

### Key Observations from Code Analysis

1. **`_*_to_json_dict()` Pattern**: All four functions share identical core logic:
   - Handle `frontmatter is None` case by returning `{name, status: "UNKNOWN", is_tip}`
   - Call `frontmatter.model_dump()` for serialization
   - Normalize StrEnum status values
   - Build result with `name` first, then `status`, then `is_tip`, then remaining fields

   The only difference is `_chunk_to_json_dict()` accepts two extra parameters (`chunks_manager`, `project_dir`) that it never uses in the conversion logic. The generic function can simply omit these.

2. **Grouped Artifact Formatters**: `_format_grouped_artifact_list()` and `_format_grouped_artifact_list_json()` are defined in `cli/chunk.py` (lines 665-793) but imported by:
   - `cli/subsystem.py` (line 137): `from cli.chunk import _format_grouped_artifact_list, _format_grouped_artifact_list_json`
   - `cli/investigation.py` (line 221): `from cli.chunk import _format_grouped_artifact_list, _format_grouped_artifact_list_json`

   These imports of private (underscore-prefixed) symbols create tight coupling between modules that should be independent.

### References

- **DEC-004**: Markdown references relative to project root - applies to path references in code comments
- **TESTING_PHILOSOPHY.md**: Tests should verify semantic behavior, not structural details

## Sequence

### Step 1: Create `src/cli/formatters.py` with the generic `artifact_to_json_dict()` function

Create the new module with:
- Module-level docstring explaining this contains shared CLI formatting helpers
- Chunk backreference comment linking to this chunk
- The `artifact_to_json_dict(name, frontmatter, tips=None)` function

The function will:
1. Handle `frontmatter is None` by returning `{"name": name, "status": "UNKNOWN", "is_tip": name in tips if tips else False}`
2. Call `frontmatter.model_dump()`
3. Normalize StrEnum status by checking `hasattr(fm_dict.get("status"), "value")`
4. Build result dict with `name` first, then `status`, then `is_tip`, then remaining fields via `result.update(fm_dict)`

Location: `src/cli/formatters.py`

### Step 2: Add `format_grouped_artifact_list()` and `format_grouped_artifact_list_json()` to formatters.py

Move these two functions from `cli/chunk.py` into `cli/formatters.py`:
- Rename from `_format_grouped_artifact_list` to `format_grouped_artifact_list` (drop underscore)
- Rename from `_format_grouped_artifact_list_json` to `format_grouped_artifact_list_json` (drop underscore)
- Add imports at the top of `formatters.py` that these functions need: `json`, `click`, `ChunkStatus`

These functions remain otherwise unchanged - they already work generically across artifact types.

Location: `src/cli/formatters.py`

### Step 3: Update `cli/chunk.py` to use the new formatters

1. Add import: `from cli.formatters import artifact_to_json_dict, format_grouped_artifact_list, format_grouped_artifact_list_json`
2. Delete the local `_chunk_to_json_dict()` function (lines 294-340)
3. Delete the local `_format_grouped_artifact_list()` function (lines 665-745)
4. Delete the local `_format_grouped_artifact_list_json()` function (lines 748-793)
5. Update all call sites:
   - `_chunk_to_json_dict(chunk_name, frontmatter, chunks, project_dir)` → `artifact_to_json_dict(chunk_name, frontmatter)`
   - `_chunk_to_json_dict(chunk_name, frontmatter, chunks, project_dir, tips)` → `artifact_to_json_dict(chunk_name, frontmatter, tips)`
   - `_format_grouped_artifact_list(...)` → `format_grouped_artifact_list(...)`
   - `_format_grouped_artifact_list_json(...)` → `format_grouped_artifact_list_json(...)`

Location: `src/cli/chunk.py`

### Step 4: Update `cli/narrative.py` to use the new formatter

1. Add import: `from cli.formatters import artifact_to_json_dict`
2. Delete the local `_narrative_to_json_dict()` function (lines 117-158)
3. Update all call sites:
   - `_narrative_to_json_dict(narrative_name, frontmatter, tips)` → `artifact_to_json_dict(narrative_name, frontmatter, tips)`

Location: `src/cli/narrative.py`

### Step 5: Update `cli/subsystem.py` to use the new formatters

1. Change import from `from cli.chunk import _format_grouped_artifact_list, _format_grouped_artifact_list_json`
   to `from cli.formatters import artifact_to_json_dict, format_grouped_artifact_list, format_grouped_artifact_list_json`
2. Delete the local `_subsystem_to_json_dict()` function (lines 44-85)
3. Update all call sites:
   - `_subsystem_to_json_dict(subsystem_name, frontmatter, tips)` → `artifact_to_json_dict(subsystem_name, frontmatter, tips)`
   - `_format_grouped_artifact_list(...)` → `format_grouped_artifact_list(...)`
   - `_format_grouped_artifact_list_json(...)` → `format_grouped_artifact_list_json(...)`

Location: `src/cli/subsystem.py`

### Step 6: Update `cli/investigation.py` to use the new formatters

1. Change import from `from cli.chunk import _format_grouped_artifact_list, _format_grouped_artifact_list_json`
   to `from cli.formatters import artifact_to_json_dict, format_grouped_artifact_list, format_grouped_artifact_list_json`
2. Delete the local `_investigation_to_json_dict()` function (lines 105-146)
3. Update all call sites:
   - `_investigation_to_json_dict(investigation_name, frontmatter, tips)` → `artifact_to_json_dict(investigation_name, frontmatter, tips)`
   - `_format_grouped_artifact_list(...)` → `format_grouped_artifact_list(...)`
   - `_format_grouped_artifact_list_json(...)` → `format_grouped_artifact_list_json(...)`

Location: `src/cli/investigation.py`

### Step 7: Run tests to verify no behavioral changes

Run `uv run pytest tests/` to ensure all existing tests pass. Key test files to verify:
- `tests/test_chunk_list.py` - Chunk list output including JSON mode
- `tests/test_narrative_list.py` - Narrative list output
- `tests/test_subsystem_list.py` - Subsystem list output
- `tests/test_investigation_list.py` - Investigation list output
- `tests/test_task_chunk_list.py` - Task context chunk listing (uses grouped formatters)
- `tests/test_task_subsystem_list.py` - Task context subsystem listing
- `tests/test_task_investigation_list.py` - Task context investigation listing

Since this is a pure refactor with byte-identical output, no test modifications should be needed.

## Dependencies

None. This chunk is independent and can be implemented without waiting for other work.

## Risks and Open Questions

1. **Call site parameter mismatch**: The chunk-specific function signature includes `chunks_manager` and `project_dir` parameters that aren't used. Need to verify all call sites can drop these parameters without breaking. Analysis shows the parameters are passed but never accessed in the function body.

2. **Import cycle risk**: Creating `cli/formatters.py` and importing from it in `cli/chunk.py` could create a cycle. However, since `formatters.py` only imports `json`, `click`, and `ChunkStatus` from `models`, and does not import from any `cli/*` module, there is no cycle risk.

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
-->
