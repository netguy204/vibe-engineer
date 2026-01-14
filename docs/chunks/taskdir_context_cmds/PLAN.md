<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk extends task-context awareness to the `ve chunk overlap`, `ve chunk validate`,
and `ve chunk activate` commands. The existing implementations work well in single-project
mode but don't fully support the task directory context established by the `cross_repo_chunks`
narrative.

The approach follows patterns already established by:
- `validate_chunk_complete()` - already has partial task context support via `task_dir` param
- `resolve_chunk_location()` - resolves external chunks in task context
- Task-aware create/list commands - detect task directory and aggregate from multiple repos

**Key strategy:**

1. **overlap**: Extend `find_overlapping_chunks()` to aggregate chunks from ALL repos in task
   context (external repo + project repos), and resolve project-qualified code references
   (e.g., `project_name::src/foo.py#Bar`) to their target projects.

2. **validate**: The existing implementation already has task context support. We need to:
   - Add verification of project-qualified code references
   - Support validation of cross-project external chunk references
   - When run from within a project directory inside a task, respect that project's context

3. **activate**: Extend to work correctly in task context, resolving chunks across the
   task's repo structure.

**Reference: DEC-002** - Git not assumed. This implementation respects that task directories
may contain worktrees without assuming git operations.

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS task-context
  extensions to operational commands. The subsystem documents external reference patterns
  and task-context requirements. Hard Invariant #11 mentions `--projects` flag support;
  we'll extend or add an invariant for task-context behavior in operational commands.

## Sequence

### Step 1: Add task-aware helper for code reference resolution

Create a helper function to resolve project-qualified code references in task context.
This function will parse refs like `project_name::src/foo.py#Bar`, resolve the project
path via task config, and verify the file/symbol exists.

Location: `src/task_utils.py`

```python
def resolve_project_qualified_ref(
    ref: str,
    task_dir: Path,
    default_project: Path,
) -> tuple[Path, str, str | None]:
    """Resolve a project-qualified code reference.

    Args:
        ref: Code reference (may be project-qualified like "proj::src/foo.py#Bar")
        task_dir: Task directory for resolving project names
        default_project: Project to use for non-qualified refs

    Returns:
        Tuple of (project_path, file_path, symbol_path or None)
    """
```

### Step 2: Extend overlap to aggregate chunks from all task repos

Modify `Chunks.find_overlapping_chunks()` to accept optional `task_dir` parameter.
When in task context, aggregate chunks from:
1. External artifact repo
2. All project repos

For each candidate chunk, resolve its code references using the task context
and check for overlap against the target chunk's references.

Location: `src/chunks.py#find_overlapping_chunks`

Add new CLI handler in `src/ve.py#overlap` to detect task context and pass it
to the method.

### Step 3: Extend validate for project-qualified references

The existing `validate_chunk_complete()` already has task context support.
Enhance `_validate_symbol_exists_with_context()` to properly handle:
- Project-qualified refs when task_dir is available
- Cross-project external chunk references validation

Location: `src/chunks.py#_validate_symbol_exists_with_context`

Update the CLI handler to ensure task context is detected correctly when
running from within a project directory that's part of a task.

### Step 4: Extend activate for task context

Add task-aware activation that:
- Detects task context from project_dir
- Resolves chunk location (could be in external repo or project repo)
- Updates status in the correct location

Location: `src/chunks.py#activate_chunk` (add task_dir parameter)
Location: `src/ve.py#activate` (CLI handler updates)

### Step 5: Write tests for task-context scenarios

Create comprehensive tests covering:
- `ve chunk overlap` with project-qualified refs
- `ve chunk overlap` aggregating chunks across task repos
- `ve chunk validate` with cross-project refs
- `ve chunk validate` from within a project inside a task
- `ve chunk activate` in task context

Location: `tests/test_taskdir_context_cmds.py` (new file)

Use the existing test helpers from `conftest.py`:
- `setup_task_directory()`
- `make_ve_initialized_git_repo()`

### Step 6: Update workflow_artifacts subsystem documentation

Add or extend an invariant documenting task-context requirements for operational
commands (overlap, validate, activate).

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:

```python
# Chunk: docs/chunks/taskdir_context_cmds - Task context for operational commands
```

## Dependencies

- Existing task-aware infrastructure from `cross_repo_chunks` narrative
- `is_task_directory()`, `load_task_config()`, `resolve_repo_directory()` from `task_utils.py`
- `resolve_chunk_location()` from `chunks.py`
- `is_external_artifact()`, `load_external_ref()` from `external_refs.py`

## Risks and Open Questions

1. **Performance concern**: Aggregating chunks from all task repos could be slow for
   large tasks with many chunks. Consider lazy evaluation or caching if needed.

2. **Ambiguous chunk resolution**: When a chunk name exists in multiple repos, how
   should `activate` resolve it? Proposal: prefer external repo, then search project
   repos in config order, error if ambiguous.

3. **Circular reference possibility**: If external chunk references another external
   chunk, overlap detection needs to handle cycles. The existing `get_ancestors()`
   in `ArtifactIndex` should handle this.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->