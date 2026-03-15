# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Filesystem-based storage adapter for the leader board.

Persists swarm registration and channel message logs to disk so state
survives server restarts. Uses JSON files for simplicity and portability.

Directory layout under the configurable root::

    <root>/
      swarms/
        <swarm_id>/
          swarm.json
          channels/
            <channel_name>/
              messages.jsonl   # one JSON object per line, append-only
              meta.json        # head_position, oldest_position counters
"""

from __future__ import annotations

import fcntl
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from leader_board.models import ChannelInfo, ChannelMessage, SwarmInfo


class FileSystemStorage:
    """StorageAdapter backed by the local filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._swarms_dir = root / "swarms"
        self._swarms_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _swarm_dir(self, swarm_id: str) -> Path:
        return self._swarms_dir / swarm_id

    def _channel_dir(self, swarm_id: str, channel: str) -> Path:
        return self._swarm_dir(swarm_id) / "channels" / channel

    def _meta_path(self, swarm_id: str, channel: str) -> Path:
        return self._channel_dir(swarm_id, channel) / "meta.json"

    def _messages_path(self, swarm_id: str, channel: str) -> Path:
        return self._channel_dir(swarm_id, channel) / "messages.jsonl"

    def _read_meta(self, swarm_id: str, channel: str) -> dict | None:
        path = self._meta_path(swarm_id, channel)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _write_meta(self, swarm_id: str, channel: str, meta: dict) -> None:
        path = self._meta_path(swarm_id, channel)
        path.write_text(json.dumps(meta))

    # ------------------------------------------------------------------
    # StorageAdapter implementation
    # ------------------------------------------------------------------

    async def save_swarm(self, swarm: SwarmInfo) -> None:
        """Persist a new swarm."""
        d = self._swarm_dir(swarm.swarm_id)
        d.mkdir(parents=True, exist_ok=True)

        swarm_file = d / "swarm.json"
        data = {
            "swarm_id": swarm.swarm_id,
            "public_key": swarm.public_key.hex(),
            "created_at": swarm.created_at.isoformat(),
        }
        swarm_file.write_text(json.dumps(data))

    async def get_swarm(self, swarm_id: str) -> SwarmInfo | None:
        """Look up a swarm by ID."""
        swarm_file = self._swarm_dir(swarm_id) / "swarm.json"
        if not swarm_file.exists():
            return None

        data = json.loads(swarm_file.read_text())
        return SwarmInfo(
            swarm_id=data["swarm_id"],
            public_key=bytes.fromhex(data["public_key"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

    async def append_message(
        self, swarm_id: str, channel: str, body: bytes
    ) -> ChannelMessage:
        """Append a message, assigning a monotonic position and timestamp."""
        ch_dir = self._channel_dir(swarm_id, channel)
        ch_dir.mkdir(parents=True, exist_ok=True)

        messages_path = self._messages_path(swarm_id, channel)
        meta_path = self._meta_path(swarm_id, channel)

        # Use file locking for atomicity across concurrent appends
        lock_path = ch_dir / ".lock"
        lock_path.touch(exist_ok=True)

        with open(lock_path) as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                # Read current position
                meta = self._read_meta(swarm_id, channel)
                if meta is None:
                    meta = {"head_position": 0, "oldest_position": 1}

                position = meta["head_position"] + 1
                sent_at = datetime.now(UTC)

                # Write message line
                msg_data = {
                    "channel": channel,
                    "position": position,
                    "body": body.hex(),
                    "sent_at": sent_at.isoformat(),
                }
                with open(messages_path, "a") as f:
                    f.write(json.dumps(msg_data) + "\n")

                # Update meta
                meta["head_position"] = position
                self._write_meta(swarm_id, channel, meta)

                return ChannelMessage(
                    channel=channel,
                    position=position,
                    body=body,
                    sent_at=sent_at,
                )
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

    async def read_after(
        self, swarm_id: str, channel: str, cursor: int
    ) -> ChannelMessage | None:
        """Return the message at position > cursor, or None."""
        messages_path = self._messages_path(swarm_id, channel)
        if not messages_path.exists():
            return None

        with open(messages_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data["position"] > cursor:
                    return ChannelMessage(
                        channel=data["channel"],
                        position=data["position"],
                        body=bytes.fromhex(data["body"]),
                        sent_at=datetime.fromisoformat(data["sent_at"]),
                    )
        return None

    async def list_channels(self, swarm_id: str) -> list[ChannelInfo]:
        """List all channels in a swarm with head/oldest positions."""
        channels_dir = self._swarm_dir(swarm_id) / "channels"
        if not channels_dir.exists():
            return []

        result: list[ChannelInfo] = []
        for ch_dir in sorted(channels_dir.iterdir()):
            if not ch_dir.is_dir():
                continue
            meta = self._read_meta(swarm_id, ch_dir.name)
            if meta is not None:
                result.append(
                    ChannelInfo(
                        name=ch_dir.name,
                        head_position=meta["head_position"],
                        oldest_position=meta["oldest_position"],
                    )
                )
        return result

    async def get_channel_info(
        self, swarm_id: str, channel: str
    ) -> ChannelInfo | None:
        """Get info for a specific channel."""
        meta = self._read_meta(swarm_id, channel)
        if meta is None:
            return None
        return ChannelInfo(
            name=channel,
            head_position=meta["head_position"],
            oldest_position=meta["oldest_position"],
        )

    async def compact(
        self, swarm_id: str, channel: str, min_age_days: int
    ) -> int:
        """Remove messages older than min_age_days, always retaining the most recent."""
        messages_path = self._messages_path(swarm_id, channel)
        if not messages_path.exists():
            return 0

        cutoff = datetime.now(UTC) - timedelta(days=min_age_days)

        # Read all messages
        all_messages: list[dict] = []
        with open(messages_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                all_messages.append(json.loads(line))

        if not all_messages:
            return 0

        # Always retain the most recent message
        most_recent = all_messages[-1]
        to_keep = [
            msg
            for msg in all_messages
            if datetime.fromisoformat(msg["sent_at"]) >= cutoff
            or msg is most_recent
        ]

        removed = len(all_messages) - len(to_keep)
        if removed == 0:
            return 0

        # Write to temp file then rename for atomicity
        ch_dir = self._channel_dir(swarm_id, channel)
        fd, tmp_path = tempfile.mkstemp(dir=ch_dir, suffix=".jsonl.tmp")
        try:
            with open(fd, "w") as f:
                for msg in to_keep:
                    f.write(json.dumps(msg) + "\n")
            Path(tmp_path).replace(messages_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

        # Update meta with new oldest position
        meta = self._read_meta(swarm_id, channel)
        if meta is not None and to_keep:
            meta["oldest_position"] = to_keep[0]["position"]
            self._write_meta(swarm_id, channel, meta)

        return removed
