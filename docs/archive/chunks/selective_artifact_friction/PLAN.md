<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk has three parts:

1. **Friction logging in task context** - Extend `ve friction log` to work in task directory mode by creating entries in the external repo and adding references to linked projects
2. **`--projects` flag on `ve friction log`** - Add selective project linking to friction, following the pattern established for chunks, narratives, investigations, and subsystems
3. **Subsystem documentation update** - Add `--projects` as a hard invariant for all task-aware artifact creation commands

The approach follows existing patterns:
- The `--projects` flag pattern is already implemented in `create_task_chunk()`, `create_task_narrative()`, `create_task_investigation()`, and `create_task_subsystem()` in `src/task_utils.py`
- Friction is a singleton file (`FRICTION.md`) rather than a directory-based artifact, requiring a different pattern for external references—we'll use frontmatter metadata to track external friction sources

**Key design insight**: Unlike chunks/narratives/etc. which use `external.yaml` files in subdirectories, friction is a single file. We'll:
1. Create friction entries in the external repo's `FRICTION.md`
2. Add frontmatter to local project `FRICTION.md` files that reference the external repo (new `external_friction_sources` field)
3. The local friction log aggregates both local entries and external references

This aligns with DEC-002 (git not assumed) and DEC-005 (commands do not prescribe git operations).

## Subsystem Considerations

- **docs/subsystems/workflow_artifacts** (STABLE): This chunk IMPLEMENTS the `--projects` flag pattern for friction logs and updates the subsystem documentation. Since the subsystem is STABLE, we follow its established patterns for task-aware commands.

## Sequence

### Step 1: Add external_friction_sources to FrictionFrontmatter

Extend the `FrictionFrontmatter` model in `src/models.py` to support external friction references:

```python
class ExternalFrictionSource(BaseModel):
    """Reference to friction entries in an external repository."""
    repo: str  # External repo ref (e.g., "acme/ext")
    track: str = "main"  # Branch to track
    pinned: str  # Commit SHA when reference was created
    entry_ids: list[str] = []  # List of F-numbers in that repo this project cares about
```

Add `external_friction_sources: list[ExternalFrictionSource] = []` to `FrictionFrontmatter`.

Location: `src/models.py`

### Step 2: Add task-aware friction helper functions

Create helper functions in `src/task_utils.py` following the pattern of other task-aware artifact functions:

- `TaskFrictionError` - Error class for friction operations
- `create_task_friction_entry()` - Create friction entry in external repo
- `add_external_friction_source()` - Add external repo reference to project's FRICTION.md

Location: `src/task_utils.py`

### Step 3: Extend ve friction log with task context detection

Modify the `log_entry()` CLI command in `src/ve.py` to:
1. Check if we're in a task directory using `is_task_directory()`
2. If in task context:
   - Create the friction entry in the external repo's `FRICTION.md`
   - Add/update `external_friction_sources` in each linked project's `FRICTION.md`
3. Add `--projects` option for selective project linking

Location: `src/ve.py` (friction commands section around line 2850)

### Step 4: Update Friction class to support external references

Extend `src/friction.py` to:
1. Parse `external_friction_sources` from frontmatter
2. Add method `add_external_source()` to update frontmatter with external references
3. Handle merged views when listing entries (local + external)

Location: `src/friction.py`

### Step 5: Update workflow_artifacts subsystem documentation

Add to `docs/subsystems/workflow_artifacts/OVERVIEW.md`:
- New hard invariant: "All task-aware artifact creation commands must support `--projects` flag for selective project linking"
- Update the code_references section to include friction task-aware functions
- Add `selective_artifact_friction` to the chunks list

Location: `docs/subsystems/workflow_artifacts/OVERVIEW.md`

### Step 6: Write tests for task-aware friction

Create `tests/test_task_friction.py` with tests for:
1. `ve friction log` in task context creates entry in external repo
2. External friction sources are added to linked project FRICTION.md files
3. `--projects` flag creates references only in specified projects
4. Omitting `--projects` links to all projects (backward compatible)
5. Error handling for missing external repo, missing FRICTION.md, etc.

Follow the test patterns in `tests/test_task_chunk_create.py` and use `setup_task_directory()` from conftest.

Location: `tests/test_task_friction.py`

### Step 7: Write tests for selective project linking

Add tests to existing test files to verify `--projects` behavior on friction log command, following the pattern in `tests/test_task_chunk_create.py#TestSelectiveProjectLinking`.

Location: `tests/test_task_friction.py`

### Step 8: Update GOAL.md code_paths

Update the chunk's GOAL.md frontmatter with the files touched:
- `src/models.py`
- `src/task_utils.py`
- `src/ve.py`
- `src/friction.py`
- `docs/subsystems/workflow_artifacts/OVERVIEW.md`
- `tests/test_task_friction.py`

---

**BACKREFERENCE COMMENTS**

When implementing code, add backreference comments:
```python
# Chunk: docs/chunks/selective_artifact_friction - Task-aware friction logging
# Subsystem: docs/subsystems/workflow_artifacts - Unified workflow artifact pattern
```

## Dependencies

- The `--projects` flag is already implemented for chunks, narratives, investigations, and subsystems via the `selective_project_linking` chunk (referenced in `created_after`)
- The `parse_projects_option()` function already exists in `src/task_utils.py`
- The Friction class already exists in `src/friction.py`

## Risks and Open Questions

1. **External friction entry IDs**: When creating friction entries in the external repo, should the entry ID sequence (F001, F002, etc.) be global across all projects, or should each project maintain its own sequence?
   - **Resolution**: Use the external repo's sequence for external entries. Local entries in project FRICTION.md use their own sequence.

2. **Merged view complexity**: When listing friction entries, should we merge external + local entries? This could be confusing if entry IDs collide (e.g., both external and local have F003).
   - **Resolution**: Prefix external entries in display (e.g., `[ext/F003]` vs `[F003]`), but for simplicity in this iteration, only the local FRICTION.md is modified to reference external sources—the external entries themselves aren't merged into local listings.

3. **FRICTION.md creation**: What if a project doesn't have a `FRICTION.md`? Unlike chunks which create directories on demand, FRICTION.md is created by `ve init`.
   - **Resolution**: Skip projects that don't have FRICTION.md (with a warning), following the pattern of other artifacts that require initialization.

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