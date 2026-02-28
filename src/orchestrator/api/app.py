# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_foundation - Starlette app factory with REST endpoints for work unit CRUD
# Chunk: docs/chunks/orchestrator_api_decompose - Application factory with modular route imports
"""HTTP API application factory for the orchestrator daemon.

This module contains the create_app factory function that assembles the
Starlette application from modular route handlers.
"""

from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute

from orchestrator.api.attention import (
    answer_endpoint,
    attention_endpoint,
    retry_all_endpoint,
    retry_endpoint,
)
from orchestrator.api.conflicts import (
    analyze_conflicts_endpoint,
    get_conflicts_endpoint,
    list_all_conflicts_endpoint,
    resolve_conflict_endpoint,
    retry_merge_endpoint,
)
from orchestrator.api.scheduling import (
    get_config_endpoint,
    inject_endpoint,
    prioritize_endpoint,
    queue_endpoint,
    update_config_endpoint,
)
from orchestrator.api.streaming import (
    dashboard_endpoint,
    log_stream_websocket_endpoint,
    websocket_endpoint,
)
from orchestrator.api.work_units import (
    create_work_unit_endpoint,
    delete_work_unit_endpoint,
    get_status_history_endpoint,
    get_work_unit_endpoint,
    list_work_units_endpoint,
    status_endpoint,
    update_work_unit_endpoint,
)
from orchestrator.api.worktrees import (
    list_worktrees_endpoint,
    prune_all_endpoint,
    prune_work_unit_endpoint,
    remove_worktree_endpoint,
)
from orchestrator.models import detect_task_context
from orchestrator.state import StateStore, get_default_db_path


def create_app(project_dir: Path) -> Starlette:
    """Create the Starlette application.

    Initializes application state and assembles routes from all sub-modules.
    The application state includes:
    - store: StateStore for persistence
    - project_dir: Path to the project directory
    - started_at: Datetime when the daemon was started
    - task_info: TaskContextInfo for multi-repo support

    Args:
        project_dir: The project directory for database location
                     (or task directory in task context mode)

    Returns:
        Configured Starlette application with all routes registered
    """
    # Detect task context for chunk location resolution
    task_info = detect_task_context(project_dir)

    # Initialize state store
    db_path = get_default_db_path(project_dir)
    store = StateStore(db_path)
    store.initialize()

    # Note: More specific routes must come before generic {chunk:path} routes
    routes = [
        Route("/", endpoint=dashboard_endpoint, methods=["GET"]),
        WebSocketRoute("/ws", endpoint=websocket_endpoint),
        # Log streaming WebSocket - must come before generic routes
        WebSocketRoute("/ws/log/{chunk:path}", endpoint=log_stream_websocket_endpoint),
        Route("/status", endpoint=status_endpoint, methods=["GET"]),
        # Config endpoints
        Route("/config", endpoint=get_config_endpoint, methods=["GET"]),
        Route("/config", endpoint=update_config_endpoint, methods=["PATCH"]),
        # Attention queue endpoint
        Route("/attention", endpoint=attention_endpoint, methods=["GET"]),
        Route("/conflicts", endpoint=list_all_conflicts_endpoint, methods=["GET"]),
        Route("/conflicts/analyze", endpoint=analyze_conflicts_endpoint, methods=["POST"]),
        Route("/conflicts/{chunk:path}", endpoint=get_conflicts_endpoint, methods=["GET"]),
        # Chunk: docs/chunks/orch_worktree_retain - Worktree management endpoints
        Route("/worktrees", endpoint=list_worktrees_endpoint, methods=["GET"]),
        Route("/worktrees/{chunk:path}", endpoint=remove_worktree_endpoint, methods=["DELETE"]),
        # Work unit endpoints
        Route("/work-units", endpoint=list_work_units_endpoint, methods=["GET"]),
        Route("/work-units", endpoint=create_work_unit_endpoint, methods=["POST"]),
        # Scheduling endpoints - must come before generic {chunk:path}
        Route("/work-units/inject", endpoint=inject_endpoint, methods=["POST"]),
        Route("/work-units/queue", endpoint=queue_endpoint, methods=["GET"]),
        # Chunk: docs/chunks/orch_retry_command - Batch retry endpoint
        Route("/work-units/retry-all", endpoint=retry_all_endpoint, methods=["POST"]),
        # Chunk: docs/chunks/orch_worktree_retain - Prune all retained worktrees
        Route("/work-units/prune", endpoint=prune_all_endpoint, methods=["POST"]),
        # Answer, history, priority and resolve endpoints must come before generic {chunk:path}
        Route(
            "/work-units/{chunk}/answer",
            endpoint=answer_endpoint,
            methods=["POST"],
        ),
        # Chunk: docs/chunks/orch_retry_command - Single work unit retry endpoint
        Route(
            "/work-units/{chunk}/retry",
            endpoint=retry_endpoint,
            methods=["POST"],
        ),
        Route(
            "/work-units/{chunk}/history",
            endpoint=get_status_history_endpoint,
            methods=["GET"],
        ),
        Route(
            "/work-units/{chunk}/priority",
            endpoint=prioritize_endpoint,
            methods=["PATCH"],
        ),
        Route(
            "/work-units/{chunk}/resolve",
            endpoint=resolve_conflict_endpoint,
            methods=["POST"],
        ),
        # Retry merge endpoint for merge failures
        Route(
            "/work-units/{chunk}/retry-merge",
            endpoint=retry_merge_endpoint,
            methods=["POST"],
        ),
        # Chunk: docs/chunks/orch_worktree_retain - Prune retained worktree
        Route(
            "/work-units/{chunk}/prune",
            endpoint=prune_work_unit_endpoint,
            methods=["POST"],
        ),
        # Generic work unit endpoints
        Route(
            "/work-units/{chunk:path}",
            endpoint=get_work_unit_endpoint,
            methods=["GET"],
        ),
        Route(
            "/work-units/{chunk:path}",
            endpoint=update_work_unit_endpoint,
            methods=["PATCH"],
        ),
        Route(
            "/work-units/{chunk:path}",
            endpoint=delete_work_unit_endpoint,
            methods=["DELETE"],
        ),
    ]

    app = Starlette(routes=routes)

    # Initialize application state
    # These replace the module-level globals from the original api.py
    app.state.store = store
    app.state.project_dir = project_dir
    app.state.started_at = datetime.now(timezone.utc)
    app.state.task_info = task_info

    return app
