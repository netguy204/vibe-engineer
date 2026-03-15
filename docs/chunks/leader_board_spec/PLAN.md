# Implementation Plan

## Approach

This chunk produces documentation only — a new "Leader Board" section in
docs/trunk/SPEC.md. No code is written. The spec adapts the original
leader-board project design (at ../leader-board/docs/trunk/SPEC.md) to the new
architecture: swarm tenant model with asymmetric key pairs, end-to-end
encryption, cursor-based append-only log (replacing the at-most-once queue), a
portable core/adapter boundary, and Cloudflare Durable Object topology.

The spec must be precise enough that a conformance test suite can be written
against it. Every wire frame, error code, and behavioral guarantee should be
unambiguous.

**Testing note**: This is a documentation-only chunk. Per
docs/trunk/TESTING_PHILOSOPHY.md, tests verify behavior, not prose. The spec
itself will be validated by subsequent implementation chunks that write
conformance tests against it.

**Relevant decisions**:
- DEC-001 (uvx CLI): The leader board CLI will be `ve board` subcommands,
  consistent with the existing `ve` tool
- DEC-005 (no git prescription): The spec must not prescribe git operations for
  cursor persistence or key storage

## Sequence

### Step 1: Read and internalize the original leader-board spec

Read ../leader-board/docs/trunk/SPEC.md and ../leader-board/docs/trunk/GOAL.md
to understand the original design. Identify every concept that must be adapted:

| Original concept | Adaptation |
|------------------|------------|
| Shared-secret auth | Asymmetric key pair (sign/verify) |
| At-most-once delivery (message deleted on consume) | At-least-once (cursor-based, client advances) |
| Single watcher per channel | Multiple watchers, each with independent cursor |
| No encryption | E2E encryption (client-side, server sees ciphertext) |
| Standalone server binary | Portable core + host adapters |
| Single-instance server | Durable Object per swarm (multi-tenant) |
| No tenant isolation | Swarm = operator-global tenant boundary |
| No compaction | 30-day TTL compaction |

Location: Read-only — no file changes in this step.

### Step 2: Write the Leader Board overview and terminology

Add a new top-level section "## Leader Board" to docs/trunk/SPEC.md, placed
after the existing "## DRAFT Sections" line (or just before it — the new
section is not a draft). Include:

- Overview paragraph: what leader board is, why it exists, one-sentence
  relationship to the original leader-board project
- Terminology subsection defining: **Swarm**, **Channel**, **Message**,
  **Cursor**, **Steward**, **SOP (Standard Operating Procedure)**, **Adapter**

These terms will be referenced throughout the remaining subsections.

Location: docs/trunk/SPEC.md

### Step 3: Write the Swarm Model section

Define the operator-global tenant boundary:

- A swarm is identified by its public key
- One operator typically manages one swarm across many repos
- The asymmetric key pair (Ed25519) is generated at swarm creation time
- Private key stored in `~/.ve/keys/{swarm_id}.key` (operator-global)
- Public key registered with the server and stored alongside the private key
- Swarm ID is derived from the public key (e.g., base58 encoding of first 16
  bytes)
- All channels exist within a swarm — no cross-swarm communication
- Multiple swarms per server are supported (multi-tenant)

Location: docs/trunk/SPEC.md (within the Leader Board section)

### Step 4: Write the End-to-End Encryption section

Specify the encryption model:

- Message bodies are encrypted client-side before transmission
- The server stores and routes opaque ciphertext
- Only the channel name and cursor position are visible to the server
- Encryption uses a symmetric key derived from the swarm's private key (e.g.,
  HKDF with context string "leader-board-message-encryption")
- All swarm members holding the private key can encrypt and decrypt
- Key derivation algorithm and parameters specified precisely
- Ciphertext format: nonce (24 bytes) || encrypted_body
- Algorithm: XChaCha20-Poly1305 (NaCl secretbox)
- The server MUST NOT require or inspect message body contents

Location: docs/trunk/SPEC.md

### Step 5: Write the Append-Only Log Channel Model section

Define the channel as an ordered log:

- Each channel is an append-only, ordered log of messages
- Messages are assigned monotonically increasing positions (uint64, starting at 1)
- Position 0 is the "before first message" sentinel — watching from position 0
  receives the first message
- The server never deletes messages on delivery (contrast with the original
  leader-board design)
- Clients supply a cursor position when watching and receive the next message
  after that position
- If no message exists after the cursor, the server blocks (holds the
  WebSocket open) until one arrives
- Multiple clients can watch the same channel with independent cursors
- A single client receives one message per watch request, then must re-watch
  to receive the next

Location: docs/trunk/SPEC.md

### Step 6: Write the 30-Day TTL Compaction section

Define server-side compaction:

- Messages older than 30 days are eligible for removal by the server
- Compaction is a server-side background process; clients have no control over it
- The TTL is a heuristic — the server makes no guarantee about exact timing
- When a client presents a cursor older than the oldest retained message, the
  server returns a `cursor_expired` error with the earliest available position
- The client can then decide: resume from the earliest position (accepting a
  gap) or alert the operator
- The server MUST retain at least the most recent message in each channel
  regardless of age
- Compaction runs per-channel, not globally

Location: docs/trunk/SPEC.md

### Step 7: Write the Cursor-Based At-Least-Once Delivery section

Define the delivery guarantee:

- Clients persist their cursor locally (project-local, not operator-global)
- Cursor storage location: `.ve/board/cursors/{channel_name}.cursor`
- Cursor file contains a single uint64 value (the last-processed position)
- The client advances the cursor only after durably processing a message
- Processing order: receive message → process → write cursor → ack (optional
  explicit ack, or implicit via next watch with advanced cursor)
- Crash-and-resume: the client re-reads from the last persisted cursor,
  potentially re-processing the same message (at-least-once)
- The server has no visibility into client cursors — it sees only the position
  supplied in watch requests
- Contrast with original design: the original leader-board used at-most-once
  delivery (message deleted on consume); leader board uses at-least-once
  (message retained, client tracks position)

Location: docs/trunk/SPEC.md

### Step 8: Write the Wire Protocol section

Define the WebSocket JSON frame protocol. All frames assume an authenticated
connection.

**Client → Server frames:**

- `watch`: `{"type": "watch", "channel": "<name>", "swarm": "<swarm_id>", "cursor": <uint64>}`
- `send`: `{"type": "send", "channel": "<name>", "swarm": "<swarm_id>", "body": "<base64-ciphertext>"}`
- `channels`: `{"type": "channels", "swarm": "<swarm_id>"}`
- `swarm_info`: `{"type": "swarm_info", "swarm": "<swarm_id>"}`

**Server → Client frames:**

- `message`: `{"type": "message", "channel": "<name>", "position": <uint64>, "body": "<base64-ciphertext>", "sent_at": "<ISO8601>"}`
- `ack`: `{"type": "ack", "channel": "<name>", "position": <uint64>}`
- `channels_list`: `{"type": "channels_list", "channels": [{"name": "...", "head_position": <uint64>, "oldest_position": <uint64>}]}`
- `swarm_info`: `{"type": "swarm_info", "swarm": "<swarm_id>", "created_at": "<ISO8601>"}`
- `error`: `{"type": "error", "code": "<error_code>", "message": "<description>", ...}`

**Error codes:**
- `auth_failed`: signature verification failed
- `cursor_expired`: cursor position older than oldest retained message (includes
  `earliest_position` field)
- `channel_not_found`: referenced channel does not exist (for watch only — send
  creates implicitly)
- `invalid_frame`: malformed JSON or missing required fields
- `swarm_not_found`: swarm ID not registered

**Behavioral rules:**
- After sending a `watch` frame, the server holds the connection open until a
  message at position > cursor exists, then sends exactly one `message` frame
- After sending a `send` frame, the server responds with an `ack` containing
  the assigned position
- Channels are created implicitly on first `send`
- Body field in `send` and `message` frames contains base64-encoded ciphertext

Location: docs/trunk/SPEC.md

### Step 9: Write the Authentication Flow section

Define asymmetric auth:

- Client signs a challenge during the WebSocket handshake
- Handshake sequence:
  1. Client opens WebSocket connection with `swarm` query parameter
  2. Server sends a `challenge` frame: `{"type": "challenge", "nonce": "<random-32-bytes-hex>"}`
  3. Client signs the nonce with the swarm's Ed25519 private key
  4. Client sends `auth` frame: `{"type": "auth", "swarm": "<swarm_id>", "signature": "<hex-signature>"}`
  5. Server looks up the public key for the swarm ID, verifies the signature
  6. On success: `{"type": "auth_ok"}`
  7. On failure: `{"type": "error", "code": "auth_failed", ...}` and connection closed
- All subsequent frames on an authenticated connection are trusted
- The server stores only public keys — compromise of the server does not
  compromise swarm private keys
- Swarm registration: `{"type": "register_swarm", "swarm": "<swarm_id>", "public_key": "<hex-ed25519-pubkey>"}` — sent once during swarm creation; server stores the mapping

Location: docs/trunk/SPEC.md

### Step 10: Write the Core/Adapter Boundary section

Define the portable core interface:

- The core is a host-independent library that owns: swarm state management,
  channel log operations (append, read-from-cursor), auth verification, message
  position assignment
- The core treats message bodies as opaque byte strings — no
  encryption/decryption
- The core has no concept of channel "types" — steward vs. changelog is a
  client convention
- The core exposes an interface (not a wire protocol) that adapters call

**Core interface (conceptual — language-agnostic):**

```
# Swarm operations
register_swarm(swarm_id, public_key) → ok | error
verify_auth(swarm_id, nonce, signature) → ok | error

# Channel operations
append(swarm_id, channel, body_bytes) → position
read_after(swarm_id, channel, cursor) → (position, body_bytes, sent_at) | blocks
list_channels(swarm_id) → [{name, head_position, oldest_position}]

# Compaction
compact(swarm_id, channel, min_age_days) → positions_removed
```

**Adapter responsibilities:**
- Transport (WebSocket, HTTP, etc.)
- Durable storage of the log (filesystem, Durable Object storage, etc.)
- Connection lifecycle management
- Wire protocol encoding/decoding (JSON frames, base64)

Location: docs/trunk/SPEC.md

### Step 11: Write the Durable Object Topology section

Define the hosted multi-tenant variant:

- One Cloudflare Durable Object per swarm
- The Worker routes incoming WebSocket connections to the correct swarm DO
  based on the swarm ID in the handshake
- The DO wraps the portable core, using DO storage for the append-only log
- DO storage layout: key-value pairs keyed by `{channel}:{position}`
- DO alarm for compaction (periodic 30-day TTL sweep)
- The local server adapter and DO adapter speak the identical wire protocol —
  clients cannot distinguish between backends
- Rate limiting and abuse prevention are handled at the Worker/CF level, not in
  the core

Location: docs/trunk/SPEC.md

### Step 12: Write the Steward SOP Document Format section

Define the project-local SOP schema:

- Stored at `docs/trunk/STEWARD.md` in each project
- YAML frontmatter with fields:
  ```yaml
  ---
  steward_name: "<human-readable name>"
  swarm: "<swarm_id>"
  channel: "<channel-name>"
  changelog_channel: "<channel-name>"
  behavior:
    mode: autonomous | queue | custom
    custom_instructions: "<markdown>" | null
  ---
  ```
- `autonomous`: steward triages, acts, and publishes results without human
  intervention
- `queue`: steward creates work items (chunks, investigations) for human
  review but does not implement
- `custom`: steward follows the freeform instructions in
  `custom_instructions`
- The SOP is created by the `/steward-setup` skill via an interactive
  interview with the operator
- The steward agent reads the SOP at startup and on each watch-respond-rewatch
  iteration to pick up live changes

Location: docs/trunk/SPEC.md

### Step 13: Write the Guarantees and Limits sections

Consolidate guarantees:

**Guarantees:**
- FIFO within a channel (messages ordered by position)
- At-least-once delivery (client-side cursor management)
- Durability (messages persist across server restarts until compacted)
- End-to-end encryption (server never sees plaintext)
- Cryptographic isolation between swarms

**Non-guarantees:**
- No cross-channel ordering
- No exactly-once delivery (clients must be idempotent)
- No guaranteed compaction timing (30-day TTL is a heuristic)

**Limits:**
- Channel name: 1-128 characters, `[a-zA-Z0-9_-]`
- Message body (plaintext, before encryption): maximum 1 MB
- Swarm ID: derived from public key, 22–44 characters (base58)

Location: docs/trunk/SPEC.md

### Step 14: Review for internal consistency

Read the complete Leader Board section end-to-end and verify:

- All terminology used is defined in the Terminology subsection
- Wire protocol frames reference the correct field names and types
- The encryption section and wire protocol section agree on body encoding
- The core interface and adapter responsibilities are disjoint (no overlap)
- The cursor model, compaction, and error codes form a consistent system
- Divergences from the original leader-board design are noted where they occur
- The spec is sufficient to write conformance tests for each guarantee

Location: docs/trunk/SPEC.md (read-only review)

## Risks and Open Questions

- **Encryption algorithm choice**: XChaCha20-Poly1305 is specified here but the
  operator may prefer a different algorithm. The spec should be opinionated but
  note the choice and rationale.
- **Key derivation for encryption**: Using HKDF from the Ed25519 private key to
  derive a symmetric encryption key is standard practice (libsodium
  crypto_sign_ed25519_sk_to_curve25519 + crypto_box), but the exact derivation
  path needs to be unambiguous.
- **Swarm registration security**: The `register_swarm` operation is
  unauthenticated (first contact). A production deployment may need rate
  limiting or proof-of-work to prevent spam registration. The spec should
  acknowledge this.
- **Cursor storage location**: `.ve/board/cursors/` is project-local, but the
  `.ve/` directory may not exist in non-git contexts (per DEC-002). Need to
  clarify that cursor storage follows the same root as other VE state.
- **Backward compatibility with original leader-board**: The original project
  at ../leader-board/ uses a different protocol. This spec is a clean break,
  not a backward-compatible evolution. This should be stated explicitly.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->
