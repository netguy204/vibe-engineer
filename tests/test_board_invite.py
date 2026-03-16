# Chunk: docs/chunks/invite_cli_command - Invite CLI commands
"""Tests for ve board invite and ve board revoke commands."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from board.config import BoardConfig, SwarmConfig
from board.crypto import (
    decrypt,
    derive_swarm_id,
    derive_token_key,
    generate_keypair,
)
from board.storage import save_keypair
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


# ---------------------------------------------------------------------------
# invite command tests
# ---------------------------------------------------------------------------


def test_invite_happy_path(runner, stored_swarm):
    """ve board invite generates a token, uploads encrypted blob, prints invite URL."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    captured_requests = []

    def mock_put(url, **kwargs):
        captured_requests.append({"url": url, "kwargs": kwargs})
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put):
        result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code == 0, result.output

    # Output should contain an invite URL
    output = result.output.strip()
    # The URL line is the last non-empty line
    lines = [l for l in output.split("\n") if l.strip()]
    invite_url = lines[-1]
    assert "http://test:8787/invite/" in invite_url

    # Extract token from URL
    token_hex = invite_url.split("/invite/")[1]
    token_bytes = bytes.fromhex(token_hex)

    # Verify the PUT was called correctly
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert "/gateway/keys" in req["url"]
    body = req["kwargs"]["json"]
    assert "token_hash" in body
    assert "encrypted_blob" in body

    # Verify token_hash matches sha256(token)
    expected_hash = hashlib.sha256(token_bytes).hexdigest()
    assert body["token_hash"] == expected_hash

    # Verify the encrypted blob can be decrypted to recover the seed
    sym_key = derive_token_key(token_bytes)
    decrypted = decrypt(body["encrypted_blob"], sym_key)
    assert bytes.fromhex(decrypted) == seed


def test_invite_shows_warning(runner, stored_swarm):
    """ve board invite displays the opt-in warning text."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    def mock_put(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put):
        result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "cleartext gateway" in result.output


def test_invite_abort_on_decline(runner, stored_swarm):
    """Answering 'n' to the confirmation prompt aborts without uploading."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put") as mock_put:
        result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ], input="n\n")

    assert "Aborted" in result.output
    mock_put.assert_not_called()


def test_invite_yes_bypasses_confirmation(runner, stored_swarm):
    """--yes flag bypasses the confirmation prompt."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    def mock_put(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put) as put_mock:
        result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code == 0
    # Confirm prompt text should NOT appear (no "Do you want to continue?")
    assert "Do you want to continue?" not in result.output
    put_mock.assert_called_once()


def test_invite_missing_swarm(runner):
    """invite with no --swarm and no default prints error."""
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, ["invite", "--yes"])

    assert result.exit_code != 0
    assert "no swarm specified" in result.output


def test_invite_keypair_not_found(runner):
    """invite errors when keypair not found for swarm."""
    config = BoardConfig(
        default_swarm="missing",
        swarms={"missing": SwarmConfig("ws://test:8787")},
    )

    with patch("cli.board.load_keypair", return_value=None), \
         patch("cli.board.load_board_config", return_value=config):
        result = runner.invoke(board, [
            "invite",
            "--swarm", "missing",
            "--yes",
        ])

    assert result.exit_code != 0
    assert "not found" in result.output


def test_invite_upload_failure(runner, stored_swarm):
    """invite reports error when server returns 500."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    def mock_put(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 500
        return resp

    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put):
        result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


# ---------------------------------------------------------------------------
# revoke command tests
# ---------------------------------------------------------------------------


def test_revoke_happy_path(runner):
    """ve board revoke deletes the token and confirms."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )
    token_hex = "aa" * 32  # 32 bytes in hex

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete) as del_mock:
        result = runner.invoke(board, [
            "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "revoked" in result.output.lower()

    # Verify correct token_hash in URL
    expected_hash = hashlib.sha256(bytes.fromhex(token_hex)).hexdigest()
    call_url = del_mock.call_args[0][0]
    assert expected_hash in call_url


def test_revoke_token_not_found(runner):
    """ve board revoke with 404 reports token not found."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )
    token_hex = "bb" * 32

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 404
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "not found" in result.output or "already revoked" in result.output


def test_revoke_server_error(runner):
    """ve board revoke reports server error on non-200/404 status."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )
    token_hex = "cc" * 32

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 500
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


# ---------------------------------------------------------------------------
# round-trip test
# ---------------------------------------------------------------------------


def test_invite_revoke_round_trip(runner, stored_swarm):
    """Round-trip: invite produces a token that can decrypt the blob, then revoke."""
    swarm_id, seed, pub, keys_dir = stored_swarm
    config = BoardConfig(
        default_swarm=swarm_id,
        swarms={swarm_id: SwarmConfig("ws://test:8787")},
    )

    captured_put = []
    captured_delete = []

    def mock_put(url, **kwargs):
        captured_put.append({"url": url, "kwargs": kwargs})
        resp = MagicMock()
        resp.status_code = 200
        return resp

    def mock_delete(url, **kwargs):
        captured_delete.append({"url": url, "kwargs": kwargs})
        resp = MagicMock()
        resp.status_code = 200
        return resp

    # Step 1: Invite
    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put):
        invite_result = runner.invoke(board, [
            "invite",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert invite_result.exit_code == 0

    # Extract token from invite URL
    lines = [l for l in invite_result.output.strip().split("\n") if l.strip()]
    invite_url = lines[-1]
    token_hex = invite_url.split("/invite/")[1]
    token_bytes = bytes.fromhex(token_hex)

    # Verify we can decrypt the blob to recover the seed
    blob = captured_put[0]["kwargs"]["json"]["encrypted_blob"]
    sym_key = derive_token_key(token_bytes)
    recovered_seed = bytes.fromhex(decrypt(blob, sym_key))
    assert recovered_seed == seed

    # Step 2: Revoke
    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        revoke_result = runner.invoke(board, [
            "revoke", token_hex,
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ])

    assert revoke_result.exit_code == 0
    assert "revoked" in revoke_result.output.lower()

    # Verify the DELETE used the correct token_hash
    expected_hash = hashlib.sha256(token_bytes).hexdigest()
    delete_url = captured_delete[0]["url"]
    assert expected_hash in delete_url
