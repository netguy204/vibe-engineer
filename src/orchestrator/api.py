# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_scheduling - Scheduling API endpoints
# Chunk: docs/chunks/orch_dashboard - Web dashboard with WebSocket support
"""HTTP API for the orchestrator daemon.

Provides REST endpoints for work unit management and daemon status.
Built with Starlette for minimal dependencies.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs

from jinja2 import Environment, PackageLoader, select_autoescape
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from orchestrator.models import (
    OrchestratorConfig,
    OrchestratorState,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore, get_default_db_path
from orchestrator.websocket import (
    broadcast_attention_update,
    broadcast_work_unit_update,
    get_manager,
)
from orchestrator.worktree import WorktreeManager

logger = logging.getLogger(__name__)

# Jinja2 environment for templates
_jinja_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    """Get or create the Jinja2 environment."""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=PackageLoader("orchestrator", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
    return _jinja_env

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

    # Broadcast the new work unit via WebSocket
    await broadcast_work_unit_update(
        chunk=created.chunk,
        status=created.status.value,
        phase=created.phase.value,
        attention_reason=created.attention_reason,
    )

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

    old_status = unit.status

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

    # Chunk: docs/chunks/orch_dashboard - Broadcast status changes via WebSocket
    await broadcast_work_unit_update(
        chunk=chunk,
        status=updated.status.value,
        phase=updated.phase.value,
        attention_reason=updated.attention_reason,
    )

    # Track attention queue changes
    if old_status != updated.status:
        if updated.status == WorkUnitStatus.NEEDS_ATTENTION:
            await broadcast_attention_update(
                "added", chunk, updated.attention_reason
            )
        elif old_status == WorkUnitStatus.NEEDS_ATTENTION:
            await broadcast_attention_update("resolved", chunk)

    return JSONResponse(updated.model_dump_json_serializable())


async def delete_work_unit_endpoint(request: Request) -> JSONResponse:
    """DELETE /work-units/{chunk} - Delete a work unit."""
    chunk = request.path_params["chunk"]
    store = _get_store()

    deleted = store.delete_work_unit(chunk)
    if not deleted:
        return _not_found_response("Work unit", chunk)

    # Broadcast the deletion via WebSocket (use DELETED as special status)
    await broadcast_work_unit_update(
        chunk=chunk,
        status="DELETED",
        phase="",
        attention_reason=None,
    )

    # Remove worktree and branch to prevent stale branch reuse on re-inject
    if _project_dir:
        try:
            worktree_manager = WorktreeManager(_project_dir)
            worktree_manager.remove_worktree(chunk, remove_branch=True)
        except Exception as e:
            # Worktree cleanup is best-effort; don't fail the delete
            logger.warning(f"Failed to cleanup worktree for '{chunk}': {e}")

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

    # Broadcast the new work unit via WebSocket
    await broadcast_work_unit_update(
        chunk=created.chunk,
        status=created.status.value,
        phase=created.phase.value,
        attention_reason=created.attention_reason,
    )

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

    # Broadcast the priority change via WebSocket
    await broadcast_work_unit_update(
        chunk=updated.chunk,
        status=updated.status.value,
        phase=updated.phase.value,
        attention_reason=updated.attention_reason,
    )

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


# Chunk: docs/chunks/orch_attention_queue - Attention queue endpoints


def _get_goal_summary(chunk_dir: Path) -> Optional[str]:
    """Extract a summary from the chunk's GOAL.md Minor Goal section.

    Args:
        chunk_dir: Path to the chunk directory

    Returns:
        First 200 chars of Minor Goal section, or None if not found
    """
    goal_path = chunk_dir / "GOAL.md"
    if not goal_path.exists():
        return None

    try:
        content = goal_path.read_text()
        # Look for ## Minor Goal section
        import re
        match = re.search(r"## Minor Goal\s*\n\s*\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if match:
            text = match.group(1).strip()
            # Truncate to 200 chars
            if len(text) > 200:
                return text[:197] + "..."
            return text
        return None
    except Exception:
        return None


async def attention_endpoint(request: Request) -> JSONResponse:
    """GET /attention - Get prioritized attention queue.

    Returns NEEDS_ATTENTION work units ordered by:
    1. Number of work units blocked by this one (descending)
    2. Time waiting (older first)
    """
    store = _get_store()

    attention_items = store.get_attention_queue()

    now = datetime.now(timezone.utc)
    result = []

    for unit, blocks_count in attention_items:
        # Compute time waiting in seconds
        time_waiting = (now - unit.updated_at).total_seconds()

        # Get goal summary from chunk directory
        goal_summary = None
        if _project_dir:
            chunk_dir = _project_dir / "docs" / "chunks" / unit.chunk
            goal_summary = _get_goal_summary(chunk_dir)

        item = {
            **unit.model_dump_json_serializable(),
            "blocks_count": blocks_count,
            "time_waiting": time_waiting,
            "goal_summary": goal_summary,
        }
        result.append(item)

    return JSONResponse({
        "attention_items": result,
        "count": len(result),
    })


# Chunk: docs/chunks/orch_dashboard - Dashboard and WebSocket endpoints


async def dashboard_endpoint(request: Request) -> HTMLResponse:
    """GET / - Render the orchestrator dashboard.

    Shows the attention queue and work unit status grid with real-time updates.
    """
    store = _get_store()

    # Get attention queue items
    attention_items = store.get_attention_queue()
    now = datetime.now(timezone.utc)

    attention_list = []
    for unit, blocks_count in attention_items:
        time_waiting = (now - unit.updated_at).total_seconds()
        goal_summary = None
        if _project_dir:
            chunk_dir = _project_dir / "docs" / "chunks" / unit.chunk
            goal_summary = _get_goal_summary(chunk_dir)

        attention_list.append({
            "chunk": unit.chunk,
            "phase": unit.phase.value,
            "status": unit.status.value,
            "blocked_by": unit.blocked_by,
            "attention_reason": unit.attention_reason,
            "blocks_count": blocks_count,
            "time_waiting": time_waiting,
            "goal_summary": goal_summary,
        })

    # Get all work units for the process grid
    all_units = store.list_work_units()
    work_units = [
        {
            "chunk": u.chunk,
            "phase": u.phase.value,
            "status": u.status.value,
            "blocked_by": u.blocked_by,
            "attention_reason": u.attention_reason,
        }
        for u in all_units
    ]

    # Render the template
    env = _get_jinja_env()
    template = env.get_template("dashboard.html")
    html = template.render(
        attention_items=attention_list,
        work_units=work_units,
    )

    return HTMLResponse(html)


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard updates.

    Sends initial state on connection and broadcasts updates when state changes.
    """
    manager = get_manager()
    await manager.connect(websocket)

    try:
        # Send initial state snapshot
        store = _get_store()
        work_units = store.list_work_units()
        attention_items = store.get_attention_queue()
        now = datetime.now(timezone.utc)

        initial_state = {
            "type": "initial_state",
            "data": {
                "work_units": [u.model_dump_json_serializable() for u in work_units],
                "attention_items": [
                    {
                        **unit.model_dump_json_serializable(),
                        "blocks_count": blocks_count,
                        "time_waiting": (now - unit.updated_at).total_seconds(),
                    }
                    for unit, blocks_count in attention_items
                ],
            },
        }
        await websocket.send_json(initial_state)

        # Keep the connection open and wait for messages or disconnect
        while True:
            try:
                # Wait for any message from the client (heartbeat, etc.)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await manager.disconnect(websocket)


async def answer_endpoint(request: Request):
    """POST /work-units/{chunk}/answer - Submit answer to attention item.

    Stores the answer on the work unit and transitions it to READY
    for the scheduler to resume.

    Supports both JSON and form submissions for dashboard compatibility.
    """
    chunk = request.path_params["chunk"]
    store = _get_store()

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    # Validate work unit is in NEEDS_ATTENTION state
    if unit.status != WorkUnitStatus.NEEDS_ATTENTION:
        return _error_response(
            f"Work unit '{chunk}' is not in NEEDS_ATTENTION state "
            f"(current: {unit.status.value})",
            status_code=400,
        )

    # Chunk: docs/chunks/orch_dashboard - Support form submissions
    # Check content type to determine how to parse the body
    content_type = request.headers.get("content-type", "")
    is_form_submission = "application/x-www-form-urlencoded" in content_type

    if is_form_submission:
        # Parse form data
        body_bytes = await request.body()
        form_data = parse_qs(body_bytes.decode("utf-8"))
        answer = form_data.get("answer", [None])[0]
    else:
        try:
            body = await request.json()
            answer = body.get("answer")
        except json.JSONDecodeError:
            return _error_response("Invalid JSON body")

    if not answer:
        return _error_response("Missing required field: answer")

    if not isinstance(answer, str):
        return _error_response("answer must be a string")

    # Store answer and transition to READY
    unit.pending_answer = answer
    unit.attention_reason = None  # Clear the reason - it's been addressed
    unit.status = WorkUnitStatus.READY
    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e))

    # Broadcast the update via WebSocket
    await broadcast_attention_update("resolved", chunk)
    await broadcast_work_unit_update(
        chunk=chunk,
        status=updated.status.value,
        phase=updated.phase.value,
    )

    # For form submissions, redirect back to dashboard
    if is_form_submission:
        return RedirectResponse(url="/", status_code=303)

    return JSONResponse(updated.model_dump_json_serializable())


# Chunk: docs/chunks/orch_conflict_oracle - Conflict analysis endpoints


async def get_conflicts_endpoint(request: Request) -> JSONResponse:
    """GET /conflicts/{chunk} - Get all conflict analyses for a chunk.

    Returns all conflict analyses involving the specified chunk, ordered by
    creation time (newest first).
    """
    chunk = request.path_params["chunk"]
    store = _get_store()

    conflicts = store.list_conflicts_for_chunk(chunk)

    return JSONResponse({
        "chunk": chunk,
        "conflicts": [c.model_dump_json_serializable() for c in conflicts],
        "count": len(conflicts),
    })


async def list_all_conflicts_endpoint(request: Request) -> JSONResponse:
    """GET /conflicts - List all conflict analyses.

    Optional query parameter:
    - verdict: Filter by verdict (INDEPENDENT, SERIALIZE, ASK_OPERATOR)
    """
    store = _get_store()

    from orchestrator.models import ConflictVerdict

    # Optional verdict filter
    verdict_param = request.query_params.get("verdict")
    verdict_filter = None
    if verdict_param:
        try:
            verdict_filter = ConflictVerdict(verdict_param)
        except ValueError:
            return _error_response(f"Invalid verdict: {verdict_param}")

    conflicts = store.list_all_conflicts(verdict=verdict_filter)

    return JSONResponse({
        "conflicts": [c.model_dump_json_serializable() for c in conflicts],
        "count": len(conflicts),
    })


async def analyze_conflicts_endpoint(request: Request) -> JSONResponse:
    """POST /conflicts/analyze - Trigger conflict analysis between two chunks.

    Request body:
    {
        "chunk_a": "chunk_name_1",
        "chunk_b": "chunk_name_2"
    }

    Returns the conflict analysis result.
    """
    store = _get_store()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _error_response("Invalid JSON body")

    chunk_a = body.get("chunk_a")
    chunk_b = body.get("chunk_b")

    if not chunk_a or not chunk_b:
        return _error_response("Missing required fields: chunk_a and chunk_b")

    # Create oracle and analyze
    from orchestrator.oracle import create_oracle

    oracle = create_oracle(_project_dir, store)

    try:
        analysis = oracle.analyze_conflict(chunk_a, chunk_b)
    except Exception as e:
        return _error_response(f"Analysis failed: {e}", status_code=500)

    return JSONResponse(analysis.model_dump_json_serializable())


async def resolve_conflict_endpoint(request: Request):
    """POST /work-units/{chunk}/resolve - Resolve an ASK_OPERATOR conflict.

    Request body:
    {
        "other_chunk": "chunk_name",
        "verdict": "parallelize" | "serialize"
    }

    Stores the operator's decision and updates the work unit accordingly.
    Supports both JSON and form submissions for dashboard compatibility.
    """
    chunk = request.path_params["chunk"]
    store = _get_store()

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    # Chunk: docs/chunks/orch_dashboard - Support form submissions
    content_type = request.headers.get("content-type", "")
    is_form_submission = "application/x-www-form-urlencoded" in content_type

    if is_form_submission:
        body_bytes = await request.body()
        form_data = parse_qs(body_bytes.decode("utf-8"))
        other_chunk = form_data.get("other_chunk", [None])[0]
        verdict = form_data.get("verdict", [None])[0]
    else:
        try:
            body = await request.json()
            other_chunk = body.get("other_chunk")
            verdict = body.get("verdict")
        except json.JSONDecodeError:
            return _error_response("Invalid JSON body")

    if not other_chunk or not verdict:
        return _error_response("Missing required fields: other_chunk and verdict")

    # Validate verdict
    if verdict not in ("parallelize", "serialize"):
        return _error_response("verdict must be 'parallelize' or 'serialize'")

    from orchestrator.models import ConflictVerdict

    # Map human-readable verdict to enum
    resolved_verdict = (
        ConflictVerdict.INDEPENDENT if verdict == "parallelize"
        else ConflictVerdict.SERIALIZE
    )

    # Update conflict_verdicts on the work unit
    unit.conflict_verdicts[other_chunk] = resolved_verdict.value
    unit.updated_at = datetime.now(timezone.utc)

    # If verdict is SERIALIZE, add to blocked_by if not already there
    # Chunk: docs/chunks/orch_blocked_lifecycle - SERIALIZE status transition
    if resolved_verdict == ConflictVerdict.SERIALIZE:
        if other_chunk not in unit.blocked_by:
            unit.blocked_by.append(other_chunk)
        # Transition from NEEDS_ATTENTION to BLOCKED and clear attention_reason
        if unit.status == WorkUnitStatus.NEEDS_ATTENTION:
            unit.status = WorkUnitStatus.BLOCKED
            unit.attention_reason = None
    # If verdict is INDEPENDENT, remove from blocked_by and potentially unblock
    elif resolved_verdict == ConflictVerdict.INDEPENDENT:
        if other_chunk in unit.blocked_by:
            unit.blocked_by.remove(other_chunk)
        # If no more blockers and status is NEEDS_ATTENTION due to conflict, unblock
        if not unit.blocked_by and unit.status == WorkUnitStatus.NEEDS_ATTENTION:
            if unit.attention_reason and "conflict" in unit.attention_reason.lower():
                unit.status = WorkUnitStatus.READY
                unit.attention_reason = None

    try:
        updated = store.update_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e))

    # Broadcast the update via WebSocket
    await broadcast_attention_update("resolved", chunk)
    await broadcast_work_unit_update(
        chunk=chunk,
        status=updated.status.value,
        phase=updated.phase.value,
    )

    # For form submissions, redirect back to dashboard
    if is_form_submission:
        return RedirectResponse(url="/", status_code=303)

    return JSONResponse({
        "chunk": chunk,
        "other_chunk": other_chunk,
        "verdict": resolved_verdict.value,
        "blocked_by": updated.blocked_by,
    })


async def retry_merge_endpoint(request: Request):
    """POST /work-units/{chunk}/retry-merge - Retry a failed merge to base.

    After a merge failure, the user can resolve conflicts manually and then
    use this endpoint to retry the merge.
    """
    chunk = request.path_params["chunk"]
    store = _get_store()

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return _not_found_response("Work unit", chunk)

    # Validate work unit is in NEEDS_ATTENTION state with merge failure
    if unit.status != WorkUnitStatus.NEEDS_ATTENTION:
        return _error_response(
            f"Work unit '{chunk}' is not in NEEDS_ATTENTION state "
            f"(current: {unit.status.value})",
            status_code=400,
        )

    if not unit.attention_reason or "merge to base failed" not in unit.attention_reason.lower():
        return _error_response(
            f"Work unit '{chunk}' is not in a merge failure state",
            status_code=400,
        )

    # Get worktree manager
    from orchestrator.worktree import WorktreeManager, WorktreeError

    worktree_manager = WorktreeManager(_project_dir)

    # Retry the merge
    try:
        if worktree_manager.has_changes(chunk):
            worktree_manager.merge_to_base(chunk, delete_branch=True)
        else:
            # No changes - just clean up the branch
            branch = worktree_manager.get_branch_name(chunk)
            if worktree_manager._branch_exists(branch):
                import subprocess
                subprocess.run(
                    ["git", "branch", "-d", branch],
                    cwd=_project_dir,
                    capture_output=True,
                )
    except WorktreeError as e:
        # Still failing - update the error message
        unit.attention_reason = f"Merge to base failed: {e}"
        unit.updated_at = datetime.now(timezone.utc)
        store.update_work_unit(unit)

        # Check if form submission for redirect
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            return RedirectResponse(url="/", status_code=303)

        return _error_response(f"Merge still failing: {e}", status_code=400)

    # Success - mark as DONE
    unit.status = WorkUnitStatus.DONE
    unit.attention_reason = None
    unit.session_id = None
    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(unit)
    except ValueError as e:
        return _error_response(str(e))

    # Broadcast the update via WebSocket
    await broadcast_attention_update("resolved", chunk)
    await broadcast_work_unit_update(
        chunk=chunk,
        status=updated.status.value,
        phase=updated.phase.value,
    )

    # Check if form submission for redirect
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        return RedirectResponse(url="/", status_code=303)

    return JSONResponse({
        "chunk": chunk,
        "status": "done",
        "message": "Merge completed successfully",
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
        # Chunk: docs/chunks/orch_dashboard - Dashboard and WebSocket routes
        Route("/", endpoint=dashboard_endpoint, methods=["GET"]),
        WebSocketRoute("/ws", endpoint=websocket_endpoint),
        Route("/status", endpoint=status_endpoint, methods=["GET"]),
        # Config endpoints
        Route("/config", endpoint=get_config_endpoint, methods=["GET"]),
        Route("/config", endpoint=update_config_endpoint, methods=["PATCH"]),
        # Attention queue endpoint
        Route("/attention", endpoint=attention_endpoint, methods=["GET"]),
        # Chunk: docs/chunks/orch_conflict_oracle - Conflict endpoints
        Route("/conflicts", endpoint=list_all_conflicts_endpoint, methods=["GET"]),
        Route("/conflicts/analyze", endpoint=analyze_conflicts_endpoint, methods=["POST"]),
        Route("/conflicts/{chunk:path}", endpoint=get_conflicts_endpoint, methods=["GET"]),
        # Work unit endpoints
        Route("/work-units", endpoint=list_work_units_endpoint, methods=["GET"]),
        Route("/work-units", endpoint=create_work_unit_endpoint, methods=["POST"]),
        # Scheduling endpoints - must come before generic {chunk:path}
        Route("/work-units/inject", endpoint=inject_endpoint, methods=["POST"]),
        Route("/work-units/queue", endpoint=queue_endpoint, methods=["GET"]),
        # Answer, history, priority and resolve endpoints must come before generic {chunk:path}
        Route(
            "/work-units/{chunk}/answer",
            endpoint=answer_endpoint,
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
        # Chunk: docs/chunks/orch_conflict_oracle - Conflict resolution endpoint
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
