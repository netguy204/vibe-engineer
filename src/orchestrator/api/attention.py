# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_attention_queue - Attention queue API endpoints
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted attention queue endpoints
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
"""Attention queue endpoints for the orchestrator API.

Provides REST endpoints for managing attention queue items and submitting answers.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from orchestrator.api.common import (
    error_response,
    get_chunk_directory,
    get_store,
    not_found_response,
)
from orchestrator.models import WorkUnitPhase, WorkUnitStatus
from orchestrator.state import StaleWriteError
from orchestrator.websocket import (
    broadcast_attention_update,
    broadcast_work_unit_update,
)


# Chunk: docs/chunks/orch_attention_queue - Extract goal summary from chunk's GOAL.md Minor Goal section
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


# Chunk: docs/chunks/orch_attention_queue - GET /attention endpoint returning prioritized queue with enriched items
async def attention_endpoint(request: Request) -> JSONResponse:
    """GET /attention - Get prioritized attention queue.

    Returns NEEDS_ATTENTION work units ordered by:
    1. Number of work units blocked by this one (descending)
    2. Time waiting (older first)
    """
    store = get_store(request)

    attention_items = store.get_attention_queue()

    now = datetime.now(timezone.utc)
    result = []

    for unit, blocks_count in attention_items:
        # Compute time waiting in seconds
        time_waiting = (now - unit.updated_at).total_seconds()

        # Get goal summary from chunk directory (uses task context if available)
        goal_summary = None
        try:
            chunk_dir = get_chunk_directory(request, unit.chunk)
            goal_summary = _get_goal_summary(chunk_dir)
        except RuntimeError:
            pass  # Project not initialized

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


# Chunk: docs/chunks/orch_attention_queue - POST /work-units/{chunk}/answer endpoint for submitting answers
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for answer submissions
async def answer_endpoint(request: Request):
    """POST /work-units/{chunk}/answer - Submit answer to attention item.

    Stores the answer on the work unit and transitions it to READY
    for the scheduler to resume.

    Supports both JSON and form submissions for dashboard compatibility.
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at

    # Validate work unit is in NEEDS_ATTENTION state
    if unit.status != WorkUnitStatus.NEEDS_ATTENTION:
        return error_response(
            f"Work unit '{chunk}' is not in NEEDS_ATTENTION state "
            f"(current: {unit.status.value})",
            status_code=400,
        )

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
            return error_response("Invalid JSON body")

    if not answer:
        return error_response("Missing required field: answer")

    if not isinstance(answer, str):
        return error_response("answer must be a string")

    # Store answer and transition to READY
    unit.pending_answer = answer
    unit.attention_reason = None  # Clear the reason - it's been addressed
    unit.status = WorkUnitStatus.READY
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


# Chunk: docs/chunks/orch_retry_command - Retry endpoint for NEEDS_ATTENTION work units
async def retry_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/{chunk}/retry - Retry a NEEDS_ATTENTION work unit.

    Properly resets the work unit state for a fresh retry:
    - Clears session_id (prevents dead session resume)
    - Clears attention_reason (the issue is being retried, not answered)
    - Resets api_retry_count to 0 (fresh retry budget)
    - Clears next_retry_at (immediate scheduling)
    - Verifies worktree validity (clears if path doesn't exist)
    - Transitions NEEDS_ATTENTION → READY

    This is the correct way to retry a stuck work unit, unlike the generic
    PATCH endpoint which only updates explicitly provided fields.
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at

    # Validate work unit is in NEEDS_ATTENTION state
    if unit.status != WorkUnitStatus.NEEDS_ATTENTION:
        return error_response(
            f"Work unit '{chunk}' is not in NEEDS_ATTENTION state "
            f"(current: {unit.status.value}). Only NEEDS_ATTENTION work units can be retried.",
            status_code=400,
        )

    # Reset state for fresh retry
    unit.session_id = None  # Clear dead session reference
    unit.attention_reason = None  # Clear the attention reason
    unit.api_retry_count = 0  # Reset retry budget
    unit.next_retry_at = None  # Allow immediate scheduling

    # Check if worktree path exists - clear if it doesn't
    if unit.worktree is not None and not Path(unit.worktree).exists():
        unit.worktree = None

    # Transition to READY
    unit.status = WorkUnitStatus.READY
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

    # Broadcast the update via WebSocket
    await broadcast_attention_update("resolved", chunk)
    await broadcast_work_unit_update(
        chunk=chunk,
        status=updated.status.value,
        phase=updated.phase.value,
    )

    return JSONResponse(updated.model_dump_json_serializable())


# Chunk: docs/chunks/orch_retry_command - Retry-all endpoint for batch retry
async def retry_all_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/retry-all - Retry all NEEDS_ATTENTION work units.

    Accepts optional query parameter:
    - phase: Only retry chunks at this phase (e.g., ?phase=REVIEW)

    Returns count of retried work units and list of chunk names.
    """
    store = get_store(request)

    # Parse optional phase filter from query params
    phase_filter: Optional[str] = request.query_params.get("phase")

    # Validate phase filter if provided
    if phase_filter:
        try:
            WorkUnitPhase(phase_filter)
        except ValueError:
            valid_phases = [p.value for p in WorkUnitPhase]
            return error_response(
                f"Invalid phase '{phase_filter}'. "
                f"Valid phases: {', '.join(valid_phases)}",
                status_code=400,
            )

    # Get all NEEDS_ATTENTION work units
    all_units = store.list_work_units(status=WorkUnitStatus.NEEDS_ATTENTION)

    # Filter by phase if specified
    if phase_filter:
        units_to_retry = [u for u in all_units if u.phase.value == phase_filter]
    else:
        units_to_retry = all_units

    retried_chunks: list[str] = []

    for unit in units_to_retry:
        # Capture for optimistic locking
        expected_updated_at = unit.updated_at

        # Reset state for fresh retry
        unit.session_id = None
        unit.attention_reason = None
        unit.api_retry_count = 0
        unit.next_retry_at = None

        # Check if worktree path exists
        if unit.worktree is not None and not Path(unit.worktree).exists():
            unit.worktree = None

        # Transition to READY
        unit.status = WorkUnitStatus.READY
        unit.updated_at = datetime.now(timezone.utc)

        try:
            updated = store.update_work_unit(
                unit, expected_updated_at=expected_updated_at
            )
            retried_chunks.append(unit.chunk)

            # Broadcast the update via WebSocket
            await broadcast_attention_update("resolved", unit.chunk)
            await broadcast_work_unit_update(
                chunk=unit.chunk,
                status=updated.status.value,
                phase=updated.phase.value,
            )
        except StaleWriteError:
            # Skip this unit if it was modified concurrently - don't fail the whole batch
            continue

    return JSONResponse({
        "count": len(retried_chunks),
        "chunks": retried_chunks,
    })
