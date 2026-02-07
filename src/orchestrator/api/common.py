# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orchestrator_api_decompose - Shared API utilities
"""Shared utilities for the orchestrator API.

This module provides helper functions for accessing application state
and generating error responses. All endpoint modules should use these
functions instead of accessing module-level globals directly.
"""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, PackageLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import JSONResponse

from orchestrator.models import TaskContextInfo, get_chunk_location
from orchestrator.state import StateStore

# Jinja2 environment for templates (lazily initialized)
_jinja_env: Optional[Environment] = None


def get_jinja_env() -> Environment:
    """Get or create the Jinja2 environment.

    Returns:
        Configured Jinja2 environment for rendering templates
    """
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=PackageLoader("orchestrator", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
    return _jinja_env


def get_store(request: Request) -> StateStore:
    """Get the state store from application state.

    Args:
        request: Starlette request object

    Returns:
        The StateStore instance

    Raises:
        RuntimeError: If state store not initialized
    """
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise RuntimeError("State store not initialized")
    return store


def get_project_dir(request: Request) -> Path:
    """Get the project directory from application state.

    Args:
        request: Starlette request object

    Returns:
        Path to the project directory

    Raises:
        RuntimeError: If project directory not initialized
    """
    project_dir = getattr(request.app.state, "project_dir", None)
    if project_dir is None:
        raise RuntimeError("Project directory not initialized")
    return project_dir


def get_started_at(request: Request):
    """Get the daemon start time from application state.

    Args:
        request: Starlette request object

    Returns:
        datetime when the daemon was started, or None
    """
    return getattr(request.app.state, "started_at", None)


def get_task_info(request: Request) -> Optional[TaskContextInfo]:
    """Get the task context info from application state.

    Args:
        request: Starlette request object

    Returns:
        TaskContextInfo if in task context mode, None otherwise
    """
    return getattr(request.app.state, "task_info", None)


def get_chunk_directory(request: Request, chunk: str) -> Path:
    """Get the chunk directory path, respecting task context.

    In task context mode, chunks are located in the external artifacts repo.
    In single-repo mode, chunks are in the project's docs/chunks/.

    Args:
        request: Starlette request object
        chunk: Chunk directory name

    Returns:
        Path to the chunk directory

    Raises:
        RuntimeError: If project directory not initialized
    """
    task_info = get_task_info(request)
    project_dir = get_project_dir(request)

    if task_info and task_info.is_task_context:
        return get_chunk_location(task_info, chunk)
    else:
        return project_dir / "docs" / "chunks" / chunk


# Error response helpers


def error_response(message: str, status_code: int = 400) -> JSONResponse:
    """Create a JSON error response.

    Args:
        message: Error message to include in response
        status_code: HTTP status code (default 400)

    Returns:
        JSONResponse with error message
    """
    return JSONResponse(
        {"error": message},
        status_code=status_code,
    )


def not_found_response(resource: str, identifier: str) -> JSONResponse:
    """Create a 404 not found response.

    Args:
        resource: Type of resource (e.g., "Work unit")
        identifier: Identifier of the resource (e.g., chunk name)

    Returns:
        JSONResponse with 404 status
    """
    return error_response(f"{resource} '{identifier}' not found", status_code=404)
