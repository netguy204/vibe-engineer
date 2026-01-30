<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The goal is to make `ve subsystem overlap <chunk_name>` work correctly in task contexts where the chunk exists in the external artifacts repo.

Currently, the `subsystem overlap` command (ve.py lines 1706-1722) only looks for chunks locally using `Chunks(project_dir)`, without any task context awareness. When run from a task directory, it fails to find chunks that exist in the external artifacts repo.

**Strategy**: Follow the same pattern used by `chunk overlap` (ve.py lines 759-804), which:
1. Detects task context using `find_task_directory()`
2. Resolves chunks through the external artifacts repo when in task context
3. Falls back to local resolution for non-task contexts

**Key insight from code review**: The `Chunks.resolve_chunk_location()` method already handles external chunk resolution when given a `task_dir` parameter. We can leverage this existing infrastructure.

**Implementation options**:

**Option A: Direct task resolution in CLI**
Add task context detection to the `subsystem overlap` CLI command, resolve the chunk's actual location, then create appropriate `Chunks` and `Subsystems` instances for the resolved location. Similar to `chunk overlap`.

**Option B: Extend Subsystems.find_overlapping_subsystems()**
Modify `find_overlapping_subsystems()` to accept an optional `task_dir` parameter and use `Chunks.resolve_chunk_location()` internally.

**Chosen approach: Option A** - This keeps the task resolution logic in the CLI layer (where it's handled for other commands) and keeps the business logic classes simpler. This matches the existing pattern used by `chunk overlap`.

**Test strategy** (per docs/trunk/TESTING_PHILOSOPHY.md):
- Write failing tests first for task context behavior
- Tests will verify: external chunk resolution works, local chunks continue to work, error messages are helpful

## Subsystem Considerations

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk USES the cross-repo operations subsystem to resolve chunks in task contexts. The existing patterns (`is_task_directory`, `find_task_directory`, `load_task_config`, `resolve_repo_directory`) will be reused.

## Sequence

### Step 1: Write failing tests for task context behavior

Create tests in `tests/test_subsystem_overlap_cli.py` that verify:

1. **External chunk resolution in task context**: When running `ve subsystem overlap <chunk>` from a task directory where the chunk exists in the external artifacts repo, the command should find the chunk and check for subsystem overlaps.

2. **Subsystem resolution in task context**: When the chunk references code that overlaps with subsystems in the external repo, those subsystems should be reported.

3. **Local chunks still work**: Ensure existing non-task behavior remains unchanged (regression test).

4. **Helpful error messages**: When a chunk genuinely doesn't exist anywhere, the error message should be clear.

These tests will use the existing `setup_task_directory()` helper from `conftest.py` to create the task context setup.

Location: `tests/test_subsystem_overlap_cli.py`

### Step 2: Update CLI command to detect task context

Modify the `subsystem overlap` CLI command in `src/ve.py` to:

1. Import task-related utilities: `is_task_directory`, `find_task_directory`, `load_task_config`, `resolve_repo_directory`
2. After normalizing `chunk_id`, detect task context (same pattern as `chunk overlap`):
   - Check if `project_dir` is a task directory
   - If not, check if we're inside a task project via `find_task_directory()`
3. Store the task directory for later use in resolution

Location: `src/ve.py` - `overlap` command under `@subsystem.command`

### Step 3: Implement task-aware chunk resolution

When task context is detected:

1. Load task config to get the external artifacts repo reference
2. Resolve the external repo path using `resolve_repo_directory()`
3. Try to resolve the chunk in the external repo first using `Chunks(external_repo_path).resolve_chunk_id()`
4. If not found in external, search in each project repo
5. If found, create `Chunks` and `Subsystems` instances against the resolved project path
6. If not found anywhere, emit helpful error message with search locations

When no task context:
- Continue with existing local-only behavior (no change)

Location: `src/ve.py` - `overlap` command under `@subsystem.command`

### Step 4: Handle cross-project subsystem matching

The current `find_overlapping_subsystems()` uses the same project for both chunk and subsystem resolution. In task context, we need to:

1. Get the chunk's code references from the resolved location (external repo)
2. Check against subsystems in the same location (external repo for external chunks)

Since the chunk and subsystems are in the same repo (the external artifacts repo), the existing `find_overlapping_subsystems()` should work once we pass it the correct `Chunks` and `Subsystems` instances from the external repo.

The key insight is that we don't need to modify `Subsystems.find_overlapping_subsystems()` - we just need to call it with the correctly resolved instances.

Location: `src/ve.py` - `overlap` command under `@subsystem.command`

### Step 5: Run tests and verify

1. Run the new task context tests - they should now pass
2. Run existing `test_subsystem_overlap_cli.py` tests to confirm no regression
3. Run `test_subsystem_overlap_logic.py` to confirm business logic unchanged

## Risks and Open Questions

1. **Cross-project subsystem matching**: The current implementation assumes chunks and subsystems are in the same project. In task context, if a chunk in the external repo references code in a project repo, should we check for subsystem overlaps in both the external repo AND the project repos?

   **Resolution**: For this chunk, we follow the existing behavior where subsystems are checked in the same repo as the chunk. This is consistent with how subsystems work - they document patterns within a single codebase. If cross-project subsystem checking is needed, that would be a separate enhancement.

2. **Error message clarity**: When chunk not found, should we list all searched locations?

   **Resolution**: Yes, we should provide helpful error messages that indicate where we looked. This matches the success criteria: "Error messages are helpful when a chunk genuinely doesn't exist (vs. resolution failure)".

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