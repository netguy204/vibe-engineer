# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.storage — key and cursor persistence."""

import pytest
from board.crypto import generate_keypair, derive_swarm_id
from board.storage import (
    load_cursor,
    load_keypair,
    list_swarms,
    save_cursor,
    save_keypair,
)


def test_save_and_load_keypair(tmp_path):
    """Save key files to a directory, load them back, assert byte equality."""
    seed, public_key = generate_keypair()
    swarm_id = derive_swarm_id(public_key)
    save_keypair(swarm_id, seed, public_key, keys_dir=tmp_path)
    loaded = load_keypair(swarm_id, keys_dir=tmp_path)
    assert loaded is not None
    loaded_seed, loaded_pub = loaded
    assert loaded_seed == seed
    assert loaded_pub == public_key


def test_load_keypair_missing(tmp_path):
    """Loading a non-existent keypair returns None."""
    result = load_keypair("nonexistent", keys_dir=tmp_path)
    assert result is None


def test_save_and_load_cursor(tmp_path):
    """Write cursor 42, read it back, assert 42."""
    save_cursor("test-channel", 42, project_root=tmp_path)
    assert load_cursor("test-channel", project_root=tmp_path) == 42


def test_load_cursor_default(tmp_path):
    """Missing cursor file returns 0."""
    assert load_cursor("nonexistent", project_root=tmp_path) == 0


def test_cursor_overwrite(tmp_path):
    """Write 10, then 20, read back 20."""
    save_cursor("ch", 10, project_root=tmp_path)
    assert load_cursor("ch", project_root=tmp_path) == 10
    save_cursor("ch", 20, project_root=tmp_path)
    assert load_cursor("ch", project_root=tmp_path) == 20


def test_list_swarms(tmp_path):
    """Create two key pairs, list returns both swarm IDs."""
    seed1, pub1 = generate_keypair()
    seed2, pub2 = generate_keypair()
    id1 = derive_swarm_id(pub1)
    id2 = derive_swarm_id(pub2)
    save_keypair(id1, seed1, pub1, keys_dir=tmp_path)
    save_keypair(id2, seed2, pub2, keys_dir=tmp_path)
    swarms = list_swarms(keys_dir=tmp_path)
    assert set(swarms) == {id1, id2}


def test_list_swarms_empty(tmp_path):
    """Empty keys directory returns empty list."""
    assert list_swarms(keys_dir=tmp_path) == []
