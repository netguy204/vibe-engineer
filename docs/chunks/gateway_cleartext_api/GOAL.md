---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/gateway-crypto.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/storage.ts
- workers/leader-board/src/index.ts
- workers/leader-board/test/gateway-crypto.test.ts
- workers/leader-board/test/gateway-api.test.ts
- workers/leader-board/package.json
code_references:
- ref: workers/leader-board/src/gateway-crypto.ts#hashToken
  implements: "SHA-256 token hashing for key blob lookup"
- ref: workers/leader-board/src/gateway-crypto.ts#decryptBlob
  implements: "NaCl secretbox decryption of encrypted key blob to recover Ed25519 seed"
- ref: workers/leader-board/src/gateway-crypto.ts#deriveSymmetricKey
  implements: "Ed25519→Curve25519→HKDF-SHA256 symmetric key derivation (wire-compatible with Python crypto)"
- ref: workers/leader-board/src/gateway-crypto.ts#decryptMessage
  implements: "NaCl secretbox message decryption for GET endpoint"
- ref: workers/leader-board/src/gateway-crypto.ts#encryptMessage
  implements: "NaCl secretbox message encryption for POST endpoint"
- ref: workers/leader-board/src/storage.ts#SwarmStorage::readAfterBatch
  implements: "Batch message read for GET endpoint (multiple messages after cursor)"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayAPI
  implements: "Cleartext gateway HTTP handler (GET/POST with token resolution, key derivation, long-poll)"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::wakePendingPolls
  implements: "Long-poll notification when new messages arrive on a channel"
- ref: workers/leader-board/src/index.ts
  implements: "Worker entry point routing for /gateway/{token}/channels/ paths"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- gateway_token_storage
created_after:
- swarm_monitor_command
---

# Chunk Goal

## Minor Goal

Add cleartext gateway HTTP routes to the leader-board Durable Object worker, enabling agents to read and write swarm messages via plain HTTP using an invite token (see `docs/investigations/agent_invite_links`). Depends on `gateway_token_storage` for the encrypted key blob storage.

Endpoints:
- **GET /gateway/{token}/channels/{channel}/messages?after={cursor}** — returns plaintext messages (server decrypts using token → key)
- **POST /gateway/{token}/channels/{channel}/messages** — accepts plaintext body, server encrypts and stores
- Optional long-poll variant with `?wait=30` for agents that can't use WebSockets

On each request, the server retrieves `encrypt(private_key, token)` from storage using `hash(token)`, decrypts the key in memory, performs the crypto operation, then discards the key. The plaintext key is never persisted.

## Success Criteria

- GET endpoint returns decrypted messages for a valid token
- POST endpoint encrypts and stores messages for a valid token
- Invalid/revoked tokens return 401
- Token is used transiently — never stored in plaintext
- Long-poll variant blocks until messages arrive or timeout