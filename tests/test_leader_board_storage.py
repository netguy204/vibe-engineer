# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Tests for the InMemoryStorage adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from leader_board.memory_storage import InMemoryStorage
from leader_board.models import SwarmInfo


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
async def swarm(storage: InMemoryStorage) -> SwarmInfo:
    """Register a test swarm and return it."""
    info = SwarmInfo(
        swarm_id="test-swarm",
        public_key=b"\x00" * 32,
        created_at=datetime.now(UTC),
    )
    await storage.save_swarm(info)
    return info


async def test_append_assigns_monotonic_positions(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    msg1 = await storage.append_message(swarm.swarm_id, "ch", b"a")
    msg2 = await storage.append_message(swarm.swarm_id, "ch", b"b")
    msg3 = await storage.append_message(swarm.swarm_id, "ch", b"c")
    assert (msg1.position, msg2.position, msg3.position) == (1, 2, 3)


async def test_read_after_returns_next_message(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    await storage.append_message(swarm.swarm_id, "ch", b"first")
    await storage.append_message(swarm.swarm_id, "ch", b"second")

    msg = await storage.read_after(swarm.swarm_id, "ch", 0)
    assert msg is not None
    assert msg.position == 1
    assert msg.body == b"first"


async def test_read_after_returns_none_when_no_message(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    result = await storage.read_after(swarm.swarm_id, "ch", 0)
    assert result is None


async def test_compact_removes_old_messages(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    # Insert messages with old timestamps by manipulating internal state
    old_time = datetime.now(UTC) - timedelta(days=60)
    msg = await storage.append_message(swarm.swarm_id, "ch", b"old1")
    # Overwrite sent_at to simulate age
    key = (swarm.swarm_id, "ch")
    storage._channels[key][0] = msg.model_copy(update={"sent_at": old_time})

    await storage.append_message(swarm.swarm_id, "ch", b"old2")
    storage._channels[key][1] = storage._channels[key][1].model_copy(
        update={"sent_at": old_time}
    )

    # Add a recent message
    await storage.append_message(swarm.swarm_id, "ch", b"recent")

    removed = await storage.compact(swarm.swarm_id, "ch", 30)
    assert removed == 2
    remaining = storage._channels[key]
    assert len(remaining) == 1
    assert remaining[0].body == b"recent"


async def test_compact_retains_most_recent(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    old_time = datetime.now(UTC) - timedelta(days=60)
    key = (swarm.swarm_id, "ch")

    await storage.append_message(swarm.swarm_id, "ch", b"only")
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )

    removed = await storage.compact(swarm.swarm_id, "ch", 30)
    # The only message is the most recent — must be retained
    assert removed == 0
    assert len(storage._channels[key]) == 1


async def test_list_channels_returns_head_and_oldest(
    storage: InMemoryStorage, swarm: SwarmInfo
) -> None:
    await storage.append_message(swarm.swarm_id, "alpha", b"a1")
    await storage.append_message(swarm.swarm_id, "alpha", b"a2")
    await storage.append_message(swarm.swarm_id, "beta", b"b1")

    channels = await storage.list_channels(swarm.swarm_id)
    by_name = {c.name: c for c in channels}

    assert by_name["alpha"].head_position == 2
    assert by_name["alpha"].oldest_position == 1
    assert by_name["beta"].head_position == 1
    assert by_name["beta"].oldest_position == 1
