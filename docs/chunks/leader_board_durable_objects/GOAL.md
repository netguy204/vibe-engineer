---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/package.json
- workers/leader-board/tsconfig.json
- workers/leader-board/wrangler.toml
- workers/leader-board/src/index.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/storage.ts
- workers/leader-board/src/auth.ts
- workers/leader-board/src/protocol.ts
- workers/leader-board/test/protocol.test.ts
- workers/leader-board/test/auth.test.ts
- workers/leader-board/test/storage.test.ts
- workers/leader-board/test/swarm-do.test.ts
- workers/leader-board/test/index.test.ts
- workers/leader-board/test/compaction.test.ts
- workers/leader-board/test/e2e.test.ts
code_references:
  - ref: workers/leader-board/src/index.ts
    implements: "Worker entry point — routes WebSocket connections to correct SwarmDO by swarm query param or invite token path"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO
    implements: "Durable Object class per swarm — owns connection lifecycle, auth handshake, post-auth frame dispatch, watcher wake-up, compaction alarm, and WebSocket keepalive heartbeats"
  - ref: workers/leader-board/src/swarm-do.ts#Env
    implements: "Worker environment interface declaring SWARM_DO binding and TOKEN_SWARM_INDEX KV namespace"
  - ref: workers/leader-board/src/storage.ts#SwarmStorage
    implements: "DO SQLite storage layer mirroring Python StorageAdapter — append-only log, monotonic positions, compaction with retain-most-recent"
  - ref: workers/leader-board/src/auth.ts#generateChallenge
    implements: "Random 32-byte challenge nonce generation for auth handshake"
  - ref: workers/leader-board/src/auth.ts#verifySignature
    implements: "Ed25519 signature verification via @noble/ed25519"
  - ref: workers/leader-board/src/protocol.ts#parseHandshakeFrame
    implements: "Handshake frame parsing and validation (auth, register_swarm)"
  - ref: workers/leader-board/src/protocol.ts#parsePostAuthFrame
    implements: "Post-auth frame parsing — watch, send, channels, swarm_info with channel name and body size validation"
  - ref: workers/leader-board/src/protocol.ts#serializeFrame
    implements: "Server frame JSON serialization"
  - ref: workers/leader-board/src/protocol.ts#ProtocolError
    implements: "Typed error class for wire protocol violations"
  - ref: workers/leader-board/wrangler.toml
    implements: "Cloudflare Workers deployment config — DO binding, SQLite migration, KV namespace, compatibility flags"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- leader_board_core
created_after:
- finalize_double_commit
---

# Chunk Goal

## Minor Goal

Implement the Cloudflare Durable Objects adapter that wraps the portable core.
One DO class per swarm. The Worker routes incoming WebSocket connections to the
correct swarm DO based on the auth handshake.

This is the **hosted multi-tenant deployment** that the project maintainer
operates for all VE users. Must speak the identical wire protocol as the local
server adapter.

## Success Criteria

- Cloudflare Worker + Durable Object deployment configuration exists
- Worker routes WebSocket connections to the correct swarm DO
- DO wraps the portable core and persists state via DO storage (SQLite)
- Wire protocol is identical to the local server adapter
- Auth handshake rejects invalid tokens with appropriate HTTP status
- Compaction runs on the 30-day TTL schedule within DO storage
- Deployable via `wrangler deploy` or equivalent

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->