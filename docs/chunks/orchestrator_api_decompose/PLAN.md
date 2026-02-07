# Implementation Plan

## Approach

This decomposition follows a bottom-up strategy: create the infrastructure first (shared state, helpers), then extract each domain module, and finally wire everything together in the application factory. The approach uses Starlette's `app.state` for dependency injection, replacing module-level globals.

**Strategy:**

1. **Create shared infrastructure** - A `common.py` module with `AppState` protocol/type for accessing `store`, `project_dir`, `started_at`, and `task_info` from request context. This replaces the four module-level globals (`_store`, `_project_dir`, `_started_at`, `_task_info`).

2. **Extract domains incrementally** - Move endpoint functions to their respective modules one domain at a time, updating imports to use `request.app.state` instead of module globals. Each extraction is a discrete step that can be tested in isolation.

3. **Preserve the original file temporarily** - Keep `api.py` during development to allow side-by-side comparison. Delete it only after all extractions are complete and tests pass.

4. **Fix the mid-file import** - Move `from chunks import plan_has_content, Chunks` (currently at line 363) to the top of `scheduling.py`.

5. **Replace the direct git subprocess call** - The `subprocess.run(["git", "branch", "-d", ...])` in `retry_merge_endpoint` (line 1180) should use `WorktreeManager.delete_branch()` if available, or we add that capability to `WorktreeManager`.

**Test strategy per TESTING_PHILOSOPHY.md:**

- Existing tests in `tests/test_orchestrator_api.py` already test the endpoints. Since this is a pure refactoring, no new behavioral tests are required.
- Run the full test suite after each domain extraction to catch import or wiring issues.
- If any tests reference internal symbols from `api.py`, update the import paths.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS the `api.py` component listed in the subsystem's Implementation Locations section. After decomposition, the subsystem documentation should be updated to reflect the new package structure (`src/orchestrator/api/` instead of `src/orchestrator/api.py`). Since the subsystem is DOCUMENTED (not REFACTORING), we will note this in the subsystem's code_references but not expand scope to fix any deviations.

## Sequence

### Step 1: Create the api/ package directory structure

Create `src/orchestrator/api/` directory with empty `__init__.py`.

Location: `src/orchestrator/api/__init__.py`

### Step 2: Create common.py with shared state access

Create `src/orchestrator/api/common.py` containing:

1. Error response helpers (`_error_response`, `_not_found_response`)
2. `get_store(request)` function that returns `request.app.state.store`
3. `get_project_dir(request)` function that returns `request.app.state.project_dir`
4. `get_task_info(request)` function that returns `request.app.state.task_info`
5. `get_chunk_directory(request, chunk)` function - refactored version of `_get_chunk_directory`
6. Jinja2 environment accessor `get_jinja_env()`

All functions accept `request: Request` as the first parameter to access `app.state`.

Location: `src/orchestrator/api/common.py`

### Step 3: Extract work_units.py (CRUD endpoints)

Move work unit CRUD endpoints to `src/orchestrator/api/work_units.py`:

- `status_endpoint`
- `list_work_units_endpoint`
- `get_work_unit_endpoint`
- `create_work_unit_endpoint`
- `update_work_unit_endpoint`
- `delete_work_unit_endpoint`
- `get_status_history_endpoint`

Update each function to:
1. Import from `common` instead of using module globals
2. Call `get_store(request)` instead of `_get_store()`
3. Use `get_project_dir(request)` where needed

Preserve all existing chunk backreference comments.

Location: `src/orchestrator/api/work_units.py`

### Step 4: Extract scheduling.py (inject, queue, config)

Move scheduling endpoints to `src/orchestrator/api/scheduling.py`:

- `_parse_chunk_status` (helper)
- `_detect_initial_phase` (helper)
- `inject_endpoint`
- `queue_endpoint`
- `prioritize_endpoint`
- `get_config_endpoint`
- `update_config_endpoint`

**Critical fix:** Move `from chunks import plan_has_content, Chunks` to the TOP of this module instead of mid-file.

Location: `src/orchestrator/api/scheduling.py`

### Step 5: Extract attention.py (attention queue, answers)

Move attention management endpoints to `src/orchestrator/api/attention.py`:

- `_get_goal_summary` (helper)
- `attention_endpoint`
- `answer_endpoint`

Location: `src/orchestrator/api/attention.py`

### Step 6: Extract conflicts.py (conflict analysis)

Move conflict endpoints to `src/orchestrator/api/conflicts.py`:

- `get_conflicts_endpoint`
- `list_all_conflicts_endpoint`
- `analyze_conflicts_endpoint`
- `resolve_conflict_endpoint`
- `retry_merge_endpoint`

**Critical fix:** Replace the direct `subprocess.run(["git", "branch", "-d", ...])` call with `WorktreeManager.remove_branch()` or equivalent. Check if `WorktreeManager` already has this capability; if not, add a `delete_branch(branch_name)` method.

Location: `src/orchestrator/api/conflicts.py`

### Step 7: Extract worktrees.py (worktree management)

Move worktree management endpoints to `src/orchestrator/api/worktrees.py`:

- `list_worktrees_endpoint`
- `remove_worktree_endpoint`
- `prune_work_unit_endpoint`
- `prune_all_endpoint`

Location: `src/orchestrator/api/worktrees.py`

### Step 8: Extract streaming.py (WebSocket log streaming)

Move log streaming functionality to `src/orchestrator/api/streaming.py`:

- `_get_log_directory` (helper)
- `_detect_current_phase` (helper)
- `_stream_log_file` (helper)
- `log_stream_websocket_endpoint`
- `websocket_endpoint` (dashboard WebSocket)
- `dashboard_endpoint`

Location: `src/orchestrator/api/streaming.py`

### Step 9: Create app.py with application factory

Create `src/orchestrator/api/app.py` containing:

1. `create_app(project_dir: Path) -> Starlette` function
2. Initialize `app.state.store`, `app.state.project_dir`, `app.state.started_at`, `app.state.task_info`
3. Import routes from all sub-modules
4. Assemble the `routes` list with proper ordering (more specific routes before generic `{chunk:path}` routes)

Location: `src/orchestrator/api/app.py`

### Step 10: Update __init__.py for backward compatibility

Update `src/orchestrator/api/__init__.py` to re-export `create_app` from `app.py`:

```python
from orchestrator.api.app import create_app

__all__ = ["create_app"]
```

This ensures any code importing `from orchestrator.api import create_app` continues to work.

Location: `src/orchestrator/api/__init__.py`

### Step 11: Delete the old api.py and run tests

1. Delete `src/orchestrator/api.py`
2. Run `uv run pytest tests/` to verify all tests pass
3. If any tests fail due to import paths, update them

Location: `src/orchestrator/api.py` (delete)

### Step 12: Update subsystem documentation

Update `docs/subsystems/orchestrator/OVERVIEW.md` code_references to reflect new structure:
- Change `src/orchestrator/api.py#create_app` to `src/orchestrator/api/app.py#create_app`
- Add entries for new sub-modules

Location: `docs/subsystems/orchestrator/OVERVIEW.md`

## Risks and Open Questions

1. **WorktreeManager.delete_branch capability** - The GOAL mentions replacing direct subprocess git calls with WorktreeManager. Need to verify if `WorktreeManager` already has a `delete_branch` method. If not, we may need to add one or use `git_utils`. (Check `src/orchestrator/worktree.py` during implementation.)

2. **Route ordering sensitivity** - Starlette's routing is order-sensitive. The more specific routes (e.g., `/work-units/inject`) must come before generic routes (e.g., `/work-units/{chunk:path}`). This ordering must be preserved exactly when assembling routes in `app.py`.

3. **Test import paths** - Some tests in `test_orchestrator_api.py` import `from orchestrator.api import create_app`. The re-export in `__init__.py` should handle this, but need to verify no tests import internal symbols directly.

4. **Mid-file import side effects** - The current mid-file `from chunks import plan_has_content, Chunks` might have been placed there intentionally to avoid circular imports. Need to verify moving it to module top-level doesn't cause import errors.

## Deviations

*To be populated during implementation.*