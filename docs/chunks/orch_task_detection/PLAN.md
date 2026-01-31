# Implementation Plan

## Approach

Add task context detection to the orchestrator daemon so it can run from a task
directory (identified by `.ve-task.yaml`) with `.ve/` at the task directory level
rather than inside individual repos.

The implementation builds on:
- **Existing orchestrator** (`src/orchestrator/daemon.py`, `scheduler.py`, `state.py`): The
  daemon, scheduler, and state store already work for single-repo mode. We extend them
  to detect and handle task context.
- **Existing task utilities** (`src/task_utils.py`): Functions like `is_task_directory()`,
  `load_task_config()`, and `resolve_repo_directory()` already handle task detection
  and config loading.
- **Existing worktree manager** (`src/orchestrator/worktree.py`): Already supports multi-repo
  worktrees (task context mode) via `create_worktree(chunk, repo_paths)`.

**Key design decisions:**
- **DEC-002 (git not assumed)**: Task directories are not git repos, so we adapt
  the daemon to work without a .git at the orchestrator root.
- The daemon detects task context via `.ve-task.yaml` presence and adjusts `.ve/`
  placement accordingly.
- Chunk definitions are read from the external artifacts repo per `.ve-task.yaml`.
- Work unit scheduling uses the `dependents` field in chunk GOAL.md to identify
  affected repos for worktree creation.

Testing follows docs/trunk/TESTING_PHILOSOPHY.md with TDD for behavioral code.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS task context
  detection for the orchestrator subsystem. Adds new code paths but follows existing
  patterns for daemon lifecycle and work unit management.

- **docs/subsystems/cross_repo_operations** (DOCUMENTED): This chunk USES the existing
  task config loading and repo resolution utilities from this subsystem.

## Sequence

### Step 1: Create task context detection helper

Add a `TaskContext` model and detection helper to `src/orchestrator/models.py`.

Create:
- `TaskContextInfo` dataclass with fields:
  - `is_task_context: bool`
  - `task_dir: Path` (the task directory, or project_dir if not task context)
  - `external_repo: str | None` (org/repo from config if task context)
  - `external_repo_path: Path | None` (resolved filesystem path)
  - `projects: list[str]` (list of org/repo refs)
  - `project_paths: list[Path]` (resolved filesystem paths)

Add function `detect_task_context(dir: Path) -> TaskContextInfo`:
- If `dir / ".ve-task.yaml"` exists, load config and resolve paths
- Otherwise return single-repo mode info

Location: `src/orchestrator/models.py`

### Step 2: Update daemon to detect task context on startup

Modify `start_daemon()` in `src/orchestrator/daemon.py`:
1. Call `detect_task_context(project_dir)` after resolving project_dir
2. Store task context info in config table for scheduler access
3. Adjust `.ve/` location based on context:
   - Task context: `.ve/` at task_dir level
   - Single-repo: `.ve/` at project_dir level (unchanged)
4. Pass appropriate directory to `StateStore`, `get_pid_path()`, etc.

Also update:
- `get_pid_path()`, `get_socket_path()`, `get_log_path()`, `get_port_path()`:
  Accept a root_dir parameter that defaults to project_dir for backward compatibility
- `_get_current_branch()`: Handle case where root_dir is not a git repo (task context)
- `get_daemon_status()`: Use the same root_dir detection

Location: `src/orchestrator/daemon.py`

### Step 3: Add chunk location helper for task context

Add function `get_chunk_location(task_info: TaskContextInfo, chunk: str) -> Path`:
- If task context: return `task_info.external_repo_path / "docs/chunks" / chunk`
- Otherwise: return `task_info.task_dir / "docs/chunks" / chunk`

Add function `get_chunk_dependents(chunk_path: Path) -> list[dict]`:
- Parse chunk GOAL.md frontmatter
- Return the `dependents` list (list of `{artifact_type, artifact_id, repo}` dicts)

Add function `resolve_affected_repos(task_info: TaskContextInfo, chunk: str) -> list[Path]`:
- Get dependents from chunk GOAL.md
- For each dependent with `artifact_type == "chunk"`, resolve its repo to a path
- Return list of affected project repo paths

Location: `src/orchestrator/models.py` (or new file `src/orchestrator/task_context.py`)

### Step 4: Update state store initialization for task context

Modify `get_default_db_path()` in `src/orchestrator/state.py`:
- Add optional `task_info: TaskContextInfo` parameter
- If task context, return `task_info.task_dir / ".ve" / "orchestrator.db"`
- Otherwise, use existing behavior

Location: `src/orchestrator/state.py`

### Step 5: Update scheduler to use task context for worktree creation

Modify `Scheduler` in `src/orchestrator/scheduler.py`:
1. Store `TaskContextInfo` in scheduler state (passed from daemon)
2. When creating worktrees, check if task context:
   - Task context: Call `resolve_affected_repos()` to get repo paths, then
     `worktree_manager.create_worktree(chunk, repo_paths)`
   - Single-repo: Use existing behavior `worktree_manager.create_worktree(chunk)`
3. When verifying chunk status, locate chunk via `get_chunk_location()`

Location: `src/orchestrator/scheduler.py`

### Step 6: Update worktree manager initialization

Modify `WorktreeManager.__init__()` in `src/orchestrator/worktree.py`:
- Add optional `task_info: TaskContextInfo` parameter
- Store task context for multi-repo operations
- When task context, set `self.project_dir` to task_dir (for `.ve/` placement)

Location: `src/orchestrator/worktree.py`

### Step 7: Update `ve orch inject` to handle task context

Modify the inject command logic:
1. Detect task context when resolving chunk location
2. If task context, look for chunk in external artifacts repo
3. Validate chunk exists before injection

Location: `src/ve.py` (orch inject command)

### Step 8: Write tests for task context detection

Add test file `tests/test_orch_task_context.py`:
- Test `detect_task_context()` with task directory (has `.ve-task.yaml`)
- Test `detect_task_context()` with single repo (no `.ve-task.yaml`)
- Test `get_chunk_location()` for both modes
- Test `resolve_affected_repos()` with dependents field

Location: `tests/test_orch_task_context.py`

### Step 9: Write integration tests for daemon in task context

Add tests to `tests/test_orch_daemon.py` or create new file:
- Test `start_daemon()` from task directory
- Verify `.ve/` is created at task directory level
- Verify daemon reads chunks from external repo
- Test `ve orch inject` finds chunks correctly in task context

Location: `tests/test_orch_daemon.py` or `tests/test_orch_task_integration.py`

### Step 10: Update code_paths in GOAL.md

Update chunk GOAL.md frontmatter with the files touched:
- `src/orchestrator/models.py`
- `src/orchestrator/daemon.py`
- `src/orchestrator/scheduler.py`
- `src/orchestrator/state.py`
- `src/orchestrator/worktree.py`
- `src/ve.py`
- `tests/test_orch_task_context.py`

## Dependencies

- **orch_task_worktrees** chunk should be complete (per investigation ordering) to
  ensure WorktreeManager supports multi-repo worktrees. Looking at the codebase,
  this is already implemented - `create_worktree()` accepts optional `repo_paths`.

## Risks and Open Questions

1. **Base branch handling in task context**: In single-repo mode, the daemon captures
   the current branch as base_branch. In task context, multiple repos may have
   different base branches. Current plan: each repo's base branch is captured
   individually when creating its worktree (already handled by
   `_get_repo_current_branch()`).

2. **Git operations in task directory**: The task directory itself is not a git repo.
   The `_get_current_branch()` function will fail if called with task_dir. Need to
   ensure daemon startup handles this - possibly by not capturing a "base branch"
   at the task level, only at per-repo level.

3. **Conflict detection across repos**: The ConflictOracle currently analyzes code
   overlaps. In task context with multiple repos, conflicts could span repos. This
   is likely out of scope for this chunk but should be noted.

4. **Dashboard display in task context**: The dashboard shows work units but may need
   updates to show which repos are affected. Likely out of scope for this chunk.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->