# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
"""End-to-end integration tests for the local WebSocket server.

These tests exercise the full stack: FileSystemStorage → LeaderBoardCore →
WebSocket handler, verifying the success criteria from the chunk goal.
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.testclient import TestClient

from leader_board.core import LeaderBoardCore
from leader_board.fs_storage import FileSystemStorage
from leader_board.server import create_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_keypair():
    private_key = Ed25519PrivateKey.generate()
    pub_bytes = private_key.public_key().public_bytes_raw()
    return private_key, pub_bytes


def _register_and_auth(ws, private_key, pub_bytes, swarm_id):
    """Register a new swarm via the websocket handshake."""
    challenge = json.loads(ws.receive_text())
    assert challenge["type"] == "challenge"

    ws.send_text(
        json.dumps(
            {
                "type": "register_swarm",
                "swarm": swarm_id,
                "public_key": pub_bytes.hex(),
            }
        )
    )
    auth_ok = json.loads(ws.receive_text())
    assert auth_ok["type"] == "auth_ok"


def _auth_existing(ws, private_key, swarm_id):
    """Authenticate with an existing swarm."""
    challenge = json.loads(ws.receive_text())
    assert challenge["type"] == "challenge"
    nonce = bytes.fromhex(challenge["nonce"])
    signature = private_key.sign(nonce)

    ws.send_text(
        json.dumps(
            {
                "type": "auth",
                "swarm": swarm_id,
                "signature": signature.hex(),
            }
        )
    )
    auth_ok = json.loads(ws.receive_text())
    assert auth_ok["type"] == "auth_ok"


# ---------------------------------------------------------------------------
# Test: send → watch → receive
# ---------------------------------------------------------------------------


class TestSendWatchReceive:
    def test_send_then_watch_receives_message(self, tmp_path) -> None:
        """E2E: register, send a message, watch with cursor 0, receive it."""
        app = create_app(storage_dir=tmp_path)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "e2e-swarm"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            # Send a message
            body_plain = b"hello from e2e"
            body_b64 = base64.b64encode(body_plain).decode()
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "test-channel",
                        "swarm": swarm_id,
                        "body": body_b64,
                    }
                )
            )

            ack = json.loads(ws.receive_text())
            assert ack["type"] == "ack"
            assert ack["position"] == 1

            # Watch from cursor 0
            ws.send_text(
                json.dumps(
                    {
                        "type": "watch",
                        "channel": "test-channel",
                        "swarm": swarm_id,
                        "cursor": 0,
                    }
                )
            )

            msg = json.loads(ws.receive_text())
            assert msg["type"] == "message"
            assert msg["position"] == 1
            assert base64.b64decode(msg["body"]) == body_plain

    def test_state_persists_across_restarts(self, tmp_path) -> None:
        """E2E: data written by one server instance is readable by another."""
        private_key, pub_bytes = _make_keypair()
        swarm_id = "persist-swarm"
        body_plain = b"persist me"
        body_b64 = base64.b64encode(body_plain).decode()

        # First server instance: register + send
        app1 = create_app(storage_dir=tmp_path)
        client1 = TestClient(app1)
        with client1.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "persist-ch",
                        "swarm": swarm_id,
                        "body": body_b64,
                    }
                )
            )
            ack = json.loads(ws.receive_text())
            assert ack["type"] == "ack"

        # Second server instance: auth + watch → should get the message
        app2 = create_app(storage_dir=tmp_path)
        client2 = TestClient(app2)
        with client2.websocket_connect("/ws") as ws:
            _auth_existing(ws, private_key, swarm_id)
            ws.send_text(
                json.dumps(
                    {
                        "type": "watch",
                        "channel": "persist-ch",
                        "swarm": swarm_id,
                        "cursor": 0,
                    }
                )
            )
            msg = json.loads(ws.receive_text())
            assert msg["type"] == "message"
            assert msg["position"] == 1
            assert base64.b64decode(msg["body"]) == body_plain


# ---------------------------------------------------------------------------
# Test: compaction removes old messages
# ---------------------------------------------------------------------------


class TestCompaction:
    def test_compaction_removes_old_messages(self, tmp_path) -> None:
        """E2E: old messages are compacted; cursor_expired returned."""
        storage = FileSystemStorage(tmp_path)
        core = LeaderBoardCore(storage)
        app = create_app(core=core, storage=storage)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "compact-swarm"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            # Send two messages
            for i in range(2):
                ws.send_text(
                    json.dumps(
                        {
                            "type": "send",
                            "channel": "compact-ch",
                            "swarm": swarm_id,
                            "body": base64.b64encode(
                                f"msg-{i}".encode()
                            ).decode(),
                        }
                    )
                )
                ack = json.loads(ws.receive_text())
                assert ack["type"] == "ack"

        # Age the first message directly in the filesystem
        messages_path = storage._messages_path(swarm_id, "compact-ch")
        lines = messages_path.read_text().strip().split("\n")
        old_data = json.loads(lines[0])
        old_time = datetime.now(UTC) - timedelta(days=60)
        old_data["sent_at"] = old_time.isoformat()
        lines[0] = json.dumps(old_data)
        messages_path.write_text("\n".join(lines) + "\n")

        # Run compaction directly via the storage (sync-friendly in test)
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            removed = loop.run_until_complete(
                core.compact(swarm_id, "compact-ch", min_age_days=30)
            )
        finally:
            loop.close()
        assert removed == 1

        # Watch with cursor 0 should get cursor_expired
        with client.websocket_connect("/ws") as ws:
            _auth_existing(ws, private_key, swarm_id)
            ws.send_text(
                json.dumps(
                    {
                        "type": "watch",
                        "channel": "compact-ch",
                        "swarm": swarm_id,
                        "cursor": 0,
                    }
                )
            )
            error = json.loads(ws.receive_text())
            assert error["type"] == "error"
            assert error["code"] == "cursor_expired"
            assert "earliest_position" in error
            assert error["earliest_position"] == 2


# ---------------------------------------------------------------------------
# Test: wire protocol byte-identity
# ---------------------------------------------------------------------------


class TestWireProtocolFormat:
    def test_message_frame_has_correct_fields(self, tmp_path) -> None:
        """Verify the exact JSON structure of a message frame."""
        app = create_app(storage_dir=tmp_path)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "wire-test"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            body_b64 = base64.b64encode(b"test body").decode()
            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "wire-ch",
                        "swarm": swarm_id,
                        "body": body_b64,
                    }
                )
            )
            ack = json.loads(ws.receive_text())
            assert ack["type"] == "ack"

            # Watch to get a message frame
            ws.send_text(
                json.dumps(
                    {
                        "type": "watch",
                        "channel": "wire-ch",
                        "swarm": swarm_id,
                        "cursor": 0,
                    }
                )
            )
            msg = json.loads(ws.receive_text())

            # Verify exact field presence per spec
            assert set(msg.keys()) == {"type", "channel", "position", "body", "sent_at"}
            assert msg["type"] == "message"
            assert isinstance(msg["position"], int)
            assert isinstance(msg["body"], str)
            # sent_at should be ISO 8601 UTC format
            assert msg["sent_at"].endswith("Z")

    def test_ack_frame_has_correct_fields(self, tmp_path) -> None:
        """Verify the exact JSON structure of an ack frame."""
        app = create_app(storage_dir=tmp_path)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "ack-wire"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "ch",
                        "swarm": swarm_id,
                        "body": base64.b64encode(b"x").decode(),
                    }
                )
            )
            ack = json.loads(ws.receive_text())
            assert set(ack.keys()) == {"type", "channel", "position"}
            assert ack["type"] == "ack"

    def test_channels_list_frame_has_correct_fields(self, tmp_path) -> None:
        """Verify channels_list frame structure matches the spec."""
        app = create_app(storage_dir=tmp_path)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "chlist-wire"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            ws.send_text(
                json.dumps(
                    {
                        "type": "send",
                        "channel": "ch",
                        "swarm": swarm_id,
                        "body": base64.b64encode(b"x").decode(),
                    }
                )
            )
            json.loads(ws.receive_text())  # ack

            ws.send_text(
                json.dumps({"type": "channels", "swarm": swarm_id})
            )
            result = json.loads(ws.receive_text())
            assert result["type"] == "channels_list"
            assert isinstance(result["channels"], list)
            ch = result["channels"][0]
            assert set(ch.keys()) == {"name", "head_position", "oldest_position"}

    def test_error_frame_has_correct_fields(self, tmp_path) -> None:
        """Verify error frame structure."""
        app = create_app(storage_dir=tmp_path)
        client = TestClient(app)
        private_key, pub_bytes = _make_keypair()
        swarm_id = "err-wire"

        with client.websocket_connect("/ws") as ws:
            _register_and_auth(ws, private_key, pub_bytes, swarm_id)

            ws.send_text("not json")
            error = json.loads(ws.receive_text())
            assert set(error.keys()) >= {"type", "code", "message"}
            assert error["type"] == "error"
