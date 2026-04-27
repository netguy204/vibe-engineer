---
status: ACTIVE
ticket: null
parent_chunk: gateway_cleartext_api
code_paths:
- workers/leader-board/src/gateway-crypto.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/test/gateway-api.test.ts
- workers/leader-board/test/gateway-crypto.test.ts
code_references:
- ref: workers/leader-board/src/gateway-crypto.ts#recoverSeedFromBlob
  implements: "Hex-decode seed from encrypted blob (Python CLI stores seed.hex() as UTF-8)"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayAPI
  implements: "Use recoverSeedFromBlob instead of raw decryptBlob, wrap encrypt/decrypt in error handling"
- ref: workers/leader-board/test/gateway-api.test.ts#hashTokenText
  implements: "Fix test helper to hash raw token bytes matching production hashToken()"
- ref: workers/leader-board/test/gateway-api.test.ts#deriveTokenKeyLocal
  implements: "HKDF key derivation test helper matching production deriveTokenKey()"
- ref: workers/leader-board/test/gateway-api.test.ts#encryptBlobWithToken
  implements: "Fix test helper to encrypt hex-encoded seed string matching Python CLI protocol"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- invite_token_instant_expiry
- websocket_hibernation_compat
---

# Chunk Goal

## Minor Goal

The cleartext gateway's read/write API (`GET`/`POST /gateway/{token}/channels/{channel}/messages`) shares its crypto pipeline with the invite-page handler. Both paths resolve a token to a symmetric message key by:

1. Hashing the raw token bytes (not the hex string) with SHA-256 to look up the encrypted blob in storage.
2. Deriving an HKDF-SHA256 key from the raw token bytes (info `leader-board-invite-token`) and using it as the NaCl secretbox key for the blob.
3. Decrypting the blob, which contains the Ed25519 seed encoded as a hex UTF-8 string; the gateway hex-decodes the plaintext back to a 32-byte seed via `recoverSeedFromBlob`.
4. Deriving the message symmetric key from that seed via `deriveSymmetricKey` (SHA-512 → Curve25519 clamp → HKDF-SHA256, info `leader-board-message-encryption`).

`handleGatewayAPI` resolves the symmetric key through the shared `resolveTokenKey` helper and wraps decryption in try/catch so a crypto failure surfaces as a 401 / 500 JSON response instead of an unhandled exception (Cloudflare error 1101). The TypeScript test helpers (`hashTokenText`, `deriveTokenKeyLocal`, `encryptBlobWithToken`) mirror the production crypto so cross-language vectors and end-to-end gateway-API tests stay aligned with the Python CLI.

## Success Criteria

- `GET /gateway/{token}/channels/{channel}/messages?after=0` returns messages (not 1101)
- `POST /gateway/{token}/channels/{channel}/messages` accepts and encrypts messages
- The 10 pre-existing `gateway-api.test.ts` failures are fixed as part of this work
- End-to-end test: create invite → post message via gateway → read message via gateway

## Relationship to Parent

Parent chunk `gateway_cleartext_api` owns the gateway HTTP routes. This chunk owns the gateway-side half of the shared crypto contract with the Python CLI: the gateway API and the invite-page path agree on token hashing, key derivation, and the hex-encoded seed format, so the same encrypted blob round-trips through both handlers.