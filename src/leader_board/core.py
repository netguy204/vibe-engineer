# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Leader board core — host-independent business logic.

The core owns swarm state, channel log operations, auth verification,
position assignment, FIFO ordering, and compaction. Adapters handle
transport, storage, connection lifecycle, and wire protocol encoding.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

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


class LeaderBoardCore:
    """Portable leader board core.

    All operations delegate to a ``StorageAdapter`` for persistence.
    The core never touches transport or storage directly — it only
    orchestrates validation, auth, and the blocking-read primitive.
    """

    def __init__(self, storage: StorageAdapter) -> None:
        self._storage = storage
        # Per-(swarm_id, channel) event used to wake blocked readers
        self._channel_events: dict[tuple[str, str], asyncio.Event] = defaultdict(
            asyncio.Event
        )

    # ------------------------------------------------------------------
    # Swarm operations
    # ------------------------------------------------------------------

    async def register_swarm(
        self, swarm_id: str, public_key: bytes
    ) -> SwarmInfo:
        """Register a new swarm with its Ed25519 public key.

        Raises ``ValueError`` if a swarm with that ID already exists.
        """
        existing = await self._storage.get_swarm(swarm_id)
        if existing is not None:
            raise ValueError(f"Swarm already exists: {swarm_id}")

        swarm = SwarmInfo(
            swarm_id=swarm_id,
            public_key=public_key,
            created_at=datetime.now(UTC),
        )
        await self._storage.save_swarm(swarm)
        return swarm

    async def verify_auth(
        self, swarm_id: str, nonce: bytes, signature: bytes
    ) -> bool:
        """Verify an Ed25519 signature over *nonce* for the given swarm.

        Returns ``True`` on success.
        Raises ``SwarmNotFoundError`` if the swarm is unknown.
        Raises ``AuthFailedError`` if the signature is invalid.
        """
        swarm = await self._storage.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(swarm_id)

        pub = Ed25519PublicKey.from_public_bytes(swarm.public_key)
        try:
            pub.verify(signature, nonce)
        except Exception:
            raise AuthFailedError("Signature verification failed")
        return True

    # ------------------------------------------------------------------
    # Channel operations
    # ------------------------------------------------------------------

    async def append(
        self, swarm_id: str, channel: str, body: bytes
    ) -> ChannelMessage:
        """Append *body* to *channel* within a swarm.

        Validates swarm existence, channel name format, and body size.
        Wakes any blocked ``read_after`` callers on the same channel.
        """
        # Swarm must exist
        swarm = await self._storage.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(swarm_id)

        # Validate channel name
        if not CHANNEL_NAME_PATTERN.match(channel):
            raise ValueError(
                f"Invalid channel name: {channel!r} "
                f"(must match {CHANNEL_NAME_PATTERN.pattern})"
            )

        # Validate body size
        if len(body) > MESSAGE_MAX_BYTES:
            raise ValueError(
                f"Message body too large: {len(body)} bytes "
                f"(max {MESSAGE_MAX_BYTES})"
            )

        msg = await self._storage.append_message(swarm_id, channel, body)

        # Wake any blocked readers
        key = (swarm_id, channel)
        event = self._channel_events[key]
        event.set()
        # Reset the event so future readers block again
        self._channel_events[key] = asyncio.Event()

        return msg

    async def read_after(
        self, swarm_id: str, channel: str, cursor: int
    ) -> ChannelMessage:
        """Return the next message after *cursor*, blocking if necessary.

        Raises ``SwarmNotFoundError`` if the swarm is unknown.
        Raises ``ChannelNotFoundError`` if the channel has never been written to.
        Raises ``CursorExpiredError`` if *cursor* is behind the compaction frontier.
        """
        swarm = await self._storage.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(swarm_id)

        key = (swarm_id, channel)

        while True:
            # Check if channel exists
            ch_info = await self._storage.get_channel_info(swarm_id, channel)
            if ch_info is None:
                raise ChannelNotFoundError(channel)

            # Check cursor expiration: if the next position the client
            # expects (cursor + 1) is older than the oldest retained message,
            # the client has missed messages.
            if cursor + 1 < ch_info.oldest_position:
                raise CursorExpiredError(ch_info.oldest_position)

            # Try to read
            msg = await self._storage.read_after(swarm_id, channel, cursor)
            if msg is not None:
                return msg

            # Block until a new message arrives
            event = self._channel_events[key]
            await event.wait()

    async def list_channels(self, swarm_id: str) -> list[ChannelInfo]:
        """List all channels in a swarm with their head/oldest positions."""
        swarm = await self._storage.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(swarm_id)
        return await self._storage.list_channels(swarm_id)

    # ------------------------------------------------------------------
    # Compaction
    # ------------------------------------------------------------------

    async def compact(
        self, swarm_id: str, channel: str, min_age_days: int = 30
    ) -> int:
        """Remove messages older than *min_age_days* from *channel*.

        Always retains the most recent message.
        Returns the count of removed messages.
        Raises ``SwarmNotFoundError`` if the swarm is unknown.
        """
        swarm = await self._storage.get_swarm(swarm_id)
        if swarm is None:
            raise SwarmNotFoundError(swarm_id)
        return await self._storage.compact(swarm_id, channel, min_age_days)
