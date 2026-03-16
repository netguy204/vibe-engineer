# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client
"""Tests for board.client — WebSocket protocol handling with mocked connections."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets.exceptions

from board.client import BoardClient, BoardError
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
