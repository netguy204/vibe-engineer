# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
# Chunk: docs/chunks/leader_board_user_config - Board user config and defaults
"""Tests for cli.board — Click command integration tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from click.testing import CliRunner

from board.config import BoardConfig, SwarmConfig
from board.crypto import generate_keypair, derive_swarm_id, derive_symmetric_key, encrypt
from board.storage import save_keypair, load_cursor
from cli.board import board


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def stored_swarm(tmp_path):
    """Create and store a swarm keypair, return (swarm_id, seed, pub, keys_dir)."""
    seed, pub = generate_keypair()
    swarm_id = derive_swarm_id(pub)
    keys_dir = tmp_path / "keys"
    save_keypair(swarm_id, seed, pub, keys_dir=keys_dir)
    return swarm_id, seed, pub, keys_dir


@pytest.fixture
def empty_config():
    """Return an empty BoardConfig (no config file)."""
    return BoardConfig()


def test_board_group_exists(runner):
    """ve board --help exits 0 and shows subcommands."""
    result = runner.invoke(board, ["--help"])
    assert result.exit_code == 0
    assert "swarm" in result.output
    assert "send" in result.output
    assert "watch" in result.output
    assert "ack" in result.output
    assert "channels" in result.output
    assert "bind" in result.output


def test_swarm_create(runner, tmp_path):
    """swarm create generates key files, prints swarm ID, and updates board.toml."""
    keys_dir = tmp_path / "keys"
    config_path = tmp_path / "board.toml"
    saved_configs = []

    def mock_save(config, config_path=None):
        saved_configs.append(config)

    with patch("cli.board.save_keypair", wraps=lambda sid, s, p: save_keypair(sid, s, p, keys_dir=keys_dir)), \
         patch("cli.board.BoardClient") as MockClient, \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.save_board_config", side_effect=mock_save):

        instance = MockClient.return_value
        instance.register_swarm = AsyncMock()

        result = runner.invoke(board, ["swarm", "create", "--server", "ws://test:8787"])

    assert result.exit_code == 0
    # Output should be the swarm ID (non-empty string)
    swarm_id = result.output.strip()
    assert len(swarm_id) > 0
    # Config should have been updated with the new swarm
    assert len(saved_configs) == 1
    assert swarm_id in saved_configs[0].swarms
    assert saved_configs[0].swarms[swarm_id].server_url == "ws://test:8787"
    assert saved_configs[0].default_swarm == swarm_id


def test_swarm_create_no_server_flag(runner, tmp_path):
    """swarm create with no --server flag uses fallback from config resolution."""
    keys_dir = tmp_path / "keys"
    saved_configs = []

    def mock_save(config, config_path=None):
        saved_configs.append(config)

    with patch("cli.board.save_keypair", wraps=lambda sid, s, p: save_keypair(sid, s, p, keys_dir=keys_dir)), \
         patch("cli.board.BoardClient") as MockClient, \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.save_board_config", side_effect=mock_save):

        instance = MockClient.return_value
        instance.register_swarm = AsyncMock()

        result = runner.invoke(board, ["swarm", "create"])

    assert result.exit_code == 0
    swarm_id = result.output.strip()
    # Should fall back to ws://localhost:8374
    assert saved_configs[0].swarms[swarm_id].server_url == "ws://localhost:8374"


def test_send_command(runner, stored_swarm, tmp_path):
    """send encrypts and sends a message, prints position."""
    swarm_id, seed, pub, keys_dir = stored_swarm

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(return_value=7)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "send", "test-channel", "hello world",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "7" in result.output

    # Verify send was called with encrypted body (not plaintext)
    call_args = instance.send.call_args
    assert call_args[0][0] == "test-channel"
    assert call_args[0][1] != "hello world"  # Should be encrypted


def test_watch_command(runner, stored_swarm, tmp_path):
    """watch receives, decrypts, and prints plaintext to stdout."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    sym_key = derive_symmetric_key(seed)
    encrypted_body = encrypt("secret message", sym_key)

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_cursor", return_value=0), \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.watch = AsyncMock(return_value={
            "position": 1,
            "body": encrypted_body,
            "sent_at": "2026-03-15T14:30:00Z",
        })
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "watch", "test-channel",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--project-root", str(tmp_path),
        ])

    assert result.exit_code == 0
    assert "secret message" in result.output


def test_watch_does_not_advance_cursor(runner, stored_swarm, tmp_path):
    """watch does NOT auto-advance the cursor."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    sym_key = derive_symmetric_key(seed)
    encrypted_body = encrypt("msg", sym_key)

    project_root = tmp_path / "project"
    project_root.mkdir()

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.watch = AsyncMock(return_value={
            "position": 5,
            "body": encrypted_body,
            "sent_at": "2026-03-15T14:30:00Z",
        })
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "watch", "test-channel",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--project-root", str(project_root),
        ])

    assert result.exit_code == 0
    # Cursor should still be 0 (not advanced)
    assert load_cursor("test-channel", project_root) == 0


def test_ack_command(runner, tmp_path):
    """ack advances cursor in project-local storage."""
    result = runner.invoke(board, [
        "ack", "my-channel", "42",
        "--project-root", str(tmp_path),
    ])
    assert result.exit_code == 0
    assert "42" in result.output
    assert load_cursor("my-channel", tmp_path) == 42


def test_channels_command(runner, stored_swarm):
    """channels lists channels from mock response."""
    swarm_id, seed, pub, keys_dir = stored_swarm

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.list_channels = AsyncMock(return_value=[
            {"name": "steward", "head_position": 10, "oldest_position": 1},
            {"name": "changelog", "head_position": 5, "oldest_position": 1},
        ])
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "channels",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "steward" in result.output
    assert "changelog" in result.output


def test_send_missing_swarm(runner):
    """send with a missing swarm prints error."""
    with patch("cli.board.load_keypair", return_value=None), \
         patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, [
            "send", "ch", "msg",
            "--swarm", "nonexistent",
        ])
    assert result.exit_code != 0
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# bind command tests
# ---------------------------------------------------------------------------


def test_bind_update_server_url(runner, tmp_path):
    """ve board bind <swarm> <url> updates the swarm's server_url."""
    config = BoardConfig(
        default_swarm="s1",
        swarms={"s1": SwarmConfig("ws://old-server")},
    )
    saved_configs = []

    def mock_save(config, config_path=None):
        saved_configs.append(config)

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.save_board_config", side_effect=mock_save):
        result = runner.invoke(board, ["bind", "s1", "wss://new-server.com"])

    assert result.exit_code == 0
    assert "bound to" in result.output
    assert saved_configs[0].swarms["s1"].server_url == "wss://new-server.com"


def test_bind_unknown_swarm_errors(runner):
    """ve board bind <swarm> <url> errors if swarm ID not found in config."""
    config = BoardConfig(swarms={"s1": SwarmConfig("ws://server")})

    with patch("cli.board.load_board_config", return_value=config):
        result = runner.invoke(board, ["bind", "unknown", "ws://new"])

    assert result.exit_code != 0
    assert "not found" in result.output


def test_bind_default(runner, tmp_path):
    """ve board bind --default <swarm> sets default_swarm."""
    config = BoardConfig(
        default_swarm="s1",
        swarms={
            "s1": SwarmConfig("ws://server1"),
            "s2": SwarmConfig("ws://server2"),
        },
    )
    saved_configs = []

    def mock_save(config, config_path=None):
        saved_configs.append(config)

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.save_board_config", side_effect=mock_save):
        result = runner.invoke(board, ["bind", "--default", "s2"])

    assert result.exit_code == 0
    assert "Default swarm set to 's2'" in result.output
    assert saved_configs[0].default_swarm == "s2"


def test_bind_default_unknown_swarm_errors(runner):
    """ve board bind --default <swarm> errors if swarm ID not in config."""
    config = BoardConfig(swarms={"s1": SwarmConfig("ws://server")})

    with patch("cli.board.load_board_config", return_value=config):
        result = runner.invoke(board, ["bind", "--default", "unknown"])

    assert result.exit_code != 0
    assert "not found" in result.output


def test_bind_no_args(runner):
    """ve board bind with no args prints usage."""
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, ["bind"])

    assert result.exit_code != 0
    assert "Usage" in result.output


# ---------------------------------------------------------------------------
# config-aware option resolution tests
# ---------------------------------------------------------------------------


def test_send_resolves_swarm_from_config(runner, stored_swarm):
    """send with --swarm omitted resolves from default_swarm in config."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://configured-server")},
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(return_value=1)
        instance.close = AsyncMock()

        result = runner.invoke(board, ["send", "ch", "msg"])

    assert result.exit_code == 0
    # Verify the client was constructed with the config server URL
    MockClient.assert_called_once()
    call_args = MockClient.call_args
    assert call_args[0][0] == "ws://configured-server"


def test_send_resolves_server_from_config(runner, stored_swarm):
    """send with --server omitted resolves from swarm's config entry."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("wss://hosted.example.com")},
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(return_value=1)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "send", "ch", "msg",
            "--swarm", swarm_id,
        ])

    assert result.exit_code == 0
    MockClient.assert_called_once()
    assert MockClient.call_args[0][0] == "wss://hosted.example.com"


def test_send_explicit_flags_override_config(runner, stored_swarm):
    """send with explicit --swarm and --server ignores config."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm="other-swarm",
        swarms={
            "other-swarm": SwarmConfig("ws://other-server"),
            swarm_id: SwarmConfig("ws://config-server"),
        },
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(return_value=1)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "send", "ch", "msg",
            "--swarm", swarm_id,
            "--server", "ws://explicit",
        ])

    assert result.exit_code == 0
    MockClient.assert_called_once()
    assert MockClient.call_args[0][0] == "ws://explicit"
    assert MockClient.call_args[0][1] == swarm_id


def test_send_no_config_no_swarm_flag_errors(runner):
    """send with no config and no --swarm flag errors."""
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, ["send", "ch", "msg"])

    assert result.exit_code != 0
    assert "no swarm specified" in result.output


def test_channels_resolves_from_config(runner, stored_swarm):
    """channels with --swarm and --server omitted resolves from config."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://config-channels")},
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.list_channels = AsyncMock(return_value=[])
        instance.close = AsyncMock()

        result = runner.invoke(board, ["channels"])

    assert result.exit_code == 0
    MockClient.assert_called_once()
    assert MockClient.call_args[0][0] == "ws://config-channels"


def test_watch_resolves_from_config(runner, stored_swarm, tmp_path):
    """watch with --swarm and --server omitted resolves from config."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    sym_key = derive_symmetric_key(seed)
    encrypted_body = encrypt("test", sym_key)
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://config-watch")},
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_cursor", return_value=0), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.watch = AsyncMock(return_value={
            "position": 1,
            "body": encrypted_body,
            "sent_at": "2026-03-15T14:30:00Z",
        })
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "watch", "ch",
            "--project-root", str(tmp_path),
        ])

    assert result.exit_code == 0
    MockClient.assert_called_once()
    assert MockClient.call_args[0][0] == "ws://config-watch"


def test_no_config_no_flags_server_falls_back(runner, stored_swarm):
    """When no config and no --server flag, server falls back to ws://localhost:8374."""
    swarm_id, seed, pub, keys_dir = stored_swarm

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=BoardConfig()), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(return_value=1)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "send", "ch", "msg",
            "--swarm", swarm_id,
        ])

    assert result.exit_code == 0
    MockClient.assert_called_once()
    assert MockClient.call_args[0][0] == "ws://localhost:8374"


# ---------------------------------------------------------------------------
# scp command tests
# Chunk: docs/chunks/board_scp_command - Board SCP command
# ---------------------------------------------------------------------------


def test_scp_help(runner):
    """ve board scp --help shows the host argument."""
    result = runner.invoke(board, ["scp", "--help"])
    assert result.exit_code == 0
    assert "HOST" in result.output


def test_scp_no_board_toml(runner, tmp_path):
    """scp errors when board.toml does not exist."""
    missing = tmp_path / "board.toml"
    with patch("cli.board.collect_board_files", side_effect=FileNotFoundError(f"{missing} does not exist")):
        result = runner.invoke(board, ["scp", "remote-host"])

    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_scp_copies_files(runner, tmp_path):
    """scp calls ssh mkdir and scp with correct arguments."""
    # Set up fake board files
    config_file = tmp_path / "board.toml"
    config_file.write_text("default_swarm = 'abc'\n")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "abc.key").write_bytes(b"\x00" * 32)
    (keys_dir / "abc.pub").write_bytes(b"\x00" * 32)

    files = [config_file, keys_dir / "abc.key", keys_dir / "abc.pub"]
    commands_run = []

    def fake_run(cmd, **kwargs):
        commands_run.append(cmd)
        return MagicMock(returncode=0)

    with patch("cli.board.collect_board_files", return_value=files), \
         patch("cli.board.subprocess.run", side_effect=fake_run):
        result = runner.invoke(board, ["scp", "myhost"])

    assert result.exit_code == 0
    assert "3 file(s)" in result.output
    assert "myhost" in result.output

    # Should have run: ssh mkdir, scp board.toml, scp keys
    assert len(commands_run) == 3
    assert commands_run[0][0] == "ssh"
    assert "mkdir" in commands_run[0]
    assert commands_run[1][0] == "scp"
    assert str(config_file) in commands_run[1]
    assert commands_run[2][0] == "scp"
    assert str(keys_dir / "abc.key") in commands_run[2]


def test_scp_config_only_no_keys(runner, tmp_path):
    """scp with board.toml but no keys skips key transfer."""
    config_file = tmp_path / "board.toml"
    config_file.write_text("default_swarm = 'abc'\n")

    files = [config_file]
    commands_run = []

    def fake_run(cmd, **kwargs):
        commands_run.append(cmd)
        return MagicMock(returncode=0)

    with patch("cli.board.collect_board_files", return_value=files), \
         patch("cli.board.subprocess.run", side_effect=fake_run):
        result = runner.invoke(board, ["scp", "myhost"])

    assert result.exit_code == 0
    assert "1 file(s)" in result.output
    # Should only run scp for board.toml, no ssh mkdir needed
    assert len(commands_run) == 1
    assert commands_run[0][0] == "scp"


def test_scp_ssh_failure(runner, tmp_path):
    """scp reports error when SSH fails."""
    import subprocess as sp

    config_file = tmp_path / "board.toml"
    config_file.write_text("")
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir()
    (keys_dir / "abc.key").write_bytes(b"\x00" * 32)
    (keys_dir / "abc.pub").write_bytes(b"\x00" * 32)

    files = [config_file, keys_dir / "abc.key", keys_dir / "abc.pub"]

    def fail_ssh(cmd, **kwargs):
        if cmd[0] == "ssh":
            raise sp.CalledProcessError(1, cmd, stderr="Connection refused")
        return MagicMock(returncode=0)

    with patch("cli.board.collect_board_files", return_value=files), \
         patch("cli.board.subprocess.run", side_effect=fail_ssh):
        result = runner.invoke(board, ["scp", "badhost"])

    assert result.exit_code != 0
    assert "SSH" in result.output or "failed" in result.output


def test_scp_scp_failure(runner, tmp_path):
    """scp reports error when SCP command fails."""
    import subprocess as sp

    config_file = tmp_path / "board.toml"
    config_file.write_text("")
    files = [config_file]

    def fail_scp(cmd, **kwargs):
        if cmd[0] == "scp":
            raise sp.CalledProcessError(1, cmd, stderr="Permission denied")
        return MagicMock(returncode=0)

    with patch("cli.board.collect_board_files", return_value=files), \
         patch("cli.board.subprocess.run", side_effect=fail_scp):
        result = runner.invoke(board, ["scp", "badhost"])

    assert result.exit_code != 0
    assert "SCP" in result.output or "failed" in result.output
