---
decision: FEEDBACK
summary: "Mid-file import of `logging` in streaming.py violates the 'no mid-file imports' success criterion"
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `src/orchestrator/api.py` is replaced by `src/orchestrator/api/` package with the following sub-modules:

- **Status**: satisfied
- **Evidence**: The old `api.py` is deleted and replaced by `api/` package containing `__init__.py`, `app.py`, `common.py`, `work_units.py`, `scheduling.py`, `attention.py`, `conflicts.py`, `worktrees.py`, `streaming.py`

### Criterion 2: `api/__init__.py` — Package init, re-exports for backward compatibility

- **Status**: satisfied
- **Evidence**: `api/__init__.py` exports `create_app` from `app.py` with proper backreference comments

### Criterion 3: `api/app.py` — Application factory (`create_app`) that imports and registers routes from all sub-modules

- **Status**: satisfied
- **Evidence**: `app.py` contains `create_app()` that imports all endpoint handlers and assembles routes with proper ordering (specific routes before generic `{chunk:path}`)

### Criterion 4: `api/work_units.py` — CRUD endpoints for work units (create, read, update, delete, list)

- **Status**: satisfied
- **Evidence**: Contains `status_endpoint`, `list_work_units_endpoint`, `get_work_unit_endpoint`, `create_work_unit_endpoint`, `update_work_unit_endpoint`, `delete_work_unit_endpoint`, `get_status_history_endpoint`

### Criterion 5: `api/scheduling.py` — Inject, queue, prioritize, and scheduling config endpoints

- **Status**: satisfied
- **Evidence**: Contains `inject_endpoint`, `queue_endpoint`, `prioritize_endpoint`, `get_config_endpoint`, `update_config_endpoint` plus helper functions `_parse_chunk_status`, `_detect_initial_phase`

### Criterion 6: `api/attention.py` — Attention queue management endpoints

- **Status**: satisfied
- **Evidence**: Contains `attention_endpoint`, `answer_endpoint`, and `_get_goal_summary` helper

### Criterion 7: `api/conflicts.py` — Conflict analysis endpoints

- **Status**: satisfied
- **Evidence**: Contains `get_conflicts_endpoint`, `list_all_conflicts_endpoint`, `analyze_conflicts_endpoint`, `resolve_conflict_endpoint`, `retry_merge_endpoint`

### Criterion 8: `api/worktrees.py` — Worktree management endpoints

- **Status**: satisfied
- **Evidence**: Contains `list_worktrees_endpoint`, `remove_worktree_endpoint`, `prune_work_unit_endpoint`, `prune_all_endpoint`

### Criterion 9: `api/streaming.py` — WebSocket log streaming

- **Status**: satisfied
- **Evidence**: Contains `log_stream_websocket_endpoint`, `websocket_endpoint`, `dashboard_endpoint` plus helpers `_get_log_directory`, `_detect_current_phase`, `_stream_log_file`

### Criterion 10: Module-level mutable globals (`_store`, `_project_dir`, `_started_at`, `_task_info`) are replaced with Starlette `app.state` attributes, accessed via request context

- **Status**: satisfied
- **Evidence**: `common.py` provides `get_store(request)`, `get_project_dir(request)`, `get_started_at(request)`, `get_task_info(request)` that access `request.app.state.*`. All endpoints use these accessors. `app.py` initializes `app.state.store`, `app.state.project_dir`, `app.state.started_at`, `app.state.task_info`

### Criterion 11: All imports are at module top level; no mid-file imports remain in any sub-module

- **Status**: gap
- **Evidence**: `streaming.py` has a mid-file import at line 147-148 inside `log_stream_websocket_endpoint`: `import logging` and `logger = logging.getLogger(__name__)`. This should be moved to module top level.

### Criterion 12: All direct `subprocess.run` calls for git operations are replaced with calls to `git_utils` or `WorktreeManager`

- **Status**: satisfied
- **Evidence**: No `subprocess.run` calls for git exist in the api package. `conflicts.py` line 249 uses `worktree_manager.delete_branch(chunk)` instead of direct subprocess call, with a comment explaining this: `# Chunk: docs/chunks/orchestrator_api_decompose - Use WorktreeManager.delete_branch instead of subprocess`

### Criterion 13: All existing orchestrator tests (`uv run pytest tests/`) continue to pass without modification (or with minimal import-path updates if tests referenced internal symbols)

- **Status**: satisfied
- **Evidence**: Ran `uv run pytest tests/` - all 2516 tests pass

### Criterion 14: No functional behavior changes: all API endpoints maintain their existing request/response contracts

- **Status**: satisfied
- **Evidence**: Test suite passes without modification, indicating endpoint contracts are preserved. Code inspection shows endpoints maintain same request/response structures.

### Criterion 15: Any external code that imports from `src/orchestrator/api` continues to work via re-exports in `__init__.py`

- **Status**: satisfied
- **Evidence**: Verified `from orchestrator.api import create_app` works correctly via Python import test

## Feedback Items

### Issue 1: Mid-file import in streaming.py

- **ID**: issue-midfile-import
- **Location**: `src/orchestrator/api/streaming.py:147-148`
- **Concern**: The `import logging` statement is inside the `log_stream_websocket_endpoint` function instead of at module top level, violating success criterion 11
- **Suggestion**: Move `import logging` to the module top level (after line 16 with other imports) and change line 148 to just `logger = logging.getLogger(__name__)` at module level
- **Severity**: functional
- **Confidence**: high
