<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The implementation extends `src/external_resolve.py` and its CLI in `src/ve.py` to
work with all artifact types. The strategy:

1. **Generalize the data model**: Update `ResolveResult` to handle any artifact type
   by replacing chunk-specific fields (`goal_content`/`plan_content`) with a generic
   structure that holds the main file content and optionally a secondary file.

2. **Generalize find functions**: Create `find_artifact_in_project()` that uses
   `ARTIFACT_DIR_NAME` from `external_refs.py` instead of hardcoding `docs/chunks/`.

3. **Auto-detect artifact type**: The artifact type comes from the path (detected via
   `detect_artifact_type_from_path()`) and is validated against the `external.yaml`
   content.

4. **Generalize file reading**: Use `ARTIFACT_MAIN_FILE` to determine which files to
   read (GOAL.md+PLAN.md for chunks, just OVERVIEW.md for others).

5. **Update CLI**: Modify `_display_resolve_result()` to show type-appropriate
   headers and only show secondary file section for chunks.

This builds on the `consolidate_ext_ref_utils` chunk's infrastructure in
`external_refs.py` which provides the mappings and utility functions.

**Testing approach** (per TESTING_PHILOSOPHY.md):
- Write tests first for new artifact type resolution
- Test both task directory and single repo modes for each type
- Tests verify semantic behavior (content is retrieved correctly) not just structure

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (REFACTORING): This chunk IMPLEMENTS part
  of the workflow_artifacts subsystem's external reference capability. The subsystem
  is in REFACTORING status, which means opportunistic improvement is appropriate.

  Since this chunk directly extends external reference support to all artifact types,
  it aligns with the subsystem's goal of "consistent cross-repository capability
  across all workflow types."

## Sequence

### Step 1: Update ResolveResult dataclass

Update the `ResolveResult` dataclass in `src/external_resolve.py` to handle any
artifact type:

**Current structure:**
```python
@dataclass
class ResolveResult:
    repo: str
    external_chunk_id: str
    track: str
    resolved_sha: str
    goal_content: str | None
    plan_content: str | None
```

**New structure:**
```python
@dataclass
class ResolveResult:
    repo: str
    artifact_type: ArtifactType
    artifact_id: str
    track: str
    resolved_sha: str
    main_content: str | None  # GOAL.md for chunks, OVERVIEW.md for others
    secondary_content: str | None  # PLAN.md for chunks, None for others
```

Location: `src/external_resolve.py`

### Step 2: Write failing tests for narrative resolution

Before implementing, write tests that verify narrative artifact resolution works
in both modes. These tests will initially fail.

Test cases to add to `tests/test_external_resolve.py`:
- `test_finds_narrative_in_project` - verify `find_artifact_in_project()` finds narratives
- `test_resolves_narrative_from_worktree` - task directory mode for narratives
- `test_resolves_narrative_via_cache` - single repo mode for narratives

Location: `tests/test_external_resolve.py`

### Step 3: Create find_artifact_in_project function

Create a generic version of `find_chunk_in_project()` that works for any artifact type.

**Function signature:**
```python
def find_artifact_in_project(
    project_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
) -> Path | None:
```

Uses `ARTIFACT_DIR_NAME[artifact_type]` instead of hardcoded `"chunks"`.

Keep `find_chunk_in_project()` as a thin wrapper that calls `find_artifact_in_project()`
with `ArtifactType.CHUNK` for backward compatibility.

Location: `src/external_resolve.py`

### Step 4: Create resolve_artifact_task_directory function

Generalize `resolve_task_directory()` to work with any artifact type by:
1. Using `find_artifact_in_project()` with the detected artifact type
2. Using `ARTIFACT_MAIN_FILE` to determine which files to read
3. Only reading secondary file (PLAN.md) for chunks

**Function signature:**
```python
def resolve_artifact_task_directory(
    task_dir: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
    at_pinned: bool = False,
    project_filter: str | None = None,
) -> ResolveResult:
```

Keep `resolve_task_directory()` as a thin wrapper for backward compatibility,
passing `ArtifactType.CHUNK`.

Location: `src/external_resolve.py`

### Step 5: Create resolve_artifact_single_repo function

Generalize `resolve_single_repo()` similarly:

**Function signature:**
```python
def resolve_artifact_single_repo(
    repo_path: Path,
    local_artifact_id: str,
    artifact_type: ArtifactType,
    at_pinned: bool = False,
) -> ResolveResult:
```

Keep `resolve_single_repo()` as a thin wrapper for backward compatibility.

Location: `src/external_resolve.py`

### Step 6: Update CLI argument and rename to local_artifact_id

Update the CLI command in `src/ve.py`:
1. Rename argument from `local_chunk_id` to `local_artifact_id`
2. Update `--goal-only`/`--plan-only` to `--main-only`/`--secondary-only`
   (maintain `--goal-only`/`--plan-only` as hidden aliases for backward compatibility)
3. Update help text to describe support for all artifact types
4. Auto-detect artifact type from the path when resolving

Location: `src/ve.py`

### Step 7: Update _display_resolve_result for any artifact type

Update the display function to:
1. Show "External Artifact Reference" or type-specific header
2. Display artifact type in the header
3. Show main file with type-appropriate name (GOAL.md vs OVERVIEW.md)
4. Only show secondary file section for chunks

Location: `src/ve.py`

### Step 8: Write tests for investigation and subsystem resolution

Add test cases for remaining artifact types:
- `test_resolves_investigation_from_worktree`
- `test_resolves_investigation_via_cache`
- `test_resolves_subsystem_from_worktree`
- `test_resolves_subsystem_via_cache`

Location: `tests/test_external_resolve.py`

### Step 9: Add CLI integration tests

Add CLI integration tests in a new test file that verify end-to-end resolution
for different artifact types:
- Test `ve external resolve` for chunks (existing behavior)
- Test `ve external resolve` for narratives
- Test `ve external resolve` for investigations
- Test `ve external resolve` for subsystems

Location: `tests/test_external_resolve_cli.py`

### Step 10: Update module docstring and add backreferences

Update `src/external_resolve.py` module docstring to describe support for all
artifact types. Add chunk backreference comment:

```python
# Chunk: docs/chunks/external_resolve_all_types - Extended to all artifact types
```

Location: `src/external_resolve.py`

---

**BACKREFERENCE COMMENTS**

Add to modified functions:
```python
# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
```

## Dependencies

- **consolidate_ext_ref_utils** (ACTIVE): Provides `ARTIFACT_MAIN_FILE`,
  `ARTIFACT_DIR_NAME`, `is_external_artifact()`, `load_external_ref()`, and
  `detect_artifact_type_from_path()` utilities in `src/external_refs.py`

## Risks and Open Questions

1. **Backward compatibility of ResolveResult**: Existing code that accesses
   `result.goal_content` and `result.plan_content` will break. However, since
   these are internal APIs (only used in `ve.py` and tests), the impact is contained.
   All callers will be updated in this chunk.

2. **CLI option naming**: Renaming `--goal-only`/`--plan-only` might break scripts.
   Mitigation: Keep old options as hidden aliases for backward compatibility.

3. **External artifacts may not exist in practice yet**: While the infrastructure
   supports external narratives/investigations/subsystems, they may not be used yet.
   Tests will create synthetic fixtures to verify the implementation works.

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