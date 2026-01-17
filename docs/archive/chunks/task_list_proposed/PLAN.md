<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds task-aware behavior to `ve chunk list-proposed` following the
established pattern for task-aware commands (see `ve chunk list`, `ve narrative list`, etc.).

The implementation strategy:
1. **Task detection**: Reuse existing `is_task_directory()` from `task_utils.py`
2. **Cross-repo aggregation**: Collect proposed chunks from external repo + all project repos
3. **Grouped output**: Display results grouped by repository, following the header format
   from `_format_grouped_artifact_list()` but adapted for proposed chunks structure

Key patterns to follow:
- Single-repo mode continues to work unchanged (backwards compatibility)
- Task mode detects `.ve-task.yaml` and aggregates from all repositories
- Grouped output uses `# External Artifacts ({repo})` and `# {repo} (local)` headers
- Empty sections show "No proposed chunks" (not omitted)

Per DEC-001 (uvx-based CLI), all functionality is accessible via command line.
Per DEC-002 (git not assumed), the task directory doesn't need to be a git repo.

## Subsystem Considerations

No subsystems are directly relevant to this chunk. The implementation follows
established patterns for task-aware commands already in the codebase.

## Sequence

### Step 1: Write failing tests for task-context behavior

Following TDD, write tests for the new task-aware behavior in
`tests/test_chunk_list_proposed.py`:

1. **Test task context detection**: Verify that running `ve chunk list-proposed`
   from a task directory (with `.ve-task.yaml`) triggers aggregated output.

2. **Test external repo collection**: Verify proposed chunks from investigations,
   narratives, and subsystems in the external artifact repo are collected.

3. **Test project repo collection**: Verify proposed chunks from each project in
   `config.projects` are collected.

4. **Test grouped output format**: Verify results display with headers:
   - `# External Artifacts ({repo})` for external repo
   - `# {repo} (local)` for each project repo
   - Empty sections show "No proposed chunks" message

5. **Test backwards compatibility**: Verify single-repo mode (no `.ve-task.yaml`)
   continues to work with existing output format.

Location: tests/test_chunk_list_proposed.py

### Step 2: Add `list_task_proposed_chunks` function to task_utils.py

Create a new function that aggregates proposed chunks from all repositories in
a task context:

```python
# Chunk: docs/chunks/task_list_proposed - Task-aware proposed chunk listing
def list_task_proposed_chunks(task_dir: Path) -> dict:
    """List proposed chunks from task context grouped by repository.

    Args:
        task_dir: Path to the task directory containing .ve-task.yaml

    Returns:
        Dict with keys:
        - external: {repo, proposed_chunks: [{prompt, source_type, source_id}]}
        - projects: [{repo, proposed_chunks: [...]}]

    Raises:
        TaskChunkError: If external repo not accessible
    """
```

The function should:
1. Load task config
2. Resolve external repo path
3. Instantiate `Chunks`, `Investigations`, `Narratives`, `Subsystems` for external repo
4. Call `chunks.list_proposed_chunks()` for external repo
5. For each project: instantiate managers, call `list_proposed_chunks()`
6. Return grouped dict matching the return format

Location: src/task_utils.py

### Step 3: Add `_format_grouped_proposed_chunks` helper to ve.py

Create a helper function to format and display grouped proposed chunk output:

```python
# Chunk: docs/chunks/task_list_proposed - Grouped proposed chunks formatter
def _format_grouped_proposed_chunks(grouped_data: dict) -> None:
    """Format and display grouped proposed chunk listing output.

    Args:
        grouped_data: Dict from list_task_proposed_chunks with external and projects keys
    """
```

Output format:
- `# External Artifacts ({repo})` header for external section
- `# {repo} (local)` header for each project section
- Within each section, group by source artifact: `From docs/{type}s/{id}:`
- Truncate prompts at 80 chars (existing behavior)
- Display "No proposed chunks" if a section is empty

Location: src/ve.py

### Step 4: Modify `list_proposed_chunks` CLI command for task awareness

Update the existing `list_proposed_chunks` command in `ve.py`:

1. Check if in task directory using `is_task_directory(project_dir)`
2. If task context: call `list_task_proposed_chunks()` and format with
   `_format_grouped_proposed_chunks()`
3. If single-repo: keep existing behavior unchanged

Location: src/ve.py (modify existing command at ~line 299)

### Step 5: Verify all tests pass

Run the full test suite to ensure:
- New task-aware tests pass
- Existing single-repo tests still pass
- No regressions in related functionality

```bash
uv run pytest tests/test_chunk_list_proposed.py -v
uv run pytest tests/ -v
```

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:
- `# Chunk: docs/chunks/task_list_proposed - Task-aware proposed chunk listing`

## Dependencies

All dependencies are already satisfied:
- `task_utils.py` provides `is_task_directory()`, `load_task_config()`, `resolve_repo_directory()`
- `chunks.py` provides `Chunks.list_proposed_chunks()` method
- Existing helper managers: `Investigations`, `Narratives`, `Subsystems`
- Test infrastructure: `conftest.py` provides `setup_task_directory()` helper

## Risks and Open Questions

1. **Output format consistency**: The existing `list_proposed_chunks` groups by
   source artifact (e.g., `From docs/narratives/foo:`). In task mode, we need
   two levels of grouping: by repository, then by source artifact. This is more
   complex but matches the success criteria.

2. **Empty section handling**: The success criteria says empty sections should
   show "No proposed chunks" rather than being omitted. This differs slightly
   from `_format_grouped_artifact_list()` which uses "No {type} found" only when
   *all* sections are empty. We'll follow the success criteria explicitly.

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