<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build a local WebSocket server adapter that wraps the existing portable
`LeaderBoardCore` (from the `leader_board_core` chunk). The adapter has two
responsibilities:

1. **Transport** — A Starlette/Uvicorn WebSocket server that speaks the wire
   protocol defined in docs/trunk/SPEC.md (JSON frames over WebSocket). Handles
   the challenge/auth handshake, then routes authenticated frames to the core.

2. **Durable storage** — A filesystem-based `StorageAdapter` implementation that
   persists swarm registration and channel message logs to disk so state survives
   server restarts. Uses JSON files for simplicity and portability.

**Strategy:**

- Use **Starlette** for the WebSocket application and **Uvicorn** for the ASGI
  server — both are already project dependencies (DEC-001 alignment: no new
  dependencies needed).
- Implement `FileSystemStorage` as a new `StorageAdapter` that stores data under
  a configurable directory (default: `~/.ve/leader_board/`).
- The wire protocol handler is a stateless translator: it parses JSON frames,
  calls the core, and serializes responses. This keeps the handler thin and
  testable.
- Compaction runs as a periodic `asyncio` background task on the 30-day TTL
  schedule.
- Follow TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first for
  the filesystem storage (using the existing adapter contract tests), then for
  the wire protocol handler, then end-to-end integration tests.
- The wire protocol encoding/decoding layer is shared code that the Durable
  Objects adapter will also use — design it as a reusable module within
  `src/leader_board/`.

**What we build:**

- `src/leader_board/fs_storage.py` — Filesystem StorageAdapter implementation
- `src/leader_board/protocol.py` — Wire protocol frame parsing and serialization
- `src/leader_board/server.py` — Starlette WebSocket app, connection lifecycle,
  compaction scheduler
- Tests for each layer

**What we don't build:**

- CLI integration (`ve board serve` command) — that's the CLI chunk's concern
- Client-side encryption/decryption — client responsibility
- Durable Objects adapter — separate chunk (but shares the protocol module)

## Sequence

### Step 1: Implement wire protocol frame types

Create `src/leader_board/protocol.py` with frame parsing and serialization.

Define dataclasses for each frame type from the spec:

**Client → Server frames:**
- `AuthFrame(swarm_id: str, signature: str)` — hex-encoded signature
- `RegisterSwarmFrame(swarm_id: str, public_key: str)` — hex-encoded public key
- `WatchFrame(channel: str, swarm: str, cursor: int)`
- `SendFrame(channel: str, swarm: str, body: str)` — base64-encoded ciphertext
- `ChannelsFrame(swarm: str)`
- `SwarmInfoFrame(swarm: str)`

**Server → Client frames:**
- `ChallengeFrame(nonce: str)` — hex-encoded 32-byte nonce
- `AuthOkFrame()`
- `MessageFrame(channel: str, position: int, body: str, sent_at: str)`
- `AckFrame(channel: str, position: int)`
- `ChannelsListFrame(channels: list[dict])`
- `SwarmInfoResponseFrame(swarm: str, created_at: str)`
- `ErrorFrame(code: str, message: str)`

Functions:
- `parse_client_frame(data: str) -> ClientFrame` — Parse JSON string into typed
  frame; raises `InvalidFrameError` for malformed input
- `serialize_server_frame(frame: ServerFrame) -> str` — Serialize frame to JSON
  string

Error codes from the spec: `auth_failed`, `cursor_expired`,
`channel_not_found`, `invalid_frame`, `swarm_not_found`.

Write tests first in `tests/test_leader_board_protocol.py`:
- `test_parse_watch_frame` — valid JSON → WatchFrame
- `test_parse_send_frame` — valid JSON → SendFrame with base64 body
- `test_parse_invalid_json_raises` — malformed JSON → InvalidFrameError
- `test_parse_unknown_type_raises` — unknown frame type → InvalidFrameError
- `test_parse_missing_fields_raises` — missing required field → InvalidFrameError
- `test_serialize_challenge_frame` — ChallengeFrame → JSON with correct structure
- `test_serialize_message_frame` — MessageFrame → JSON with ISO 8601 sent_at
- `test_serialize_error_frame` — ErrorFrame → JSON with code and message
- `test_round_trip_all_frame_types` — serialize then parse round-trips correctly

Location: `src/leader_board/protocol.py`, `tests/test_leader_board_protocol.py`

### Step 2: Implement filesystem storage adapter

Create `src/leader_board/fs_storage.py` implementing `StorageAdapter`.

Directory structure under the configurable root (e.g., `~/.ve/leader_board/`):

```
<root>/
  swarms/
    <swarm_id>/
      swarm.json          # SwarmInfo serialized as JSON
      channels/
        <channel_name>/
          messages.jsonl   # One JSON object per line, append-only
          meta.json        # head_position, oldest_position counters
```

Implementation details:
- `save_swarm()` — Write `swarm.json` with swarm_id, hex-encoded public_key,
  ISO 8601 created_at. Create the swarm directory atomically.
- `get_swarm()` — Read and parse `swarm.json`, return `SwarmInfo` or `None`.
- `append_message()` — Read `meta.json` to get current head_position (or 0 if
  new channel), increment, write message as JSON line to `messages.jsonl`,
  update `meta.json`. Use file locking (`fcntl.flock`) for atomicity.
- `read_after()` — Scan `messages.jsonl` for first message with position >
  cursor. For efficiency, read lines from the end if the file is large (but
  correctness first, optimization later).
- `list_channels()` — Enumerate subdirectories under
  `<swarm_id>/channels/`, read each `meta.json`.
- `get_channel_info()` — Read `meta.json` for the specific channel.
- `compact()` — Rewrite `messages.jsonl` excluding messages older than
  `min_age_days` (always retaining the most recent). Update `meta.json`
  with new oldest_position. Use write-to-temp-then-rename for atomicity.

Write tests using the existing adapter contract test base class:

In `tests/test_leader_board_fs_storage.py`:
- Subclass `AdapterContractTests` with a fixture that creates a
  `FileSystemStorage` pointing at `tmp_path`
- This automatically validates all contract tests pass
- Add filesystem-specific tests:
  - `test_data_survives_new_instance` — write data, create new
    FileSystemStorage instance on same directory, data is readable
  - `test_compact_rewrites_file_atomically` — compact, verify no partial
    writes if interrupted (file either old or new, never corrupt)
  - `test_concurrent_appends_are_serialized` — multiple concurrent
    `append_message` calls produce monotonic positions without gaps

Location: `src/leader_board/fs_storage.py`, `tests/test_leader_board_fs_storage.py`

### Step 3: Implement WebSocket connection handler

Create `src/leader_board/server.py` with the Starlette WebSocket application.

The connection lifecycle follows the spec:

1. **Accept WebSocket connection**
2. **Send challenge** — generate 32-byte random nonce, send as
   `ChallengeFrame`
3. **Await auth response** — client sends `AuthFrame` (existing swarm) or
   `RegisterSwarmFrame` (new swarm registration)
4. **Verify** — for `AuthFrame`, call `core.verify_auth()`; for
   `RegisterSwarmFrame`, call `core.register_swarm()`. On failure, send
   `ErrorFrame` and close.
5. **Send `AuthOkFrame`** — connection is now authenticated with a swarm_id
6. **Message loop** — receive frames, dispatch to handler methods:
   - `watch` → call `core.read_after()` (blocks until message), send
     `MessageFrame`, connection remains open for more frames
   - `send` → decode base64 body, call `core.append()`, send `AckFrame`
   - `channels` → call `core.list_channels()`, send `ChannelsListFrame`
   - `swarm_info` → look up swarm, send `SwarmInfoResponseFrame`

Error handling:
- `SwarmNotFoundError` → `ErrorFrame(code="swarm_not_found")`
- `ChannelNotFoundError` → `ErrorFrame(code="channel_not_found")`
- `CursorExpiredError` → `ErrorFrame(code="cursor_expired", message=...)` with
  earliest_position in the message
- `AuthFailedError` → `ErrorFrame(code="auth_failed")`
- `InvalidFrameError` → `ErrorFrame(code="invalid_frame")`
- JSON decode error → `ErrorFrame(code="invalid_frame")`

The handler validates that post-auth frames reference the authenticated swarm_id
(a connection is scoped to the swarm it authenticated with).

Key design: the `watch` frame triggers a potentially long-lived blocking call
(`core.read_after`). This must not block other frames on the same connection.
Use `asyncio.create_task` for watch operations so the connection can handle
concurrent watches on different channels simultaneously.

Write tests in `tests/test_leader_board_server.py`:
- `test_challenge_sent_on_connect` — connect, first message is a challenge
- `test_auth_flow_success` — connect, receive challenge, send auth, receive
  auth_ok
- `test_auth_flow_invalid_signature` — send bad signature, receive error,
  connection closed
- `test_register_swarm_flow` — send register_swarm, receive auth_ok
- `test_send_and_ack` — authenticate, send message, receive ack with position
- `test_watch_immediate_delivery` — send message first, then watch with
  cursor 0, receive message immediately
- `test_watch_blocks_then_delivers` — watch with cursor 0 on empty channel
  (in background task), send message, watch resolves with message
- `test_channels_list` — send messages to multiple channels, request channel
  list, verify response
- `test_error_on_invalid_frame` — send malformed JSON, receive error frame
- `test_swarm_scoping` — authenticate as swarm A, try to send to swarm B,
  receive error

Use Starlette's `TestClient` with `httpx` for WebSocket testing. Create a
test fixture that stands up the app with `InMemoryStorage` (fast, no disk I/O
in unit tests).

Location: `src/leader_board/server.py`, `tests/test_leader_board_server.py`

### Step 4: Add compaction scheduler

Add a background task to `server.py` that periodically runs compaction.

- On server startup, spawn an `asyncio.Task` that runs in a loop:
  1. Sleep for a configurable interval (default: 1 hour)
  2. Enumerate all swarms and channels
  3. Call `core.compact(swarm_id, channel, min_age_days=30)` for each
  4. Log the number of messages compacted
- The task is cancelled on server shutdown via Starlette's lifespan events.

The compaction interval is configurable but the 30-day TTL is fixed per the
spec.

Write tests:
- `test_compaction_runs_on_schedule` — use a short interval (0.1s), insert
  old messages, verify they're compacted after a brief wait
- `test_compaction_stops_on_shutdown` — start server, stop it, verify the
  compaction task is cancelled cleanly

Location: `src/leader_board/server.py`, `tests/test_leader_board_server.py`

### Step 5: Server entry point and configuration

Add a `create_app()` factory function to `server.py` that wires everything
together:

```python
def create_app(
    storage_dir: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8374,
    compaction_interval_seconds: int = 3600,
) -> Starlette:
```

- Defaults `storage_dir` to `~/.ve/leader_board/`
- Creates `FileSystemStorage(storage_dir)`
- Creates `LeaderBoardCore(storage)`
- Mounts the WebSocket endpoint at `/ws`
- Registers compaction scheduler via Starlette lifespan
- Returns the configured Starlette app

Add a `run_server()` convenience function that calls `uvicorn.run()` with
the app. This is the entry point that the CLI chunk will eventually call.

Write a test:
- `test_create_app_returns_runnable_starlette_app` — create app with
  tmp_path storage, verify it's a Starlette instance with the expected
  routes

Location: `src/leader_board/server.py`

### Step 6: End-to-end integration test

Create `tests/test_leader_board_e2e.py` with a full end-to-end test that
exercises the success criteria:

**Test: send a message, watch with cursor, receive the message**

1. Start the server with `FileSystemStorage` on a temp directory
2. Connect via WebSocket
3. Register a new swarm (generate Ed25519 keypair, send `register_swarm`)
4. Send a message to channel "test-channel" with a known body
5. Open a second WebSocket connection, authenticate with the same swarm
6. Watch channel "test-channel" with cursor 0
7. Verify the received message matches what was sent (position=1, body matches)
8. Verify state persists: stop the server, start a new one on the same
   storage directory, connect, watch with cursor 0, receive the same message

**Test: compaction removes old messages**

1. Start server, register swarm, authenticate
2. Append messages with artificially old timestamps (requires a test helper
   that directly writes to storage)
3. Trigger compaction (either wait for scheduler or call core.compact directly)
4. Watch with cursor 0, verify `cursor_expired` error with earliest_position

**Test: wire protocol byte-identity**

1. Capture the exact JSON frames produced by the server for each frame type
2. Assert they match the spec format exactly (field names, value encoding,
   JSON structure)
3. This test documents the wire protocol contract that the DO adapter must
   also satisfy

Location: `tests/test_leader_board_e2e.py`

### Step 7: Update package exports and add backreferences

Update `src/leader_board/__init__.py` to export the new public API:
- `FileSystemStorage`
- `create_app`
- `run_server`
- Protocol frame types (for use by the DO adapter and CLI)

Add module-level backreference comments to all new source files:
```python
# Chunk: docs/chunks/leader_board_local_server - Local WebSocket server adapter
```

Run the full test suite: `uv run pytest tests/test_leader_board_*.py` and
verify all tests pass.

Location: `src/leader_board/__init__.py`, all new source files

## Dependencies

- **leader_board_core** (ACTIVE) — Provides `LeaderBoardCore`, `StorageAdapter`
  protocol, domain models, and `InMemoryStorage` for testing.
- **leader_board_spec** (ACTIVE) — Defines the wire protocol, auth flow, and
  behavioral rules that this adapter must conform to.
- **starlette** (already in pyproject.toml) — ASGI framework for WebSocket
  handling.
- **uvicorn** (already in pyproject.toml) — ASGI server to run the app.
- **cryptography** (dev dependency) — Used in tests for Ed25519 keypair
  generation during auth flow testing.

No new dependencies need to be added to pyproject.toml.

## Risks and Open Questions

- **File locking portability**: `fcntl.flock` is POSIX-only. This is acceptable
  for the local server (development/self-hosting on macOS/Linux), but if Windows
  support is ever needed, `msvcrt.locking` or a cross-platform library would be
  required. The Durable Objects adapter doesn't need file locking at all.
- **JSONL performance at scale**: Scanning `messages.jsonl` for `read_after` is
  O(n) in the number of retained messages. For the development/self-hosting use
  case, channels are unlikely to exceed thousands of messages. If performance
  becomes an issue, an index file or SQLite could replace JSONL — but that's an
  optimization, not a correctness concern.
- **Concurrent WebSocket watch + send on same connection**: The spec doesn't
  explicitly forbid sending a `watch` and a `send` on the same connection
  simultaneously. The implementation must handle this gracefully using
  `asyncio.create_task` for long-lived watch operations.
- **Starlette WebSocket testing**: Starlette's `TestClient` uses `httpx` for
  WebSocket testing, which may have limitations around concurrent operations.
  May need to use actual `websockets` client library for the E2E tests.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->
