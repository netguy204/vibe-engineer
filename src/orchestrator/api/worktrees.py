# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_worktree_retain - Worktree management endpoints
# Chunk: docs/chunks/orch_prune_consolidate - Consolidated worktree finalization
# Chunk: docs/chunks/orchestrator_api_decompose - Extracted worktree management endpoints
"""Worktree management endpoints for the orchestrator API.

Provides REST endpoints for listing, removing, and pruning worktrees.
"""

import json
import os
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from orchestrator.api.common import (
    get_project_dir,
    get_store,
    not_found_response,
)
from orchestrator.models import WorktreeInfo, WorkUnitStatus
from orchestrator.worktree import WorktreeError, WorktreeManager


# Chunk: docs/chunks/orch_worktree_retain - Worktree listing endpoint
async def list_worktrees_endpoint(request: Request) -> JSONResponse:
    """GET /worktrees - List all worktrees with their status.

    Returns worktrees with status: active, completed, orphaned, or retained.
    - active: Work unit exists and is RUNNING
    - completed: Work unit is DONE without retain_worktree
    - retained: Work unit is DONE with retain_worktree=True
    - orphaned: No work unit exists, or work unit is not RUNNING/DONE
    """
    store = get_store(request)
    project_dir = get_project_dir(request)
    worktree_manager = WorktreeManager(project_dir)

    # Get all worktrees from the filesystem
    worktree_chunks = worktree_manager.list_worktrees()

    # Build list with status info
    worktrees = []
    for chunk_name in worktree_chunks:
        worktree_path = worktree_manager.get_worktree_path(chunk_name)

        # Get created_at from directory mtime
        created_at = None
        if worktree_path.exists():
            stat = os.stat(worktree_path)
            created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        # Look up work unit to determine status
        unit = store.get_work_unit(chunk_name)

        if unit is None:
            # No work unit - orphaned
            status = "orphaned"
            work_unit_status = None
            retain_worktree = False
        elif unit.status == WorkUnitStatus.RUNNING:
            status = "active"
            work_unit_status = unit.status
            retain_worktree = unit.retain_worktree
        elif unit.status == WorkUnitStatus.DONE:
            if unit.retain_worktree:
                status = "retained"
            else:
                status = "completed"
            work_unit_status = unit.status
            retain_worktree = unit.retain_worktree
        else:
            # Other statuses (READY, BLOCKED, etc.) - treat as orphaned
            status = "orphaned"
            work_unit_status = unit.status
            retain_worktree = unit.retain_worktree

        worktrees.append(WorktreeInfo(
            chunk=chunk_name,
            path=worktree_path,
            status=status,
            work_unit_status=work_unit_status,
            retain_worktree=retain_worktree,
            created_at=created_at,
        ))

    # Sort by status (retained first for visibility), then by chunk name
    status_order = {"retained": 0, "active": 1, "orphaned": 2, "completed": 3}
    worktrees.sort(key=lambda w: (status_order.get(w.status, 99), w.chunk))

    return JSONResponse({
        "worktrees": [w.to_dict() for w in worktrees],
        "count": len(worktrees),
    })


# Chunk: docs/chunks/orch_worktree_retain - Worktree removal endpoint
async def remove_worktree_endpoint(request: Request) -> JSONResponse:
    """DELETE /worktrees/{chunk} - Remove a specific worktree.

    Removes the worktree directory and optionally the branch.
    Does NOT merge changes - use prune for that.
    """
    chunk = request.path_params["chunk"]
    project_dir = get_project_dir(request)

    # Parse query params
    query = request.query_params
    remove_branch = query.get("remove_branch", "true").lower() == "true"

    worktree_manager = WorktreeManager(project_dir)

    # Check worktree exists
    if not worktree_manager.worktree_exists(chunk):
        return not_found_response("Worktree", chunk)

    try:
        worktree_manager.remove_worktree(chunk, remove_branch=remove_branch)
    except WorktreeError as e:
        return JSONResponse({
            "chunk": chunk,
            "status": "error",
            "error": str(e),
        }, status_code=500)

    return JSONResponse({
        "chunk": chunk,
        "status": "removed",
        "branch_removed": remove_branch,
    })


# Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
async def prune_work_unit_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/{chunk}/prune - Prune a retained worktree.

    Merges the worktree changes back to base and removes the worktree/branch.
    Only works on DONE work units with retain_worktree=True.
    """
    chunk = request.path_params["chunk"]
    store = get_store(request)
    project_dir = get_project_dir(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    dry_run = body.get("dry_run", False)

    # Get existing work unit
    unit = store.get_work_unit(chunk)
    if unit is None:
        return not_found_response("Work unit", chunk)

    # Must be DONE with retain_worktree set
    if unit.status != WorkUnitStatus.DONE:
        return JSONResponse({
            "chunk": chunk,
            "status": "skipped",
            "reason": f"Work unit not DONE (status: {unit.status.value})",
        })

    if not unit.retain_worktree:
        return JSONResponse({
            "chunk": chunk,
            "status": "skipped",
            "reason": "Work unit does not have retain_worktree set",
        })

    if dry_run:
        return JSONResponse({
            "chunk": chunk,
            "status": "would_prune",
        })

    # Chunk: docs/chunks/orch_prune_consolidate - Use consolidated finalize_work_unit
    worktree_manager = WorktreeManager(project_dir)

    try:
        worktree_manager.finalize_work_unit(chunk)
    except WorktreeError as e:
        return JSONResponse({
            "chunk": chunk,
            "status": "error",
            "error": str(e),
        })

    # Clear retain_worktree flag
    unit.retain_worktree = False
    unit.worktree = None
    unit.updated_at = datetime.now(timezone.utc)
    store.update_work_unit(unit)

    return JSONResponse({
        "chunk": chunk,
        "status": "pruned",
    })


# Chunk: docs/chunks/orch_worktree_retain - POST /work-units/prune for batch cleanup of retained worktrees
async def prune_all_endpoint(request: Request) -> JSONResponse:
    """POST /work-units/prune - Prune all retained worktrees.

    Finds all DONE work units with retain_worktree=True and prunes them.
    """
    store = get_store(request)
    project_dir = get_project_dir(request)

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}

    dry_run = body.get("dry_run", False)

    # Find all DONE work units with retain_worktree
    all_units = store.list_work_units(status=WorkUnitStatus.DONE)
    retained_units = [u for u in all_units if u.retain_worktree]

    results = []

    if dry_run:
        for unit in retained_units:
            results.append({
                "chunk": unit.chunk,
                "status": "would_prune",
            })
        return JSONResponse({"results": results})

    # Chunk: docs/chunks/orch_prune_consolidate - Use consolidated finalize_work_unit
    worktree_manager = WorktreeManager(project_dir)

    for unit in retained_units:
        chunk = unit.chunk
        try:
            worktree_manager.finalize_work_unit(chunk)

            # Clear retain_worktree flag
            unit.retain_worktree = False
            unit.worktree = None
            unit.updated_at = datetime.now(timezone.utc)
            store.update_work_unit(unit)

            results.append({
                "chunk": chunk,
                "status": "pruned",
            })
        except WorktreeError as e:
            results.append({
                "chunk": chunk,
                "status": "error",
                "error": str(e),
            })

    return JSONResponse({"results": results})
