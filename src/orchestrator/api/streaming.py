# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orchestrator_api_decompose - WebSocket streaming and dashboard endpoints
"""WebSocket streaming and dashboard endpoints for the orchestrator API.

Provides WebSocket endpoints for real-time log streaming and dashboard updates,
plus the dashboard HTML endpoint.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from orchestrator.api.attention import _get_goal_summary
from orchestrator.api.common import (
    get_chunk_directory,
    get_jinja_env,
    get_project_dir,
    get_store,
)
from orchestrator.log_parser import (
    format_entry_for_html,
    format_phase_header_for_html,
    parse_log_line,
)
from orchestrator.models import WorkUnitStatus
from orchestrator.websocket import get_manager


def _get_log_directory(project_dir: Path, chunk: str) -> Path:
    """Get the log directory for a chunk.

    Args:
        project_dir: The project directory
        chunk: Chunk name

    Returns:
        Path to the log directory (.ve/chunks/{chunk}/log/)
    """
    return project_dir / ".ve" / "chunks" / chunk / "log"


def _detect_current_phase(log_dir: Path) -> Optional[str]:
    """Detect the current phase from existing log files.

    Returns the most recent phase based on file modification time.

    Args:
        log_dir: Path to the log directory

    Returns:
        Phase name (e.g., 'plan', 'implement') or None if no logs
    """
    if not log_dir.exists():
        return None

    phases = ["goal", "plan", "implement", "review", "complete"]
    latest_mtime = 0.0
    latest_phase = None

    for phase in phases:
        log_file = log_dir / f"{phase}.txt"
        if log_file.exists():
            mtime = log_file.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_phase = phase

    return latest_phase


async def _stream_log_file(
    websocket: WebSocket,
    log_file: Path,
    phase: str,
    start_position: int = 0,
) -> int:
    """Stream log file contents to the WebSocket.

    Parses existing log lines and sends them as formatted HTML.

    Args:
        websocket: WebSocket connection to send to
        log_file: Path to the log file
        phase: Phase name for header
        start_position: File position to start reading from

    Returns:
        Final file position after reading
    """
    if not log_file.exists():
        return 0

    with open(log_file, "r") as f:
        f.seek(start_position)

        # If starting from beginning, send phase header
        if start_position == 0:
            # Get first entry timestamp for header
            first_line = f.readline()
            if first_line:
                entry = parse_log_line(first_line)
                if entry:
                    header = format_phase_header_for_html(
                        phase.upper(), entry.timestamp
                    )
                    await websocket.send_json({
                        "type": "log_line",
                        "content": header,
                        "is_header": True,
                    })
                    # Also send the first entry
                    lines = format_entry_for_html(entry)
                    for line in lines:
                        await websocket.send_json({
                            "type": "log_line",
                            "content": line,
                        })
            else:
                # Empty file, reset position
                f.seek(0)

        # Read remaining lines
        for line in f:
            entry = parse_log_line(line)
            if entry:
                formatted_lines = format_entry_for_html(entry)
                for formatted_line in formatted_lines:
                    await websocket.send_json({
                        "type": "log_line",
                        "content": formatted_line,
                    })

        return f.tell()


async def log_stream_websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming parsed log output.

    Connects to /ws/log/{chunk} and streams log entries for the specified chunk.
    Streams existing logs then follows for new entries.
    """
    import logging
    logger = logging.getLogger(__name__)

    chunk = websocket.path_params["chunk"]
    await websocket.accept()

    # Get log directory
    try:
        project_dir = get_project_dir(websocket)
        log_dir = _get_log_directory(project_dir, chunk)
    except RuntimeError as e:
        await websocket.send_json({
            "type": "error",
            "content": str(e),
        })
        await websocket.close()
        return

    # Check if chunk exists
    store = get_store(websocket)
    work_unit = store.get_work_unit(chunk)

    if work_unit is None:
        await websocket.send_json({
            "type": "error",
            "content": f"Chunk '{chunk}' not found",
        })
        await websocket.close()
        return

    # Detect current phase
    current_phase = _detect_current_phase(log_dir)

    if current_phase is None:
        # No logs yet - send informative message
        await websocket.send_json({
            "type": "info",
            "content": "Waiting for log output...",
        })

    # Track file positions for each phase
    file_positions: dict[str, int] = {}
    phases = ["goal", "plan", "implement", "review", "complete"]

    # Stream existing logs
    if current_phase:
        for phase in phases:
            log_file = log_dir / f"{phase}.txt"
            if log_file.exists():
                position = await _stream_log_file(websocket, log_file, phase, 0)
                file_positions[phase] = position

                # Stop if we've reached the current phase
                if phase == current_phase:
                    break

    # Enter follow mode - poll for new content
    poll_interval = 0.5  # 500ms polling
    try:
        while True:
            # Check if work unit is still running
            work_unit = store.get_work_unit(chunk)
            if work_unit is None:
                await websocket.send_json({
                    "type": "info",
                    "content": "Work unit removed",
                })
                break

            if work_unit.status == WorkUnitStatus.DONE:
                await websocket.send_json({
                    "type": "completed",
                    "content": "Work unit completed",
                })
                break

            # Re-detect current phase (might have transitioned)
            new_phase = _detect_current_phase(log_dir)

            if new_phase and new_phase != current_phase:
                # Phase transition - stream the new phase's logs
                log_file = log_dir / f"{new_phase}.txt"
                if log_file.exists():
                    position = await _stream_log_file(
                        websocket, log_file, new_phase, 0
                    )
                    file_positions[new_phase] = position
                    current_phase = new_phase

            elif current_phase:
                # Check for new content in current phase
                log_file = log_dir / f"{current_phase}.txt"
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    last_position = file_positions.get(current_phase, 0)

                    if current_size > last_position:
                        # New content available
                        position = await _stream_log_file(
                            websocket, log_file, current_phase, last_position
                        )
                        file_positions[current_phase] = position

            # Wait for next poll or client message
            try:
                # Use asyncio.wait_for to implement timeout while still
                # being able to receive messages (like heartbeat)
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=poll_interval,
                )
            except asyncio.TimeoutError:
                # Normal timeout, continue polling
                pass
            except WebSocketDisconnect:
                # Client disconnected
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Log stream error for chunk '{chunk}': {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Stream error: {e}",
            })
        except Exception:
            pass

    try:
        await websocket.close()
    except Exception:
        pass


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard updates.

    Sends initial state on connection and broadcasts updates when state changes.
    """
    manager = get_manager()
    await manager.connect(websocket)

    try:
        # Send initial state snapshot
        store = get_store(websocket)
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


async def dashboard_endpoint(request: Request) -> HTMLResponse:
    """GET / - Render the orchestrator dashboard.

    Shows the attention queue and work unit status grid with real-time updates.
    """
    store = get_store(request)

    # Get attention queue items
    attention_items = store.get_attention_queue()
    now = datetime.now(timezone.utc)

    attention_list = []
    for unit, blocks_count in attention_items:
        time_waiting = (now - unit.updated_at).total_seconds()
        goal_summary = None
        try:
            chunk_dir = get_chunk_directory(request, unit.chunk)
            goal_summary = _get_goal_summary(chunk_dir)
        except RuntimeError:
            pass  # Project not initialized

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
            # Chunk: docs/chunks/orch_worktree_retain - Include retain_worktree for dashboard display
            "retain_worktree": u.retain_worktree,
        }
        for u in all_units
    ]

    # Render the template
    env = get_jinja_env()
    template = env.get_template("dashboard.html")
    html = template.render(
        attention_items=attention_list,
        work_units=work_units,
    )

    return HTMLResponse(html)
