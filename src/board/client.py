# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""WebSocket client for the Leader Board wire protocol.

Handles the auth handshake (challenge-response) and exposes methods for
send, watch, channels, and register_swarm.

Spec reference: docs/trunk/SPEC.md §Wire Protocol, §Authentication Flow
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, AsyncGenerator

import websockets

from board.crypto import sign

logger = logging.getLogger(__name__)


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
        # Chunk: docs/chunks/websocket_keepalive - Configure client-side ping for dead connection detection
        # Chunk: docs/chunks/websocket_cloudflare_diag - Increase ping_timeout from 10→30 to
        # accommodate Cloudflare DO hibernation wake latency (H3 fix)
        self._ws = await websockets.connect(
            url, close_timeout=1, ping_interval=20, ping_timeout=30
        )
        logger.debug(
            "WebSocket connected: url=%s ping_interval=20 ping_timeout=30",
            url,
        )

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
            logger.debug("WebSocket closing (client-initiated)")
            await self._ws.close()
            self._ws = None

    async def register_swarm(self, public_key: bytes) -> None:
        """Register a swarm (unauthenticated — separate connection).

        Opens a fresh WebSocket, sends register_swarm, waits for auth_ok,
        then closes. This does NOT use the main authenticated connection.
        """
        url = f"{self.server_url}/ws?swarm={self.swarm_id}"
        async with websockets.connect(url, close_timeout=1) as ws:
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

        response = json.loads(await self._ws.recv())
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

        response = json.loads(await self._ws.recv())
        self._check_error(response)
        if response.get("type") != "message":
            raise BoardError("protocol_error", f"Expected message, got {response.get('type')}")
        return {
            "position": response["position"],
            "body": response["body"],
            "sent_at": response["sent_at"],
        }

    # Chunk: docs/chunks/websocket_keepalive - Reconnect wrapper for watch()
    # Chunk: docs/chunks/websocket_reconnect_tuning - Backoff reset and keepalive tuning
    async def watch_with_reconnect(
        self,
        channel: str,
        cursor: int,
        max_retries: int | None = None,
    ) -> dict:
        """Watch with automatic reconnect on connection failure.

        On disconnect, reconnects with exponential backoff and re-sends the
        watch frame from the same cursor position. No messages are lost because
        the cursor tracks the last processed position.

        Parameters
        ----------
        channel:
            Channel to watch.
        cursor:
            Position to watch after.
        max_retries:
            Maximum reconnect attempts. ``None`` means unlimited.

        Returns dict with keys: position, body, sent_at.
        """
        attempt = 0
        backoff = 1.0
        max_backoff = 30.0

        while True:
            try:
                return await self.watch(channel, cursor)
            except (
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                ConnectionError,
                OSError,
            ) as exc:
                attempt += 1
                if max_retries is not None and attempt > max_retries:
                    raise

                # Chunk: docs/chunks/websocket_cloudflare_diag - Log close code for diagnostics
                close_code = None
                close_reason = None
                if isinstance(exc, (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK)):
                    if exc.rcvd is not None:
                        close_code = exc.rcvd.code
                        close_reason = exc.rcvd.reason

                # Exponential backoff with jitter
                jitter = random.uniform(0, backoff * 0.5)
                wait_time = min(backoff + jitter, max_backoff)
                logger.warning(
                    "WebSocket disconnected, reconnecting in %.1fs (attempt %d) "
                    "close_code=%s close_reason=%s exc=%s",
                    wait_time,
                    attempt,
                    close_code,
                    close_reason,
                    type(exc).__name__,
                )
                await asyncio.sleep(wait_time)
                backoff = min(backoff * 2, max_backoff)

                # Re-establish connection and re-authenticate
                try:
                    await self.close()
                except Exception:
                    pass
                await self.connect()
                # Chunk: docs/chunks/websocket_reconnect_tuning - Reset backoff after successful reconnect
                # Only reset backoff, not attempt — max_retries should count total
                # failures, not just consecutive failures since last connect().
                # connect() succeeds (auth handshake) even when the server will
                # immediately drop the watch, so resetting attempt here would make
                # max_retries unreachable in degraded-server scenarios.
                backoff = 1.0

    # Chunk: docs/chunks/multichannel_watch - Multi-channel watch support
    # Chunk: docs/chunks/watchmulti_exit_on_message - Count-limited watch_multi
    async def watch_multi(
        self,
        channels: dict[str, int],
        count: int = 1,
    ) -> AsyncGenerator[dict, None]:
        """Watch multiple channels on a single connection.

        Sends a watch frame for each channel, then yields messages as they
        arrive from any channel. After yielding a message, automatically
        re-sends the watch frame for that channel with cursor = message.position.

        Parameters
        ----------
        channels:
            Mapping of channel name to cursor position.
        count:
            Maximum number of messages to yield before returning. When
            ``count > 0``, the generator yields at most *count* messages
            then returns. When ``count == 0``, it streams indefinitely
            (backwards-compatible with the original behavior).

        Yields dicts with keys: channel, position, body, sent_at.
        """
        # Send initial watch frames for all channels
        for channel, cursor in channels.items():
            frame = {
                "type": "watch",
                "channel": channel,
                "swarm": self.swarm_id,
                "cursor": cursor,
            }
            await self._ws.send(json.dumps(frame))

        # Track active channels (channels that haven't errored)
        active_channels = set(channels.keys())
        delivered = 0

        # Receive loop: yield messages as they arrive from any channel
        while active_channels:
            response = json.loads(await self._ws.recv())

            if response.get("type") == "error":
                # Per-channel error: remove that channel from active set
                error_msg = response.get("message", "")
                # Try to extract channel name from error message
                code = response.get("code", "")
                if code == "channel_not_found":
                    # Extract channel name from "Channel not found: <name>"
                    for ch in list(active_channels):
                        if ch in error_msg:
                            active_channels.discard(ch)
                            logger.warning(
                                "Channel %r not found, removing from watch", ch
                            )
                            break
                    else:
                        # Can't determine which channel errored, log and continue
                        logger.warning("Watch error: %s: %s", code, error_msg)
                else:
                    # Non-channel error — raise
                    raise BoardError(code, error_msg)
                continue

            if response.get("type") != "message":
                raise BoardError(
                    "protocol_error",
                    f"Expected message, got {response.get('type')}",
                )

            channel = response["channel"]
            position = response["position"]

            yield {
                "channel": channel,
                "position": position,
                "body": response["body"],
                "sent_at": response["sent_at"],
            }

            # Track delivered count and exit if limit reached
            delivered += 1
            if count > 0 and delivered >= count:
                return

            # Re-send watch frame for this channel with updated cursor
            if channel in active_channels:
                frame = {
                    "type": "watch",
                    "channel": channel,
                    "swarm": self.swarm_id,
                    "cursor": position,
                }
                await self._ws.send(json.dumps(frame))

    # Chunk: docs/chunks/watchmulti_exit_on_message - Count-limited reconnect wrapper
    async def watch_multi_with_reconnect(
        self,
        channels: dict[str, int],
        max_retries: int | None = None,
        count: int = 1,
    ) -> AsyncGenerator[dict, None]:
        """Watch multiple channels with automatic reconnect on connection failure.

        On disconnect, reconnects with exponential backoff and re-sends all
        watch frames with their latest known cursors.

        Parameters
        ----------
        channels:
            Initial mapping of channel name to cursor position.
        max_retries:
            Maximum reconnect attempts. ``None`` means unlimited.
        count:
            Maximum total messages to yield across all reconnects. When
            ``count > 0``, the generator yields at most *count* messages
            then returns. When ``count == 0``, it streams indefinitely.

        Yields dicts with keys: channel, position, body, sent_at.
        """
        # Track latest cursors across reconnects
        cursors = dict(channels)
        attempt = 0
        backoff = 1.0
        max_backoff = 30.0
        delivered = 0

        while True:
            try:
                # Inner watch_multi streams indefinitely (count=0); the
                # reconnect wrapper manages the overall message cap so that
                # reconnects don't reset the count.
                async for msg in self.watch_multi(cursors, count=0):
                    # Update cursor for the channel that delivered a message
                    cursors[msg["channel"]] = msg["position"]
                    # Reset backoff on successful message receipt
                    attempt = 0
                    backoff = 1.0
                    yield msg
                    delivered += 1
                    if count > 0 and delivered >= count:
                        return
                # Generator exhausted (all channels errored) — stop
                return
            except (
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                ConnectionError,
                OSError,
            ):
                attempt += 1
                if max_retries is not None and attempt > max_retries:
                    raise

                jitter = random.uniform(0, backoff * 0.5)
                wait_time = min(backoff + jitter, max_backoff)
                logger.warning(
                    "WebSocket disconnected, reconnecting in %.1fs (attempt %d)...",
                    wait_time,
                    attempt,
                )
                await asyncio.sleep(wait_time)
                backoff = min(backoff * 2, max_backoff)

                try:
                    await self.close()
                except Exception:
                    pass
                await self.connect()
                backoff = 1.0

    async def list_channels(self) -> list[dict]:
        """List channels in the swarm."""
        frame = {
            "type": "channels",
            "swarm": self.swarm_id,
        }
        await self._ws.send(json.dumps(frame))

        response = json.loads(await self._ws.recv())
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
