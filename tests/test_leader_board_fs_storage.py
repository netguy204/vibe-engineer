# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Tests for the filesystem storage adapter."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from leader_board.fs_storage import FileSystemStorage
from leader_board.models import SwarmInfo
from test_leader_board_adapter_contract import AdapterContractTests


# ---------------------------------------------------------------------------
# Contract tests — validates all generic StorageAdapter behavior
# ---------------------------------------------------------------------------


class TestFileSystemStorageContract(AdapterContractTests):
    @pytest.fixture
    def storage(self, tmp_path) -> FileSystemStorage:
        return FileSystemStorage(tmp_path)


# ---------------------------------------------------------------------------
# Filesystem-specific tests
# ---------------------------------------------------------------------------


class TestFileSystemStorageSpecific:
    @pytest.fixture
    def storage(self, tmp_path) -> FileSystemStorage:
        return FileSystemStorage(tmp_path)

    @pytest.fixture
    async def swarm(self, storage: FileSystemStorage) -> SwarmInfo:
        info = SwarmInfo(
            swarm_id="fs-test-swarm",
            public_key=b"\x00" * 32,
            created_at=datetime.now(UTC),
        )
        await storage.save_swarm(info)
        return info

    async def test_data_survives_new_instance(
        self, tmp_path, swarm: SwarmInfo
    ) -> None:
        """Data written by one instance is readable by a fresh instance."""
        storage1 = FileSystemStorage(tmp_path)
        # Re-save the swarm in storage1 (fixture used a different instance)
        await storage1.save_swarm(swarm)
        await storage1.append_message(swarm.swarm_id, "ch", b"hello")

        # Create a completely new instance pointing at the same directory
        storage2 = FileSystemStorage(tmp_path)
        loaded_swarm = await storage2.get_swarm(swarm.swarm_id)
        assert loaded_swarm is not None
        assert loaded_swarm.swarm_id == swarm.swarm_id

        msg = await storage2.read_after(swarm.swarm_id, "ch", 0)
        assert msg is not None
        assert msg.body == b"hello"
        assert msg.position == 1

    async def test_compact_rewrites_file_atomically(
        self, storage: FileSystemStorage, swarm: SwarmInfo
    ) -> None:
        """After compaction, messages file is valid (no partial writes)."""
        # Append messages with one old
        m1 = await storage.append_message(swarm.swarm_id, "ch", b"old")
        await storage.append_message(swarm.swarm_id, "ch", b"new")

        # Age the first message by rewriting the JSONL
        import json

        messages_path = storage._messages_path(swarm.swarm_id, "ch")
        lines = messages_path.read_text().strip().split("\n")
        old_data = json.loads(lines[0])
        old_time = datetime.now(UTC) - timedelta(days=60)
        old_data["sent_at"] = old_time.isoformat()
        lines[0] = json.dumps(old_data)
        messages_path.write_text("\n".join(lines) + "\n")

        removed = await storage.compact(swarm.swarm_id, "ch", 30)
        assert removed == 1

        # Verify the file is still valid
        msg = await storage.read_after(swarm.swarm_id, "ch", 0)
        assert msg is not None
        assert msg.body == b"new"

    async def test_concurrent_appends_are_serialized(
        self, storage: FileSystemStorage, swarm: SwarmInfo
    ) -> None:
        """Multiple concurrent appends produce monotonic positions without gaps."""

        async def append_one(i: int) -> int:
            msg = await storage.append_message(
                swarm.swarm_id, "ch", f"msg-{i}".encode()
            )
            return msg.position

        # Run several appends concurrently
        positions = await asyncio.gather(
            *[append_one(i) for i in range(10)]
        )

        # Positions should be 1..10 with no gaps
        assert sorted(positions) == list(range(1, 11))

    async def test_compact_updates_oldest_position_in_meta(
        self, storage: FileSystemStorage, swarm: SwarmInfo
    ) -> None:
        """After compaction, get_channel_info reflects updated oldest_position."""
        import json

        await storage.append_message(swarm.swarm_id, "ch", b"a")
        await storage.append_message(swarm.swarm_id, "ch", b"b")
        await storage.append_message(swarm.swarm_id, "ch", b"c")

        # Age the first two messages
        messages_path = storage._messages_path(swarm.swarm_id, "ch")
        lines = messages_path.read_text().strip().split("\n")
        old_time = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        for i in range(2):
            data = json.loads(lines[i])
            data["sent_at"] = old_time
            lines[i] = json.dumps(data)
        messages_path.write_text("\n".join(lines) + "\n")

        await storage.compact(swarm.swarm_id, "ch", 30)

        info = await storage.get_channel_info(swarm.swarm_id, "ch")
        assert info is not None
        assert info.oldest_position == 3
        assert info.head_position == 3
