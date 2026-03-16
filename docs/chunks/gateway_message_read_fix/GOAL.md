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

Fix the cleartext gateway returning Cloudflare error 1101 (Worker internal error / unhandled exception) when reading messages via `GET /gateway/{token}/channels/{channel}/messages`. The invite page renders correctly and invite creation works, but the actual message read/write API throws an unhandled exception.

Error 1101 means the Worker threw an unhandled exception. Likely causes:
- **Crypto mismatch after `invite_token_instant_expiry` fix**: The `hashToken()` and `deriveSymmetricKey()` changes may have broken the gateway API handler (`handleGatewayAPI`) which uses the same crypto functions. The token hash fix (raw bytes vs hex string) and HKDF key derivation need to be consistent across all code paths.
- **`deriveSymmetricKey` input format**: The attention reason from `invite_token_instant_expiry` noted "swarm-do.ts passes hex-encoded UTF-8 bytes to deriveSymmetricKey instead of raw 32-byte seed" — this may not have been fully fixed.
- **Missing error handling**: The gateway API handler may lack try/catch, causing crypto failures to bubble up as unhandled exceptions.

Repro: `curl 'https://leader-board.zack-98d.workers.dev/gateway/<token>/channels/<channel>/messages?after=0'` → error 1101

## Success Criteria

- `GET /gateway/{token}/channels/{channel}/messages?after=0` returns messages (not 1101)
- `POST /gateway/{token}/channels/{channel}/messages` accepts and encrypts messages
- The 10 pre-existing `gateway-api.test.ts` failures are fixed as part of this work
- End-to-end test: create invite → post message via gateway → read message via gateway

## Relationship to Parent

Parent chunk `gateway_cleartext_api` implemented the gateway HTTP routes. The `invite_token_instant_expiry` chunk fixed crypto for the invite page path but the same crypto changes likely broke the gateway API path where `deriveSymmetricKey` is called with the wrong input format.