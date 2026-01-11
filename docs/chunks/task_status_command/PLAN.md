<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk enhances the artifact list commands (`ve chunk list`, `ve narrative list`, `ve subsystem list`, `ve investigation list`) to show a grouped-by-location output when running from a task directory context. Currently, these commands show only artifacts from the external repo when at task root. The new behavior shows the complete cross-project picture: external repo artifacts first, then each participating project's local artifacts, with each group preserving its own causal ordering.

**Strategy:**

1. Add a new function in `task_utils.py` that collects artifacts from ALL locations in a task (external repo + each project) and groups them by source.
2. Update the `_list_task_*` handler functions in `ve.py` to use this grouped output format.
3. Preserve backward compatibility: non-task context behavior remains unchanged.
4. The same grouped listing behavior applies to all four artifact types (chunks, narratives, subsystems, investigations).

**Patterns to follow:**

- Follow the existing `list_task_chunks()` pattern in `task_utils.py:354-403`
- Use `ArtifactIndex` for per-project causal ordering (per workflow_artifacts subsystem)
- The grouped output format uses "External Artifacts" header for the external repo and "org/repo (local)" for each project

**Output format per success criteria:**
```
# External Artifacts (org/external-repo)
cross_cutting_feature [IMPLEMENTING] (tip)
  → referenced by: org/project-a, org/project-b

# org/project-a (local)
local_fix_a [ACTIVE] (tip)

# org/project-b (local)
local_fix_b [IMPLEMENTING] (tip)
```

**Testing approach:**

Per TESTING_PHILOSOPHY.md, tests will verify:
- Grouped output format for each artifact type
- Per-group causal ordering is preserved
- External artifact dependents are shown
- Non-task context behavior unchanged
- Edge cases: empty external repo, empty projects, mixed scenarios

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS an extension to the grouped listing behavior for task contexts. The subsystem currently documents list commands but only covers external repo listing in task context. This chunk extends the behavior to show all locations grouped.

After implementation, the subsystem's OVERVIEW.md should be updated with a new section documenting the grouped listing behavior pattern.

## Sequence

### Step 1: Add grouped listing function to task_utils.py

Create `list_task_artifacts_grouped()` function that:
- Takes `task_dir` and `artifact_type` parameters
- Returns a structured result containing:
  - External repo artifacts with their dependents
  - Each project's local-only artifacts
  - Per-group causal ordering via `ArtifactIndex`
- Uses existing utilities: `load_task_config()`, `resolve_repo_directory()`, `ArtifactIndex`

The function should return a data structure like:
```python
{
    "external": {
        "repo": "org/external-repo",
        "artifacts": [
            {"name": "...", "status": "...", "dependents": [...], "is_tip": bool}
        ]
    },
    "projects": [
        {
            "repo": "org/project-a",
            "artifacts": [
                {"name": "...", "status": "...", "is_tip": bool}
            ]
        }
    ]
}
```

Location: `src/task_utils.py`

### Step 2: Create generic artifact listing helper

Add helper function `_list_artifacts_with_tips()` that:
- Takes a project path and artifact type
- Returns list of artifacts with status and tip indicator
- Filters out external artifacts (those with `external.yaml` pointing elsewhere)
- Uses the appropriate manager class (Chunks, Narratives, etc.) and `ArtifactIndex`

This helper consolidates common logic across artifact types.

Location: `src/task_utils.py`

### Step 3: Update _list_task_chunks in ve.py

Modify `_list_task_chunks()` to:
- Call the new `list_task_artifacts_grouped()` instead of `list_task_chunks()`
- Format output with group headers
- Show tip indicators
- Show dependents only for external artifacts

Location: `src/ve.py`

### Step 4: Update _list_task_narratives in ve.py

Apply the same grouped listing pattern to `_list_task_narratives()`.

Location: `src/ve.py`

### Step 5: Update _list_task_investigations in ve.py

Apply the same grouped listing pattern to `_list_task_investigations()`.

Location: `src/ve.py`

### Step 6: Update _list_task_subsystems in ve.py

Apply the same grouped listing pattern to `_list_task_subsystems()`.

Location: `src/ve.py`

### Step 7: Write tests for grouped chunk listing

Create tests in `tests/test_task_chunk_list.py` (extend existing file):
- Test grouped output format with external and local artifacts
- Test per-group causal ordering is preserved
- Test external artifact dependents display
- Test tip indicators shown correctly
- Test empty projects handled gracefully
- Test filtering excludes external references in local listings

Location: `tests/test_task_chunk_list.py`

### Step 8: Write tests for grouped narrative listing

Create tests in `tests/test_task_narrative_list.py` (extend existing file):
- Same test patterns as chunks

Location: `tests/test_task_narrative_list.py`

### Step 9: Write tests for grouped investigation listing

Create tests in `tests/test_task_investigation_list.py` (extend existing file):
- Same test patterns as chunks

Location: `tests/test_task_investigation_list.py`

### Step 10: Write tests for grouped subsystem listing

Create tests in `tests/test_task_subsystem_list.py` (extend existing file):
- Same test patterns as chunks

Location: `tests/test_task_subsystem_list.py`

### Step 11: Update subsystem documentation

Add a new section to `docs/subsystems/workflow_artifacts/OVERVIEW.md` documenting:
- The grouped listing behavior for task contexts
- The output format specification
- The per-group causal ordering preservation

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

```python
# Chunk: docs/chunks/task_status_command - Grouped task artifact listing
```

For the subsystem update:
```
# Chunk: docs/chunks/task_status_command - Grouped listing behavior
# Subsystem: docs/subsystems/workflow_artifacts - Task-aware artifact listing
```

## Dependencies

- **task_aware_investigations** and **task_aware_subsystem_cmds** chunks must be complete (they are - listed in `created_after`)
- Existing `list_task_*` functions in `task_utils.py` provide the foundation

## Risks and Open Questions

1. **Performance with many projects**: Loading artifacts from multiple projects might be slow. The `ArtifactIndex` cache should help, but we may need to consider lazy loading if task directories have many participating projects. For now, assume reasonable project counts (< 10).

2. **External artifact detection in local listings**: Need to correctly identify and exclude artifacts that are external references (have `external.yaml` but no main doc) from local listings. The `is_external_artifact()` function handles this.

3. **Empty groups**: Should empty groups (no local artifacts in a project) be shown or hidden? Design choice: Show all projects in the task config even if they have no local artifacts of that type, to provide complete visibility. Can show "(none)" if preferred.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
