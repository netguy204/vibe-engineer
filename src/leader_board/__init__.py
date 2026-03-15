# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Leader board core — portable, host-independent library.

Public API
----------
- :class:`LeaderBoardCore` — entry-point for all operations
- :class:`StorageAdapter` — protocol that adapters implement
- :class:`InMemoryStorage` — reference / test implementation of StorageAdapter
- Domain models: :class:`SwarmInfo`, :class:`ChannelMessage`, :class:`ChannelInfo`
- Exceptions: :class:`CursorExpiredError`, :class:`SwarmNotFoundError`,
  :class:`ChannelNotFoundError`, :class:`AuthFailedError`
- Constants: :data:`CHANNEL_NAME_PATTERN`, :data:`MESSAGE_MAX_BYTES`
"""

from leader_board.core import LeaderBoardCore
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
from leader_board.storage import StorageAdapter

__all__ = [
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
]
