

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This is a targeted removal of the alarm-based heartbeat mechanism added by `websocket_keepalive` from the Cloudflare DO worker, plus cleanup of the application-level `PingFrame` protocol type that only existed to support it. The local Starlette server (`server.py`) also has a heartbeat loop that uses `PingFrame`—this must be removed for consistency.

The key insight: Cloudflare's runtime already handles WebSocket keepalive at the protocol level. Incoming ping frames receive automatic pong responses *without interrupting hibernation*. The client-side `ping_interval=20` / `ping_timeout=10` on the `websockets` library sends protocol-level pings that the runtime auto-responds to. No application-level ping frames are needed.

**What stays:**
- Client-side `ping_interval`/`ping_timeout` configuration in `BoardClient.connect()` — this drives protocol-level pings
- Client-side `watch_with_reconnect()` — safety net for transient disconnects
- Compaction alarm logic in `alarm()` — only fires when compaction is due
- `ensureAlarm()` — schedules compaction-only alarms

**What goes:**
- `HEARTBEAT_INTERVAL_MS` constant and `ensureHeartbeatAlarm()` in `swarm-do.ts`
- Heartbeat ping-sending logic in `alarm()` and dynamic alarm interval based on WebSocket count
- `PingFrame` interface in `protocol.ts` and its inclusion in `ServerFrame` union
- `PingFrame` dataclass in `protocol.py`, its `ServerFrame` union membership, and serialization case
- `_heartbeat_loop()` in `server.py` and the heartbeat task lifecycle in `websocket_handler()`
- `HEARTBEAT_INTERVAL` constant in `server.py`
- `_recv_data_frame()` ping-filtering method in `client.py` — callers revert to direct `recv()` + `json.loads()`
- Test cases for ping frame filtering in `test_board_client.py`

Testing approach follows TESTING_PHILOSOPHY.md: update existing tests that relied on `PingFrame` behavior, remove tests that only verified ping filtering (now meaningless), and keep reconnect tests untouched (that behavior is preserved).

## Sequence

### Step 1: Remove heartbeat alarm from `swarm-do.ts`

**Location:** `workers/leader-board/src/swarm-do.ts`

1. Delete `HEARTBEAT_INTERVAL_MS` constant (line 92)
2. Delete `ensureHeartbeatAlarm()` method (lines 896-904)
3. Remove the call to `ensureHeartbeatAlarm()` in `webSocketMessage` / WebSocket accept path (line 180) — replace with a call to `ensureAlarm()` so that the compaction alarm is still scheduled when a WebSocket connects
4. In `alarm()`:
   - Remove the ping-sending loop (lines 582-589) that iterates `ctx.getWebSockets()` and sends `serializeFrame({type:"ping"})`
   - Remove the dynamic `nextInterval` logic (lines 601-606) that chooses between heartbeat and compaction interval
   - Keep the compaction logic intact (lines 591-599)
   - After compaction, always reschedule at `COMPACTION_INTERVAL_MS`
5. Simplify `ensureAlarm()` (lines 906-916): remove the WebSocket-count check — always use `COMPACTION_INTERVAL_MS`
6. Remove the `lastCompactionAt` tracking field (line 578) and the time-elapsed guard in `alarm()` (line 593) — with only compaction alarms firing at 24h intervals, there's no need to gate compaction within alarm ticks. Every alarm tick *is* a compaction tick.
7. Update backreference comments: replace `websocket_keepalive` references with `websocket_hibernation_compat` where the logic is being changed, remove backreferences on deleted code.

### Step 2: Remove `PingFrame` from TypeScript protocol

**Location:** `workers/leader-board/src/protocol.ts`

1. Delete the `PingFrame` interface (lines 90-92)
2. Remove `PingFrame` from the `ServerFrame` union type (line 113)
3. Remove the `import` of `serializeFrame` for ping in `swarm-do.ts` if it becomes unused (check — it's still used for other frame types, so the import stays)

### Step 3: Remove heartbeat from local Starlette server

**Location:** `src/leader_board/server.py`

1. Delete `HEARTBEAT_INTERVAL` constant (line 58)
2. Delete `_heartbeat_loop()` function (lines 67-74)
3. In `websocket_handler()`:
   - Remove `heartbeat_task = asyncio.create_task(_heartbeat_loop(ws))` (line 198)
   - In the `finally` block (lines 296-301), remove the heartbeat task cancellation/cleanup
4. Remove the `PingFrame` import (line 41) since nothing in server.py uses it anymore
5. Update backreference comments.

### Step 4: Remove `PingFrame` from Python protocol

**Location:** `src/leader_board/protocol.py`

1. Delete the `PingFrame` dataclass (lines 137-141)
2. Remove `PingFrame` from the `ServerFrame` union (line 161)
3. Remove the `PingFrame` serialization case in `serialize_server_frame()` (lines 257-258)

### Step 5: Remove ping filtering from Python client

**Location:** `src/board/client.py`

1. Delete the `_recv_data_frame()` method (lines 121-132)
2. Replace all call sites with inline `json.loads(await self._ws.recv())`:
   - `send()` (line 144): `response = json.loads(await self._ws.recv())`
   - `watch()` (line 163): `response = json.loads(await self._ws.recv())`
   - `channels()` or similar (line 240): `response = json.loads(await self._ws.recv())`
3. Remove the backreference comment for `_recv_data_frame`.

### Step 6: Update tests

**Location:** `tests/test_board_client.py`

1. **Remove ping-filtering tests** (lines 176-219):
   - Delete `test_watch_ignores_ping_frames()`
   - Delete `test_send_ignores_ping_frames()`
   - These tested behavior that no longer exists (application-level ping filtering)
2. **Update test fixtures** in remaining tests: Remove any `{"type":"ping"}` frames from mock WebSocket message sequences, since the server no longer sends them
3. **Keep all reconnect tests** untouched — `watch_with_reconnect()` behavior is preserved
4. **Run full test suite** to verify nothing else breaks: `uv run pytest tests/`

### Step 7: Update GOAL.md code_paths

**Location:** `docs/chunks/websocket_hibernation_compat/GOAL.md`

Update the `code_paths` frontmatter to list all files touched:
- `workers/leader-board/src/swarm-do.ts`
- `workers/leader-board/src/protocol.ts`
- `src/leader_board/server.py`
- `src/leader_board/protocol.py`
- `src/board/client.py`
- `tests/test_board_client.py`

## Risks and Open Questions

- **Local Starlette server idle disconnects**: The local server (`server.py`) doesn't benefit from Cloudflare's automatic ping/pong. Removing `_heartbeat_loop` may reintroduce idle disconnects for local development. However, the client still sends protocol-level pings via `ping_interval=20`, and the `websockets` library (used by both client and Starlette's ASGI layer) handles ping/pong at the protocol level. This should be sufficient, but warrants verification.
- **`ensureAlarm` on WebSocket connect**: After removing `ensureHeartbeatAlarm()`, we still want to ensure *some* alarm exists when WebSockets connect (for compaction). Replacing with `ensureAlarm()` handles this — it schedules a compaction alarm if none exists.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
