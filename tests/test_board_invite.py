# Chunk: docs/chunks/invite_cli_command - Invite CLI commands
# Chunk: docs/chunks/invite_list_revoke - List and bulk revoke tests
# Chunk: docs/chunks/invite_revoke_subcommand - Moved revoke under invite group
"""Tests for ve board invite (create, list, revoke) commands."""

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
# invite create command tests (formerly "invite" command, now "invite create")
# ---------------------------------------------------------------------------


def test_invite_create_happy_path(runner, stored_swarm):
    """ve board invite create generates a token, uploads encrypted blob, prints invite URL."""
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
            "invite", "create",
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


def test_invite_create_shows_warning(runner, stored_swarm):
    """ve board invite create displays the opt-in warning text."""
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
            "invite", "create",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code == 0
    assert "WARNING" in result.output
    assert "cleartext gateway" in result.output


def test_invite_create_abort_on_decline(runner, stored_swarm):
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
            "invite", "create",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ], input="n\n")

    assert "Aborted" in result.output
    mock_put.assert_not_called()


def test_invite_create_yes_bypasses_confirmation(runner, stored_swarm):
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
            "invite", "create",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code == 0
    # Confirm prompt text should NOT appear (no "Do you want to continue?")
    assert "Do you want to continue?" not in result.output
    put_mock.assert_called_once()


def test_invite_create_missing_swarm(runner):
    """invite create with no --swarm and no default prints error."""
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, ["invite", "create", "--yes"])

    assert result.exit_code != 0
    assert "no swarm specified" in result.output


def test_invite_create_keypair_not_found(runner):
    """invite create errors when keypair not found for swarm."""
    config = BoardConfig(
        default_swarm="missing",
        swarms={"missing": SwarmConfig("ws://test:8787")},
    )

    with patch("cli.board.load_keypair", return_value=None), \
         patch("cli.board.load_board_config", return_value=config):
        result = runner.invoke(board, [
            "invite", "create",
            "--swarm", "missing",
            "--yes",
        ])

    assert result.exit_code != 0
    assert "not found" in result.output


def test_invite_create_upload_failure(runner, stored_swarm):
    """invite create reports error when server returns 500."""
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
            "invite", "create",
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
            "--yes",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


# ---------------------------------------------------------------------------
# invite list command tests
# ---------------------------------------------------------------------------


def test_invite_list_no_tokens(runner):
    """invite list with no tokens shows 'No active invite tokens.'"""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"keys": []}
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get):
        result = runner.invoke(board, [
            "invite", "list",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "No active invite tokens." in result.output


def test_invite_list_populated(runner):
    """invite list with tokens displays hint and creation time."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "keys": [
                {"token_hash": "abcdef1234567890", "created_at": "2026-03-16T00:00:00Z", "hint": "abcdef12"},
                {"token_hash": "1234567890abcdef", "created_at": "2026-03-16T01:00:00Z", "hint": "12345678"},
            ]
        }
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get):
        result = runner.invoke(board, [
            "invite", "list",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "abcdef12" in result.output
    assert "12345678" in result.output
    assert "2026-03-16T00:00:00Z" in result.output
    assert "2026-03-16T01:00:00Z" in result.output


def test_invite_list_missing_swarm(runner):
    """invite list with no --swarm and no default prints error."""
    with patch("cli.board.load_board_config", return_value=BoardConfig()):
        result = runner.invoke(board, ["invite", "list"])

    assert result.exit_code != 0
    assert "no swarm specified" in result.output


def test_invite_list_server_error(runner):
    """invite list reports error when server returns 500."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 500
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get):
        result = runner.invoke(board, [
            "invite", "list",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


# ---------------------------------------------------------------------------
# invite revoke command tests
# ---------------------------------------------------------------------------


def test_revoke_happy_path(runner):
    """ve board invite revoke deletes the token and confirms."""
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
            "invite", "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "revoked" in result.output.lower()

    # Verify correct token_hash in URL
    expected_hash = hashlib.sha256(bytes.fromhex(token_hex)).hexdigest()
    call_url = del_mock.call_args[0][0]
    assert expected_hash in call_url


def test_revoke_by_hint(runner):
    """ve board invite revoke with a short hint prefix looks up the full token_hash."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )
    full_hash = "abcdef1234567890" * 4  # 64-char token_hash
    hint = "abcdef12"

    call_log = []

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "keys": [
                {"token_hash": full_hash, "hint": hint, "created_at": "2026-03-16T00:00:00Z"},
            ]
        }
        return resp

    def mock_delete(url, **kwargs):
        call_log.append(url)
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "invite", "revoke", hint,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0, result.output
    assert "revoked" in result.output.lower()
    # The DELETE should use the full token_hash, not a re-hash of the hint
    assert full_hash in call_log[0]


def test_revoke_by_hint_ambiguous(runner):
    """ve board invite revoke with an ambiguous prefix reports error."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "keys": [
                {"token_hash": "abcdef12aaaa" + "0" * 52, "hint": "abcdef12"},
                {"token_hash": "abcdef12bbbb" + "0" * 52, "hint": "abcdef12"},
            ]
        }
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get):
        result = runner.invoke(board, [
            "invite", "revoke", "abcdef12",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "ambiguous" in result.output.lower()


def test_revoke_by_hint_not_found(runner):
    """ve board invite revoke with a non-matching hint reports not found."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"keys": []}
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.get", side_effect=mock_get):
        result = runner.invoke(board, [
            "invite", "revoke", "deadbeef",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_revoke_token_not_found(runner):
    """ve board invite revoke with 404 reports token not found."""
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
            "invite", "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "not found" in result.output or "already revoked" in result.output


def test_revoke_server_error(runner):
    """ve board invite revoke reports server error on non-200/404 status."""
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
            "invite", "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


# ---------------------------------------------------------------------------
# invite revoke --all tests
# ---------------------------------------------------------------------------


def test_revoke_all_happy_path(runner):
    """ve board invite revoke --all deletes all tokens and reports count."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True, "deleted": 3}
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete) as del_mock:
        result = runner.invoke(board, [
            "invite", "revoke", "--all",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "Revoked 3 invite token(s)." in result.output

    # Verify the DELETE went to /gateway/keys (no token hash in path)
    call_url = del_mock.call_args[0][0]
    assert call_url.endswith("/gateway/keys")


def test_revoke_all_empty_swarm(runner):
    """ve board invite revoke --all on empty swarm reports zero revoked."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"ok": True, "deleted": 0}
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "invite", "revoke", "--all",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "Revoked 0 invite token(s)." in result.output


def test_revoke_all_server_error(runner):
    """ve board invite revoke --all reports server error on non-200 status."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 500
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "invite", "revoke", "--all",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "500" in result.output


def test_revoke_neither_token_nor_all_errors(runner):
    """ve board invite revoke with neither token nor --all prints error."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )

    with patch("cli.board.load_board_config", return_value=config):
        result = runner.invoke(board, [
            "invite", "revoke",
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code != 0
    assert "provide a TOKEN argument or use --all" in result.output


# ---------------------------------------------------------------------------
# round-trip test
# ---------------------------------------------------------------------------


def test_invite_revoke_round_trip(runner, stored_swarm):
    """Round-trip: invite create produces a token that can decrypt the blob, then revoke."""
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

    # Step 1: Invite create
    with patch("cli.board.load_keypair", return_value=(seed, pub)), \
         patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.put", side_effect=mock_put):
        invite_result = runner.invoke(board, [
            "invite", "create",
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

    # Step 2: Revoke via invite revoke
    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        revoke_result = runner.invoke(board, [
            "invite", "revoke", token_hex,
            "--swarm", swarm_id,
            "--server", "ws://test:8787",
        ])

    assert revoke_result.exit_code == 0
    assert "revoked" in revoke_result.output.lower()

    # Verify the DELETE used the correct token_hash
    expected_hash = hashlib.sha256(token_bytes).hexdigest()
    delete_url = captured_delete[0]["url"]
    assert expected_hash in delete_url


# ---------------------------------------------------------------------------
# deprecated alias tests
# ---------------------------------------------------------------------------


def test_deprecated_board_revoke_warns(runner):
    """ve board revoke (old path) still works but emits deprecation warning."""
    config = BoardConfig(
        default_swarm="myswarm",
        swarms={"myswarm": SwarmConfig("ws://test:8787")},
    )
    token_hex = "aa" * 32

    def mock_delete(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("cli.board.load_board_config", return_value=config), \
         patch("cli.board.httpx.delete", side_effect=mock_delete):
        result = runner.invoke(board, [
            "revoke", token_hex,
            "--swarm", "myswarm",
            "--server", "ws://test:8787",
        ])

    assert result.exit_code == 0
    assert "deprecated" in result.output.lower()
    assert "ve board invite revoke" in result.output


# ---------------------------------------------------------------------------
# invite --help test
# ---------------------------------------------------------------------------


def test_invite_help_shows_revoke(runner):
    """ve board invite --help lists create, list, and revoke subcommands."""
    result = runner.invoke(board, ["invite", "--help"])

    assert result.exit_code == 0
    assert "create" in result.output
    assert "list" in result.output
    assert "revoke" in result.output
