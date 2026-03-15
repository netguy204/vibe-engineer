# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.storage — key and cursor persistence."""

import pytest
from board.crypto import generate_keypair, derive_swarm_id
from board.storage import (
    collect_board_files,
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


# ---------------------------------------------------------------------------
# collect_board_files tests
# Chunk: docs/chunks/board_scp_command - Board SCP command
# ---------------------------------------------------------------------------


def test_collect_board_files_missing_config(tmp_path):
    """collect_board_files raises FileNotFoundError when board.toml missing."""
    with pytest.raises(FileNotFoundError, match="does not exist"):
        collect_board_files(config_path=tmp_path / "board.toml", keys_dir=tmp_path / "keys")


def test_collect_board_files_config_only(tmp_path):
    """collect_board_files returns only board.toml when no keys exist."""
    config = tmp_path / "board.toml"
    config.write_text("default_swarm = 'abc'\n")
    files = collect_board_files(config_path=config, keys_dir=tmp_path / "keys")
    assert files == [config]


def test_collect_board_files_with_keys(tmp_path):
    """collect_board_files returns board.toml and key files."""
    config = tmp_path / "board.toml"
    config.write_text("default_swarm = 'abc'\n")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    key_file = keys_dir / "abc.key"
    pub_file = keys_dir / "abc.pub"
    key_file.write_bytes(b"\x00" * 32)
    pub_file.write_bytes(b"\x00" * 32)

    files = collect_board_files(config_path=config, keys_dir=keys_dir)
    assert config in files
    assert key_file in files
    assert pub_file in files
    assert len(files) == 3


def test_collect_board_files_ignores_non_key_files(tmp_path):
    """collect_board_files ignores files without .key or .pub suffix."""
    config = tmp_path / "board.toml"
    config.write_text("")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "abc.key").write_bytes(b"\x00" * 32)
    (keys_dir / "abc.pub").write_bytes(b"\x00" * 32)
    (keys_dir / "notes.txt").write_text("random file")

    files = collect_board_files(config_path=config, keys_dir=keys_dir)
    assert len(files) == 3  # board.toml + .key + .pub
    assert not any(f.name == "notes.txt" for f in files)
