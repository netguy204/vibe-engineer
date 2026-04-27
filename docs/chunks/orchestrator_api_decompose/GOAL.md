---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/orchestrator/api/__init__.py
  - src/orchestrator/api/common.py
  - src/orchestrator/api/work_units.py
  - src/orchestrator/api/scheduling.py
  - src/orchestrator/api/attention.py
  - src/orchestrator/api/conflicts.py
  - src/orchestrator/api/worktrees.py
  - src/orchestrator/api/streaming.py
  - src/orchestrator/api/app.py
  - docs/subsystems/orchestrator/OVERVIEW.md
code_references:
  - ref: src/orchestrator/api/__init__.py
    implements: "API package entry point with create_app re-export for backward compatibility"
  - ref: src/orchestrator/api/app.py#create_app
    implements: "Application factory that initializes app.state (store, project_dir, started_at, task_info) and assembles routes from all sub-modules"
  - ref: src/orchestrator/api/common.py
    implements: "Shared utilities: get_store, get_project_dir, get_started_at, get_task_info, get_chunk_directory replacing module-level globals"
  - ref: src/orchestrator/api/common.py#error_response
    implements: "Standardized error response helper"
  - ref: src/orchestrator/api/common.py#not_found_response
    implements: "Standardized 404 not found response helper"
  - ref: src/orchestrator/api/work_units.py
    implements: "CRUD endpoints for work units: status, list, get, create, update, delete, history"
  - ref: src/orchestrator/api/scheduling.py
    implements: "Scheduling endpoints: inject, queue, prioritize, config endpoints with top-level imports (no mid-file imports)"
  - ref: src/orchestrator/api/scheduling.py#_detect_initial_phase
    implements: "Phase detection helper moved to scheduling module"
  - ref: src/orchestrator/api/attention.py
    implements: "Attention queue management endpoints: attention list, answer submission"
  - ref: src/orchestrator/api/conflicts.py
    implements: "Conflict analysis endpoints: get, list, analyze, resolve conflicts"
  - ref: src/orchestrator/api/conflicts.py#retry_merge_endpoint
    implements: "Merge retry using WorktreeManager.delete_branch instead of subprocess.run"
  - ref: src/orchestrator/api/worktrees.py
    implements: "Worktree management endpoints: list, remove, prune"
  - ref: src/orchestrator/api/streaming.py
    implements: "WebSocket log streaming and dashboard endpoints"
  - ref: src/orchestrator/api/streaming.py#log_stream_websocket_endpoint
    implements: "Real-time log streaming via WebSocket"
  - ref: src/orchestrator/api/streaming.py#dashboard_endpoint
    implements: "HTML dashboard rendering endpoint"
narrative: null
investigation: null
subsystems:
  - subsystem_id: orchestrator
    relationship: implements
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_prune_consolidate
- chunk_validator_extract
- cli_formatters_extract
- frontmatter_import_consolidate
- models_subpackage
- orch_client_context
- project_artifact_registry
- remove_legacy_prefix
- scheduler_decompose
---

# Chunk Goal

## Minor Goal

The orchestrator HTTP API lives in domain-specific sub-modules under `src/orchestrator/api/` rather than a single 1,832-line `src/orchestrator/api.py`. Sub-modules separate CRUD endpoints, scheduling logic, attention queue management, conflict analysis, merge retry logic, worktree management, WebSocket log streaming, and dashboard rendering, so the orchestrator is easier to navigate, test in isolation, and modify safely.

This decomposition advances the project's maintainability goals through:

- **Reduced cognitive load**: Each sub-module owns a single domain, making it easier for agents and developers to locate and reason about specific functionality.
- **Improved testability**: Starlette application state (`app.state.store`, `app.state.project_dir`, `app.state.started_at`, `app.state.task_info`) replaces module-level mutable globals, enabling proper test isolation without monkeypatching.
- **Explicit dependency graph**: All imports sit at module top level rather than inline mid-file, making dependencies traceable.
- **Consolidated git operations**: `git_utils` and `WorktreeManager` mediate git operations rather than direct `subprocess.run` calls, reducing duplication and ensuring consistent error handling.

## Success Criteria

- `src/orchestrator/api.py` is replaced by `src/orchestrator/api/` package with the following sub-modules:
  - `api/__init__.py` — Package init, re-exports for backward compatibility
  - `api/app.py` — Application factory (`create_app`) that imports and registers routes from all sub-modules
  - `api/work_units.py` — CRUD endpoints for work units (create, read, update, delete, list)
  - `api/scheduling.py` — Inject, queue, prioritize, and scheduling config endpoints
  - `api/attention.py` — Attention queue management endpoints
  - `api/conflicts.py` — Conflict analysis endpoints
  - `api/worktrees.py` — Worktree management endpoints
  - `api/streaming.py` — WebSocket log streaming
- Module-level mutable globals (`_store`, `_project_dir`, `_started_at`, `_task_info`) are replaced with Starlette `app.state` attributes, accessed via request context
- All imports are at module top level; no mid-file imports remain in any sub-module
- All direct `subprocess.run` calls for git operations are replaced with calls to `git_utils` or `WorktreeManager`
- All existing orchestrator tests (`uv run pytest tests/`) continue to pass without modification (or with minimal import-path updates if tests referenced internal symbols)
- No functional behavior changes: all API endpoints maintain their existing request/response contracts
- Any external code that imports from `src/orchestrator/api` continues to work via re-exports in `__init__.py`