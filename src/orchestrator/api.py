# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
"""HTTP API for the orchestrator daemon.

Provides REST endpoints for work unit management and daemon status.
Built with Starlette for minimal dependencies.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from orchestrator.models import (
    OrchestratorState,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore, get_default_db_path


# Global state store - initialized when app is created
_store: Optional[StateStore] = None
_project_dir: Optional[Path] = None
_started_at: Optional[datetime] = None


def _get_store() -> StateStore:
    """Get the state store, raising an error if not initialized."""
    if _store is None:
        raise RuntimeError("State store not initialized")
    return _store


# Error response helpers


def _error_response(message: str, status_code: int = 400) -> JSONResponse:
    """Create a JSON error response."""
    return JSONResponse(
        {"error": message},
        status_code=status_code,
    )


def _not_found_response(resource: str, identifier: str) -> JSONResponse:
    """Create a 404 not found response."""
    return _error_response(f"{resource} '{identifier}' not found", status_code=404)


# Endpoint handlers


async def status_endpoint(request: Request) -> JSONResponse:
    """GET /status - Return daemon status information."""
    store = _get_store()

    work_unit_counts = store.count_by_status()

    uptime_seconds = None
    if _started_at:
        uptime_seconds = (datetime.now(timezone.utc) - _started_at).total_seconds()

    import os

    state = OrchestratorState(
        running=True,
        pid=os.getpid(),
        uptime_seconds=uptime_seconds,
        started_at=_started_at,
        work_unit_counts=work_unit_counts,
    )

    return JSONResponse(state.model_dump_json_serializable())


async def list_work_units_endpoint(request: Request) -> JSONResponse:
    """GET /work-units - List all work units."""
    store = _get_store()

    # Optional status filter
    status_param = request.query_params.get("status")
    status_filter = None
    if status_param:
        try:
            status_filter = WorkUnitStatus(status_param)
        except ValueError:
            return _error_response(f"Invalid status: {status_param}")

    units = store.list_work_units(status=status_filter)

    return JSONResponse({
        "work_units": [u.model_dump_json_serializable() for u in units],
        "count": len(units),
    })


async def get_work_unit_endpoint(request: Request) -> JSONResponse:
    """GET /work-units/{chunk} - Get a specific work unit."""
    chunk = request.path_params["chunk"]
    store = _get_store()

    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    return JSONResponse(unit.model_dump_json_serializable())


async def create_work_unit_endpoint(request: Request) -> JSONResponse:
    """POST /work-units - Create a new work unit."""
    store = _get_store()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response("Invalid JSON body")

    # Validate required fields
    if "chunk" not in body:
        return _error_response("Missing required field: chunk")

    # Parse phase with default
    phase_str = body.get("phase", "GOAL")
    try:
        phase = WorkUnitPhase(phase_str)
    except ValueError:
        return _error_response(f"Invalid phase: {phase_str}")

    # Parse status with default
    status_str = body.get("status", "READY")
    try:
        status = WorkUnitStatus(status_str)
    except ValueError:
        return _error_response(f"Invalid status: {status_str}")

    # Create work unit
    now = datetime.now(timezone.utc)
    unit = WorkUnit(
        chunk=body["chunk"],
        phase=phase,
        status=status,
        blocked_by=body.get("blocked_by", []),
        worktree=body.get("worktree"),
        created_at=now,
        updated_at=now,
    )

    try:
        created = store.create_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e), status_code=409)  # Conflict

    return JSONResponse(
        created.model_dump_json_serializable(),
        status_code=201,
    )


async def update_work_unit_endpoint(request: Request) -> JSONResponse:
    """PATCH /work-units/{chunk} - Update a work unit."""
    chunk = request.path_params["chunk"]
    store = _get_store()

    # Get existing unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response("Invalid JSON body")

    # Update fields if provided
    if "phase" in body:
        try:
            unit.phase = WorkUnitPhase(body["phase"])
        except ValueError:
            return _error_response(f"Invalid phase: {body['phase']}")

    if "status" in body:
        try:
            unit.status = WorkUnitStatus(body["status"])
        except ValueError:
            return _error_response(f"Invalid status: {body['status']}")

    if "blocked_by" in body:
        if not isinstance(body["blocked_by"], list):
            return _error_response("blocked_by must be a list")
        unit.blocked_by = body["blocked_by"]

    if "worktree" in body:
        unit.worktree = body["worktree"]

    # Update timestamp
    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e))

    return JSONResponse(updated.model_dump_json_serializable())


async def delete_work_unit_endpoint(request: Request) -> JSONResponse:
    """DELETE /work-units/{chunk} - Delete a work unit."""
    chunk = request.path_params["chunk"]
    store = _get_store()

    deleted = store.delete_work_unit(chunk)
    if not deleted:
        return _not_found_response("Work unit", chunk)

    return JSONResponse({"deleted": True, "chunk": chunk})


async def get_status_history_endpoint(request: Request) -> JSONResponse:
    """GET /work-units/{chunk}/history - Get status transition history."""
    chunk = request.path_params["chunk"]
    store = _get_store()

    # Verify work unit exists
    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    history = store.get_status_history(chunk)

    return JSONResponse({
        "chunk": chunk,
        "history": history,
    })


# Application factory


def create_app(project_dir: Path) -> Starlette:
    """Create the Starlette application.

    Args:
        project_dir: The project directory for database location

    Returns:
        Configured Starlette application
    """
    global _store, _project_dir, _started_at

    _project_dir = project_dir
    _started_at = datetime.now(timezone.utc)

    # Initialize state store
    db_path = get_default_db_path(project_dir)
    _store = StateStore(db_path)
    _store.initialize()

    # Note: More specific routes must come before generic {chunk:path} routes
    routes = [
        Route("/status", endpoint=status_endpoint, methods=["GET"]),
        Route("/work-units", endpoint=list_work_units_endpoint, methods=["GET"]),
        Route("/work-units", endpoint=create_work_unit_endpoint, methods=["POST"]),
        # History endpoint must come before generic {chunk:path} routes
        Route(
            "/work-units/{chunk}/history",
            endpoint=get_status_history_endpoint,
            methods=["GET"],
        ),
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

    return app
