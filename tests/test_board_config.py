# Chunk: docs/chunks/leader_board_user_config - Board user config and defaults
"""Tests for board.config — BoardConfig load/save and resolution logic."""

from pathlib import Path

import pytest

from board.config import (
    BoardConfig,
    SwarmConfig,
    add_swarm,
    load_board_config,
    resolve_server,
    resolve_swarm,
    save_board_config,
)


# ---------------------------------------------------------------------------
# load_board_config
# ---------------------------------------------------------------------------


def test_load_returns_empty_config_when_no_file(tmp_path):
    """load_board_config returns a default (empty) config when no file exists."""
    config = load_board_config(tmp_path / "nonexistent.toml")
    assert config.default_swarm is None
    assert config.swarms == {}


def test_load_reads_valid_toml(tmp_path):
    """load_board_config reads a valid TOML file and returns structured data."""
    toml_file = tmp_path / "board.toml"
    toml_file.write_text(
        'default_swarm = "swarm1"\n\n'
        '[swarms.swarm1]\n'
        'server_url = "wss://example.com"\n\n'
        '[swarms.swarm2]\n'
        'server_url = "ws://localhost:8374"\n'
    )
    config = load_board_config(toml_file)
    assert config.default_swarm == "swarm1"
    assert len(config.swarms) == 2
    assert config.swarms["swarm1"].server_url == "wss://example.com"
    assert config.swarms["swarm2"].server_url == "ws://localhost:8374"


# ---------------------------------------------------------------------------
# save_board_config / round-trip
# ---------------------------------------------------------------------------


def test_save_round_trips(tmp_path):
    """save_board_config writes a TOML file that round-trips correctly."""
    toml_file = tmp_path / "board.toml"
    original = BoardConfig(
        default_swarm="abc",
        swarms={
            "abc": SwarmConfig(server_url="wss://hosted.example.com"),
            "def": SwarmConfig(server_url="ws://localhost:8374"),
        },
    )
    save_board_config(original, toml_file)
    loaded = load_board_config(toml_file)
    assert loaded.default_swarm == original.default_swarm
    assert set(loaded.swarms.keys()) == set(original.swarms.keys())
    for sid in original.swarms:
        assert loaded.swarms[sid].server_url == original.swarms[sid].server_url


def test_save_creates_parent_directories(tmp_path):
    """save_board_config creates parent directories if they don't exist."""
    toml_file = tmp_path / "deep" / "nested" / "board.toml"
    config = BoardConfig(default_swarm="s1", swarms={"s1": SwarmConfig("ws://x")})
    save_board_config(config, toml_file)
    assert toml_file.exists()


def test_save_empty_config(tmp_path):
    """save_board_config handles an empty config."""
    toml_file = tmp_path / "board.toml"
    save_board_config(BoardConfig(), toml_file)
    loaded = load_board_config(toml_file)
    assert loaded.default_swarm is None
    assert loaded.swarms == {}


# ---------------------------------------------------------------------------
# add_swarm
# ---------------------------------------------------------------------------


def test_add_swarm_sets_default_if_first(tmp_path):
    """add_swarm sets default_swarm if it's the first swarm."""
    config = BoardConfig()
    add_swarm(config, "first", "ws://server1")
    assert config.default_swarm == "first"
    assert "first" in config.swarms
    assert config.swarms["first"].server_url == "ws://server1"


def test_add_swarm_does_not_overwrite_default():
    """add_swarm does not overwrite default_swarm if one is already set."""
    config = BoardConfig(
        default_swarm="existing",
        swarms={"existing": SwarmConfig("ws://s")},
    )
    add_swarm(config, "second", "ws://server2")
    assert config.default_swarm == "existing"
    assert "second" in config.swarms


# ---------------------------------------------------------------------------
# resolve_swarm
# ---------------------------------------------------------------------------


def test_resolve_swarm_explicit():
    """resolve_swarm returns explicit value if provided."""
    config = BoardConfig(default_swarm="default_one")
    assert resolve_swarm(config, "explicit") == "explicit"


def test_resolve_swarm_from_default():
    """resolve_swarm returns default_swarm when no explicit value."""
    config = BoardConfig(default_swarm="default_one")
    assert resolve_swarm(config, None) == "default_one"


def test_resolve_swarm_none():
    """resolve_swarm returns None when no explicit and no default."""
    config = BoardConfig()
    assert resolve_swarm(config, None) is None


# ---------------------------------------------------------------------------
# resolve_server
# ---------------------------------------------------------------------------


def test_resolve_server_explicit():
    """resolve_server returns explicit value if provided."""
    config = BoardConfig(swarms={"s1": SwarmConfig("ws://configured")})
    assert resolve_server(config, "s1", "ws://override") == "ws://override"


def test_resolve_server_from_config():
    """resolve_server returns the swarm's server_url from config."""
    config = BoardConfig(swarms={"s1": SwarmConfig("ws://configured")})
    assert resolve_server(config, "s1", None) == "ws://configured"


def test_resolve_server_fallback():
    """resolve_server returns fallback when no explicit and no config entry."""
    config = BoardConfig()
    assert resolve_server(config, None, None) == "ws://localhost:8374"


def test_resolve_server_unknown_swarm():
    """resolve_server returns fallback when swarm ID not in config."""
    config = BoardConfig(swarms={"s1": SwarmConfig("ws://configured")})
    assert resolve_server(config, "unknown", None) == "ws://localhost:8374"
