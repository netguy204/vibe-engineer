# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""WebSocket client for the Leader Board wire protocol.

Handles the auth handshake (challenge-response) and exposes methods for
send, watch, channels, and register_swarm.

Spec reference: docs/trunk/SPEC.md §Wire Protocol, §Authentication Flow
"""

from __future__ import annotations

import json
from typing import Any

import websockets

from board.crypto import sign


class BoardError(Exception):
    """Error returned by the Leader Board server."""

    def __init__(self, code: str, message: str, **extra: Any):
        self.code = code
        self.server_message = message
        self.extra = extra
        super().__init__(f"{code}: {message}")


class BoardClient:
    """Async WebSocket client for the Leader Board protocol.

    Usage::

        client = BoardClient("ws://localhost:8374", swarm_id, seed)
        await client.connect()
        try:
            position = await client.send("channel", ciphertext_b64)
        finally:
            await client.close()
    """

    def __init__(self, server_url: str, swarm_id: str, seed: bytes):
        self.server_url = server_url.rstrip("/")
        self.swarm_id = swarm_id
        self.seed = seed
        self._ws: Any = None

    async def connect(self) -> None:
        """Open WebSocket and perform auth handshake."""
        url = f"{self.server_url}/ws?swarm={self.swarm_id}"
        self._ws = await websockets.connect(url)

        # Receive challenge
        challenge_raw = await self._ws.recv()
        challenge = json.loads(challenge_raw)
        if challenge.get("type") != "challenge":
            raise BoardError("protocol_error", f"Expected challenge, got {challenge.get('type')}")

        # Sign the nonce
        nonce_hex = challenge["nonce"]
        nonce_bytes = bytes.fromhex(nonce_hex)
        signature = sign(nonce_bytes, self.seed)

        # Send auth
        auth_frame = {
            "type": "auth",
            "swarm": self.swarm_id,
            "signature": signature.hex(),
        }
        await self._ws.send(json.dumps(auth_frame))

        # Wait for auth_ok
        response_raw = await self._ws.recv()
        response = json.loads(response_raw)
        if response.get("type") == "error":
            raise BoardError(response["code"], response.get("message", ""))
        if response.get("type") != "auth_ok":
            raise BoardError("protocol_error", f"Expected auth_ok, got {response.get('type')}")

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def register_swarm(self, public_key: bytes) -> None:
        """Register a swarm (unauthenticated — separate connection).

        Opens a fresh WebSocket, sends register_swarm, waits for auth_ok,
        then closes. This does NOT use the main authenticated connection.
        """
        url = f"{self.server_url}/ws?swarm={self.swarm_id}"
        async with websockets.connect(url) as ws:
            # Server sends a challenge first, but we ignore it for registration
            await ws.recv()  # discard challenge

            frame = {
                "type": "register_swarm",
                "swarm": self.swarm_id,
                "public_key": public_key.hex(),
            }
            await ws.send(json.dumps(frame))

            response_raw = await ws.recv()
            response = json.loads(response_raw)
            if response.get("type") == "error":
                raise BoardError(response["code"], response.get("message", ""))
            if response.get("type") != "auth_ok":
                raise BoardError("protocol_error", f"Expected auth_ok, got {response.get('type')}")

    async def send(self, channel: str, body_b64: str) -> int:
        """Send a message. Returns the assigned position."""
        frame = {
            "type": "send",
            "channel": channel,
            "swarm": self.swarm_id,
            "body": body_b64,
        }
        await self._ws.send(json.dumps(frame))

        response_raw = await self._ws.recv()
        response = json.loads(response_raw)
        self._check_error(response)
        if response.get("type") != "ack":
            raise BoardError("protocol_error", f"Expected ack, got {response.get('type')}")
        return response["position"]

    async def watch(self, channel: str, cursor: int) -> dict:
        """Watch a channel from cursor. Blocks until a message arrives.

        Returns dict with keys: position, body, sent_at.
        """
        frame = {
            "type": "watch",
            "channel": channel,
            "swarm": self.swarm_id,
            "cursor": cursor,
        }
        await self._ws.send(json.dumps(frame))

        response_raw = await self._ws.recv()
        response = json.loads(response_raw)
        self._check_error(response)
        if response.get("type") != "message":
            raise BoardError("protocol_error", f"Expected message, got {response.get('type')}")
        return {
            "position": response["position"],
            "body": response["body"],
            "sent_at": response["sent_at"],
        }

    async def list_channels(self) -> list[dict]:
        """List channels in the swarm."""
        frame = {
            "type": "channels",
            "swarm": self.swarm_id,
        }
        await self._ws.send(json.dumps(frame))

        response_raw = await self._ws.recv()
        response = json.loads(response_raw)
        self._check_error(response)
        if response.get("type") != "channels_list":
            raise BoardError("protocol_error", f"Expected channels_list, got {response.get('type')}")
        return response["channels"]

    def _check_error(self, response: dict) -> None:
        """Raise BoardError if the response is an error frame."""
        if response.get("type") == "error":
            raise BoardError(
                response["code"],
                response.get("message", ""),
                **{k: v for k, v in response.items() if k not in ("type", "code", "message")},
            )
