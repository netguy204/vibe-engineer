# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_scheduling - Scheduling API endpoints
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
    OrchestratorConfig,
    OrchestratorState,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore, get_default_db_path
from orchestrator.worktree import WorktreeManager


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

    # Remove worktree and branch to prevent stale branch reuse on re-inject
    if _project_dir:
        try:
            worktree_manager = WorktreeManager(_project_dir)
            worktree_manager.remove_worktree(chunk, remove_branch=True)
        except Exception:
            # Worktree cleanup is best-effort; don't fail the delete
            pass

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


# Scheduling endpoints


# Chunk: docs/chunks/orch_inject_validate - Import shared validation
# Chunk: docs/chunks/orch_activate_on_inject - Use Chunks class for status parsing
from chunks import plan_has_content, Chunks


def _parse_chunk_status(chunk_dir: Path) -> Optional[str]:
    """Parse the status field from a chunk's GOAL.md frontmatter.

    Uses the Chunks class for consistent frontmatter parsing.

    Args:
        chunk_dir: Path to the chunk directory

    Returns:
        The status string (e.g., "FUTURE", "IMPLEMENTING") or None if not found
    """
    # Extract chunk name from path
    chunk_name = chunk_dir.name

    # Navigate to project root (chunk_dir is /project/docs/chunks/chunk_name)
    project_root = chunk_dir.parent.parent.parent

    try:
        chunks = Chunks(project_root)
        frontmatter = chunks.parse_chunk_frontmatter(chunk_name)
        if frontmatter is not None:
            return frontmatter.status.value
        return None
    except Exception:
        return None


def _detect_initial_phase(chunk_dir: Path) -> WorkUnitPhase:
    """Detect the initial phase for a chunk based on existing files and status.

    Checks both file existence AND content to determine the appropriate phase.
    A PLAN.md that's just a template (no actual content) is treated as if it
    doesn't exist.

    Args:
        chunk_dir: Path to the chunk directory

    Returns:
        WorkUnitPhase to start from
    """
    goal_path = chunk_dir / "GOAL.md"
    plan_path = chunk_dir / "PLAN.md"

    # If no GOAL.md, start with GOAL phase
    if not goal_path.exists():
        return WorkUnitPhase.GOAL

    # Check chunk status from frontmatter
    chunk_status = _parse_chunk_status(chunk_dir)

    # Check if PLAN.md exists AND has actual content (not just template)
    plan_exists_with_content = plan_path.exists() and plan_has_content(plan_path)

    # For FUTURE or IMPLEMENTING chunks, the goal is already defined
    # so we start from PLAN phase (if no populated PLAN.md exists)
    if chunk_status in ("FUTURE", "IMPLEMENTING"):
        if not plan_exists_with_content:
            return WorkUnitPhase.PLAN
        else:
            return WorkUnitPhase.IMPLEMENT

    # If GOAL.md exists but no populated PLAN.md, start with PLAN
    if not plan_exists_with_content:
        return WorkUnitPhase.PLAN

    # Both exist with content - start with IMPLEMENT
    return WorkUnitPhase.IMPLEMENT


# Chunk: docs/chunks/orch_scheduling - Original inject endpoint
# Chunk: docs/chunks/orch_inject_validate - Added injection validation
async def inject_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/inject - Inject a chunk into the work pool.

    Validates chunk exists, is in a valid state for injection, and determines
    initial phase from chunk state.
    """
    store = _get_store()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response("Invalid JSON body")

    chunk = body.get("chunk")
    if not chunk:
        return _error_response("Missing required field: chunk")

    # Validate chunk is injectable (exists and status-content consistent)
    chunks_manager = Chunks(_project_dir)
    validation_result = chunks_manager.validate_chunk_injectable(chunk)

    if not validation_result.success:
        # Return all validation errors
        error_message = "; ".join(validation_result.errors)
        return _error_response(error_message, status_code=400)

    # Get the chunk directory for phase detection
    chunk_dir = _project_dir / "docs" / "chunks" / chunk

    # Check if work unit already exists
    existing = store.get_work_unit(chunk)
    if existing:
        return _error_response(
            f"Work unit for chunk '{chunk}' already exists (status: {existing.status.value})",
            status_code=409,
        )

    # Detect initial phase
    phase = body.get("phase")
    if phase:
        try:
            phase = WorkUnitPhase(phase)
        except ValueError:
            return _error_response(f"Invalid phase: {phase}")
    else:
        phase = _detect_initial_phase(chunk_dir)

    # Get optional priority
    priority = body.get("priority", 0)
    if not isinstance(priority, int):
        return _error_response("priority must be an integer")

    # Create work unit
    now = datetime.now(timezone.utc)
    unit = WorkUnit(
        chunk=chunk,
        phase=phase,
        status=WorkUnitStatus.READY,
        priority=priority,
        created_at=now,
        updated_at=now,
    )

    try:
        created = store.create_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e), status_code=409)

    # Include any validation warnings in the response
    response_data = created.model_dump_json_serializable()
    if validation_result.warnings:
        response_data["warnings"] = validation_result.warnings

    return JSONResponse(
        response_data,
        status_code=201,
    )


async def queue_endpoint(request: Request) -> JSONResponse:
    """GET /work-units/queue - Get ready queue ordered by priority."""
    store = _get_store()

    # Get ready queue
    units = store.get_ready_queue()

    return JSONResponse({
        "work_units": [u.model_dump_json_serializable() for u in units],
        "count": len(units),
    })


async def prioritize_endpoint(request: Request) -> JSONResponse:
    """PATCH /work-units/{chunk}/priority - Update work unit priority."""
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

    priority = body.get("priority")
    if priority is None:
        return _error_response("Missing required field: priority")

    if not isinstance(priority, int):
        return _error_response("priority must be an integer")

    # Update priority
    unit.priority = priority
    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e))

    return JSONResponse(updated.model_dump_json_serializable())


async def get_config_endpoint(request: Request) -> JSONResponse:
    """GET /config - Get orchestrator configuration."""
    store = _get_store()

    # Build config from stored values
    config = OrchestratorConfig()

    max_agents_str = store.get_config("max_agents")
    if max_agents_str:
        try:
            config.max_agents = int(max_agents_str)
        except ValueError:
            pass

    dispatch_str = store.get_config("dispatch_interval_seconds")
    if dispatch_str:
        try:
            config.dispatch_interval_seconds = float(dispatch_str)
        except ValueError:
            pass

    return JSONResponse(config.model_dump_json_serializable())


async def update_config_endpoint(request: Request) -> JSONResponse:
    """PATCH /config - Update orchestrator configuration."""
    store = _get_store()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response("Invalid JSON body")

    # Update max_agents if provided
    if "max_agents" in body:
        max_agents = body["max_agents"]
        if not isinstance(max_agents, int) or max_agents < 1:
            return _error_response("max_agents must be a positive integer")
        store.set_config("max_agents", str(max_agents))

    # Update dispatch_interval_seconds if provided
    if "dispatch_interval_seconds" in body:
        interval = body["dispatch_interval_seconds"]
        if not isinstance(interval, (int, float)) or interval <= 0:
            return _error_response("dispatch_interval_seconds must be a positive number")
        store.set_config("dispatch_interval_seconds", str(interval))

    # Return updated config
    config = OrchestratorConfig()

    max_agents_str = store.get_config("max_agents")
    if max_agents_str:
        try:
            config.max_agents = int(max_agents_str)
        except ValueError:
            pass

    dispatch_str = store.get_config("dispatch_interval_seconds")
    if dispatch_str:
        try:
            config.dispatch_interval_seconds = float(dispatch_str)
        except ValueError:
            pass

    return JSONResponse(config.model_dump_json_serializable())


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
        # Config endpoints
        Route("/config", endpoint=get_config_endpoint, methods=["GET"]),
        Route("/config", endpoint=update_config_endpoint, methods=["PATCH"]),
        # Work unit endpoints
        Route("/work-units", endpoint=list_work_units_endpoint, methods=["GET"]),
        Route("/work-units", endpoint=create_work_unit_endpoint, methods=["POST"]),
        # Scheduling endpoints - must come before generic {chunk:path}
        Route("/work-units/inject", endpoint=inject_endpoint, methods=["POST"]),
        Route("/work-units/queue", endpoint=queue_endpoint, methods=["GET"]),
        # History and priority endpoints must come before generic {chunk:path}
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

    return app
