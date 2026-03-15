# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for cli.board — Click command integration tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from click.testing import CliRunner

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


def test_board_group_exists(runner):
    """ve board --help exits 0 and shows subcommands."""
    result = runner.invoke(board, ["--help"])
    assert result.exit_code == 0
    assert "swarm" in result.output
    assert "send" in result.output
    assert "watch" in result.output
    assert "ack" in result.output
    assert "channels" in result.output


def test_swarm_create(runner, tmp_path):
    """swarm create generates key files and prints swarm ID."""
    keys_dir = tmp_path / "keys"

    with patch("cli.board.save_keypair", wraps=lambda sid, s, p: save_keypair(sid, s, p, keys_dir=keys_dir)), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.register_swarm = AsyncMock()

        result = runner.invoke(board, ["swarm", "create", "--server", "ws://test:8787"])

    assert result.exit_code == 0
    # Output should be the swarm ID (non-empty string)
    swarm_id = result.output.strip()
    assert len(swarm_id) > 0


def test_send_command(runner, stored_swarm, tmp_path):
    """send encrypts and sends a message, prints position."""
    swarm_id, seed, pub, keys_dir = stored_swarm

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
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
    with patch("cli.board.load_keypair", return_value=None):
        result = runner.invoke(board, [
            "send", "ch", "msg",
            "--swarm", "nonexistent",
        ])
    assert result.exit_code != 0
    assert "not found" in result.output
