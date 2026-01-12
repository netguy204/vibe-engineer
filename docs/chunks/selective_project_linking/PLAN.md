<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk implements **Option D (flag with all-default)** from the selective_artifact_linking investigation: add an optional `--projects` flag to task artifact creation commands that filters which projects receive `external.yaml` references.

**Strategy:**

1. **CLI Layer** (`src/ve.py`): Add `--projects` option to the four task-aware CLI helpers
2. **Task Utils** (`src/task_utils.py`): Modify `create_task_*` functions to accept an optional `projects` parameter that filters the iteration over `config.projects`
3. **Project Resolution**: Leverage the existing `resolve_project_ref()` function for flexible input handling (supports both `repo` and `org/repo` formats)

**Key Design Decisions:**

- **Backward compatible**: When `--projects` is omitted, all projects are linked (current behavior)
- **Flexible input**: Accept comma-separated project refs; each can be full `org/repo` or just `repo`
- **Validation**: Invalid project refs raise clear errors using existing `resolve_project_ref()` validation
- **Consistent UX**: Same flag name (`--projects`) across all four artifact types

**Relevant decisions from docs/trunk/DECISIONS.md:**
- DEC-001: CLI accessibility via uvx - this is a CLI feature addition
- DEC-002: Git not assumed - the feature works whether projects are git repos or not

**Testing strategy per docs/trunk/TESTING_PHILOSOPHY.md:**
- Test-driven: Write failing tests first for the new flag behavior
- Goal-driven: Tests verify success criteria from GOAL.md
- Boundary testing: Test empty project list, single project, invalid project refs

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS an extension to task-aware artifact creation commands. The subsystem documents the existing `create_task_*` functions that will be modified. Since the subsystem is STABLE, follow its existing patterns.

The existing code pattern in `create_task_*` functions iterates over all `config.projects`:
```python
for project_ref in config.projects:
    # create external.yaml
```

The modification adds an optional filter:
```python
effective_projects = projects if projects else config.projects
for project_ref in effective_projects:
    # create external.yaml
```

This maintains the invariant that every created artifact has a `dependents` list matching the projects that received `external.yaml` files.

## Sequence

### Step 1: Write failing tests for selective project linking

Create test cases in existing test files for the new `--projects` flag behavior:

**File: `tests/test_task_chunk_create.py`**
- Test: `test_creates_external_yaml_only_in_specified_projects` - verify selective linking
- Test: `test_creates_external_yaml_in_all_projects_when_flag_omitted` - verify backward compatibility
- Test: `test_accepts_flexible_project_refs` - verify both `repo` and `org/repo` work
- Test: `test_error_on_invalid_project_ref` - verify clear error for non-existent project

Similar tests needed for investigation, narrative, and subsystem create commands.

### Step 2: Modify create_task_chunk to accept projects parameter

Update `create_task_chunk()` in `src/task_utils.py`:

1. Add optional `projects: list[str] | None = None` parameter to function signature
2. After loading config, resolve provided project refs to canonical format using `resolve_project_ref()`
3. Compute `effective_projects`: if `projects` is None or empty, use `config.projects`; otherwise use resolved refs
4. Iterate over `effective_projects` instead of `config.projects`
5. Build `dependents` list from `effective_projects` only

**Location:** `src/task_utils.py#create_task_chunk` (lines 293-403)

### Step 3: Update CLI chunk create command with --projects flag

Update the `create()` command in `src/ve.py`:

1. Add `--projects` option: `@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")`
2. Parse comma-separated input into list (if provided)
3. Pass the list to `_start_task_chunk()` which passes to `create_task_chunk()`

**Location:** `src/ve.py#create` (lines 115-165)

### Step 4: Modify create_task_narrative to accept projects parameter

Same pattern as Step 2, applied to `create_task_narrative()`:

1. Add optional `projects: list[str] | None = None` parameter
2. Resolve and filter projects
3. Iterate over effective_projects

**Location:** `src/task_utils.py#create_task_narrative` (lines 582-684)

### Step 5: Update CLI narrative create command with --projects flag

Same pattern as Step 3, applied to `create_narrative()`:

1. Add `--projects` option
2. Parse and pass to `_create_task_narrative()` which passes to `create_task_narrative()`

**Location:** `src/ve.py#create_narrative` (lines 705-731)

### Step 6: Modify create_task_investigation to accept projects parameter

Same pattern as Step 2, applied to `create_task_investigation()`:

1. Add optional `projects: list[str] | None = None` parameter
2. Resolve and filter projects
3. Iterate over effective_projects

**Location:** `src/task_utils.py#create_task_investigation` (lines 746-848)

### Step 7: Update CLI investigation create command with --projects flag

Same pattern as Step 3, applied to `create_investigation()`:

1. Add `--projects` option
2. Parse and pass to `_create_task_investigation()` which passes to `create_task_investigation()`

**Location:** `src/ve.py#create_investigation` (lines 1122-1148)

### Step 8: Modify create_task_subsystem to accept projects parameter

Same pattern as Step 2, applied to `create_task_subsystem()`:

1. Add optional `projects: list[str] | None = None` parameter
2. Resolve and filter projects
3. Iterate over effective_projects

**Location:** `src/task_utils.py#create_task_subsystem` (lines 910-1012)

### Step 9: Update CLI subsystem discover command with --projects flag

Same pattern as Step 3, applied to `discover()`:

1. Add `--projects` option
2. Parse and pass to `_create_task_subsystem()` which passes to `create_task_subsystem()`

**Location:** `src/ve.py#discover` (lines 946-980)

### Step 10: Add helper function for parsing --projects input

Create a helper function to parse the comma-separated project input and resolve refs:

```python
def parse_projects_option(
    projects_input: str | None,
    available_projects: list[str],
) -> list[str] | None:
    """Parse --projects option into resolved project refs."""
    if projects_input is None:
        return None

    # Split on comma, strip whitespace
    project_names = [p.strip() for p in projects_input.split(",") if p.strip()]

    if not project_names:
        return None

    # Resolve each to canonical format
    return [resolve_project_ref(p, available_projects) for p in project_names]
```

This helper can be placed in `task_utils.py` and used by the CLI layer to parse input before passing to `create_task_*` functions.

**Location:** `src/task_utils.py`

### Step 11: Run tests and verify all pass

Run the test suite to verify:
1. New selective linking tests pass
2. Existing tests still pass (no regressions)
3. Help text is properly documented

```bash
uv run pytest tests/test_task_chunk_create.py tests/test_task_narrative_create.py tests/test_task_investigation_create.py tests/test_task_subsystem_discover.py -v
```

### Step 12: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/task_utils.py`
- `src/ve.py`
- `tests/test_task_chunk_create.py`
- `tests/test_task_narrative_create.py`
- `tests/test_task_investigation_create.py`
- `tests/test_task_subsystem_discover.py`

---

**BACKREFERENCE COMMENTS**

When implementing, add backreference comments at the function level for modified functions:

```python
# Chunk: docs/chunks/selective_project_linking - Optional project filtering for artifact creation
def create_task_chunk(
    task_dir: Path,
    short_name: str,
    ticket_id: str | None = None,
    status: str = "IMPLEMENTING",
    projects: list[str] | None = None,  # Filter to specific projects
) -> dict:
```

## Risks and Open Questions

1. **Interaction with `ve artifact copy-external`**: The investigation notes that mistakes in selective linking can be corrected via `ve artifact copy-external`. Verify this workflow still works as expected after changes.

2. **Error message clarity**: When an invalid project is specified, the error should clearly indicate which project was not found and list available options. The existing `resolve_project_ref()` already provides good error messages.

3. **Empty projects list edge case**: If `--projects ""` is passed (empty string), should it create zero project links or fall back to all projects? The implementation should treat empty input the same as omitting the flag (all projects).

4. **Ambiguous repo names**: If multiple projects have the same repo name (e.g., `acme/service` and `beta/service`), specifying just `service` is ambiguous. The existing `resolve_project_ref()` handles this by raising a clear error asking for full `org/repo` format.

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