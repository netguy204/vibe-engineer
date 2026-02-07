# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_attention_queue - Attention queue API endpoints
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted attention queue endpoints
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
from orchestrator.models import WorkUnitStatus
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
        updated = store.update_work_unit(unit)
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
