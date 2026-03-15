# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Local WebSocket server adapter for the leader board.

Wraps the portable :class:`LeaderBoardCore` with a Starlette/Uvicorn
WebSocket server that speaks the wire protocol defined in the spec.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

from leader_board.core import LeaderBoardCore
from leader_board.fs_storage import FileSystemStorage
from leader_board.models import (
    AuthFailedError,
    ChannelNotFoundError,
    CursorExpiredError,
    SwarmNotFoundError,
)
from leader_board.protocol import (
    AckFrame,
    AuthFrame,
    AuthOkFrame,
    ChallengeFrame,
    ChannelsFrame,
    ChannelsListFrame,
    ErrorFrame,
    InvalidFrameError,
    MessageFrame,
    RegisterSwarmFrame,
    SendFrame,
    SwarmInfoFrame,
    SwarmInfoResponseFrame,
    WatchFrame,
    parse_client_frame,
    serialize_server_frame,
)

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path.home() / ".ve" / "leader_board"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8374
DEFAULT_COMPACTION_INTERVAL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# WebSocket connection handler
# ---------------------------------------------------------------------------


async def _send_frame(ws: WebSocket, frame) -> None:
    """Serialize and send a server frame."""
    await ws.send_text(serialize_server_frame(frame))


async def _send_error(ws: WebSocket, code: str, message: str, **kwargs) -> None:
    """Send an error frame."""
    await _send_frame(ws, ErrorFrame(code=code, message=message, **kwargs))


async def _handle_watch(
    ws: WebSocket,
    core: LeaderBoardCore,
    frame: WatchFrame,
    authenticated_swarm: str,
) -> None:
    """Handle a watch frame — runs as a separate task to allow concurrency."""
    if frame.swarm != authenticated_swarm:
        await _send_error(
            ws,
            "swarm_not_found",
            f"Connection authenticated for swarm {authenticated_swarm!r}, "
            f"not {frame.swarm!r}",
        )
        return

    try:
        msg = await core.read_after(frame.swarm, frame.channel, frame.cursor)
        await _send_frame(
            ws,
            MessageFrame(
                channel=msg.channel,
                position=msg.position,
                body=base64.b64encode(msg.body).decode("ascii"),
                sent_at=msg.sent_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
    except ChannelNotFoundError:
        await _send_error(ws, "channel_not_found", f"Channel not found: {frame.channel}")
    except CursorExpiredError as exc:
        await _send_error(
            ws,
            "cursor_expired",
            f"Cursor expired; earliest available position: {exc.earliest_position}",
            earliest_position=exc.earliest_position,
        )
    except SwarmNotFoundError:
        await _send_error(ws, "swarm_not_found", f"Swarm not found: {frame.swarm}")


async def websocket_handler(ws: WebSocket) -> None:
    """Handle a single WebSocket connection through the full lifecycle."""
    await ws.accept()

    core: LeaderBoardCore = ws.app.state.core

    # Step 1: Send challenge
    nonce = os.urandom(32)
    await _send_frame(ws, ChallengeFrame(nonce=nonce.hex()))

    # Step 2: Await auth response
    try:
        raw = await ws.receive_text()
    except WebSocketDisconnect:
        return

    try:
        auth_frame = parse_client_frame(raw)
    except InvalidFrameError as exc:
        await _send_error(ws, "invalid_frame", str(exc))
        await ws.close()
        return

    authenticated_swarm: str | None = None

    if isinstance(auth_frame, AuthFrame):
        try:
            await core.verify_auth(
                auth_frame.swarm,
                nonce,
                bytes.fromhex(auth_frame.signature),
            )
            authenticated_swarm = auth_frame.swarm
        except SwarmNotFoundError:
            await _send_error(
                ws, "swarm_not_found", f"Swarm not found: {auth_frame.swarm}"
            )
            await ws.close()
            return
        except AuthFailedError:
            await _send_error(ws, "auth_failed", "Signature verification failed")
            await ws.close()
            return

    elif isinstance(auth_frame, RegisterSwarmFrame):
        try:
            await core.register_swarm(
                auth_frame.swarm,
                bytes.fromhex(auth_frame.public_key),
            )
            authenticated_swarm = auth_frame.swarm
        except ValueError as exc:
            await _send_error(ws, "auth_failed", str(exc))
            await ws.close()
            return

    else:
        await _send_error(
            ws,
            "invalid_frame",
            "Expected 'auth' or 'register_swarm' frame after challenge",
        )
        await ws.close()
        return

    # Step 3: Send auth_ok
    await _send_frame(ws, AuthOkFrame())

    # Step 4: Message loop
    watch_tasks: list[asyncio.Task] = []

    try:
        while True:
            try:
                raw = await ws.receive_text()
            except WebSocketDisconnect:
                break

            try:
                frame = parse_client_frame(raw)
            except InvalidFrameError as exc:
                await _send_error(ws, "invalid_frame", str(exc))
                continue

            # All post-auth frames must reference the authenticated swarm
            if isinstance(frame, (WatchFrame, SendFrame, ChannelsFrame, SwarmInfoFrame)):
                if frame.swarm != authenticated_swarm:
                    await _send_error(
                        ws,
                        "swarm_not_found",
                        f"Connection authenticated for swarm {authenticated_swarm!r}, "
                        f"not {frame.swarm!r}",
                    )
                    continue

            if isinstance(frame, WatchFrame):
                # Run watch in a separate task for concurrency
                task = asyncio.create_task(
                    _handle_watch(ws, core, frame, authenticated_swarm)
                )
                watch_tasks.append(task)

            elif isinstance(frame, SendFrame):
                try:
                    body = base64.b64decode(frame.body)
                    msg = await core.append(frame.swarm, frame.channel, body)
                    await _send_frame(
                        ws,
                        AckFrame(channel=msg.channel, position=msg.position),
                    )
                except SwarmNotFoundError:
                    await _send_error(
                        ws, "swarm_not_found", f"Swarm not found: {frame.swarm}"
                    )
                except ValueError as exc:
                    await _send_error(ws, "invalid_frame", str(exc))

            elif isinstance(frame, ChannelsFrame):
                try:
                    channels = await core.list_channels(frame.swarm)
                    await _send_frame(
                        ws,
                        ChannelsListFrame(
                            channels=[
                                {
                                    "name": ch.name,
                                    "head_position": ch.head_position,
                                    "oldest_position": ch.oldest_position,
                                }
                                for ch in channels
                            ]
                        ),
                    )
                except SwarmNotFoundError:
                    await _send_error(
                        ws, "swarm_not_found", f"Swarm not found: {frame.swarm}"
                    )

            elif isinstance(frame, SwarmInfoFrame):
                try:
                    swarm = await core._storage.get_swarm(frame.swarm)
                    if swarm is None:
                        await _send_error(
                            ws, "swarm_not_found", f"Swarm not found: {frame.swarm}"
                        )
                    else:
                        await _send_frame(
                            ws,
                            SwarmInfoResponseFrame(
                                swarm=swarm.swarm_id,
                                created_at=swarm.created_at.strftime(
                                    "%Y-%m-%dT%H:%M:%SZ"
                                ),
                            ),
                        )
                except SwarmNotFoundError:
                    await _send_error(
                        ws, "swarm_not_found", f"Swarm not found: {frame.swarm}"
                    )

            else:
                await _send_error(
                    ws,
                    "invalid_frame",
                    "Unexpected frame type in post-auth context",
                )
    finally:
        # Cancel any outstanding watch tasks
        for task in watch_tasks:
            task.cancel()
        for task in watch_tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


# ---------------------------------------------------------------------------
# Compaction scheduler
# ---------------------------------------------------------------------------


async def _compaction_loop(
    core: LeaderBoardCore,
    storage: FileSystemStorage,
    interval_seconds: int,
) -> None:
    """Periodically run compaction on all swarms and channels."""
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            channels = await _enumerate_all_channels(storage)
            total_removed = 0
            for swarm_id, channel in channels:
                removed = await core.compact(swarm_id, channel, min_age_days=30)
                total_removed += removed
            if total_removed > 0:
                logger.info("Compaction removed %d messages", total_removed)
        except Exception:
            logger.exception("Compaction error")


async def _enumerate_all_channels(
    storage: FileSystemStorage,
) -> list[tuple[str, str]]:
    """Enumerate all (swarm_id, channel) pairs from the filesystem."""
    result: list[tuple[str, str]] = []
    swarms_dir = storage._swarms_dir
    if not swarms_dir.exists():
        return result

    for swarm_dir in swarms_dir.iterdir():
        if not swarm_dir.is_dir():
            continue
        channels_dir = swarm_dir / "channels"
        if not channels_dir.exists():
            continue
        for ch_dir in channels_dir.iterdir():
            if ch_dir.is_dir():
                result.append((swarm_dir.name, ch_dir.name))
    return result


# ---------------------------------------------------------------------------
# Application factory and entry point
# ---------------------------------------------------------------------------


def create_app(
    storage_dir: Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    compaction_interval_seconds: int = DEFAULT_COMPACTION_INTERVAL,
    *,
    core: LeaderBoardCore | None = None,
    storage: FileSystemStorage | None = None,
) -> Starlette:
    """Create a configured Starlette application.

    Parameters
    ----------
    storage_dir:
        Root directory for filesystem storage. Defaults to ``~/.ve/leader_board/``.
    host:
        Bind address (stored on app.state for ``run_server``).
    port:
        Bind port (stored on app.state for ``run_server``).
    compaction_interval_seconds:
        How often (in seconds) to run the compaction sweep.
    core:
        Optional pre-configured core instance (for testing).
    storage:
        Optional pre-configured storage instance (for testing).
    """
    if storage is None:
        if storage_dir is None:
            storage_dir = DEFAULT_STORAGE_DIR
        storage = FileSystemStorage(storage_dir)

    if core is None:
        core = LeaderBoardCore(storage)

    compaction_task: asyncio.Task | None = None

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncGenerator:
        nonlocal compaction_task
        # Start compaction scheduler
        compaction_task = asyncio.create_task(
            _compaction_loop(core, storage, compaction_interval_seconds)
        )
        try:
            yield
        finally:
            # Stop compaction scheduler
            compaction_task.cancel()
            try:
                await compaction_task
            except asyncio.CancelledError:
                pass

    app = Starlette(
        routes=[WebSocketRoute("/ws", websocket_handler)],
        lifespan=lifespan,
    )
    app.state.core = core
    app.state.host = host
    app.state.port = port

    return app


def run_server(
    storage_dir: Path | None = None,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    compaction_interval_seconds: int = DEFAULT_COMPACTION_INTERVAL,
) -> None:
    """Create and run the leader board server.

    Called by ``ve board start``.
    """
    app = create_app(
        storage_dir=storage_dir,
        host=host,
        port=port,
        compaction_interval_seconds=compaction_interval_seconds,
    )
    uvicorn.run(app, host=host, port=port)
