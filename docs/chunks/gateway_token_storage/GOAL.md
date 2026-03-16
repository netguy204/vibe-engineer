---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/storage.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/index.ts
- workers/leader-board/test/gateway-keys.test.ts
code_references:
- ref: workers/leader-board/src/storage.ts#SwarmStorage::putGatewayKey
  implements: "Store encrypted key blob indexed by token hash (INSERT OR REPLACE)"
- ref: workers/leader-board/src/storage.ts#SwarmStorage::getGatewayKey
  implements: "Retrieve encrypted key blob by token hash"
- ref: workers/leader-board/src/storage.ts#SwarmStorage::deleteGatewayKey
  implements: "Delete encrypted key blob for revocation"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayKeys
  implements: "HTTP route handler dispatching PUT/GET/DELETE for gateway keys"
- ref: workers/leader-board/src/index.ts
  implements: "Worker entry point routing /gateway/keys paths as plain HTTP to DO"
- ref: workers/leader-board/test/gateway-keys.test.ts
  implements: "Round-trip tests: store → retrieve → delete → 404"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- swarm_monitor_command
---

# Chunk Goal

## Minor Goal

Add encrypted key blob storage routes to the leader-board Durable Object worker. This is the foundational storage layer for the cleartext gateway invite system (see `docs/investigations/agent_invite_links`).

Routes:
- **PUT /gateway/keys** — accepts `{token_hash, encrypted_blob, swarm_id}`, stores the encrypted key blob indexed by `hash(token)`
- **GET /gateway/keys/{token_hash}** — returns the encrypted blob (internal use by the cleartext API)
- **DELETE /gateway/keys/{token_hash}** — deletes the blob (revocation)

The security model: the private key is encrypted using the token as the encryption key, and stored indexed by `hash(token)`. The server never has access to the plaintext private key at rest — given only `hash(token)` and `encrypt(private_key, token)`, the key is irrecoverable without the token.

## Success Criteria

- PUT route stores encrypted blobs indexed by token hash
- GET route retrieves encrypted blobs by token hash
- DELETE route removes blobs (enabling revocation)
- Storage is scoped to the swarm's Durable Object
- Tests verify round-trip: store → retrieve → delete → 404