# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - Inject, queue, prioritize and config endpoints
# Chunk: docs/chunks/explicit_deps_batch_inject - Batch injection with explicit_deps parameter
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted scheduling endpoints
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
"""Scheduling endpoints for the orchestrator API.

Provides REST endpoints for work unit injection, queue management,
prioritization, and configuration.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

# NOTE: These imports were moved from mid-file in the original api.py
from chunks import Chunks, plan_has_content

from orchestrator.api.common import (
    error_response,
    get_chunk_directory,
    get_store,
    not_found_response,
)
from orchestrator.models import (
    OrchestratorConfig,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StaleWriteError
from orchestrator.websocket import broadcast_work_unit_update


# Chunk: docs/chunks/orch_activate_on_inject - Refactored to use Chunks class for consistent frontmatter parsing
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


# Chunk: docs/chunks/explicit_deps_batch_inject - API endpoint extended to accept blocked_by and explicit_deps parameters
# Chunk: docs/chunks/orch_task_detection - Inject endpoint with task context chunk location resolution
async def inject_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/inject - Inject a chunk into the work pool.

    Validates chunk exists, is in a valid state for injection, and determines
    initial phase from chunk state.

    In task context mode, chunks are validated against the external artifacts repo.
    In single-repo mode, chunks are validated against the project's docs/chunks/.
    """
    store = get_store(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    chunk = body.get("chunk")
    if not chunk:
        return error_response("Missing required field: chunk")

    # Get chunk directory using task context (uses external repo in task context mode)
    chunk_dir = get_chunk_directory(request, chunk)

    # Validate chunk is injectable (exists and status-content consistent)
    # Use the chunk directory's parent parent (docs/) parent (repo root) for Chunks manager
    chunk_repo_root = chunk_dir.parent.parent.parent
    chunks_manager = Chunks(chunk_repo_root)
    validation_result = chunks_manager.validate_chunk_injectable(chunk)

    if not validation_result.success:
        # Return all validation errors
        error_message = "; ".join(validation_result.errors)
        return error_response(error_message, status_code=400)

    # Check if work unit already exists
    existing = store.get_work_unit(chunk)
    if existing:
        return error_response(
            f"Work unit for chunk '{chunk}' already exists (status: {existing.status.value})",
            status_code=409,
        )

    # Detect initial phase
    phase = body.get("phase")
    if phase:
        try:
            phase = WorkUnitPhase(phase)
        except ValueError:
            return error_response(f"Invalid phase: {phase}")
    else:
        phase = _detect_initial_phase(chunk_dir)

    # Get optional priority
    priority = body.get("priority", 0)
    if not isinstance(priority, int):
        return error_response("priority must be an integer")

    # Get optional blocked_by list (for explicit dependency injection)
    blocked_by = body.get("blocked_by", [])
    if not isinstance(blocked_by, list):
        return error_response("blocked_by must be a list")

    # Get optional explicit_deps flag (signals oracle bypass for dependency management)
    explicit_deps = body.get("explicit_deps", False)
    if not isinstance(explicit_deps, bool):
        return error_response("explicit_deps must be a boolean")

    # Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
    # Get optional retain_worktree flag
    retain_worktree = body.get("retain_worktree", False)
    if not isinstance(retain_worktree, bool):
        return error_response("retain_worktree must be a boolean")

    # Chunk: docs/chunks/orch_inject_filter_done - Filter out already-DONE blockers
    # When injecting, remove blockers that are already DONE since they won't
    # trigger unblock_dependents() (that only fires on status transitions TO DONE).
    # Keep blockers that don't exist (can't assume they're DONE - may be injected later).
    active_blockers = []
    for blocker in blocked_by:
        blocker_unit = store.get_work_unit(blocker)
        if blocker_unit is None or blocker_unit.status != WorkUnitStatus.DONE:
            active_blockers.append(blocker)
    blocked_by = active_blockers

    # Determine initial status based on blocked_by
    initial_status = WorkUnitStatus.BLOCKED if blocked_by else WorkUnitStatus.READY

    # Create work unit
    now = datetime.now(timezone.utc)
    unit = WorkUnit(
        chunk=chunk,
        phase=phase,
        status=initial_status,
        priority=priority,
        blocked_by=blocked_by,
        explicit_deps=explicit_deps,
        # Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
        retain_worktree=retain_worktree,
        created_at=now,
        updated_at=now,
    )

    try:
        created = store.create_work_unit(unit)
    except ValueError as e:
        return error_response(str(e), status_code=409)

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
    store = get_store(request)

    # Get ready queue
    units = store.get_ready_queue()

    return JSONResponse({
        "work_units": [u.model_dump_json_serializable() for u in units],
        "count": len(units),
    })


# Chunk: docs/chunks/optimistic_locking - Optimistic locking for priority updates
async def prioritize_endpoint(request: Request) -> JSONResponse:
    """PATCH /work-units/{chunk}/priority - Update work unit priority."""
    chunk = request.path_params["chunk"]
    store = get_store(request)

    # Get existing unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    priority = body.get("priority")
    if priority is None:
        return error_response("Missing required field: priority")

    if not isinstance(priority, int):
        return error_response("priority must be an integer")

    # Update priority
    unit.priority = priority
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
    store = get_store(request)

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

    # Chunk: docs/chunks/orch_worktree_retain - Read worktree_warning_threshold from config
    threshold_str = store.get_config("worktree_warning_threshold")
    if threshold_str:
        try:
            config.worktree_warning_threshold = int(threshold_str)
        except ValueError:
            pass

    return JSONResponse(config.model_dump_json_serializable())


async def update_config_endpoint(request: Request) -> JSONResponse:
    """PATCH /config - Update orchestrator configuration."""
    store = get_store(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    # Update max_agents if provided
    if "max_agents" in body:
        max_agents = body["max_agents"]
        if not isinstance(max_agents, int) or max_agents < 1:
            return error_response("max_agents must be a positive integer")
        store.set_config("max_agents", str(max_agents))

    # Update dispatch_interval_seconds if provided
    if "dispatch_interval_seconds" in body:
        interval = body["dispatch_interval_seconds"]
        if not isinstance(interval, (int, float)) or interval <= 0:
            return error_response("dispatch_interval_seconds must be a positive number")
        store.set_config("dispatch_interval_seconds", str(interval))

    # Chunk: docs/chunks/orch_worktree_retain - Update worktree_warning_threshold if provided
    if "worktree_warning_threshold" in body:
        threshold = body["worktree_warning_threshold"]
        if not isinstance(threshold, int) or threshold < 1:
            return error_response("worktree_warning_threshold must be a positive integer")
        store.set_config("worktree_warning_threshold", str(threshold))

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

    # Chunk: docs/chunks/orch_worktree_retain - Read worktree_warning_threshold from config
    threshold_str = store.get_config("worktree_warning_threshold")
    if threshold_str:
        try:
            config.worktree_warning_threshold = int(threshold_str)
        except ValueError:
            pass

    return JSONResponse(config.model_dump_json_serializable())
