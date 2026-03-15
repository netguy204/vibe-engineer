# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Leader board — portable core library and local server adapter.

Public API
----------
**Core:**
- :class:`LeaderBoardCore` — entry-point for all operations
- :class:`StorageAdapter` — protocol that adapters implement
- :class:`InMemoryStorage` — reference / test implementation of StorageAdapter
- Domain models: :class:`SwarmInfo`, :class:`ChannelMessage`, :class:`ChannelInfo`
- Exceptions: :class:`CursorExpiredError`, :class:`SwarmNotFoundError`,
  :class:`ChannelNotFoundError`, :class:`AuthFailedError`
- Constants: :data:`CHANNEL_NAME_PATTERN`, :data:`MESSAGE_MAX_BYTES`

**Local server adapter:**
- :class:`FileSystemStorage` — filesystem-backed StorageAdapter
- :func:`create_app` — Starlette application factory
- :func:`run_server` — convenience entry point for Uvicorn

**Wire protocol:**
- Frame types and :func:`parse_client_frame` / :func:`serialize_server_frame`
"""

from leader_board.core import LeaderBoardCore
from leader_board.fs_storage import FileSystemStorage
from leader_board.memory_storage import InMemoryStorage
from leader_board.models import (
    CHANNEL_NAME_PATTERN,
    MESSAGE_MAX_BYTES,
    AuthFailedError,
    ChannelInfo,
    ChannelMessage,
    ChannelNotFoundError,
    CursorExpiredError,
    SwarmInfo,
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
from leader_board.server import create_app, run_server
from leader_board.storage import StorageAdapter

__all__ = [
    # Core
    "LeaderBoardCore",
    "StorageAdapter",
    "InMemoryStorage",
    "SwarmInfo",
    "ChannelMessage",
    "ChannelInfo",
    "CursorExpiredError",
    "SwarmNotFoundError",
    "ChannelNotFoundError",
    "AuthFailedError",
    "CHANNEL_NAME_PATTERN",
    "MESSAGE_MAX_BYTES",
    # Local server adapter
    "FileSystemStorage",
    "create_app",
    "run_server",
    # Wire protocol frames
    "AuthFrame",
    "RegisterSwarmFrame",
    "WatchFrame",
    "SendFrame",
    "ChannelsFrame",
    "SwarmInfoFrame",
    "ChallengeFrame",
    "AuthOkFrame",
    "MessageFrame",
    "AckFrame",
    "ChannelsListFrame",
    "SwarmInfoResponseFrame",
    "ErrorFrame",
    "InvalidFrameError",
    "parse_client_frame",
    "serialize_server_frame",
]
