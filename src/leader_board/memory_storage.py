# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""In-memory storage adapter for the leader board core.

Used in tests and as a reference implementation for adapter authors.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from leader_board.models import ChannelInfo, ChannelMessage, SwarmInfo


class InMemoryStorage:
    """In-memory implementation of the StorageAdapter protocol."""

    def __init__(self) -> None:
        self._swarms: dict[str, SwarmInfo] = {}
        self._channels: dict[tuple[str, str], list[ChannelMessage]] = {}
        self._counters: dict[tuple[str, str], int] = {}

    async def save_swarm(self, swarm: SwarmInfo) -> None:
        self._swarms[swarm.swarm_id] = swarm

    async def get_swarm(self, swarm_id: str) -> SwarmInfo | None:
        return self._swarms.get(swarm_id)

    async def append_message(
        self, swarm_id: str, channel: str, body: bytes
    ) -> ChannelMessage:
        key = (swarm_id, channel)
        counter = self._counters.get(key, 0) + 1
        self._counters[key] = counter

        msg = ChannelMessage(
            channel=channel,
            position=counter,
            body=body,
            sent_at=datetime.now(UTC),
        )
        self._channels.setdefault(key, []).append(msg)
        return msg

    async def read_after(
        self, swarm_id: str, channel: str, cursor: int
    ) -> ChannelMessage | None:
        key = (swarm_id, channel)
        messages = self._channels.get(key, [])
        for msg in messages:
            if msg.position > cursor:
                return msg
        return None

    async def list_channels(self, swarm_id: str) -> list[ChannelInfo]:
        result: list[ChannelInfo] = []
        for (sid, ch), messages in self._channels.items():
            if sid == swarm_id and messages:
                result.append(
                    ChannelInfo(
                        name=ch,
                        head_position=messages[-1].position,
                        oldest_position=messages[0].position,
                    )
                )
        return result

    async def get_channel_info(
        self, swarm_id: str, channel: str
    ) -> ChannelInfo | None:
        key = (swarm_id, channel)
        messages = self._channels.get(key)
        if not messages:
            return None
        return ChannelInfo(
            name=channel,
            head_position=messages[-1].position,
            oldest_position=messages[0].position,
        )

    async def compact(
        self, swarm_id: str, channel: str, min_age_days: int
    ) -> int:
        key = (swarm_id, channel)
        messages = self._channels.get(key)
        if not messages:
            return 0

        cutoff = datetime.now(UTC) - timedelta(days=min_age_days)

        # Always retain the most recent message
        most_recent = messages[-1]
        to_keep = [
            msg for msg in messages if msg.sent_at >= cutoff or msg is most_recent
        ]
        removed = len(messages) - len(to_keep)
        self._channels[key] = to_keep
        return removed
