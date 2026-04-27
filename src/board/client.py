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
import ssl
from typing import Any, AsyncGenerator

import websockets
import websockets.exceptions

from board.crypto import sign

logger = logging.getLogger(__name__)

# Chunk: docs/chunks/board_watch_handshake_retry - Centralized retryable exception tuple
_RETRYABLE_ERRORS = (
    websockets.exceptions.ConnectionClosedError,
    websockets.exceptions.ConnectionClosedOK,
    ConnectionError,
    OSError,
    TimeoutError,
    ssl.SSLCertVerificationError,
)


class BoardError(Exception):
    """Error returned by the Leader Board server."""

    def __init__(self, code: str, message: str, **extra: Any):
        self.code = code
        self.server_message = message
        self.extra = extra
        super().__init__(f"{code}: {message}")


# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle timeout sentinel
class StaleWatchError(ConnectionError):
    """Raised when a watch re-registration cycle times out with no message.

    Distinct from genuine connection failures: the server is reachable but the
    channel is idle. Used to suppress budget accounting in reconnect wrappers.
    """


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
        # Chunk: docs/chunks/websocket_zombie_cleanup - Increase close_timeout to allow server close handshake after hibernation wake
        self._ws = await websockets.connect(
            url, close_timeout=10, ping_interval=20, ping_timeout=30
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
        # Chunk: docs/chunks/websocket_zombie_cleanup - Increase close_timeout to allow server close handshake after hibernation wake
        async with websockets.connect(url, close_timeout=10) as ws:
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
    # Chunk: docs/chunks/board_watch_stale_reconnect - Stale connection detection via re-registration
    # Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnects exempt from budget
    async def watch_with_reconnect(
        self,
        channel: str,
        cursor: int,
        max_retries: int | None = 10,
        stale_timeout: float = 300,
    ) -> dict:
        """Watch with automatic reconnect on connection failure.

        On disconnect, reconnects with exponential backoff and re-sends the
        watch frame from the same cursor position. No messages are lost because
        the cursor tracks the last processed position.

        When no message arrives within ``stale_timeout`` seconds, re-sends the
        watch frame on the existing connection to re-register as a watcher
        (cheaper than a full reconnect). If re-registration also times out,
        forces a full reconnect.

        Parameters
        ----------
        channel:
            Channel to watch.
        cursor:
            Position to watch after.
        max_retries:
            Maximum reconnect attempts. ``None`` means unlimited. Default 10.
        stale_timeout:
            Seconds to wait for a message before re-registering the watch
            frame on the existing connection. Default 300 (5 minutes).

        Returns dict with keys: position, body, sent_at.
        """
        attempt = 0
        backoff = 1.0
        max_backoff = 60.0
        idle_reconnects = 0
        current_stale_timeout = stale_timeout

        while True:
            try:
                # Send watch frame and enter recv loop with stale detection
                frame = {
                    "type": "watch",
                    "channel": channel,
                    "swarm": self.swarm_id,
                    "cursor": cursor,
                }
                await self._ws.send(json.dumps(frame))
                logger.debug(
                    "Watch registered channel=%s cursor=%d", channel, cursor
                )

                reregister_count = 0
                while True:
                    try:
                        raw = await asyncio.wait_for(
                            self._ws.recv(), timeout=current_stale_timeout
                        )
                    except asyncio.TimeoutError:
                        reregister_count += 1
                        if reregister_count > 1:
                            logger.warning(
                                "Watch stale after %d re-registrations, forcing "
                                "reconnect channel=%s cursor=%d",
                                reregister_count,
                                channel,
                                cursor,
                            )
                            raise StaleWatchError("Watch connection stale")
                        logger.info(
                            "Watch re-registering: no message in %ds, "
                            "channel=%s cursor=%d",
                            current_stale_timeout,
                            channel,
                            cursor,
                        )
                        await self._ws.send(json.dumps(frame))
                        continue

                    response = json.loads(raw)
                    self._check_error(response)
                    if response.get("type") != "message":
                        raise BoardError(
                            "protocol_error",
                            f"Expected message, got {response.get('type')}",
                        )
                    # Message received — reset idle tracking
                    idle_reconnects = 0
                    current_stale_timeout = stale_timeout
                    return {
                        "position": response["position"],
                        "body": response["body"],
                        "sent_at": response["sent_at"],
                    }
            except StaleWatchError:
                # Idle timeout — reconnect without counting against the failure budget.
                idle_reconnects += 1
                if idle_reconnects >= 3:
                    # Back off re-register interval to reduce churn on very quiet channels.
                    current_stale_timeout = min(current_stale_timeout * 2, 600.0)
                    logger.info(
                        "Idle reconnect #%d, increasing stale_timeout to %.0fs channel=%s",
                        idle_reconnects, current_stale_timeout, channel,
                    )
                logger.info(
                    "Idle reconnect (not counted against budget) channel=%s cursor=%d",
                    channel, cursor,
                )
                # Reconnect without backoff sleep — the network is fine.
                try:
                    await self.close()
                except Exception:
                    pass
                await self.connect()
                backoff = 1.0  # reset failure backoff too
            # Chunk: docs/chunks/board_watch_handshake_retry - Widen exception tuple to catch handshake errors
            except _RETRYABLE_ERRORS as exc:
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
                # Chunk: docs/chunks/board_watch_handshake_retry - Retry connect() on handshake errors
                while True:
                    try:
                        await self.close()
                    except Exception:
                        pass
                    try:
                        await self.connect()
                        break  # Connected successfully
                    except _RETRYABLE_ERRORS as connect_exc:
                        attempt += 1
                        if max_retries is not None and attempt > max_retries:
                            raise connect_exc
                        jitter = random.uniform(0, backoff * 0.5)
                        wait_time = min(backoff + jitter, max_backoff)
                        logger.warning(
                            "Handshake failed during reconnect in %.1fs "
                            "(attempt %d) exc=%s",
                            wait_time,
                            attempt,
                            type(connect_exc).__name__,
                        )
                        await asyncio.sleep(wait_time)
                        backoff = min(backoff * 2, max_backoff)
                # Chunk: docs/chunks/board_watch_reconnect_delivery - Log re-poll after reconnect
                logger.info(
                    "Reconnected, re-polling channel=%s from cursor=%d",
                    channel,
                    cursor,
                )
                # Chunk: docs/chunks/board_watch_reconnect_fix - Explicit re-subscription log
                logger.info(
                    "Re-subscribing to channel=%s after reconnect",
                    channel,
                )
                # Chunk: docs/chunks/websocket_reconnect_tuning - Reset backoff after successful reconnect
                backoff = 1.0
                # Chunk: docs/chunks/watch_reconnect_counter_reset - Reset attempt counter after successful reconnect
                attempt = 0

    # Chunk: docs/chunks/multichannel_watch - Multi-channel watch support
    # Chunk: docs/chunks/watchmulti_exit_on_message - Count-limited watch_multi
    # Chunk: docs/chunks/watchmulti_manual_ack - Manual ack mode
    # Chunk: docs/chunks/board_watch_stale_reconnect - Stale connection detection via re-registration
    async def watch_multi(
        self,
        channels: dict[str, int],
        count: int = 1,
        auto_ack: bool = True,
        stale_timeout: float = 300,
    ) -> AsyncGenerator[dict, None]:
        """Watch multiple channels on a single connection.

        Sends a watch frame for each channel, then yields messages as they
        arrive from any channel. After yielding a message, automatically
        re-sends the watch frame for that channel with cursor = message.position.

        When no message arrives within ``stale_timeout`` seconds, re-sends all
        watch frames on the existing connection to re-register as watchers.
        If re-registration also times out, raises ``ConnectionError`` to
        trigger reconnect in the caller.

        Parameters
        ----------
        channels:
            Mapping of channel name to cursor position.
        count:
            Maximum number of messages to yield before returning. When
            ``count > 0``, the generator yields at most *count* messages
            then returns. When ``count == 0``, it streams indefinitely
            (backwards-compatible with the original behavior).
        auto_ack:
            When ``True`` (default), re-sends the watch frame with the
            updated cursor after yielding each message. When ``False``,
            skips the re-send so the server will re-deliver the same
            message on reconnect until the consumer manually acks.
        stale_timeout:
            Seconds to wait for a message before re-registering all watch
            frames on the existing connection. Default 300 (5 minutes).
            Set to ``0`` to disable stale detection.

        Yields dicts with keys: channel, position, body, sent_at.
        """
        # Track current cursors (updated as messages are delivered)
        cursors = dict(channels)

        # Send initial watch frames for all channels
        async def _send_all_watch_frames() -> None:
            for channel, cursor in cursors.items():
                if channel not in active_channels:
                    continue
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
        reregister_count = 0

        await _send_all_watch_frames()

        # Receive loop: yield messages as they arrive from any channel
        while active_channels:
            try:
                if stale_timeout > 0:
                    raw = await asyncio.wait_for(
                        self._ws.recv(), timeout=stale_timeout
                    )
                else:
                    raw = await self._ws.recv()
            except asyncio.TimeoutError:
                reregister_count += 1
                if reregister_count > 1:
                    logger.warning(
                        "Watch stale after %d re-registrations, forcing "
                        "reconnect channels=%s",
                        reregister_count,
                        list(active_channels),
                    )
                    raise StaleWatchError("Watch connection stale")
                logger.info(
                    "Watch re-registering: no message in %ds, channels=%s",
                    stale_timeout,
                    list(active_channels),
                )
                await _send_all_watch_frames()
                continue

            response = json.loads(raw)
            # Reset re-registration counter on any successful recv
            reregister_count = 0

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

            # Update tracked cursor for this channel
            cursors[channel] = position

            # Track delivered count and exit if limit reached
            delivered += 1
            if count > 0 and delivered >= count:
                return

            # Re-send watch frame for this channel with updated cursor
            # Chunk: docs/chunks/watchmulti_manual_ack - Skip re-send when auto_ack=False
            if auto_ack and channel in active_channels:
                frame = {
                    "type": "watch",
                    "channel": channel,
                    "swarm": self.swarm_id,
                    "cursor": position,
                }
                await self._ws.send(json.dumps(frame))

    # Chunk: docs/chunks/multichannel_watch - Reconnect wrapper for multi-channel watch
    # Chunk: docs/chunks/watchmulti_exit_on_message - Count-limited reconnect wrapper
    # Chunk: docs/chunks/watchmulti_manual_ack - Manual ack mode
    # Chunk: docs/chunks/board_watch_stale_reconnect - Stale connection detection via re-registration
    # Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnects exempt from budget
    async def watch_multi_with_reconnect(
        self,
        channels: dict[str, int],
        max_retries: int | None = 10,
        count: int = 1,
        auto_ack: bool = True,
        stale_timeout: float = 300,
    ) -> AsyncGenerator[dict, None]:
        """Watch multiple channels with automatic reconnect on connection failure.

        On disconnect, reconnects with exponential backoff and re-sends all
        watch frames with their latest known cursors.

        Parameters
        ----------
        channels:
            Initial mapping of channel name to cursor position.
        max_retries:
            Maximum reconnect attempts. ``None`` means unlimited. Default 10.
        count:
            Maximum total messages to yield across all reconnects. When
            ``count > 0``, the generator yields at most *count* messages
            then returns. When ``count == 0``, it streams indefinitely.
        auto_ack:
            When ``True`` (default), the inner ``watch_multi`` re-sends
            watch frames with updated cursors after each message. When
            ``False``, skips cursor advancement for manual acking.
        stale_timeout:
            Seconds to wait for a message before re-registering watch
            frames. Passed through to ``watch_multi``. Default 300.

        Yields dicts with keys: channel, position, body, sent_at.
        """
        # Track latest cursors across reconnects
        cursors = dict(channels)
        attempt = 0
        backoff = 1.0
        max_backoff = 60.0
        delivered = 0
        idle_reconnects = 0
        current_stale_timeout = stale_timeout

        while True:
            try:
                # Inner watch_multi streams indefinitely (count=0); the
                # reconnect wrapper manages the overall message cap so that
                # reconnects don't reset the count.
                async for msg in self.watch_multi(
                    cursors, count=0, auto_ack=auto_ack, stale_timeout=current_stale_timeout
                ):
                    # Update cursor for the channel that delivered a message
                    cursors[msg["channel"]] = msg["position"]
                    # Reset backoff and idle tracking on successful message receipt
                    attempt = 0
                    backoff = 1.0
                    idle_reconnects = 0
                    current_stale_timeout = stale_timeout
                    yield msg
                    delivered += 1
                    if count > 0 and delivered >= count:
                        return
                # Generator exhausted (all channels errored) — stop
                return
            except StaleWatchError:
                # Idle timeout — reconnect without counting against the failure budget.
                idle_reconnects += 1
                if idle_reconnects >= 3:
                    current_stale_timeout = min(current_stale_timeout * 2, 600.0)
                    logger.info(
                        "Idle reconnect #%d, increasing stale_timeout to %.0fs channels=%s",
                        idle_reconnects, current_stale_timeout, list(cursors),
                    )
                logger.info(
                    "Idle reconnect (not counted against budget) channels=%s", list(cursors)
                )
                try:
                    await self.close()
                except Exception:
                    pass
                await self.connect()
                backoff = 1.0
            # Chunk: docs/chunks/board_watch_handshake_retry - Widen exception tuple to catch handshake errors
            except _RETRYABLE_ERRORS:
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

                # Chunk: docs/chunks/board_watch_handshake_retry - Retry connect() on handshake errors
                while True:
                    try:
                        await self.close()
                    except Exception:
                        pass
                    try:
                        await self.connect()
                        break  # Connected successfully
                    except _RETRYABLE_ERRORS as connect_exc:
                        attempt += 1
                        if max_retries is not None and attempt > max_retries:
                            raise connect_exc
                        jitter = random.uniform(0, backoff * 0.5)
                        wait_time = min(backoff + jitter, max_backoff)
                        logger.warning(
                            "Handshake failed during reconnect in %.1fs "
                            "(attempt %d) exc=%s",
                            wait_time,
                            attempt,
                            type(connect_exc).__name__,
                        )
                        await asyncio.sleep(wait_time)
                        backoff = min(backoff * 2, max_backoff)
                # Chunk: docs/chunks/board_watch_reconnect_delivery - Log re-poll after reconnect
                logger.info(
                    "Reconnected, re-polling %d channel(s) from cursors=%s",
                    len(cursors),
                    cursors,
                )
                # Chunk: docs/chunks/board_watch_reconnect_fix - Explicit re-subscription log
                logger.info(
                    "Re-subscribing to %d channel(s) after reconnect, cursors=%s",
                    len(cursors),
                    cursors,
                )
                backoff = 1.0
                # Chunk: docs/chunks/watch_reconnect_counter_reset - Reset attempt counter after successful reconnect
                attempt = 0

    # Chunk: docs/chunks/board_channel_delete - Delete a channel and all its messages
    async def delete_channel(self, channel: str) -> None:
        """Delete a channel and all its messages.

        Raises BoardError with code 'channel_not_found' if the channel
        does not exist.
        """
        frame = {
            "type": "delete_channel",
            "channel": channel,
            "swarm": self.swarm_id,
        }
        await self._ws.send(json.dumps(frame))

        response = json.loads(await self._ws.recv())
        self._check_error(response)
        if response.get("type") != "channel_deleted":
            raise BoardError(
                "protocol_error",
                f"Expected channel_deleted, got {response.get('type')}",
            )

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
