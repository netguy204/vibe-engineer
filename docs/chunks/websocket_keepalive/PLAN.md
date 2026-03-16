

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Fix WebSocket idle disconnects by adding keepalive at both server and client layers, plus automatic reconnect on the client side.

**Strategy:** Use WebSocket protocol-level ping/pong frames for keepalive (not application-level heartbeat frames). This avoids protocol changes — both `websockets` (Python) and Cloudflare's DO API support native ping/pong. The client adds a reconnect-with-backoff wrapper around `watch()` to handle transient disconnects transparently.

Three layers of defense:
1. **Server heartbeat** — Both the local Starlette server and the Cloudflare DO send periodic WebSocket pings (every 30s) to prevent idle timeout eviction by proxies/infrastructure.
2. **Client ping configuration** — The `websockets.connect()` call is configured with `ping_interval` and `ping_timeout` so the client also detects dead connections proactively.
3. **Client reconnect loop** — `BoardClient.watch()` is wrapped with retry logic that catches `ConnectionClosedError`, reconnects, and re-subscribes from the current cursor position.

No wire protocol changes are needed — native WebSocket pings are transparent to the application-layer protocol.

## Sequence

### Step 1: Add server-side heartbeat to the local Starlette server

Add a periodic ping task to `websocket_handler()` in `src/leader_board/server.py`. When the connection enters the post-auth message loop, spawn a background `asyncio.Task` that sends a WebSocket ping every 30 seconds. Cancel it on disconnect.

The Starlette `WebSocket` object wraps an ASGI send scope — use `ws.send_bytes(b"")` with the raw ASGI scope to send pings, or more practically, rely on the fact that Uvicorn's WebSocket implementation supports keepalive. The simplest approach: send a lightweight application-level ping (a small JSON `{"type":"ping"}`) that the client can ignore, OR use the Starlette websocket's underlying `send` with ping opcode.

**Refined approach:** Starlette doesn't expose a raw ping method. Instead, add a `_heartbeat_loop` coroutine that periodically sends a small application-level frame `{"type":"ping"}`. The client will receive this and can simply ignore non-"message" frames. This keeps the connection alive at the TCP level.

Location: `src/leader_board/server.py`

Key changes:
- Add `HEARTBEAT_INTERVAL = 30` constant
- Create `async def _heartbeat_loop(ws: WebSocket, interval: int)` that loops sending `{"type":"ping"}` with `asyncio.sleep(interval)`
- In `websocket_handler()`, spawn the heartbeat task after auth_ok, cancel in the finally block alongside watch_tasks
- Update the protocol module to handle `ping` as a known server frame type

### Step 2: Add ping frame to wire protocol (both Python and TypeScript)

Add a `PingFrame` server frame to the protocol so both servers speak the same keepalive.

**Python** (`src/leader_board/protocol.py`):
- Add `PingFrame` dataclass (no fields beyond type)
- Add it to `ServerFrame` union
- Add serialization case in `serialize_server_frame()`

**TypeScript** (`workers/leader-board/src/protocol.ts`):
- Add `PingFrame` interface with `type: "ping"`
- Add it to `ServerFrame` union
- Add serialization case in `serializeFrame()`

The client should simply ignore ping frames — they exist only to keep the TCP connection alive.

Location: `src/leader_board/protocol.py`, `workers/leader-board/src/protocol.ts`

### Step 3: Add server-side heartbeat to the Cloudflare Durable Object

The DO uses the Hibernation API (`ctx.acceptWebSocket`), which means the DO can be evicted between messages. Cloudflare's proxy layer can also drop idle WebSocket connections.

Add a heartbeat mechanism using DO alarms (the DO already uses alarms for compaction). Since the DO can hibernate, we can't rely on `setInterval`. Instead:

- When an authenticated WebSocket exists, schedule a heartbeat alarm
- In the `alarm()` handler, in addition to compaction, iterate over all connected WebSockets (`this.ctx.getWebSockets()`) and send a ping frame to each
- Re-schedule the heartbeat alarm for the next interval

Since the DO already has a compaction alarm, the simplest approach is to send pings from the alarm handler at a more frequent interval. The compaction alarm runs hourly — we need 30-second pings. Options:
  - **Option A:** Use a separate alarm cadence (DOs support only one alarm, so we'd need to check "is this a heartbeat or compaction alarm?" based on timing)
  - **Option B:** Set the alarm to 30s and run compaction only when enough time has elapsed since the last compaction

**Chosen: Option B.** Set the alarm interval to 30 seconds. On each alarm tick, send pings to all connected WebSockets. Track `lastCompactionAt` in storage and only run compaction when `COMPACTION_INTERVAL_MS` has elapsed.

Location: `workers/leader-board/src/swarm-do.ts`

Key changes:
- Add `HEARTBEAT_INTERVAL_MS = 30_000` constant
- Change the alarm scheduling from `COMPACTION_INTERVAL_MS` to `HEARTBEAT_INTERVAL_MS`
- In `alarm()`, always send pings to all connected WebSockets via `this.ctx.getWebSockets()`
- Track last compaction time and only run compaction when the interval has elapsed
- Ensure the heartbeat alarm is scheduled whenever a WebSocket is accepted (in `fetch()`)

### Step 4: Configure client-side ping parameters

Update `BoardClient.connect()` in `src/board/client.py` to pass `ping_interval` and `ping_timeout` to `websockets.connect()`. This makes the client proactively detect dead connections rather than hanging forever on `recv()`.

Location: `src/board/client.py`

Key changes:
- Add `ping_interval=20` and `ping_timeout=10` to the `websockets.connect()` call
- This means the client sends its own pings every 20s and considers the connection dead if no pong arrives within 10s

### Step 5: Add reconnect logic to BoardClient.watch()

Add a `watch_with_reconnect()` method (or modify the existing `watch()`) that wraps the watch call with retry logic:

1. On `ConnectionClosedError` or `ConnectionClosedOK`, log a warning
2. Wait with exponential backoff (1s, 2s, 4s, capped at 30s)
3. Call `connect()` to re-establish the connection and re-authenticate
4. Re-send the `watch` frame with the same cursor
5. Retry up to a configurable max attempts (default: unlimited for steward loops)

The reconnect must re-run the full auth handshake since the server assigns a new nonce per connection.

Location: `src/board/client.py`

Key changes:
- Add `async def watch_with_reconnect(self, channel, cursor, max_retries=None)` method
- Catches `websockets.exceptions.ConnectionClosedError`, `ConnectionError`, `OSError`
- Implements exponential backoff with jitter
- Logs reconnection attempts via `logging.getLogger(__name__)`
- Returns the same dict as `watch()` on success
- The existing `watch()` method remains unchanged for callers that don't want reconnect

### Step 6: Update the client to ignore ping frames

Since the server now sends `{"type":"ping"}` frames, the client's `watch()` method (which calls `self._ws.recv()`) may receive a ping frame instead of a message frame. Update `watch()` to loop on `recv()`, discarding any `ping` frames until a real `message` frame arrives.

Location: `src/board/client.py`

Key changes:
- In `watch()`, wrap the `recv()` call in a loop
- Parse each received frame; if `type == "ping"`, continue the loop
- If `type == "message"` or `type == "error"`, process as before
- This also applies to any other methods that call `recv()` (but `send()`, `list_channels()` etc. get immediate responses so pings are unlikely to interleave — still, add the loop for safety)

### Step 7: Update CLI `watch_cmd` to use reconnect

Update `src/cli/board.py` `watch_cmd` to use `watch_with_reconnect()` instead of `watch()`. The steward watch loop already calls this command repeatedly, but using reconnect within a single invocation prevents the command from crashing during the blocking wait.

Location: `src/cli/board.py`

Key changes:
- Replace `client.watch(channel, cursor)` with `client.watch_with_reconnect(channel, cursor)`
- Add a `--no-reconnect` flag for cases where the caller wants fail-fast behavior

### Step 8: Write tests for client reconnect logic

Write tests that verify:
1. **Ping frame filtering**: `watch()` correctly ignores `{"type":"ping"}` frames and returns the next `message` frame
2. **Reconnect on disconnect**: `watch_with_reconnect()` catches connection errors, reconnects, and retries the watch
3. **Backoff behavior**: Verify exponential backoff timing (mock `asyncio.sleep`)
4. **Max retries**: When `max_retries` is set, verify it raises after exhausting attempts

Use the existing mock-based approach from `tests/test_board_client.py` — mock `websockets.connect` to simulate disconnects and reconnects.

Location: `tests/test_board_client.py` (extend existing file)

### Step 9: Write tests for server-side heartbeat (local server)

Add a test to `tests/test_leader_board_e2e.py` that verifies the server sends ping frames during idle periods:
1. Connect and authenticate
2. Send a watch frame
3. Wait and verify that ping frames arrive within the heartbeat interval
4. Verify the connection stays alive beyond the previous 2-5 minute timeout window

Location: `tests/test_leader_board_e2e.py` (extend existing file)

## Dependencies

- The `websockets` library (already a dependency) supports `ping_interval`/`ping_timeout` parameters
- No new external libraries needed
- Cloudflare DO alarm API is already in use for compaction

## Risks and Open Questions

- **Starlette ping limitation**: Starlette's `WebSocket` doesn't expose raw ping frames. Using an application-level `{"type":"ping"}` frame works but adds protocol surface. This is acceptable since the frame is trivial and both servers must be consistent.
- **DO alarm granularity**: Cloudflare DOs support only one alarm at a time. Combining heartbeat and compaction into the same alarm handler adds complexity. If the DO has no connected WebSockets, the 30s alarm cadence is wasteful — consider only scheduling the heartbeat alarm when WebSockets are connected, and falling back to the compaction-only cadence when idle.
- **Reconnect during watch vs. between watches**: The steward watch loop already re-invokes `ve board watch` per message. The reconnect logic within `watch_with_reconnect()` handles disconnects *during* the blocking wait. Both layers provide resilience.
- **websockets library version**: The `ping_interval`/`ping_timeout` parameters are available in websockets >= 10.0. Verify the project's pinned version supports this.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->