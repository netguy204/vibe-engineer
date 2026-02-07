<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `--json` flag to all artifact list commands following the established pattern from
`ve orch status` (see `src/cli/orch.py` lines 59-70). Each list command will:

1. Accept a `--json` flag using `@click.option("--json", "json_output", is_flag=True)`
2. Import Python's `json` module
3. Build a list of artifact dictionaries containing the artifact name, status, and full
   frontmatter fields
4. Output `json.dumps(results, indent=2)` when `--json` is specified

For frontmatter serialization, we'll use Pydantic's `model_dump()` method to convert
frontmatter models to dictionaries. StrEnum values need explicit `.value` conversion
for JSON serialization.

The JSON output will:
- Follow existing filtering behavior (e.g., `--status`, `--current`, `--recent`)
- Handle external references by including them with status="EXTERNAL" and repo info
- Handle parse errors by including them with a status="PARSE_ERROR" and error message
- Be parseable by standard tools (`jq`, Python's `json.loads()`)

Tests will follow the pattern established in `tests/test_chunk_list.py`, using Click's
`CliRunner` and validating JSON output with `json.loads()`.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk USES the workflow_artifacts
  subsystem's frontmatter models (`ChunkFrontmatter`, `NarrativeFrontmatter`,
  `InvestigationFrontmatter`, `SubsystemFrontmatter`) for JSON serialization.

## Sequence

### Step 1: Add `--json` flag to `ve chunk list`

Modify `src/cli/chunk.py#list_chunks` to:
- Add `@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")`
- Import `json` at module top
- When `json_output` is True, collect chunk data into a list of dicts
- Each dict includes: `name`, `status`, and all frontmatter fields from `ChunkFrontmatter`
- External chunks include: `name`, `status="EXTERNAL"`, `repo`, and available external.yaml fields
- Parse error chunks include: `name`, `status="PARSE_ERROR"`, `error`
- Output `json.dumps(results, indent=2)` and return early

JSON works with all existing flags (`--current`, `--last-active`, `--recent`, `--status`)
and applies the same filtering logic before collecting results.

Location: `src/cli/chunk.py`

### Step 2: Add tests for `ve chunk list --json`

Add tests to `tests/test_chunk_list.py`:
- `test_json_output_basic` - Valid JSON with chunk objects
- `test_json_output_with_status_filter` - Filtering works with JSON
- `test_json_output_with_current_flag` - Single chunk output
- `test_json_output_external_chunk` - External chunks serialized correctly
- `test_json_output_parse_error` - Parse errors included in output
- `test_json_output_empty_project` - Empty array (not error) when no chunks

Location: `tests/test_chunk_list.py`

### Step 3: Add `--json` flag to `ve narrative list`

Modify `src/cli/narrative.py#list_narratives` to:
- Add `@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")`
- When `json_output`, collect narrative data with `NarrativeFrontmatter.model_dump()`
- Include `name`, `status`, and all frontmatter fields
- Return empty array (not error) when no narratives found with JSON output

Location: `src/cli/narrative.py`

### Step 4: Add tests for `ve narrative list --json`

Add tests to `tests/test_narrative_list.py`:
- `test_json_output_basic` - Valid JSON with narrative objects
- `test_json_output_includes_frontmatter` - All frontmatter fields present
- `test_json_output_empty` - Empty array when no narratives

Location: `tests/test_narrative_list.py`

### Step 5: Add `--json` flag to `ve investigation list`

Modify `src/cli/investigation.py#list_investigations` to:
- Add `@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")`
- When `json_output`, collect investigation data with `InvestigationFrontmatter.model_dump()`
- Include `name`, `status`, and all frontmatter fields
- Existing `--state` filter works with JSON output

Location: `src/cli/investigation.py`

### Step 6: Add tests for `ve investigation list --json`

Add tests to `tests/test_investigation_list.py`:
- `test_json_output_basic` - Valid JSON with investigation objects
- `test_json_output_with_state_filter` - State filtering works with JSON
- `test_json_output_empty` - Empty array when no investigations

Location: `tests/test_investigation_list.py`

### Step 7: Add `--json` flag to `ve subsystem list`

Modify `src/cli/subsystem.py#list_subsystems` to:
- Add `@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")`
- When `json_output`, collect subsystem data with `SubsystemFrontmatter.model_dump()`
- Include `id` (directory name), `name` (extracted from directory), `status`, and all frontmatter fields

Location: `src/cli/subsystem.py`

### Step 8: Add tests for `ve subsystem list --json`

Add tests to `tests/test_subsystem_list.py`:
- `test_json_output_basic` - Valid JSON with subsystem objects
- `test_json_output_includes_code_references` - Code references serialized
- `test_json_output_empty` - Empty array when no subsystems

Location: `tests/test_subsystem_list.py`

### Step 9: Add `--json` flag to `ve friction list`

Modify `src/cli/friction.py#list_entries` to:
- Add `@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")`
- When `json_output`, collect friction entry data
- Include `entry_id`, `status`, `theme_id`, `title`, and other entry fields
- Existing `--open` and `--tags` filters work with JSON output

Location: `src/cli/friction.py`

### Step 10: Add tests for `ve friction list --json`

Add tests in a new test class within `tests/test_friction.py` or create
`tests/test_friction_list.py`:
- `test_json_output_basic` - Valid JSON with friction entry objects
- `test_json_output_with_open_filter` - Open filter works with JSON
- `test_json_output_empty` - Empty array when no entries

Location: `tests/test_friction.py` or `tests/test_friction_list.py`

### Step 11: Update GOAL.md code_paths

Update the chunk's frontmatter with the files touched during implementation.

Location: `docs/chunks/cli_json_output/GOAL.md`

## Risks and Open Questions

1. **StrEnum serialization**: Pydantic's `model_dump()` returns StrEnum values as strings
   automatically, but we should verify this behavior in tests.

2. **External artifact dereferencing**: External chunks in single-repo mode only have
   `external.yaml`, not `GOAL.md`. We'll include the available metadata (repo, artifact_id,
   created_after) but not attempt to dereference the external content.

3. **Parse error representation**: When frontmatter parsing fails, we'll include a
   simplified error message. The full Pydantic validation error may be too verbose for
   JSON output; we'll use the first error message for brevity.

4. **Task directory mode**: The JSON output should work correctly in task directory mode
   (cross-repo). We'll need to test this path to ensure grouped artifact listings serialize
   properly.

5. **Empty result handling**: With `--json`, an empty result should return an empty array
   `[]` with exit code 0, not an error message with exit code 1. This differs from text
   output behavior but is more appropriate for machine consumption.

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