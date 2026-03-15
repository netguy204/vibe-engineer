<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Implement the Cloudflare Workers + Durable Objects adapter as a TypeScript
project under `workers/leader-board/`. This is a separate deployment artifact
from the Python VE CLI — CF Workers run JavaScript/TypeScript natively, so the
DO adapter re-implements the portable core's behavioral contract in TypeScript
rather than calling the Python code directly. The spec describes the core
interface as "language-agnostic" (SPEC.md, Core/Adapter Boundary section), and
the DO adapter is the TypeScript realization of that interface.

**Architecture:**

- **Worker** (`src/index.ts`): HTTP entry point that accepts WebSocket upgrade
  requests. Extracts the `swarm` query parameter, routes the connection to the
  correct Durable Object instance by swarm ID. Also handles `register_swarm`
  via the WebSocket handshake (unauthenticated first contact).
- **SwarmDO** (`src/swarm-do.ts`): Durable Object class — one instance per
  swarm. Owns all state for that swarm: channels, messages, public key. Uses
  DO SQLite storage for the append-only log. Implements the wire protocol
  (challenge/auth/watch/send/channels/swarm_info). Uses DO alarms for
  compaction scheduling.
- **Storage layer** (`src/storage.ts`): Thin abstraction over DO SQLite storage
  that mirrors the Python `StorageAdapter` protocol. Handles position
  assignment, key layout (`{channel}:{zero-padded-position}`), and compaction.
- **Auth** (`src/auth.ts`): Ed25519 signature verification using the Web Crypto
  API (available in CF Workers runtime). Challenge nonce generation.
- **Wire protocol** (`src/protocol.ts`): JSON frame types and
  validation/serialization. Ensures wire-level compatibility with the local
  server adapter.

The wire protocol is **identical** to what the local server adapter implements
— same JSON frame types, same field names, same error codes, same behavioral
rules (SPEC.md, Wire Protocol section). Clients cannot distinguish between
backends.

**Testing strategy:**

Since CF Workers have a specialized runtime, testing uses two approaches:

1. **Vitest + Miniflare**: Unit and integration tests that run against a local
   Miniflare environment simulating the CF Workers runtime. These cover the
   storage adapter contract, auth verification, wire protocol frame handling,
   and end-to-end WebSocket flows.
2. **Adapter contract tests**: A TypeScript port of the Python
   `AdapterContractTests` (from `tests/test_leader_board_adapter_contract.py`)
   that verifies the DO storage layer satisfies the same behavioral contract
   as the Python `InMemoryStorage`.

Per the testing philosophy, tests focus on behavior at boundaries: empty
channels, expired cursors, unknown swarms, concurrent watchers, compaction
edge cases.

## Subsystem Considerations

No existing subsystems are relevant. This is a standalone TypeScript deployment
that does not touch the Python workflow artifact lifecycle or any other VE
subsystem. The leader board codebase may eventually become a subsystem if it
grows, but that decision is deferred.

## Sequence

### Step 1: Scaffold the Workers project

Create the `workers/leader-board/` directory with:

- `package.json` with dependencies: `wrangler`, `@cloudflare/workers-types`,
  `vitest`, `miniflare`
- `tsconfig.json` targeting ES2022 with CF Workers module resolution
- `wrangler.toml` with:
  - Worker name: `leader-board`
  - Compatibility date: `2024-01-01` (or latest stable)
  - Durable Object binding: `SWARM_DO` → `SwarmDO` class
  - Migration tag for DO creation
- `.dev.vars` template for local development secrets (if any)
- Basic `src/index.ts` that returns 200 OK (smoke test)

Run `npx wrangler dev` to verify the scaffold works.

Location: `workers/leader-board/`

### Step 2: Define wire protocol types and validation

Create `src/protocol.ts` with TypeScript types for all wire protocol frames
exactly as specified in SPEC.md (Wire Protocol section):

**Handshake frames:**
- `ChallengeFrame`: `{ type: "challenge", nonce: string }`
- `AuthFrame`: `{ type: "auth", swarm: string, signature: string }`
- `RegisterSwarmFrame`: `{ type: "register_swarm", swarm: string, public_key: string }`
- `AuthOkFrame`: `{ type: "auth_ok" }`

**Client → Server frames:**
- `WatchFrame`: `{ type: "watch", channel: string, swarm: string, cursor: number }`
- `SendFrame`: `{ type: "send", channel: string, swarm: string, body: string }`
- `ChannelsFrame`: `{ type: "channels", swarm: string }`
- `SwarmInfoFrame`: `{ type: "swarm_info", swarm: string }`

**Server → Client frames:**
- `MessageFrame`: `{ type: "message", channel: string, position: number, body: string, sent_at: string }`
- `AckFrame`: `{ type: "ack", channel: string, position: number }`
- `ChannelsListFrame`: `{ type: "channels_list", channels: Array<{ name: string, head_position: number, oldest_position: number }> }`
- `SwarmInfoResponseFrame`: `{ type: "swarm_info", swarm: string, created_at: string }`
- `ErrorFrame`: `{ type: "error", code: string, message: string, earliest_position?: number }`

Add a `parseClientFrame(raw: string)` function that parses JSON and validates
required fields, returning a typed discriminated union or throwing an
`invalid_frame` error. Validate:
- Channel names match `^[a-zA-Z0-9_-]{1,128}$`
- Required fields present per frame type
- `cursor` is a non-negative integer
- `body` is a non-empty string

Write Vitest tests for frame parsing: valid frames, missing fields, invalid
channel names, negative cursors.

Location: `workers/leader-board/src/protocol.ts`, `workers/leader-board/test/protocol.test.ts`

### Step 3: Implement Ed25519 auth module

Create `src/auth.ts` with:

- `generateChallenge(): string` — generates 32 random bytes, returns hex string
- `verifySignature(publicKeyHex: string, nonceHex: string, signatureHex: string): Promise<boolean>` —
  imports the Ed25519 public key via Web Crypto API (`crypto.subtle.importKey`
  with `Ed25519` algorithm), verifies the signature over the nonce bytes.
  Returns true if valid, false if invalid.

The CF Workers runtime supports Ed25519 via the Web Crypto API. If
`crypto.subtle` doesn't directly support Ed25519 import (it may require the
`NODE-ED25519` named curve), use the `@noble/ed25519` package as a fallback —
it's pure JS and works in Workers.

Write tests:
- `test_verify_valid_signature` — generate a keypair (in test), sign a nonce,
  verify succeeds
- `test_verify_invalid_signature` — tampered signature returns false
- `test_verify_wrong_key` — different public key returns false

Location: `workers/leader-board/src/auth.ts`, `workers/leader-board/test/auth.test.ts`

### Step 4: Implement DO storage layer

Create `src/storage.ts` with a `SwarmStorage` class that wraps the Durable
Object's `DurableObjectStorage` (SQLite-backed):

**Schema (via DO SQL API):**

```sql
CREATE TABLE IF NOT EXISTS swarm_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  channel TEXT NOT NULL,
  position INTEGER NOT NULL,
  body TEXT NOT NULL,
  sent_at TEXT NOT NULL,
  PRIMARY KEY (channel, position)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel_position
  ON messages(channel, position);
```

**Methods (mirroring StorageAdapter protocol):**

- `saveSwarm(swarmId: string, publicKeyHex: string): Promise<void>` — stores
  swarm metadata (public key, created_at) in `swarm_meta` table
- `getSwarm(swarmId: string): Promise<SwarmMeta | null>` — retrieves swarm metadata
- `appendMessage(channel: string, body: string): Promise<{ position: number, sent_at: string }>` —
  inserts message with next position (SELECT MAX(position) + 1 or 1 if empty),
  ISO 8601 UTC timestamp. Uses a transaction to ensure monotonic position
  assignment.
- `readAfter(channel: string, cursor: number): Promise<StoredMessage | null>` —
  `SELECT * FROM messages WHERE channel = ? AND position > ? ORDER BY position LIMIT 1`
- `listChannels(): Promise<ChannelInfo[]>` — aggregates per-channel: MAX(position)
  as head_position, MIN(position) as oldest_position
- `getChannelInfo(channel: string): Promise<ChannelInfo | null>` — same for one channel
- `compact(channel: string, minAgeDays: number): Promise<number>` — deletes
  messages older than cutoff, ALWAYS retains the row with MAX(position). Returns
  count of deleted rows.

Write adapter contract tests (port of
`tests/test_leader_board_adapter_contract.py`):
- Monotonic position assignment starting at 1
- `readAfter` cursor behavior (returns next message, returns null at head)
- Compact removes old messages but retains most recent
- Multiple channels are independent
- List channels with correct head/oldest positions

Location: `workers/leader-board/src/storage.ts`, `workers/leader-board/test/storage.test.ts`

### Step 5: Implement the SwarmDO class — connection lifecycle and auth

Create `src/swarm-do.ts` with the `SwarmDO` Durable Object class:

**Constructor:**
- Initializes `SwarmStorage` from the DO's storage handle
- Maintains a set of pending watchers (for blocking read wake-up)

**`fetch(request: Request): Response`:**
- Accepts WebSocket upgrade requests only (return 426 otherwise)
- Creates a WebSocket pair, accepts the server side
- Enters the handshake state machine:
  1. Send `challenge` frame with random nonce
  2. Wait for client response:
     - If `register_swarm`: store public key via storage, send `auth_ok`
     - If `auth`: verify signature against stored public key
       - Success: send `auth_ok`, transition to authenticated state
       - Failure: send `error` with code `auth_failed`, close connection
  3. After auth, enter the message handling loop

**WebSocket message handler (authenticated):**
- Parse incoming frame via `parseClientFrame()`
- Dispatch by frame type to handler methods (implemented in Step 6)
- On parse error: send `error` with code `invalid_frame`

Write tests:
- Auth flow: valid signature → `auth_ok`
- Auth flow: invalid signature → `error` + close
- Register swarm: stores public key
- Non-WebSocket request returns 426
- Invalid frame during auth → `invalid_frame` error

Location: `workers/leader-board/src/swarm-do.ts`, `workers/leader-board/test/swarm-do.test.ts`

### Step 6: Implement post-auth frame handlers

Add handler methods to `SwarmDO` for each post-auth frame type:

**`handleSend(ws, frame)`:**
- Validate body is non-empty and within 1MB limit (base64 decoded)
- Call `storage.appendMessage(channel, body)`
- Wake any pending watchers on this channel (set their events)
- Send `ack` frame with assigned position

**`handleWatch(ws, frame)`:**
- Check channel exists: if not, send `error` with code `channel_not_found`
- Check cursor validity: get channel info, if cursor + 1 < oldest_position,
  send `error` with code `cursor_expired` and `earliest_position`
- Call `storage.readAfter(channel, cursor)`
- If message exists: send `message` frame immediately
- If no message: register this WebSocket + cursor as a pending watcher.
  When `handleSend` appends to this channel, wake the watcher and send the
  message. If the WebSocket closes before a message arrives, clean up the
  watcher.

**`handleChannels(ws, frame)`:**
- Call `storage.listChannels()`
- Send `channels_list` frame

**`handleSwarmInfo(ws, frame)`:**
- Call `storage.getSwarm(swarmId)`
- Send `swarm_info` response frame with `created_at`

**Watcher mechanism:**
- Maintain a `Map<string, Set<{ ws: WebSocket, cursor: number }>>` keyed by
  channel name
- When `handleSend` appends a message, iterate watchers for that channel:
  for each watcher whose cursor < new position, send the message frame and
  remove from the set
- On WebSocket close: remove from all watcher sets

Write tests:
- Send and receive ack with correct position
- Watch on empty channel → blocks, then resolves when message sent
- Watch with expired cursor → `cursor_expired` error with `earliest_position`
- Watch on non-existent channel → `channel_not_found` error
- Channels list returns correct head/oldest positions
- Swarm info returns created_at
- Multiple concurrent watchers all receive the message
- Body size validation (> 1MB → error)

Location: `workers/leader-board/src/swarm-do.ts`, `workers/leader-board/test/swarm-do.test.ts`

### Step 7: Implement the Worker entry point and routing

Complete `src/index.ts`:

- Export the `SwarmDO` class for the Durable Object binding
- Handle incoming requests:
  1. Extract `swarm` query parameter from the URL
  2. If no `swarm` param, return 400 with error message
  3. Generate the DO ID from the swarm ID string
     (`env.SWARM_DO.idFromName(swarmId)`)
  4. Get the DO stub (`env.SWARM_DO.get(id)`)
  5. Forward the request to the DO (`stub.fetch(request)`)

The Worker itself does no auth or protocol handling — it's a pure router.
The swarm query parameter is required even for `register_swarm` (the client
knows its swarm ID at registration time since it derives from the public key).

Write tests:
- Request with `?swarm=foo` routes to DO
- Request without `swarm` param returns 400
- Non-WebSocket request forwarded to DO (which returns 426)

Location: `workers/leader-board/src/index.ts`, `workers/leader-board/test/index.test.ts`

### Step 8: Implement compaction via DO alarm

Add alarm-based compaction to `SwarmDO`:

- **`alarm()` handler**: When the DO alarm fires:
  1. List all channels via `storage.listChannels()`
  2. For each channel, call `storage.compact(channel, 30)`
  3. Schedule the next alarm (e.g., every 24 hours)
  4. Log compaction results

- **Alarm scheduling**: On first `register_swarm` or first `handleSend`, if no
  alarm is set, schedule one for 24 hours from now. The alarm repeats by
  re-scheduling itself at the end of each `alarm()` invocation.

- **Compaction logic in storage**: The `compact()` method in Step 4 already
  handles the 30-day TTL and "always retain most recent" rule.

Write tests:
- Alarm triggers compaction of old messages
- Most recent message survives compaction regardless of age
- Alarm re-schedules itself after firing
- Cursor expired error after compaction

Location: `workers/leader-board/src/swarm-do.ts`, `workers/leader-board/test/compaction.test.ts`

### Step 9: End-to-end integration tests

Write full WebSocket flow tests using Miniflare's WebSocket support:

- **Full lifecycle**: register swarm → connect → auth → send → watch → receive
  message → verify positions
- **Wire protocol compatibility**: Verify every frame type matches the exact
  JSON structure from SPEC.md. Ensure field names, types, and error codes are
  identical to what the local server adapter would produce.
- **Concurrent connections**: Two clients connected to the same swarm, one
  sends, the other watches — message delivered correctly
- **Reconnection**: Client disconnects after receiving a message, reconnects,
  watches from last cursor — receives next message
- **Compaction flow**: Send messages with backdated timestamps, trigger alarm,
  verify old messages removed, verify cursor_expired error for stale cursor

Location: `workers/leader-board/test/e2e.test.ts`

### Step 10: Wrangler deployment configuration and documentation

Finalize `wrangler.toml` for production deployment:

- Ensure DO migrations are configured correctly
- Add environment-specific configuration (production vs staging)
- Verify `wrangler deploy` succeeds (dry-run if no CF account in CI)

Add backreference comments to all source files:
```typescript
// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
```

Run the full test suite: `npx vitest run`

Location: `workers/leader-board/wrangler.toml`

## Dependencies

- **leader_board_core** (ACTIVE) — The portable core defines the behavioral
  contract that this adapter must satisfy. The spec (produced by
  `leader_board_spec`) defines the wire protocol and DO topology.
- **@noble/ed25519** — Pure JS Ed25519 implementation for signature verification
  in the CF Workers runtime. Fallback if Web Crypto API Ed25519 support is
  insufficient.
- **wrangler** — CF Workers CLI for local development and deployment.
- **vitest + miniflare** — Testing framework with CF Workers runtime simulation.
- **@cloudflare/workers-types** — TypeScript type definitions for the Workers
  runtime (DurableObject, DurableObjectStorage, WebSocket, etc.)

## Risks and Open Questions

- **Ed25519 in Workers runtime**: CF Workers support for Ed25519 via Web Crypto
  API may be limited. The `@noble/ed25519` package is a proven fallback that
  works in Workers. If Web Crypto works natively, prefer it for performance.
- **DO SQLite vs KV storage**: The spec describes the storage layout as
  key-value pairs (`{channel}:{zero-padded-position}`), but DO SQLite
  (available since 2024) provides better query capabilities for compaction and
  range reads. This plan uses SQLite. If SQLite is unavailable in the target
  CF plan, fall back to KV-style `storage.get()`/`storage.put()` with the
  zero-padded key format from the spec.
- **WebSocket hibernation**: CF Workers support WebSocket hibernation (DO
  doesn't consume CPU while waiting for messages). The watcher mechanism
  should leverage this for cost efficiency with long-lived watch connections.
  Implementation may need to use the Hibernation API
  (`DurableObject#webSocketMessage`, `DurableObject#webSocketClose`) instead
  of the basic WebSocket event listeners.
- **Concurrent position assignment**: Multiple simultaneous `send` operations
  to the same channel must not produce duplicate positions. DO storage
  transactions (via SQL) handle this, but need to verify that the
  `MAX(position) + 1` pattern is safe under concurrent access within a single
  DO (DOs are single-threaded, so this should be safe).
- **Wire protocol parity**: The test suite must verify frame-level
  compatibility with the local server adapter. Any divergence is a bug. A
  shared JSON schema or snapshot tests against known-good frames would add
  confidence.

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