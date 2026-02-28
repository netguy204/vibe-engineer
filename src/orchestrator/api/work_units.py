# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_foundation - REST endpoints for work unit CRUD and daemon status
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted work unit CRUD endpoints
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
"""Work unit CRUD endpoints for the orchestrator API.

Provides REST endpoints for creating, reading, updating, and deleting work units.
"""

import json
import logging
import os
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from orchestrator.api.common import (
    error_response,
    get_project_dir,
    get_started_at,
    get_store,
    not_found_response,
)
from orchestrator.models import (
    OrchestratorState,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.scheduler import unblock_dependents
from orchestrator.state import StaleWriteError
from orchestrator.websocket import (
    broadcast_attention_update,
    broadcast_work_unit_update,
)
from orchestrator.worktree import WorktreeManager

logger = logging.getLogger(__name__)


async def status_endpoint(request: Request) -> JSONResponse:
    """GET /status - Return daemon status information."""
    store = get_store(request)
    started_at = get_started_at(request)

    work_unit_counts = store.count_by_status()

    uptime_seconds = None
    if started_at:
        uptime_seconds = (datetime.now(timezone.utc) - started_at).total_seconds()

    state = OrchestratorState(
        running=True,
        pid=os.getpid(),
        uptime_seconds=uptime_seconds,
        started_at=started_at,
        work_unit_counts=work_unit_counts,
    )

    return JSONResponse(state.model_dump_json_serializable())


async def list_work_units_endpoint(request: Request) -> JSONResponse:
    """GET /work-units - List all work units."""
    store = get_store(request)

    # Optional status filter
    status_param = request.query_params.get("status")
    status_filter = None
    if status_param:
        try:
            status_filter = WorkUnitStatus(status_param)
        except ValueError:
            return error_response(f"Invalid status: {status_param}")

    units = store.list_work_units(status=status_filter)

    return JSONResponse({
        "work_units": [u.model_dump_json_serializable() for u in units],
        "count": len(units),
    })


async def get_work_unit_endpoint(request: Request) -> JSONResponse:
    """GET /work-units/{chunk} - Get a specific work unit."""
    chunk = request.path_params["chunk"]
    store = get_store(request)

    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    return JSONResponse(unit.model_dump_json_serializable())


async def create_work_unit_endpoint(request: Request) -> JSONResponse:
    """POST /work-units - Create a new work unit."""
    store = get_store(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    # Validate required fields
    if "chunk" not in body:
        return error_response("Missing required field: chunk")

    # Parse phase with default
    phase_str = body.get("phase", "GOAL")
    try:
        phase = WorkUnitPhase(phase_str)
    except ValueError:
        return error_response(f"Invalid phase: {phase_str}")

    # Parse status with default
    status_str = body.get("status", "READY")
    try:
        status = WorkUnitStatus(status_str)
    except ValueError:
        return error_response(f"Invalid status: {status_str}")

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
        return error_response(str(e), status_code=409)  # Conflict

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


# Chunk: docs/chunks/orch_manual_done_unblock - Unblock dependents when manually set to DONE
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for API updates
async def update_work_unit_endpoint(request: Request) -> JSONResponse:
    """PATCH /work-units/{chunk} - Update a work unit."""
    chunk = request.path_params["chunk"]
    store = get_store(request)

    # Get existing unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at
    old_status = unit.status

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    # Update fields if provided
    if "phase" in body:
        try:
            unit.phase = WorkUnitPhase(body["phase"])
        except ValueError:
            return error_response(f"Invalid phase: {body['phase']}")

    if "status" in body:
        try:
            unit.status = WorkUnitStatus(body["status"])
        except ValueError:
            return error_response(f"Invalid status: {body['status']}")

    if "blocked_by" in body:
        if not isinstance(body["blocked_by"], list):
            return error_response("blocked_by must be a list")
        unit.blocked_by = body["blocked_by"]

    if "worktree" in body:
        unit.worktree = body["worktree"]

    # Chunk: docs/chunks/orch_worktree_retain - Allow updating retain_worktree
    if "retain_worktree" in body:
        if not isinstance(body["retain_worktree"], bool):
            return error_response("retain_worktree must be a boolean")
        unit.retain_worktree = body["retain_worktree"]

    # Chunk: docs/chunks/orch_attention_queue - Allow updating attention_reason
    if "attention_reason" in body:
        unit.attention_reason = body["attention_reason"]

    # Update timestamp
    unit.updated_at = datetime.now(timezone.utc)

    try:
        updated = store.update_work_unit(
            unit, expected_updated_at=expected_updated_at
        )
    except StaleWriteError as e:
        return JSONResponse(
            {"error": "Concurrent modification detected", "detail": str(e)},
            status_code=409,
        )
    except ValueError as e:
        return error_response(str(e))

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

    # Chunk: docs/chunks/orch_manual_done_unblock - Unblock dependents when manually set to DONE
    # When status transitions to DONE via API, unblock any dependent work units
    if old_status != WorkUnitStatus.DONE and updated.status == WorkUnitStatus.DONE:
        unblock_dependents(store, chunk)

    return JSONResponse(updated.model_dump_json_serializable())


# Chunk: docs/chunks/orch_safe_branch_delete - Safety check for unmerged commits
async def delete_work_unit_endpoint(request: Request) -> JSONResponse:
    """DELETE /work-units/{chunk} - Delete a work unit.

    Query parameters:
        force: If "true", force delete even if branch has unmerged commits.
               If not provided or "false", deletion is refused when unmerged
               commits exist.
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)
    project_dir = get_project_dir(request)

    # Parse force query parameter
    force_param = request.query_params.get("force", "false").lower()
    force = force_param == "true"

    # Check for unmerged commits before deleting
    # This may fail if project_dir is not a git repo (e.g., in tests)
    worktree_manager = None
    try:
        worktree_manager = WorktreeManager(project_dir)
        has_unmerged, commit_count = worktree_manager.has_unmerged_commits(chunk)

        if has_unmerged and not force:
            return error_response(
                f"Branch has {commit_count} unmerged commit(s). "
                f"Use force=true to delete anyway, or merge changes first.",
                status_code=409,
            )
    except Exception as e:
        # If we can't check for unmerged commits (e.g., not a git repo),
        # proceed with deletion. This maintains compatibility with tests
        # and non-git environments.
        logger.debug(f"Could not check for unmerged commits: {e}")

    deleted = store.delete_work_unit(chunk)
    if not deleted:
        return not_found_response("Work unit", chunk)

    # Broadcast the deletion via WebSocket (use DELETED as special status)
    await broadcast_work_unit_update(
        chunk=chunk,
        status="DELETED",
        phase="",
        attention_reason=None,
    )

    # Remove worktree and branch to prevent stale branch reuse on re-inject
    if worktree_manager is not None:
        try:
            worktree_manager.remove_worktree(chunk, remove_branch=True, force=force)
        except Exception as e:
            # Worktree cleanup is best-effort; don't fail the delete
            logger.warning(f"Failed to cleanup worktree for '{chunk}': {e}")

    return JSONResponse({"deleted": True, "chunk": chunk})


async def get_status_history_endpoint(request: Request) -> JSONResponse:
    """GET /work-units/{chunk}/history - Get status transition history."""
    chunk = request.path_params["chunk"]
    store = get_store(request)

    # Verify work unit exists
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    history = store.get_status_history(chunk)

    return JSONResponse({
        "chunk": chunk,
        "history": history,
    })
