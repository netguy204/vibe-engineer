<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Implement the portable leader board core as a new `src/leader_board/` package
within the existing vibe-engineer codebase. The core is a pure-Python library
with **no I/O dependencies** — no WebSocket, HTTP, or filesystem code. It
exposes a clean adapter interface that host-specific adapters (local server,
Durable Objects) will call.

The design follows the **Core/Adapter Boundary** from the spec in
docs/trunk/SPEC.md: the core owns swarm state, channel log operations, auth
verification, position assignment, FIFO ordering, and compaction. Adapters
handle transport, storage, connection lifecycle, and wire protocol encoding.

**Strategy:**

- Use Pydantic models for domain types (consistent with DEC-008)
- Use `asyncio.Event` for the blocking read primitive — adapters that need
  sync can wrap in their own event loop
- Define an `AdapterStorage` protocol (Python `Protocol` class) that the core
  calls for durable persistence. Tests use an in-memory implementation.
- Per the testing philosophy, follow TDD: write failing tests first, then
  implement to make them pass. Test behavior at boundaries (empty channels,
  expired cursors, unknown swarms).

**What we don't build:**

- No wire protocol encoding/decoding (adapter responsibility)
- No WebSocket/HTTP code (adapter responsibility)
- No filesystem code (adapter responsibility)
- No encryption/decryption (client responsibility — core handles opaque bytes)

## Subsystem Considerations

No existing subsystems are directly relevant to this chunk. The leader board
core is a new domain-specific library that doesn't touch the workflow artifact
lifecycle (docs/subsystems/workflow_artifacts) or any other existing subsystem.

The `leader_board_core` chunk may eventually become the seed of a new subsystem
if the leader board codebase grows, but that decision is deferred.

## Sequence

### Step 1: Define domain models

Create `src/leader_board/__init__.py` and `src/leader_board/models.py` with
Pydantic models and domain types:

- `SwarmInfo` — swarm_id (str), public_key (bytes), created_at (datetime)
- `ChannelMessage` — channel (str), position (int), body (bytes), sent_at (datetime)
- `ChannelInfo` — name (str), head_position (int), oldest_position (int)
- `CursorExpiredError` — custom exception with `earliest_position` field
- `SwarmNotFoundError`, `ChannelNotFoundError`, `AuthFailedError` — custom exceptions
- `CHANNEL_NAME_PATTERN` — regex `^[a-zA-Z0-9_-]{1,128}$`
- `MESSAGE_MAX_BYTES` — 1 MB limit constant

Validation rules:
- Channel names must match `CHANNEL_NAME_PATTERN`
- Message body must not exceed `MESSAGE_MAX_BYTES`

Location: `src/leader_board/__init__.py`, `src/leader_board/models.py`

### Step 2: Define the adapter storage protocol

Create `src/leader_board/storage.py` with a `StorageAdapter` Protocol that the
core calls for all persistence:

```python
class StorageAdapter(Protocol):
    async def save_swarm(self, swarm: SwarmInfo) -> None: ...
    async def get_swarm(self, swarm_id: str) -> SwarmInfo | None: ...
    async def append_message(self, swarm_id: str, channel: str, body: bytes) -> ChannelMessage: ...
    async def read_after(self, swarm_id: str, channel: str, cursor: int) -> ChannelMessage | None: ...
    async def list_channels(self, swarm_id: str) -> list[ChannelInfo]: ...
    async def get_channel_info(self, swarm_id: str, channel: str) -> ChannelInfo | None: ...
    async def compact(self, swarm_id: str, channel: str, min_age_days: int) -> int: ...
```

The `read_after` method returns `None` when no message exists after the cursor
(the core handles the blocking/waiting semantics). `append_message` is
responsible for assigning the monotonic position and `sent_at` timestamp.

Location: `src/leader_board/storage.py`

### Step 3: Implement in-memory storage adapter

Create `src/leader_board/memory_storage.py` with `InMemoryStorage` implementing
`StorageAdapter`. This is used in tests and also serves as a reference
implementation for adapter authors.

- Swarms stored in `dict[str, SwarmInfo]`
- Channel logs stored in `dict[tuple[str, str], list[ChannelMessage]]` keyed by
  (swarm_id, channel)
- Position counters per (swarm_id, channel) starting at 0, incrementing to 1 on
  first append
- `compact()` removes messages with `sent_at` older than `min_age_days` but
  always retains the most recent message

Write tests first in `tests/test_leader_board_storage.py`:

- `test_append_assigns_monotonic_positions` — append 3 messages, verify positions 1, 2, 3
- `test_read_after_returns_next_message` — append 2 messages, read_after(0) returns position 1
- `test_read_after_returns_none_when_no_message` — read_after on empty channel returns None
- `test_compact_removes_old_messages` — append messages with old timestamps, compact, verify removal
- `test_compact_retains_most_recent` — even if all messages are old, the most recent survives
- `test_list_channels_returns_head_and_oldest` — verify ChannelInfo after appends and compaction

Location: `src/leader_board/memory_storage.py`, `tests/test_leader_board_storage.py`

### Step 4: Implement the core — swarm operations

Create `src/leader_board/core.py` with the `LeaderBoardCore` class.

Constructor takes a `StorageAdapter` instance (dependency injection).

Swarm operations:
- `register_swarm(swarm_id: str, public_key: bytes) -> SwarmInfo` — creates a
  new swarm via `storage.save_swarm()`. Raises `ValueError` if swarm_id already
  exists.
- `verify_auth(swarm_id: str, nonce: bytes, signature: bytes) -> bool` — looks
  up the swarm's public key via `storage.get_swarm()`, verifies the Ed25519
  signature over the nonce. Raises `SwarmNotFoundError` if swarm doesn't exist.
  Returns True if valid, raises `AuthFailedError` if signature doesn't verify.

Auth verification uses the `cryptography` library (`Ed25519PublicKey`). The core
only verifies — it never signs (that's the client's job).

Write tests first in `tests/test_leader_board_core.py`:

- `test_register_swarm_stores_public_key` — register, then verify the swarm exists
- `test_register_swarm_rejects_duplicate` — registering same swarm_id twice raises ValueError
- `test_verify_auth_accepts_valid_signature` — generate keypair, register, sign nonce, verify succeeds
- `test_verify_auth_rejects_invalid_signature` — tampered signature raises AuthFailedError
- `test_verify_auth_unknown_swarm_raises` — verify on unregistered swarm raises SwarmNotFoundError

Location: `src/leader_board/core.py`, `tests/test_leader_board_core.py`

### Step 5: Implement the core — channel operations

Add channel operations to `LeaderBoardCore`:

- `append(swarm_id: str, channel: str, body: bytes) -> ChannelMessage` —
  validates channel name and body size, delegates to `storage.append_message()`.
  Raises `SwarmNotFoundError` if swarm doesn't exist. Validates channel name
  format and body size limit.
- `read_after(swarm_id: str, channel: str, cursor: int) -> ChannelMessage` —
  async method that blocks until a message exists after the cursor. Uses an
  internal `asyncio.Event` per (swarm_id, channel) to wake blocked readers when
  `append()` adds a new message. Returns `CursorExpiredError` when cursor is
  behind the compaction frontier (oldest_position - 1). Returns
  `ChannelNotFoundError` when watching a channel that has never been written to.
- `list_channels(swarm_id: str) -> list[ChannelInfo]` — delegates to storage.

The blocking mechanism works as follows:
1. `read_after` calls `storage.read_after()`
2. If a message is available, return it immediately
3. If not, wait on an `asyncio.Event` for that (swarm_id, channel)
4. When `append()` writes a new message, it sets the event, waking all waiters
5. After waking, re-read from storage (another waiter may have consumed the
   position range; in a single-reader scenario this is a no-op check)

Write tests:

- `test_append_and_read_back` — append a message, read_after(0) returns it
- `test_read_after_blocks_then_resolves` — start read_after in background task, append a message, verify it resolves
- `test_read_after_cursor_expired` — compact a channel, then read_after with old cursor raises CursorExpiredError with earliest_position
- `test_read_after_channel_not_found` — read_after on non-existent channel raises ChannelNotFoundError
- `test_append_validates_channel_name` — invalid channel names raise ValueError
- `test_append_validates_body_size` — body > 1MB raises ValueError
- `test_append_unknown_swarm_raises` — append to unregistered swarm raises SwarmNotFoundError
- `test_fifo_ordering` — append 3 messages, read_after(0), read_after(1), read_after(2) returns them in order
- `test_multiple_concurrent_watchers` — two concurrent read_after calls on same channel both resolve when a message arrives

Location: `src/leader_board/core.py`, `tests/test_leader_board_core.py`

### Step 6: Implement the core — compaction

Add compaction to `LeaderBoardCore`:

- `compact(swarm_id: str, channel: str, min_age_days: int = 30) -> int` —
  delegates to `storage.compact()`, returns count of removed positions. Raises
  `SwarmNotFoundError` if swarm doesn't exist.

Write tests:

- `test_compact_removes_old_messages` — insert messages with old timestamps, compact, verify they're gone
- `test_compact_retains_recent_messages` — insert mix of old and recent, compact, verify recent survive
- `test_compact_always_retains_most_recent` — all messages old, compact, the last one remains
- `test_read_after_reflects_compaction` — after compaction, read_after with pre-compaction cursor gets CursorExpiredError

Location: `src/leader_board/core.py`, `tests/test_leader_board_core.py`

### Step 7: Validate the adapter interface contract

Create `tests/test_leader_board_adapter_contract.py` — a set of tests that any
`StorageAdapter` implementation must pass. This is a reusable test class that
the in-memory adapter passes now, and future adapters (filesystem, DO) can
subclass to verify compliance.

Tests cover:
- Append assigns monotonic positions starting at 1
- read_after with cursor 0 returns first message
- read_after with cursor = head returns None
- Compaction removes old messages but retains the most recent
- list_channels returns correct head/oldest positions
- Multiple channels within the same swarm are independent

The test class is parameterized with a factory fixture that creates a
`StorageAdapter` instance. The in-memory adapter test file imports and runs
these tests.

Location: `tests/test_leader_board_adapter_contract.py`

### Step 8: Package exports and documentation

Finalize `src/leader_board/__init__.py` to export the public API:

- `LeaderBoardCore`
- `StorageAdapter`
- `InMemoryStorage`
- All model types (`SwarmInfo`, `ChannelMessage`, `ChannelInfo`)
- All exception types (`CursorExpiredError`, `SwarmNotFoundError`, etc.)

Add module-level backreference comments to all source files:
```python
# Chunk: docs/chunks/leader_board_core - Portable leader board core library
```

Run `uv run pytest tests/test_leader_board_*.py` and verify all tests pass.

Location: `src/leader_board/__init__.py`

## Dependencies

- **leader_board_spec** (ACTIVE) — The specification in docs/trunk/SPEC.md
  defines the core interface, behavioral rules, and error semantics that this
  implementation must conform to.
- **cryptography** library — For Ed25519 signature verification in auth. Must be
  added to pyproject.toml dependencies. (Already likely available as a
  transitive dependency, but should be declared explicitly.)

## Risks and Open Questions

- **Ed25519 library choice**: The spec references libsodium for key conversion
  (Ed25519 → Curve25519 for encryption key derivation). The core only needs
  signature *verification*, not key conversion — that's a client concern. The
  `cryptography` library provides Ed25519 verification and is widely available.
  If the project already depends on `pynacl` or similar, we should prefer that
  for consistency with the encryption spec.
- **Async API surface**: The core uses `asyncio.Event` for blocking reads. This
  means all adapters must run in an async context. This is appropriate for
  WebSocket servers but may require sync wrappers for CLI usage. The CLI chunk
  will need to address this (out of scope here).
- **Thread safety**: The in-memory storage and core event map are not
  thread-safe. For single-process adapters (local server, DO), this is fine
  since they use asyncio concurrency. If a multi-threaded adapter is ever
  needed, locking would need to be added to the storage layer — but that's an
  adapter concern, not a core concern.

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
