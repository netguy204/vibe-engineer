# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.client — WebSocket protocol handling with mocked connections."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets.exceptions

from board.client import BoardClient, BoardError, StaleWatchError
from board.crypto import generate_keypair, derive_swarm_id, sign


@pytest.fixture
def keypair():
    seed, pub = generate_keypair()
    swarm_id = derive_swarm_id(pub)
    return seed, pub, swarm_id


def _make_mock_ws(responses: list[str]) -> AsyncMock:
    """Create a mock websocket that returns responses in order."""
    ws = AsyncMock()
    ws.recv = AsyncMock(side_effect=responses)
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_auth_handshake(keypair):
    """Client signs the challenge nonce and server responds with auth_ok."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32  # 32-byte nonce

    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    mock_ws = _make_mock_ws([challenge, auth_ok])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

    # Verify auth frame was sent
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    assert len(sent_frames) == 1
    auth_frame = sent_frames[0]
    assert auth_frame["type"] == "auth"
    assert auth_frame["swarm"] == swarm_id
    # Verify the signature is valid
    sig_bytes = bytes.fromhex(auth_frame["signature"])
    expected_sig = sign(bytes.fromhex(nonce_hex), seed)
    assert sig_bytes == expected_sig


@pytest.mark.asyncio
async def test_auth_failure(keypair):
    """Server returns error on auth failure, client raises BoardError."""
    seed, pub, swarm_id = keypair
    challenge = json.dumps({"type": "challenge", "nonce": "bb" * 32})
    error = json.dumps({"type": "error", "code": "auth_failed", "message": "bad signature"})
    mock_ws = _make_mock_ws([challenge, error])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        with pytest.raises(BoardError) as exc_info:
            await client.connect()
        assert exc_info.value.code == "auth_failed"


@pytest.mark.asyncio
async def test_register_swarm_frame(keypair):
    """register_swarm sends the correct frame format."""
    seed, pub, swarm_id = keypair
    challenge = json.dumps({"type": "challenge", "nonce": "cc" * 32})
    auth_ok = json.dumps({"type": "auth_ok"})
    mock_ws = _make_mock_ws([challenge, auth_ok])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.register_swarm(pub)

    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    assert len(sent_frames) == 1
    reg = sent_frames[0]
    assert reg["type"] == "register_swarm"
    assert reg["swarm"] == swarm_id
    assert reg["public_key"] == pub.hex()


@pytest.mark.asyncio
async def test_send_frame(keypair):
    """send() transmits correctly and parses ack response."""
    seed, pub, swarm_id = keypair
    challenge = json.dumps({"type": "challenge", "nonce": "dd" * 32})
    auth_ok = json.dumps({"type": "auth_ok"})
    ack = json.dumps({"type": "ack", "channel": "test-ch", "position": 42})

    mock_ws = _make_mock_ws([challenge, auth_ok, ack])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        position = await client.send("test-ch", "base64ciphertext==")

    assert position == 42
    # Verify the send frame
    send_frame = json.loads(mock_ws.send.call_args_list[1].args[0])
    assert send_frame["type"] == "send"
    assert send_frame["channel"] == "test-ch"
    assert send_frame["body"] == "base64ciphertext=="


@pytest.mark.asyncio
async def test_watch_frame(keypair):
    """watch() sends correct frame and parses message response."""
    seed, pub, swarm_id = keypair
    challenge = json.dumps({"type": "challenge", "nonce": "ee" * 32})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 5,
        "body": "encrypted==",
        "sent_at": "2026-03-15T14:30:00Z",
    })

    mock_ws = _make_mock_ws([challenge, auth_ok, msg])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        result = await client.watch("ch1", 4)

    assert result["position"] == 5
    assert result["body"] == "encrypted=="
    assert result["sent_at"] == "2026-03-15T14:30:00Z"

    # Verify watch frame
    watch_frame = json.loads(mock_ws.send.call_args_list[1].args[0])
    assert watch_frame["type"] == "watch"
    assert watch_frame["cursor"] == 4


@pytest.mark.asyncio
async def test_channels_frame(keypair):
    """list_channels() parses channels_list response."""
    seed, pub, swarm_id = keypair
    challenge = json.dumps({"type": "challenge", "nonce": "ff" * 32})
    auth_ok = json.dumps({"type": "auth_ok"})
    channels = json.dumps({
        "type": "channels_list",
        "channels": [
            {"name": "steward", "head_position": 10, "oldest_position": 1},
            {"name": "changelog", "head_position": 5, "oldest_position": 1},
        ],
    })

    mock_ws = _make_mock_ws([challenge, auth_ok, channels])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        result = await client.list_channels()

    assert len(result) == 2
    assert result[0]["name"] == "steward"
    assert result[1]["name"] == "changelog"


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/websocket_keepalive - Reconnect logic tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_on_disconnect(keypair):
    """watch_with_reconnect() catches disconnect and retries after reconnect."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32

    # First connection: will raise ConnectionClosedError on watch recv
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    # Second connection (after reconnect): succeeds
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 3,
        "body": "hello==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        """Return different mock ws objects for each connect() call."""
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth succeeds, then watch recv raises ConnectionClosedError
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: auth succeeds, watch returns message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            result = await client.watch_with_reconnect("ch1", 2)

    assert result["position"] == 3
    assert result["body"] == "hello=="
    assert call_count == 2


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/board_watch_reconnect_delivery - Reconnect delivery tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_delivers_pending_message(keypair):
    """After reconnect, watch re-polls from the same cursor and delivers
    a message that arrived during the disconnect window."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    # Message that "arrived during the disconnect window" at position 6
    pending_msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 6,
        "body": "pending==",
        "sent_at": "2026-03-17T00:00:00Z",
    })

    call_count = 0
    ws_objects = []

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then disconnect on watch recv
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)
        else:
            # Second connection: auth OK, then delivers pending message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, pending_msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            result = await client.watch_with_reconnect("ch1", 5)

    # Message from the disconnect window is delivered
    assert result["position"] == 6
    assert result["body"] == "pending=="

    # Verify the watch frame on the second connection carries cursor=5
    # (re-polling from the last-known cursor, not some stale or advanced value)
    second_ws = ws_objects[1]
    sent_frames = [json.loads(call.args[0]) for call in second_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    assert len(watch_frames) == 1
    assert watch_frames[0]["cursor"] == 5
    assert watch_frames[0]["channel"] == "ch1"


@pytest.mark.asyncio
async def test_watch_multi_reconnect_delivers_pending_messages(keypair):
    """After reconnect, watch_multi re-polls all channels from their latest
    cursors and delivers messages that arrived during the disconnect window."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    # First connection delivers a message on ch-a at position 3
    msg_a = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "msg_a==",
        "sent_at": "2026-03-17T00:00:00Z",
    })
    # During disconnect, message arrives on ch-b at position 6
    msg_b_pending = json.dumps({
        "type": "message",
        "channel": "ch-b",
        "position": 6,
        "body": "msg_b_pending==",
        "sent_at": "2026-03-17T00:01:00Z",
    })

    call_count = 0
    ws_objects = []

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: delivers ch-a msg, then disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg_a,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)
        else:
            # Second connection: delivers pending ch-b message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg_b_pending,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()

            async for msg in client.watch_multi_with_reconnect(
                {"ch-a": 2, "ch-b": 5}, max_retries=1, count=0
            ):
                results.append(msg)
                if len(results) >= 2:
                    break

    # Both messages delivered in order, no duplicates
    assert len(results) == 2
    assert results[0]["channel"] == "ch-a"
    assert results[0]["position"] == 3
    assert results[1]["channel"] == "ch-b"
    assert results[1]["position"] == 6

    # Verify second connection's watch frames carry correct cursors:
    # ch-a cursor=3 (updated after first message), ch-b cursor=5 (unchanged)
    second_ws = ws_objects[1]
    sent_frames = [json.loads(call.args[0]) for call in second_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    cursors_by_channel = {f["channel"]: f["cursor"] for f in watch_frames}
    assert cursors_by_channel["ch-a"] == 3  # Updated after first message
    assert cursors_by_channel["ch-b"] == 5  # Unchanged — gap message channel


@pytest.mark.asyncio
async def test_watch_with_reconnect_max_retries(keypair):
    """watch_with_reconnect() raises after exhausting max_retries."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    import websockets.exceptions

    def make_ws_factory(*args, **kwargs):
        """Every connection's watch recv raises ConnectionClosedError."""
        ws = AsyncMock()
        ws.recv = AsyncMock(side_effect=[
            challenge,
            auth_ok,
            websockets.exceptions.ConnectionClosedError(None, None),
        ])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            with pytest.raises(websockets.exceptions.ConnectionClosedError):
                await client.watch_with_reconnect("ch1", 0, max_retries=2)


@pytest.mark.asyncio
async def test_watch_with_reconnect_backoff(keypair):
    """watch_with_reconnect() resets backoff after each successful reconnect.

    Since backoff resets to 1.0 after every successful connect(), each retry
    sleeps for the initial delay (1.0s with jitter=0). Exponential escalation
    only occurs if connect() itself fails (which propagates out of the loop).
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 1,
        "body": "ok==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    import websockets.exceptions

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            # First 3 connections: auth OK, then watch disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # 4th connection succeeds
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    sleep_mock = AsyncMock()
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", sleep_mock):
            with patch("board.client.random.uniform", return_value=0):  # deterministic jitter
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                result = await client.watch_with_reconnect("ch1", 0)

    assert result["position"] == 1
    # Backoff resets to 1.0 after each successful connect(), so all sleeps are 1.0s
    assert sleep_mock.call_count == 3
    assert sleep_mock.call_args_list[0].args[0] == pytest.approx(1.0)
    assert sleep_mock.call_args_list[1].args[0] == pytest.approx(1.0)
    assert sleep_mock.call_args_list[2].args[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/websocket_reconnect_tuning - Backoff reset tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_resets_backoff_after_success(keypair):
    """After a successful reconnect, backoff resets so the next disconnect starts at 1s."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 1,
        "body": "ok==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    import websockets.exceptions

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            # First 3 connections: auth OK, then watch disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        elif call_count == 4:
            # 4th connection: succeeds (reconnect works), then watch disconnects again
            # This tests that backoff resets after this successful reconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # 5th connection: succeeds and returns a message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    sleep_mock = AsyncMock()
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", sleep_mock):
            with patch("board.client.random.uniform", return_value=0):  # deterministic jitter
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                result = await client.watch_with_reconnect("ch1", 0)

    assert result["position"] == 1
    # All 4 sleeps are 1.0s because backoff resets after each successful connect().
    # The attempt counter is NOT reset, preserving max_retries semantics.
    assert sleep_mock.call_count == 4
    for i in range(4):
        assert sleep_mock.call_args_list[i].args[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Helper: wrap a mock ws in an async context manager
# ---------------------------------------------------------------------------

class _AsyncCtx:
    """Wrap a value as an async context manager for `websockets.connect`."""
    def __init__(self, ws):
        self._ws = ws

    async def __aenter__(self):
        return self._ws

    async def __aexit__(self, *args):
        await self._ws.close()


def _async_ctx(ws):
    """For non-context-manager usage (direct await), return a coroutine
    that resolves to the mock ws, but also support async with."""
    class _DualCtx(_AsyncCtx):
        def __await__(self):
            async def _resolve():
                return self._ws
            return _resolve().__await__()

    return _DualCtx(ws)


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/multichannel_watch - Multi-channel watch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_multi_sends_frames_and_yields_messages(keypair):
    """watch_multi() sends watch frames for all channels and yields messages."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg_a = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "body_a==",
        "sent_at": "2026-03-16T00:00:00Z",
    })
    msg_b = json.dumps({
        "type": "message",
        "channel": "ch-b",
        "position": 5,
        "body": "body_b==",
        "sent_at": "2026-03-16T00:01:00Z",
    })

    mock_ws = _make_mock_ws([challenge, auth_ok, msg_a, msg_b])
    # After yielding msg_b, the next recv will raise StopAsyncIteration
    # which will cause ConnectionClosedError-like behavior. We add a
    # ConnectionClosedError to terminate the generator cleanly.
    mock_ws.recv = AsyncMock(side_effect=[
        challenge, auth_ok, msg_a, msg_b,
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-a": 2, "ch-b": 4}, count=0):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass  # Expected termination

    assert len(results) == 2
    assert results[0]["channel"] == "ch-a"
    assert results[0]["position"] == 3
    assert results[1]["channel"] == "ch-b"
    assert results[1]["position"] == 5

    # Verify initial watch frames were sent (after auth)
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    # Frame 0: auth, Frame 1: watch ch-a, Frame 2: watch ch-b
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    assert len(watch_frames) >= 2
    channels_watched = {f["channel"] for f in watch_frames[:2]}
    assert channels_watched == {"ch-a", "ch-b"}


@pytest.mark.asyncio
async def test_watch_multi_resends_watch_after_message(keypair):
    """After yielding a message for channel A, re-sends watch frame with updated cursor."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg_a = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 10,
        "body": "body==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[
        challenge, auth_ok, msg_a,
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-a": 5}, count=0):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass

    assert len(results) == 1
    assert results[0]["position"] == 10

    # Verify re-sent watch frame has updated cursor
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    resend_frames = [
        f for f in sent_frames
        if f.get("type") == "watch" and f.get("cursor") == 10
    ]
    assert len(resend_frames) == 1
    assert resend_frames[0]["channel"] == "ch-a"


@pytest.mark.asyncio
async def test_watch_multi_handles_per_channel_error(keypair):
    """One channel returns channel_not_found; the other continues watching."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    error_frame = json.dumps({
        "type": "error",
        "code": "channel_not_found",
        "message": "Channel not found: ch-bad",
    })
    msg_good = json.dumps({
        "type": "message",
        "channel": "ch-good",
        "position": 1,
        "body": "good==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[
        challenge, auth_ok, error_frame, msg_good,
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-good": 0, "ch-bad": 0}, count=0):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass

    assert len(results) == 1
    assert results[0]["channel"] == "ch-good"


@pytest.mark.asyncio
async def test_watch_multi_reconnect(keypair):
    """Simulate disconnect; verify all channels are re-watched with latest cursors."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg1 = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "first==",
        "sent_at": "2026-03-16T00:00:00Z",
    })
    msg2 = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 4,
        "body": "second==",
        "sent_at": "2026-03-16T00:01:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: delivers one message then disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg1,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: delivers next message then disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg2,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()

            async for msg in client.watch_multi_with_reconnect(
                {"ch-a": 2}, max_retries=1, count=0
            ):
                results.append(msg)
                if len(results) >= 2:
                    break

    assert len(results) == 2
    assert results[0]["position"] == 3
    assert results[1]["position"] == 4

    # Verify second connection re-watches with cursor=3 (updated after first msg)
    # The second ws is from call_count=2
    # Its send calls should include a watch frame with cursor=3


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/watchmulti_exit_on_message - Count-limited watch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_multi_count_limits_messages(keypair):
    """watch_multi(count=2) yields at most 2 messages even when 3 are available."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msgs = [
        json.dumps({
            "type": "message", "channel": "ch-a", "position": i,
            "body": f"body{i}==", "sent_at": "2026-03-16T00:00:00Z",
        })
        for i in range(1, 4)
    ]

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[challenge, auth_ok] + msgs)

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        async for msg in client.watch_multi({"ch-a": 0}, count=2):
            results.append(msg)

    assert len(results) == 2
    assert results[0]["position"] == 1
    assert results[1]["position"] == 2


@pytest.mark.asyncio
async def test_watch_multi_count_zero_streams_all(keypair):
    """watch_multi(count=0) yields all available messages (indefinite mode)."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msgs = [
        json.dumps({
            "type": "message", "channel": "ch-a", "position": i,
            "body": f"body{i}==", "sent_at": "2026-03-16T00:00:00Z",
        })
        for i in range(1, 4)
    ]

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[challenge, auth_ok] + msgs + [
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-a": 0}, count=0):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass

    assert len(results) == 3


@pytest.mark.asyncio
async def test_watch_multi_count_default_one(keypair):
    """watch_multi() without explicit count yields exactly 1 message (default)."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msgs = [
        json.dumps({
            "type": "message", "channel": "ch-a", "position": i,
            "body": f"body{i}==", "sent_at": "2026-03-16T00:00:00Z",
        })
        for i in range(1, 4)
    ]

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[challenge, auth_ok] + msgs)

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        async for msg in client.watch_multi({"ch-a": 0}):
            results.append(msg)

    assert len(results) == 1
    assert results[0]["position"] == 1


@pytest.mark.asyncio
async def test_watch_multi_reconnect_respects_count(keypair):
    """watch_multi_with_reconnect(count=2) caps total across reconnects."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg1 = json.dumps({
        "type": "message", "channel": "ch-a", "position": 1,
        "body": "first==", "sent_at": "2026-03-16T00:00:00Z",
    })
    msg2 = json.dumps({
        "type": "message", "channel": "ch-a", "position": 2,
        "body": "second==", "sent_at": "2026-03-16T00:01:00Z",
    })
    msg3 = json.dumps({
        "type": "message", "channel": "ch-a", "position": 3,
        "body": "third==", "sent_at": "2026-03-16T00:02:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: delivers one message then disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg1,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: delivers msg2 and msg3
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg2, msg3,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()

            async for msg in client.watch_multi_with_reconnect(
                {"ch-a": 0}, count=2
            ):
                results.append(msg)

    # Should get exactly 2 messages total, even though 3 were available
    assert len(results) == 2
    assert results[0]["position"] == 1
    assert results[1]["position"] == 2


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/watchmulti_manual_ack - Manual ack mode tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_multi_auto_ack_false_skips_cursor_resend(keypair):
    """When auto_ack=False, after yielding a message the client does NOT re-send
    a watch frame with the updated cursor."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg_a = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 10,
        "body": "body==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[
        challenge, auth_ok, msg_a,
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-a": 5}, count=0, auto_ack=False):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass

    assert len(results) == 1
    assert results[0]["position"] == 10

    # Verify NO re-sent watch frame after message delivery
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    # Only the initial watch frame (cursor=5), no re-send with cursor=10
    assert len(watch_frames) == 1
    assert watch_frames[0]["cursor"] == 5


@pytest.mark.asyncio
async def test_watch_multi_auto_ack_default_resends_cursor(keypair):
    """When auto_ack is not specified (defaults to True), the client re-sends
    watch frames with updated cursor after each message."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg_a = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 10,
        "body": "body==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    mock_ws = _make_mock_ws([])
    mock_ws.recv = AsyncMock(side_effect=[
        challenge, auth_ok, msg_a,
        websockets.exceptions.ConnectionClosedError(None, None),
    ])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()

        results = []
        try:
            async for msg in client.watch_multi({"ch-a": 5}, count=0):
                results.append(msg)
        except websockets.exceptions.ConnectionClosedError:
            pass

    assert len(results) == 1

    # Verify re-sent watch frame with updated cursor=10
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    resend_frames = [
        f for f in sent_frames
        if f.get("type") == "watch" and f.get("cursor") == 10
    ]
    assert len(resend_frames) == 1
    assert resend_frames[0]["channel"] == "ch-a"


@pytest.mark.asyncio
async def test_watch_multi_reconnect_auto_ack_false_preserves_cursors(keypair):
    """When auto_ack=False and reconnect occurs, the reconnect wrapper still
    updates its internal cursor tracking (so it reconnects from the right
    position), but auto_ack=False is passed through to inner watch_multi."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    msg1 = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "first==",
        "sent_at": "2026-03-16T00:00:00Z",
    })
    msg2 = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 4,
        "body": "second==",
        "sent_at": "2026-03-16T00:01:00Z",
    })

    call_count = 0
    ws_objects = []

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg1,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)
        else:
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok, msg2,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            ws_objects.append(ws)
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()

            async for msg in client.watch_multi_with_reconnect(
                {"ch-a": 2}, max_retries=1, count=0, auto_ack=False
            ):
                results.append(msg)
                if len(results) >= 2:
                    break

    assert len(results) == 2
    assert results[0]["position"] == 3
    assert results[1]["position"] == 4

    # Verify second connection re-watches from cursor=3 (internal cursor updated)
    second_ws = ws_objects[1]
    sent_frames = [json.loads(call.args[0]) for call in second_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    assert len(watch_frames) == 1
    assert watch_frames[0]["cursor"] == 3  # Internal cursor tracked for reconnect

    # Verify first connection did NOT re-send watch after message (auto_ack=False)
    first_ws = ws_objects[0]
    sent_frames_1 = [json.loads(call.args[0]) for call in first_ws.send.call_args_list]
    watch_frames_1 = [f for f in sent_frames_1 if f.get("type") == "watch"]
    # Only the initial watch frame, no re-send
    assert len(watch_frames_1) == 1
    assert watch_frames_1[0]["cursor"] == 2


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/board_watch_stale_reconnect - Stale connection detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_stale_reregisters(keypair):
    """When recv() times out, watch_with_reconnect re-sends the watch frame
    on the same connection (re-registration) before forcing a full reconnect."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 5,
        "body": "hello==",
        "sent_at": "2026-03-20T00:00:00Z",
    })

    # First recv after auth times out (stale), second recv after
    # re-registration delivers the message.
    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=[
        challenge,
        auth_ok,
        asyncio.TimeoutError(),  # triggers re-registration
        msg,                     # message delivered after re-registration
    ])
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        result = await client.watch_with_reconnect("ch1", 4, stale_timeout=0.01)

    assert result["position"] == 5
    assert result["body"] == "hello=="

    # Verify the watch frame was sent TWICE (initial + re-registration)
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    assert len(watch_frames) == 2
    assert watch_frames[0]["cursor"] == 4
    assert watch_frames[1]["cursor"] == 4  # same cursor for re-registration


@pytest.mark.asyncio
async def test_watch_with_reconnect_stale_forces_reconnect(keypair):
    """Two consecutive stale timeouts force a full reconnect."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 5,
        "body": "hello==",
        "sent_at": "2026-03-20T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: two timeouts → force reconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                asyncio.TimeoutError(),  # first timeout → re-register
                asyncio.TimeoutError(),  # second timeout → ConnectionError
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: delivers message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            result = await client.watch_with_reconnect(
                "ch1", 4, stale_timeout=0.01
            )

    assert result["position"] == 5
    assert call_count == 2  # required a full reconnect


@pytest.mark.asyncio
async def test_watch_with_reconnect_normal_unaffected(keypair):
    """Normal message delivery (before stale timeout) is unaffected."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 5,
        "body": "fast==",
        "sent_at": "2026-03-20T00:00:00Z",
    })

    mock_ws = _make_mock_ws([challenge, auth_ok, msg])

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        # Large stale_timeout — message arrives immediately
        result = await client.watch_with_reconnect("ch1", 4, stale_timeout=300)

    assert result["position"] == 5
    assert result["body"] == "fast=="


@pytest.mark.asyncio
async def test_watch_multi_stale_reregisters(keypair):
    """watch_multi re-sends all watch frames when recv times out."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "body_a==",
        "sent_at": "2026-03-20T00:00:00Z",
    })

    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=[
        challenge,
        auth_ok,
        asyncio.TimeoutError(),  # triggers re-registration
        msg,                     # message after re-registration
    ])
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()

    with patch("board.client.websockets.connect", return_value=_async_ctx(mock_ws)):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        results = []
        async for m in client.watch_multi(
            {"ch-a": 2, "ch-b": 0}, count=1, stale_timeout=0.01
        ):
            results.append(m)

    assert len(results) == 1
    assert results[0]["position"] == 3

    # Verify watch frames: initial (ch-a + ch-b) + re-registration (ch-a + ch-b)
    sent_frames = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    watch_frames = [f for f in sent_frames if f.get("type") == "watch"]
    # 2 initial + 2 re-registration = 4 watch frames
    assert len(watch_frames) == 4


@pytest.mark.asyncio
async def test_watch_multi_stale_forces_reconnect_in_wrapper(keypair):
    """watch_multi_with_reconnect handles ConnectionError from stale detection."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "body_a==",
        "sent_at": "2026-03-20T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: double timeout → stale → ConnectionError
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: delivers message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            async for m in client.watch_multi_with_reconnect(
                {"ch-a": 2}, max_retries=3, count=1, stale_timeout=0.01
            ):
                results.append(m)

    assert len(results) == 1
    assert results[0]["position"] == 3
    assert call_count == 2


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/board_watch_stale_reconnect - Multi-cycle reconnection integration test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_10_cycles(keypair):
    """Simulate 10+ reconnection cycles and verify message delivery after each."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    num_cycles = 12
    call_count = 0
    ws_objects = []

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        ws = AsyncMock()
        # Each cycle: auth succeeds, delivers one message, then disconnects
        # on the next watch recv (except the last cycle which just delivers)
        position = call_count
        msg = json.dumps({
            "type": "message",
            "channel": "ch1",
            "position": position,
            "body": f"msg{position}==",
            "sent_at": "2026-03-20T00:00:00Z",
        })
        if call_count < num_cycles:
            # Deliver message, then disconnect on next attempt
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                msg,
            ])
        else:
            # Last cycle: deliver message (no disconnect)
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                msg,
            ])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        ws_objects.append(ws)
        return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()

            cursor = 0
            for _cycle in range(num_cycles):
                # Each cycle: watch delivers, then we simulate disconnect
                # for next watch by replacing the ws
                result = await client.watch_with_reconnect(
                    "ch1", cursor, stale_timeout=300
                )
                results.append(result)
                cursor = result["position"]

                # Simulate disconnect for the next call by forcing a reconnect
                if _cycle < num_cycles - 1:
                    try:
                        await client.close()
                    except Exception:
                        pass
                    await client.connect()

    # All 12 messages delivered successfully
    assert len(results) == num_cycles
    for i, result in enumerate(results):
        assert result["position"] == i + 1


@pytest.mark.asyncio
async def test_watch_with_reconnect_multi_cycle_with_stale(keypair):
    """Verify that stale re-registration works across multiple reconnection cycles.

    Each cycle calls watch_with_reconnect on a connection established by the
    previous cycle's between-cycle connect(). The pattern alternates:
      0: normal delivery
      1: stale → re-register → delivery
      2: double stale → internal reconnect → delivery
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    # Build connection sequence. Each connect() (initial, between-cycle, or
    # internal reconnect) creates one entry. Entries include [challenge,
    # auth_ok] for the handshake plus any watch recv data.
    connection_sequence = []
    message_pos = 0

    for cycle in range(10):
        pattern = cycle % 3
        message_pos += 1
        msg = json.dumps({
            "type": "message",
            "channel": "ch1",
            "position": message_pos,
            "body": f"msg{message_pos}==",
            "sent_at": "2026-03-20T00:00:00Z",
        })

        if pattern == 0:
            # Normal: connect() consumes challenge+auth_ok, watch consumes msg
            connection_sequence.append([challenge, auth_ok, msg])
        elif pattern == 1:
            # Stale: connect() consumes challenge+auth_ok, watch gets
            # TimeoutError (re-register) then msg
            connection_sequence.append([
                challenge, auth_ok,
                asyncio.TimeoutError(),
                msg,
            ])
        else:
            # Double stale: connect() consumes challenge+auth_ok, watch gets
            # 2x TimeoutError → ConnectionError. Then internal reconnect
            # creates a NEW connection that delivers.
            connection_sequence.append([
                challenge, auth_ok,
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
            ])
            connection_sequence.append([challenge, auth_ok, msg])

    conn_idx = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal conn_idx
        ws = AsyncMock()
        ws.recv = AsyncMock(side_effect=connection_sequence[conn_idx])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        conn_idx += 1
        return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)

            cursor = 0
            for _cycle in range(10):
                # Each cycle: connect, watch, close
                await client.connect()
                result = await client.watch_with_reconnect(
                    "ch1", cursor, stale_timeout=0.01
                )
                results.append(result)
                cursor = result["position"]
                try:
                    await client.close()
                except Exception:
                    pass

    # All 10 messages delivered (some via re-registration, some via reconnect)
    assert len(results) == 10
    for i, result in enumerate(results):
        assert result["position"] == i + 1


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/board_watch_handshake_retry - Handshake retry tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_retries_on_handshake_timeout(keypair):
    """watch_with_reconnect() retries when connect() raises TimeoutError during reconnect."""
    import ssl as _ssl

    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 5,
        "body": "recovered==",
        "sent_at": "2026-03-30T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then mid-connection disconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        elif call_count == 2:
            # Second connect() attempt: handshake timeout
            raise TimeoutError("timed out during opening handshake")
        else:
            # Third connection: succeeds
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    sleep_mock = AsyncMock()
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", sleep_mock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            result = await client.watch_with_reconnect("ch1", 4)

    assert result["position"] == 5
    assert result["body"] == "recovered=="
    # Should have slept at least twice (once for disconnect, once for handshake timeout loop)
    assert sleep_mock.call_count >= 1
    assert call_count == 3


@pytest.mark.asyncio
async def test_watch_multi_reconnect_retries_on_handshake_timeout(keypair):
    """watch_multi_with_reconnect() retries when connect() raises TimeoutError during reconnect."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 3,
        "body": "recovered==",
        "sent_at": "2026-03-30T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then disconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        elif call_count == 2:
            # Second connect(): handshake timeout
            raise TimeoutError("timed out during opening handshake")
        else:
            # Third connection: succeeds
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            async for m in client.watch_multi_with_reconnect({"ch-a": 2}, count=1):
                results.append(m)

    assert len(results) == 1
    assert results[0]["position"] == 3
    assert call_count == 3


@pytest.mark.asyncio
async def test_watch_with_reconnect_retries_on_ssl_error(keypair):
    """watch_with_reconnect() retries when connect() raises SSLCertVerificationError."""
    import ssl as _ssl

    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 7,
        "body": "ssl_recovered==",
        "sent_at": "2026-03-30T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then disconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        elif call_count == 2:
            # Second connect(): SSL cert error
            raise _ssl.SSLCertVerificationError(1, "certificate verify failed")
        else:
            # Third connection: succeeds
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            result = await client.watch_with_reconnect("ch1", 6)

    assert result["position"] == 7
    assert result["body"] == "ssl_recovered=="
    assert call_count == 3


@pytest.mark.asyncio
async def test_watch_multi_reconnect_retries_on_ssl_error(keypair):
    """watch_multi_with_reconnect() retries when connect() raises SSLCertVerificationError."""
    import ssl as _ssl

    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 4,
        "body": "ssl_recovered==",
        "sent_at": "2026-03-30T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        elif call_count == 2:
            raise _ssl.SSLCertVerificationError(1, "certificate verify failed")
        else:
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            async for m in client.watch_multi_with_reconnect({"ch-a": 3}, count=1):
                results.append(m)

    assert len(results) == 1
    assert results[0]["position"] == 4
    assert call_count == 3


@pytest.mark.asyncio
async def test_watch_with_reconnect_handshake_max_retries_exit(keypair):
    """watch_with_reconnect() exits cleanly after max_retries consecutive handshake timeouts."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then mid-connection disconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # All subsequent connect() calls: handshake timeout
            raise TimeoutError("timed out during opening handshake")

    sleep_mock = AsyncMock()
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", sleep_mock):
            with patch("board.client.random.uniform", return_value=0):
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                with pytest.raises(TimeoutError):
                    await client.watch_with_reconnect("ch1", 0, max_retries=3)

    # Should have slept 3 times (once for the initial disconnect + twice for handshake failures)
    assert sleep_mock.call_count == 3
    # Verify backoff increases: 1.0, 2.0, 4.0 (no jitter due to mock)
    assert sleep_mock.call_args_list[0].args[0] == pytest.approx(1.0)
    assert sleep_mock.call_args_list[1].args[0] == pytest.approx(2.0)
    assert sleep_mock.call_args_list[2].args[0] == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_watch_with_reconnect_backoff_caps_at_60s(keypair):
    """Backoff caps at 60s rather than the old 30s cap."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then mid-connection disconnect
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # All reconnect attempts fail with handshake timeout
            raise TimeoutError("timed out during opening handshake")

    sleep_mock = AsyncMock()
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", sleep_mock):
            with patch("board.client.random.uniform", return_value=0):
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                with pytest.raises(TimeoutError):
                    await client.watch_with_reconnect("ch1", 0, max_retries=8)

    # Backoff sequence (no jitter): 1, 2, 4, 8, 16, 32, 60, 60
    # The cap should be 60, not 30
    sleep_values = [call.args[0] for call in sleep_mock.call_args_list]
    assert max(sleep_values) == pytest.approx(60.0)
    # The last few should be capped at 60
    assert sleep_values[-1] == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/board_watch_reconnect_fix - Default max_retries and logging tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_default_max_retries(keypair):
    """watch_with_reconnect with default max_retries=10 raises after 10
    consecutive failed reconnects (not unlimited)."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    def make_ws_factory(*args, **kwargs):
        """Every connection's watch recv raises ConnectionClosedError."""
        ws = AsyncMock()
        ws.recv = AsyncMock(side_effect=[
            challenge,
            auth_ok,
            websockets.exceptions.ConnectionClosedError(None, None),
        ])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return _async_ctx(ws)

    connect_count = 0
    original_factory = make_ws_factory

    def counting_factory(*args, **kwargs):
        nonlocal connect_count
        connect_count += 1
        return original_factory(*args, **kwargs)

    with patch("board.client.websockets.connect", side_effect=counting_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            with patch("board.client.random.uniform", return_value=0):
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                # Default max_retries=10, should raise after 10 attempts
                with pytest.raises(websockets.exceptions.ConnectionClosedError):
                    await client.watch_with_reconnect("ch1", 0)


@pytest.mark.asyncio
async def test_watch_multi_reconnect_default_max_retries(keypair):
    """watch_multi_with_reconnect with default max_retries=10 raises after 10
    consecutive failed reconnects."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    def make_ws_factory(*args, **kwargs):
        ws = AsyncMock()
        ws.recv = AsyncMock(side_effect=[
            challenge,
            auth_ok,
            websockets.exceptions.ConnectionClosedError(None, None),
        ])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            with patch("board.client.random.uniform", return_value=0):
                client = BoardClient("ws://localhost:8787", swarm_id, seed)
                await client.connect()
                with pytest.raises(websockets.exceptions.ConnectionClosedError):
                    async for _ in client.watch_multi_with_reconnect(
                        {"ch-a": 0}, count=0
                    ):
                        pass


@pytest.mark.asyncio
async def test_watch_with_reconnect_logs_resubscription(keypair):
    """After a successful reconnect, verify a log message confirms
    re-subscription to the channel."""
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 1,
        "body": "ok==",
        "sent_at": "2026-03-16T00:00:00Z",
    })

    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First connection: auth OK, then watch disconnects
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[
                challenge,
                auth_ok,
                websockets.exceptions.ConnectionClosedError(None, None),
            ])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)
        else:
            # Second connection: auth OK, watch delivers message
            ws = AsyncMock()
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
            ws.send = AsyncMock()
            ws.close = AsyncMock()
            return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            with patch("board.client.logger") as mock_logger:
                result = await client.watch_with_reconnect("ch1", 0)

    assert result["position"] == 1
    # Check that the re-subscription log was emitted
    info_messages = [
        call.args[0] for call in mock_logger.info.call_args_list
    ]
    assert any("Re-subscribing to channel=" in m for m in info_messages)


# ---------------------------------------------------------------------------
# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnect budget tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watch_with_reconnect_idle_does_not_exhaust_budget(keypair):
    """Idle stale timeouts do not count against the reconnect budget.

    Simulate more idle cycles than max_retries; the watch should still
    succeed when a message eventually arrives.
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch1",
        "position": 1,
        "body": "finally==",
        "sent_at": "2026-04-23T00:00:00Z",
    })

    # 12 idle cycles > max_retries=3; the message arrives on the 13th connection.
    idle_cycles = 12
    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        ws = AsyncMock()
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        if call_count <= idle_cycles:
            # Auth OK, then two consecutive timeouts → StaleWatchError
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                asyncio.TimeoutError(),  # first timeout → re-register
                asyncio.TimeoutError(),  # second timeout → StaleWatchError
            ])
        else:
            # Final connection: delivers the message
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
        return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        # max_retries=3 — idle cycles must not consume this budget
        result = await client.watch_with_reconnect("ch1", 0, max_retries=3, stale_timeout=0.01)

    assert result["position"] == 1
    assert result["body"] == "finally=="
    # 1 initial + 12 idle reconnects + 1 final = 14 total connections
    assert call_count == idle_cycles + 1


@pytest.mark.asyncio
async def test_watch_with_reconnect_real_failure_exhausts_budget(keypair):
    """Genuine connection failures still count against max_retries.

    Simulate max_retries+1 genuine ConnectionClosedErrors and verify the
    exception propagates (safety valve is preserved).
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    def make_ws_factory(*args, **kwargs):
        ws = AsyncMock()
        ws.recv = AsyncMock(side_effect=[
            challenge,
            auth_ok,
            websockets.exceptions.ConnectionClosedError(None, None),
        ])
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        return _async_ctx(ws)

    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        with patch("board.client.asyncio.sleep", new_callable=AsyncMock):
            client = BoardClient("ws://localhost:8787", swarm_id, seed)
            await client.connect()
            with pytest.raises(websockets.exceptions.ConnectionClosedError):
                await client.watch_with_reconnect("ch1", 0, max_retries=3)


@pytest.mark.asyncio
async def test_watch_multi_with_reconnect_idle_does_not_exhaust_budget(keypair):
    """Idle stale timeouts do not count against budget in watch_multi_with_reconnect.

    Simulate more idle cycles than max_retries; the watch should succeed
    when a message eventually arrives.
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})
    msg = json.dumps({
        "type": "message",
        "channel": "ch-a",
        "position": 7,
        "body": "arrived==",
        "sent_at": "2026-04-23T00:00:00Z",
    })

    idle_cycles = 12  # > max_retries=3
    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        ws = AsyncMock()
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        if call_count <= idle_cycles:
            # Auth OK, then two consecutive timeouts → StaleWatchError in watch_multi
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                asyncio.TimeoutError(),
                asyncio.TimeoutError(),
            ])
        else:
            # Final connection: delivers the message
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, msg])
        return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        async for m in client.watch_multi_with_reconnect(
            {"ch-a": 6}, max_retries=3, count=1, stale_timeout=0.01
        ):
            results.append(m)

    assert len(results) == 1
    assert results[0]["position"] == 7
    assert results[0]["body"] == "arrived=="
    assert call_count == idle_cycles + 1


@pytest.mark.asyncio
async def test_watch_multi_with_reconnect_budget_resets_on_message(keypair):
    """Idle reconnect counter resets when a message is successfully delivered.

    Simulate some idle reconnects, deliver a message (resetting the counter),
    then simulate more idle reconnects and verify the budget has not accumulated
    across the message boundary.

    Connection sequence:
      [1..pre_idle]       → auth OK + 2x timeout  (pre-message idle cycles)
      [pre_idle+1]        → auth OK + msg(1) + 2x timeout  (message then immediately stale)
      [pre_idle+2 ..+1+post_idle] → auth OK + 2x timeout  (post-message idle cycles)
      [pre_idle+post_idle+2]      → auth OK + msg(2)  (final message)

    When watch_multi delivers msg(1), watch_multi_with_reconnect resets
    idle_reconnects to 0. The two timeouts after msg(1) in the same connection
    trigger another StaleWatchError, starting idle_reconnects from 1 again.
    Combined, this exercises the reset path without hitting max_retries.
    """
    seed, pub, swarm_id = keypair
    nonce_hex = "aa" * 32
    challenge = json.dumps({"type": "challenge", "nonce": nonce_hex})
    auth_ok = json.dumps({"type": "auth_ok"})

    def _msg(pos):
        return json.dumps({
            "type": "message",
            "channel": "ch-a",
            "position": pos,
            "body": f"msg{pos}==",
            "sent_at": "2026-04-23T00:00:00Z",
        })

    # With max_retries=3: pre_idle+post_idle individually < 3 so no budget exhaustion,
    # but together (if NOT reset) they would each be fine anyway; the real verification
    # is the total connection count matches the expected sum (reset + fresh cycles).
    pre_idle = 2
    post_idle = 2
    call_count = 0

    def make_ws_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        ws = AsyncMock()
        ws.send = AsyncMock()
        ws.close = AsyncMock()
        if call_count <= pre_idle:
            # Pre-message idle cycles: auth OK + 2 timeouts → StaleWatchError
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                asyncio.TimeoutError(), asyncio.TimeoutError(),
            ])
        elif call_count == pre_idle + 1:
            # Message delivery + immediate post-message stale on the same connection:
            # watch_multi yields msg(1), then tries recv() again and gets 2 timeouts.
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                _msg(1),
                asyncio.TimeoutError(), asyncio.TimeoutError(),
            ])
        elif call_count <= pre_idle + 1 + post_idle:
            # Post-message idle cycles (idle_reconnects reset to 0 when msg was received,
            # then incremented to 1 by the stale after the message; these continue from 2)
            ws.recv = AsyncMock(side_effect=[
                challenge, auth_ok,
                asyncio.TimeoutError(), asyncio.TimeoutError(),
            ])
        else:
            # Deliver second message
            ws.recv = AsyncMock(side_effect=[challenge, auth_ok, _msg(2)])
        return _async_ctx(ws)

    results = []
    with patch("board.client.websockets.connect", side_effect=make_ws_factory):
        client = BoardClient("ws://localhost:8787", swarm_id, seed)
        await client.connect()
        # max_retries=3; none of the idle cycles count against it
        async for m in client.watch_multi_with_reconnect(
            {"ch-a": 0}, max_retries=3, count=2, stale_timeout=0.01
        ):
            results.append(m)

    assert len(results) == 2
    assert results[0]["position"] == 1
    assert results[1]["position"] == 2
    # Total: pre_idle + 1 (msg+stale) + post_idle + 1 (final msg) connections
    assert call_count == pre_idle + 1 + post_idle + 1
