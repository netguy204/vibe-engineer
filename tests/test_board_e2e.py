# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""End-to-end integration test for the Leader Board CLI.

Exercises the full send→watch→ack cycle by mocking at the BoardClient level.
Validates that crypto, storage, client, and CLI compose correctly.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from board.crypto import (
    derive_swarm_id,
    derive_symmetric_key,
    encrypt,
    decrypt,
    generate_keypair,
)
from board.config import BoardConfig
from board.storage import load_cursor, load_keypair, save_keypair
from cli.board import board


@pytest.fixture
def e2e_env(tmp_path):
    """Set up a complete e2e environment with keys and project root."""
    seed, pub = generate_keypair()
    swarm_id = derive_swarm_id(pub)
    keys_dir = tmp_path / "keys"
    save_keypair(swarm_id, seed, pub, keys_dir=keys_dir)

    project_root = tmp_path / "project"
    project_root.mkdir()

    return {
        "seed": seed,
        "pub": pub,
        "swarm_id": swarm_id,
        "keys_dir": keys_dir,
        "project_root": project_root,
        "sym_key": derive_symmetric_key(seed),
    }


def test_send_watch_ack_cycle(e2e_env):
    """Full end-to-end: send a message, watch for it, ack the cursor.

    1. Create a swarm (keys already generated in fixture)
    2. Send a message to channel "test-channel"
    3. Watch channel "test-channel" from cursor 0
    4. Verify decrypted message matches original plaintext
    5. Ack position 1
    6. Verify cursor file contains position 1
    """
    runner = CliRunner()
    env = e2e_env
    swarm_id = env["swarm_id"]
    seed = env["seed"]
    pub = env["pub"]
    sym_key = env["sym_key"]
    project_root = env["project_root"]

    original_message = "Hello from the leader board!"

    # The send command will encrypt the message; we need to capture what it
    # sends so we can return it from the mock watch.
    captured_ciphertext = {}

    async def mock_send(channel, body_b64):
        captured_ciphertext["body"] = body_b64
        return 1  # assigned position

    async def mock_watch(channel, cursor, **kwargs):
        assert cursor == 0, "First watch should start from cursor 0"
        return {
            "position": 1,
            "body": captured_ciphertext["body"],
            "sent_at": "2026-03-15T14:30:00Z",
        }

    # Step 2: Send a message
    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.send = AsyncMock(side_effect=mock_send)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "send", "test-channel", original_message,
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "1" in result.output  # position

    # Verify the captured ciphertext is actually encrypted (not plaintext)
    assert captured_ciphertext["body"] != original_message
    # Verify we can decrypt it
    decrypted = decrypt(captured_ciphertext["body"], sym_key)
    assert decrypted == original_message

    # Step 3: Watch for the message
    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.watch = AsyncMock(side_effect=mock_watch)
        instance.watch_with_reconnect = AsyncMock(side_effect=mock_watch)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "watch", "test-channel",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--project-root", str(project_root),
        ])

    # Step 4: Verify decrypted message
    assert result.exit_code == 0
    assert original_message in result.output

    # Verify cursor was NOT auto-advanced
    assert load_cursor("test-channel", project_root) == 0

    # Step 5: Ack position 1
    # Patch load_board_config so the head guard doesn't attempt a real server connection.
    # (The guard is tested separately in test_board_cli; this e2e test focuses on the
    # storage layer composing correctly with crypto and CLI.)
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, [
            "ack", "test-channel", "1",
            "--project-root", str(project_root),
        ])
    assert result.exit_code == 0

    # Step 6: Verify cursor file contains position 1
    assert load_cursor("test-channel", project_root) == 1


def test_watch_uses_persisted_cursor(e2e_env):
    """After ack, the next watch should use the updated cursor.

    1. Ack position 1
    2. Watch — verify the cursor passed to the client is 1 (not 0)
    """
    runner = CliRunner()
    env = e2e_env
    swarm_id = env["swarm_id"]
    seed = env["seed"]
    pub = env["pub"]
    sym_key = env["sym_key"]
    project_root = env["project_root"]

    # Ack position 1 first (patch board config so head guard doesn't hit real server)
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, [
            "ack", "test-channel", "1",
            "--project-root", str(project_root),
        ])
    assert result.exit_code == 0

    # Now watch — should use cursor=1
    encrypted_body = encrypt("message two", sym_key)

    async def mock_watch(channel, cursor, **kwargs):
        assert cursor == 1, f"Expected cursor=1 after ack, got {cursor}"
        return {
            "position": 2,
            "body": encrypted_body,
            "sent_at": "2026-03-15T15:00:00Z",
        }

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.BoardClient") as MockClient:

        instance = MockClient.return_value
        instance.connect = AsyncMock()
        instance.watch = AsyncMock(side_effect=mock_watch)
        instance.watch_with_reconnect = AsyncMock(side_effect=mock_watch)
        instance.close = AsyncMock()

        result = runner.invoke(board, [
            "watch", "test-channel",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--project-root", str(project_root),
        ])

    assert result.exit_code == 0
    assert "message two" in result.output
    # Cursor should still be 1 (watch doesn't advance)
    assert load_cursor("test-channel", project_root) == 1


def test_channels_listing(e2e_env):
    """List channels returns formatted output."""
    runner = CliRunner()
    env = e2e_env
    swarm_id = env["swarm_id"]
    seed = env["seed"]
    pub = env["pub"]

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
    assert "head=10" in result.output
    assert "changelog" in result.output
