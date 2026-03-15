# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Adapter storage protocol for the leader board core.

Adapters implement this protocol to provide durable persistence.
The core calls these methods; it never touches storage directly.
"""

from __future__ import annotations

from typing import Protocol

from leader_board.models import ChannelInfo, ChannelMessage, SwarmInfo


class StorageAdapter(Protocol):
    """Protocol that adapter storage implementations must satisfy."""

    async def save_swarm(self, swarm: SwarmInfo) -> None:
        """Persist a new swarm. Caller ensures uniqueness."""
        ...

    async def get_swarm(self, swarm_id: str) -> SwarmInfo | None:
        """Look up a swarm by ID. Returns None if not found."""
        ...

    async def append_message(
        self, swarm_id: str, channel: str, body: bytes
    ) -> ChannelMessage:
        """Append a message, assigning a monotonic position and sent_at timestamp.

        The adapter is responsible for position assignment (starting at 1)
        and timestamping.
        """
        ...

    async def read_after(
        self, swarm_id: str, channel: str, cursor: int
    ) -> ChannelMessage | None:
        """Return the message at position > cursor, or None if none exists."""
        ...

    async def list_channels(self, swarm_id: str) -> list[ChannelInfo]:
        """List all channels in a swarm with head/oldest positions."""
        ...

    async def get_channel_info(
        self, swarm_id: str, channel: str
    ) -> ChannelInfo | None:
        """Get info for a specific channel, or None if it doesn't exist."""
        ...

    async def compact(
        self, swarm_id: str, channel: str, min_age_days: int
    ) -> int:
        """Remove messages older than min_age_days, always retaining the most recent.

        Returns the count of removed messages.
        """
        ...
