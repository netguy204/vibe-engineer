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
