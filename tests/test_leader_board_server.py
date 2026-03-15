# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""Tests for the WebSocket connection handler and server."""

from __future__ import annotations

import asyncio
import base64
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.applications import Starlette
from starlette.testclient import TestClient

from leader_board.core import LeaderBoardCore
from leader_board.memory_storage import InMemoryStorage
from leader_board.server import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def core(memory_storage: InMemoryStorage) -> LeaderBoardCore:
    return LeaderBoardCore(memory_storage)


@pytest.fixture
def app(core: LeaderBoardCore, memory_storage: InMemoryStorage) -> Starlette:
    return create_app(core=core, storage=memory_storage)


@pytest.fixture
def client(app: Starlette) -> TestClient:
    return TestClient(app)


@pytest.fixture
def keypair():
    """Generate an Ed25519 keypair for testing."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes_raw()
    return private_key, pub_bytes


def _auth_handshake(ws, private_key, pub_bytes, swarm_id="test-swarm"):
    """Complete the challenge-auth handshake on an open websocket."""
    # Receive challenge
    challenge = json.loads(ws.receive_text())
    assert challenge["type"] == "challenge"
    nonce = bytes.fromhex(challenge["nonce"])

    # Sign the nonce
    signature = private_key.sign(nonce)

    # Send auth
    ws.send_text(
        json.dumps(
            {
                "type": "auth",
                "swarm": swarm_id,
                "signature": signature.hex(),
            }
        )
    )

    # Receive auth_ok
    auth_ok = json.loads(ws.receive_text())
    assert auth_ok["type"] == "auth_ok"
    return auth_ok


def _register_handshake(ws, pub_bytes, swarm_id="test-swarm"):
    """Complete the challenge-register_swarm handshake on an open websocket."""
    # Receive challenge
    challenge = json.loads(ws.receive_text())
    assert challenge["type"] == "challenge"

    # Send register_swarm
    ws.send_text(
        json.dumps(
            {
                "type": "register_swarm",
                "swarm": swarm_id,
                "public_key": pub_bytes.hex(),
            }
        )
    )

    # Receive auth_ok
    auth_ok = json.loads(ws.receive_text())
    assert auth_ok["type"] == "auth_ok"
    return auth_ok


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWebSocketHandler:
    def test_challenge_sent_on_connect(self, client: TestClient) -> None:
        """Connecting to /ws should immediately receive a challenge frame."""
        with client.websocket_connect("/ws") as ws:
            msg = json.loads(ws.receive_text())
            assert msg["type"] == "challenge"
            assert len(msg["nonce"]) == 64  # 32 bytes hex-encoded

    def test_register_swarm_flow(
        self, client: TestClient, keypair
    ) -> None:
        """register_swarm → auth_ok flow."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes)

    def test_auth_flow_success(
        self, client: TestClient, keypair
    ) -> None:
        """Connect, receive challenge, send auth, receive auth_ok."""
        private_key, pub_bytes = keypair
        swarm_id = "auth-test"

        # Register the swarm first via a websocket connection
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, swarm_id)

        # Now authenticate with the registered swarm
        with client.websocket_connect("/ws") as ws:
            _auth_handshake(ws, private_key, pub_bytes, swarm_id)

    def test_auth_flow_invalid_signature(
        self, client: TestClient, keypair
    ) -> None:
        """Bad signature → error frame, connection closed."""
        private_key, pub_bytes = keypair
        swarm_id = "bad-sig-test"

        # Register the swarm first
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, swarm_id)

        with client.websocket_connect("/ws") as ws:
            challenge = json.loads(ws.receive_text())
            assert challenge["type"] == "challenge"

            # Send auth with a bad signature
            ws.send_text(
                json.dumps(
                    {
                        "type": "auth",
                        "swarm": swarm_id,
                        "signature": "00" * 64,  # bogus
                    }
                )
            )

            error = json.loads(ws.receive_text())
            assert error["type"] == "error"
            assert error["code"] == "auth_failed"

    def test_send_and_ack(
        self, client: TestClient, keypair
    ) -> None:
        """Authenticate, send message, receive ack with position."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "send-test")

            body = base64.b64encode(b"hello world").decode()
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "test-ch",
                        "swarm": "send-test",
                        "body": body,
                    }
                )
            )

            ack = json.loads(ws.receive_text())
            assert ack["type"] == "ack"
            assert ack["channel"] == "test-ch"
            assert ack["position"] == 1

    def test_watch_immediate_delivery(
        self, client: TestClient, keypair
    ) -> None:
        """Send a message first, then watch from cursor 0 → immediate delivery."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "watch-test")

            # Send a message first
            body = base64.b64encode(b"payload").decode()
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "ch",
                        "swarm": "watch-test",
                        "body": body,
                    }
                )
            )
            ack = json.loads(ws.receive_text())
            assert ack["type"] == "ack"

            # Now watch from cursor 0
            ws.send_text(
                json.dumps(
                    {
                        "type": "watch",
                        "channel": "ch",
                        "swarm": "watch-test",
                        "cursor": 0,
                    }
                )
            )

            msg = json.loads(ws.receive_text())
            assert msg["type"] == "message"
            assert msg["channel"] == "ch"
            assert msg["position"] == 1
            assert base64.b64decode(msg["body"]) == b"payload"

    def test_channels_list(
        self, client: TestClient, keypair
    ) -> None:
        """Send to multiple channels, request channel list, verify response."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "ch-list")

            # Send to two channels
            for ch in ("alpha", "beta"):
                ws.send_text(
                    json.dumps(
                        {
                            "type": "send",
                            "channel": ch,
                            "swarm": "ch-list",
                            "body": base64.b64encode(b"data").decode(),
                        }
                    )
                )
                ack = json.loads(ws.receive_text())
                assert ack["type"] == "ack"

            # Request channels
            ws.send_text(
                json.dumps({"type": "channels", "swarm": "ch-list"})
            )

            result = json.loads(ws.receive_text())
            assert result["type"] == "channels_list"
            names = {ch["name"] for ch in result["channels"]}
            assert names == {"alpha", "beta"}

    def test_error_on_invalid_frame(self, client: TestClient, keypair) -> None:
        """Send malformed JSON after auth → error frame."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "invalid-frame")

            ws.send_text("not valid json {{{")

            error = json.loads(ws.receive_text())
            assert error["type"] == "error"
            assert error["code"] == "invalid_frame"

    def test_swarm_scoping(
        self, client: TestClient, keypair
    ) -> None:
        """Authenticate as swarm A, try to send to swarm B → error."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "swarm-a")

            # Try to send to a different swarm
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "ch",
                        "swarm": "swarm-b",
                        "body": base64.b64encode(b"data").decode(),
                    }
                )
            )

            error = json.loads(ws.receive_text())
            assert error["type"] == "error"
            assert error["code"] == "swarm_not_found"

    def test_swarm_info(
        self, client: TestClient, keypair
    ) -> None:
        """Retrieve swarm info after registration."""
        private_key, pub_bytes = keypair
        with client.websocket_connect("/ws") as ws:
            _register_handshake(ws, pub_bytes, "info-swarm")

            ws.send_text(
                json.dumps({"type": "swarm_info", "swarm": "info-swarm"})
            )

            result = json.loads(ws.receive_text())
            assert result["type"] == "swarm_info"
            assert result["swarm"] == "info-swarm"
            assert "created_at" in result


class TestCreateApp:
    def test_create_app_returns_runnable_starlette_app(
        self, tmp_path
    ) -> None:
        """create_app with a tmp_path returns a Starlette instance."""
        app = create_app(storage_dir=tmp_path)
        assert isinstance(app, Starlette)

        # Verify the /ws route exists
        route_paths = [r.path for r in app.routes]
        assert "/ws" in route_paths
