# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Domain models and exceptions for the leader board core."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

# --- Constants ---

CHANNEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
"""Valid channel names: 1-128 alphanumeric chars, underscores, hyphens."""

MESSAGE_MAX_BYTES = 1_048_576  # 1 MB
"""Maximum message body size in bytes."""


# --- Domain Models ---


class SwarmInfo(BaseModel):
    """Represents a registered swarm."""

    swarm_id: str
    public_key: bytes
    created_at: datetime


class ChannelMessage(BaseModel):
    """A single message in a channel log."""

    channel: str
    position: int = Field(ge=1)
    body: bytes
    sent_at: datetime


class ChannelInfo(BaseModel):
    """Summary info for a channel within a swarm."""

    name: str
    head_position: int = Field(ge=0)
    oldest_position: int = Field(ge=0)


# --- Exceptions ---


class SwarmNotFoundError(Exception):
    """Raised when a swarm_id is not registered."""

    def __init__(self, swarm_id: str) -> None:
        self.swarm_id = swarm_id
        super().__init__(f"Swarm not found: {swarm_id}")


class ChannelNotFoundError(Exception):
    """Raised when a channel has never been written to."""

    def __init__(self, channel: str) -> None:
        self.channel = channel
        super().__init__(f"Channel not found: {channel}")


class AuthFailedError(Exception):
    """Raised when signature verification fails."""

    pass


class CursorExpiredError(Exception):
    """Raised when a cursor is behind the compaction frontier."""

    def __init__(self, earliest_position: int) -> None:
        self.earliest_position = earliest_position
        super().__init__(
            f"Cursor expired; earliest available position: {earliest_position}"
        )
