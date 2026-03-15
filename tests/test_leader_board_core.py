# Chunk: docs/chunks/leader_board_core - Portable leader board core library
"""Tests for the LeaderBoardCore business logic."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from leader_board.core import LeaderBoardCore
from leader_board.memory_storage import InMemoryStorage
from leader_board.models import (
    MESSAGE_MAX_BYTES,
    AuthFailedError,
    ChannelNotFoundError,
    CursorExpiredError,
    SwarmNotFoundError,
)


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def core(storage: InMemoryStorage) -> LeaderBoardCore:
    return LeaderBoardCore(storage)


# ------------------------------------------------------------------
# Swarm operations (Step 4)
# ------------------------------------------------------------------


async def test_register_swarm_stores_public_key(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    key = Ed25519PrivateKey.generate()
    pub_bytes = key.public_key().public_bytes_raw()
    swarm = await core.register_swarm("my-swarm", pub_bytes)

    assert swarm.swarm_id == "my-swarm"
    assert swarm.public_key == pub_bytes

    # Verify it was persisted
    stored = await storage.get_swarm("my-swarm")
    assert stored is not None
    assert stored.public_key == pub_bytes


async def test_register_swarm_rejects_duplicate(core: LeaderBoardCore) -> None:
    pub = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    await core.register_swarm("dup", pub)
    with pytest.raises(ValueError, match="already exists"):
        await core.register_swarm("dup", pub)


async def test_verify_auth_accepts_valid_signature(
    core: LeaderBoardCore,
) -> None:
    private = Ed25519PrivateKey.generate()
    pub_bytes = private.public_key().public_bytes_raw()
    await core.register_swarm("auth-swarm", pub_bytes)

    nonce = b"random-challenge-nonce-data-here!"
    sig = private.sign(nonce)

    result = await core.verify_auth("auth-swarm", nonce, sig)
    assert result is True


async def test_verify_auth_rejects_invalid_signature(
    core: LeaderBoardCore,
) -> None:
    private = Ed25519PrivateKey.generate()
    pub_bytes = private.public_key().public_bytes_raw()
    await core.register_swarm("auth-swarm2", pub_bytes)

    nonce = b"some-nonce"
    bad_sig = b"\x00" * 64  # invalid signature

    with pytest.raises(AuthFailedError):
        await core.verify_auth("auth-swarm2", nonce, bad_sig)


async def test_verify_auth_unknown_swarm_raises(core: LeaderBoardCore) -> None:
    with pytest.raises(SwarmNotFoundError):
        await core.verify_auth("nonexistent", b"nonce", b"sig")


# ------------------------------------------------------------------
# Channel operations (Step 5)
# ------------------------------------------------------------------


async def _register_swarm(core: LeaderBoardCore, swarm_id: str = "s1") -> None:
    """Helper to register a swarm with a dummy key."""
    pub = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    await core.register_swarm(swarm_id, pub)


async def test_append_and_read_back(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    msg = await core.append("s1", "ch1", b"hello")
    assert msg.position == 1
    assert msg.body == b"hello"

    read = await core.read_after("s1", "ch1", 0)
    assert read.position == 1
    assert read.body == b"hello"


async def test_read_after_blocks_then_resolves(
    core: LeaderBoardCore,
) -> None:
    await _register_swarm(core)
    # Seed the channel so it exists
    await core.append("s1", "ch1", b"seed")

    resolved = asyncio.Event()
    result_holder: list = []

    async def reader() -> None:
        msg = await core.read_after("s1", "ch1", 1)  # block after pos 1
        result_holder.append(msg)
        resolved.set()

    task = asyncio.create_task(reader())
    # Give the reader a chance to block
    await asyncio.sleep(0.05)
    assert not resolved.is_set()

    # Append should wake the reader
    await core.append("s1", "ch1", b"wake-up")
    await asyncio.wait_for(resolved.wait(), timeout=2.0)

    assert len(result_holder) == 1
    assert result_holder[0].body == b"wake-up"
    assert result_holder[0].position == 2
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_read_after_cursor_expired(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    await _register_swarm(core)
    # Append messages and age them
    await core.append("s1", "ch", b"old1")
    await core.append("s1", "ch", b"old2")
    await core.append("s1", "ch", b"recent")

    key = ("s1", "ch")
    old_time = datetime.now(UTC) - timedelta(days=60)
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )
    storage._channels[key][1] = storage._channels[key][1].model_copy(
        update={"sent_at": old_time}
    )

    await core.compact("s1", "ch", 30)

    # Now the oldest position should be 3 (the recent one)
    with pytest.raises(CursorExpiredError) as exc_info:
        await core.read_after("s1", "ch", 1)
    assert exc_info.value.earliest_position == 3


async def test_read_after_channel_not_found(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    with pytest.raises(ChannelNotFoundError):
        await core.read_after("s1", "nonexistent", 0)


async def test_append_validates_channel_name(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    with pytest.raises(ValueError, match="Invalid channel name"):
        await core.append("s1", "bad channel!", b"data")

    with pytest.raises(ValueError, match="Invalid channel name"):
        await core.append("s1", "", b"data")

    with pytest.raises(ValueError, match="Invalid channel name"):
        await core.append("s1", "x" * 129, b"data")


async def test_append_validates_body_size(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    with pytest.raises(ValueError, match="too large"):
        await core.append("s1", "ch", b"\x00" * (MESSAGE_MAX_BYTES + 1))


async def test_append_unknown_swarm_raises(core: LeaderBoardCore) -> None:
    with pytest.raises(SwarmNotFoundError):
        await core.append("ghost", "ch", b"data")


async def test_fifo_ordering(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"first")
    await core.append("s1", "ch", b"second")
    await core.append("s1", "ch", b"third")

    m1 = await core.read_after("s1", "ch", 0)
    m2 = await core.read_after("s1", "ch", 1)
    m3 = await core.read_after("s1", "ch", 2)

    assert m1.body == b"first" and m1.position == 1
    assert m2.body == b"second" and m2.position == 2
    assert m3.body == b"third" and m3.position == 3


async def test_multiple_concurrent_watchers(core: LeaderBoardCore) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"seed")

    results: list = []

    async def watcher(idx: int) -> None:
        msg = await core.read_after("s1", "ch", 1)
        results.append((idx, msg))

    t1 = asyncio.create_task(watcher(1))
    t2 = asyncio.create_task(watcher(2))
    await asyncio.sleep(0.05)

    await core.append("s1", "ch", b"broadcast")

    await asyncio.wait_for(asyncio.gather(t1, t2), timeout=2.0)

    assert len(results) == 2
    for _, msg in results:
        assert msg.body == b"broadcast"
        assert msg.position == 2


# ------------------------------------------------------------------
# Compaction (Step 6)
# ------------------------------------------------------------------


async def test_compact_removes_old_messages(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"old")
    await core.append("s1", "ch", b"recent")

    key = ("s1", "ch")
    old_time = datetime.now(UTC) - timedelta(days=60)
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )

    removed = await core.compact("s1", "ch", 30)
    assert removed == 1


async def test_compact_retains_recent_messages(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"old")
    await core.append("s1", "ch", b"recent")

    key = ("s1", "ch")
    old_time = datetime.now(UTC) - timedelta(days=60)
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )

    await core.compact("s1", "ch", 30)
    remaining = storage._channels[key]
    assert len(remaining) == 1
    assert remaining[0].body == b"recent"


async def test_compact_always_retains_most_recent(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"only-msg")

    key = ("s1", "ch")
    old_time = datetime.now(UTC) - timedelta(days=60)
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )

    removed = await core.compact("s1", "ch", 30)
    assert removed == 0
    assert len(storage._channels[key]) == 1


async def test_read_after_reflects_compaction(
    core: LeaderBoardCore, storage: InMemoryStorage
) -> None:
    await _register_swarm(core)
    await core.append("s1", "ch", b"old")
    await core.append("s1", "ch", b"keep")

    key = ("s1", "ch")
    old_time = datetime.now(UTC) - timedelta(days=60)
    storage._channels[key][0] = storage._channels[key][0].model_copy(
        update={"sent_at": old_time}
    )

    await core.compact("s1", "ch", 30)

    # Cursor 0 is now behind the compaction frontier (oldest is pos 2)
    with pytest.raises(CursorExpiredError) as exc_info:
        await core.read_after("s1", "ch", 0)
    assert exc_info.value.earliest_position == 2
