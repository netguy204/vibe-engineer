# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_conflict_oracle - Conflict analysis API endpoints
# Chunk: docs/chunks/orch_blocked_lifecycle - SERIALIZE verdict transitions to BLOCKED
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted conflict endpoints
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
"""Conflict analysis endpoints for the orchestrator API.

Provides REST endpoints for conflict detection and resolution between
concurrent work units.
"""

import json
from datetime import datetime, timezone
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from orchestrator.api.common import (
    error_response,
    get_project_dir,
    get_store,
    not_found_response,
)
from orchestrator.models import ConflictVerdict, WorkUnitStatus
from orchestrator.oracle import create_oracle
from orchestrator.scheduler import unblock_dependents
from orchestrator.state import StaleWriteError
from orchestrator.websocket import (
    broadcast_attention_update,
    broadcast_work_unit_update,
)
from orchestrator.worktree import WorktreeError, WorktreeManager


async def get_conflicts_endpoint(request: Request) -> JSONResponse:
    """GET /conflicts/{chunk} - Get all conflict analyses for a chunk.

    Returns all conflict analyses involving the specified chunk, ordered by
    creation time (newest first).
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)

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
    store = get_store(request)

    # Optional verdict filter
    verdict_param = request.query_params.get("verdict")
    verdict_filter = None
    if verdict_param:
        try:
            verdict_filter = ConflictVerdict(verdict_param)
        except ValueError:
            return error_response(f"Invalid verdict: {verdict_param}")

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
    store = get_store(request)
    project_dir = get_project_dir(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON body")

    chunk_a = body.get("chunk_a")
    chunk_b = body.get("chunk_b")

    if not chunk_a or not chunk_b:
        return error_response("Missing required fields: chunk_a and chunk_b")

    # Create oracle and analyze
    oracle = create_oracle(project_dir, store)

    try:
        analysis = oracle.analyze_conflict(chunk_a, chunk_b)
    except Exception as e:
        return error_response(f"Analysis failed: {e}", status_code=500)

    return JSONResponse(analysis.model_dump_json_serializable())


# Chunk: docs/chunks/orch_blocked_lifecycle - SERIALIZE verdict transitions to BLOCKED and clears attention_reason
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for conflict resolution
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
    store = get_store(request)

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at

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
            return error_response("Invalid JSON body")

    if not other_chunk or not verdict:
        return error_response("Missing required fields: other_chunk and verdict")

    # Validate verdict
    if verdict not in ("parallelize", "serialize"):
        return error_response("verdict must be 'parallelize' or 'serialize'")

    # Map human-readable verdict to enum
    resolved_verdict = (
        ConflictVerdict.INDEPENDENT if verdict == "parallelize"
        else ConflictVerdict.SERIALIZE
    )

    # Update conflict_verdicts on the work unit
    unit.conflict_verdicts[other_chunk] = resolved_verdict.value
    unit.updated_at = datetime.now(timezone.utc)

    # If verdict is SERIALIZE, add to blocked_by if not already there
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

    return JSONResponse({
        "chunk": chunk,
        "other_chunk": other_chunk,
        "verdict": resolved_verdict.value,
        "blocked_by": updated.blocked_by,
    })


# Chunk: docs/chunks/optimistic_locking - Optimistic locking for retry merge
async def retry_merge_endpoint(request: Request):
    """POST /work-units/{chunk}/retry-merge - Retry a failed merge to base.

    After a merge failure, the user can resolve conflicts manually and then
    use this endpoint to retry the merge.
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)
    project_dir = get_project_dir(request)

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Capture for optimistic locking
    expected_updated_at = unit.updated_at

    # Validate work unit is in NEEDS_ATTENTION state with merge failure
    if unit.status != WorkUnitStatus.NEEDS_ATTENTION:
        return error_response(
            f"Work unit '{chunk}' is not in NEEDS_ATTENTION state "
            f"(current: {unit.status.value})",
            status_code=400,
        )

    if not unit.attention_reason or "merge to base failed" not in unit.attention_reason.lower():
        return error_response(
            f"Work unit '{chunk}' is not in a merge failure state",
            status_code=400,
        )

    # Get worktree manager
    worktree_manager = WorktreeManager(project_dir)

    # Retry the merge
    try:
        if worktree_manager.has_changes(chunk):
            worktree_manager.merge_to_base(chunk, delete_branch=True)
        else:
            # No changes - just clean up the branch using WorktreeManager
            # Chunk: docs/chunks/orchestrator_api_decompose - Use WorktreeManager.delete_branch instead of subprocess
            worktree_manager.delete_branch(chunk)
    except WorktreeError as e:
        # Still failing - update the error message
        unit.attention_reason = f"Merge to base failed: {e}"
        unit.updated_at = datetime.now(timezone.utc)
        try:
            store.update_work_unit(unit, expected_updated_at=expected_updated_at)
        except StaleWriteError:
            pass  # Best effort - merge error takes precedence

        # Check if form submission for redirect
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            return RedirectResponse(url="/", status_code=303)

        return error_response(f"Merge still failing: {e}", status_code=400)

    # Success - mark as DONE
    unit.status = WorkUnitStatus.DONE
    unit.attention_reason = None
    unit.session_id = None
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

    # Chunk: docs/chunks/orch_manual_done_unblock - Unblock dependents after successful merge retry
    # After a successful merge marks the work unit as DONE, unblock any dependent work units
    unblock_dependents(store, chunk)

    # Check if form submission for redirect
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        return RedirectResponse(url="/", status_code=303)

    return JSONResponse({
        "chunk": chunk,
        "status": "done",
        "message": "Merge completed successfully",
    })
