# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Reusable adapter contract tests for any StorageAdapter implementation.

Any StorageAdapter implementation can subclass ``AdapterContractTests``
and provide a ``storage`` fixture to verify protocol compliance.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from leader_board.memory_storage import InMemoryStorage
from leader_board.models import SwarmInfo


class AdapterContractTests:
    """Base class containing the contract tests every StorageAdapter must pass.

    Subclasses must define a ``storage`` fixture that returns an instance
    of their StorageAdapter implementation.
    """

    @pytest.fixture
    def storage(self):  # noqa: ANN201 — overridden by subclass
        raise NotImplementedError("Subclass must provide a storage fixture")

    @pytest.fixture
    async def swarm(self, storage) -> SwarmInfo:
        info = SwarmInfo(
            swarm_id="contract-swarm",
            public_key=b"\x00" * 32,
            created_at=datetime.now(UTC),
        )
        await storage.save_swarm(info)
        return info

    async def test_append_assigns_monotonic_positions_starting_at_1(
        self, storage, swarm: SwarmInfo
    ) -> None:
        m1 = await storage.append_message(swarm.swarm_id, "ch", b"a")
        m2 = await storage.append_message(swarm.swarm_id, "ch", b"b")
        m3 = await storage.append_message(swarm.swarm_id, "ch", b"c")
        assert (m1.position, m2.position, m3.position) == (1, 2, 3)

    async def test_read_after_cursor_0_returns_first_message(
        self, storage, swarm: SwarmInfo
    ) -> None:
        await storage.append_message(swarm.swarm_id, "ch", b"first")
        msg = await storage.read_after(swarm.swarm_id, "ch", 0)
        assert msg is not None
        assert msg.position == 1

    async def test_read_after_cursor_at_head_returns_none(
        self, storage, swarm: SwarmInfo
    ) -> None:
        await storage.append_message(swarm.swarm_id, "ch", b"only")
        msg = await storage.read_after(swarm.swarm_id, "ch", 1)
        assert msg is None

    async def test_compact_removes_old_retains_most_recent(
        self, storage, swarm: SwarmInfo
    ) -> None:
        key = (swarm.swarm_id, "ch")
        old_time = datetime.now(UTC) - timedelta(days=60)

        m1 = await storage.append_message(swarm.swarm_id, "ch", b"old")
        m2 = await storage.append_message(swarm.swarm_id, "ch", b"recent")

        # Age the first message (adapter-specific hack)
        if hasattr(storage, "_channels"):
            # InMemoryStorage
            storage._channels[key][0] = m1.model_copy(
                update={"sent_at": old_time}
            )
        elif hasattr(storage, "_messages_path"):
            # FileSystemStorage
            import json as _json

            mp = storage._messages_path(swarm.swarm_id, "ch")
            lines = mp.read_text().strip().split("\n")
            data = _json.loads(lines[0])
            data["sent_at"] = old_time.isoformat()
            lines[0] = _json.dumps(data)
            mp.write_text("\n".join(lines) + "\n")

        removed = await storage.compact(swarm.swarm_id, "ch", 30)
        assert removed >= 1

        # Head message should survive
        info = await storage.get_channel_info(swarm.swarm_id, "ch")
        assert info is not None
        assert info.head_position == 2

    async def test_list_channels_returns_correct_positions(
        self, storage, swarm: SwarmInfo
    ) -> None:
        await storage.append_message(swarm.swarm_id, "alpha", b"a1")
        await storage.append_message(swarm.swarm_id, "alpha", b"a2")
        await storage.append_message(swarm.swarm_id, "beta", b"b1")

        channels = await storage.list_channels(swarm.swarm_id)
        by_name = {c.name: c for c in channels}

        assert "alpha" in by_name
        assert by_name["alpha"].head_position == 2
        assert by_name["alpha"].oldest_position == 1
        assert "beta" in by_name
        assert by_name["beta"].head_position == 1

    async def test_multiple_channels_are_independent(
        self, storage, swarm: SwarmInfo
    ) -> None:
        m_a = await storage.append_message(swarm.swarm_id, "ch-a", b"a")
        m_b = await storage.append_message(swarm.swarm_id, "ch-b", b"b")

        # Both start at position 1 independently
        assert m_a.position == 1
        assert m_b.position == 1

        # Reading from one doesn't affect the other
        read_a = await storage.read_after(swarm.swarm_id, "ch-a", 0)
        read_b = await storage.read_after(swarm.swarm_id, "ch-b", 0)
        assert read_a is not None and read_a.body == b"a"
        assert read_b is not None and read_b.body == b"b"


# --- Concrete test class for InMemoryStorage ---


class TestInMemoryStorageContract(AdapterContractTests):
    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        return InMemoryStorage()
