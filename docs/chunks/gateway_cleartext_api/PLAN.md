

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk adds cleartext HTTP gateway endpoints to the leader-board Durable Object worker, allowing agents to read and write swarm messages via plain HTTP using an invite token. It builds directly on the `gateway_token_storage` chunk, which provides the encrypted key blob storage (`gateway_keys` table, `putGatewayKey`/`getGatewayKey`/`deleteGatewayKey` on `SwarmStorage`).

**High-level flow per request:**

1. Agent sends `GET /gateway/{token}/channels/{channel}/messages?after=0` with the raw token in the URL path
2. Worker entry point computes `SHA-256(token)` to get `token_hash`, extracts `swarm_id` from the gateway key record, and routes to the correct DO
3. DO retrieves `encrypted_blob` via `storage.getGatewayKey(token_hash)`
4. DO decrypts the blob using the token to recover the Ed25519 seed (XSalsa20-Poly1305 / NaCl secretbox)
5. DO derives the symmetric message key from the seed (Ed25519 → Curve25519 → HKDF-SHA256, matching `src/board/crypto.py`)
6. For GET: reads messages from storage, decrypts each body, returns plaintext JSON array
7. For POST: encrypts the plaintext body, stores as ciphertext via `storage.appendMessage()`
8. Plaintext key material is discarded after the request completes

**Key design choices:**

1. **Crypto module in TypeScript.** A new `src/gateway-crypto.ts` module implements the same algorithms as the Python `src/board/crypto.py`: XSalsa20-Poly1305 (via `tweetnacl`), Ed25519→Curve25519 conversion (SHA-512 + clamping via Web Crypto), and HKDF-SHA256 (via `@noble/hashes`). This ensures wire-compatible encryption with the Python client.

2. **Token-based routing without `?swarm` query param.** Unlike the `/gateway/keys` routes which require `?swarm=<id>`, the cleartext API routes derive the swarm from the token. The worker hashes the token, looks up the gateway key record (which was stored scoped to a specific DO/swarm), and routes accordingly. This means the entry point needs a new lookup mechanism — a global index or a two-step fetch. The simplest approach: store `swarm_id` alongside the encrypted blob in `gateway_keys`, so the Worker can determine routing from the token hash alone. The `gateway_token_storage` chunk already stores blobs per-DO, but the Worker entry point doesn't know which DO to ask. **Resolution:** Add a KV namespace or a convention where the CLI includes `swarm_id` in the PUT body (it already does — the investigation specifies `{token_hash, encrypted_blob, swarm_id}`). The Worker entry point can then require `?swarm=<id>` on gateway API routes too, matching the existing pattern. This is the simplest approach and avoids a global index.

3. **Batch read for GET endpoint.** The existing `storage.readAfter()` returns a single message. The GET endpoint should return multiple messages. Add a `readAfterBatch(channel, cursor, limit)` method to `SwarmStorage` that returns up to `limit` messages after the cursor.

4. **Long-poll via DO concurrency.** Cloudflare DOs handle concurrent `fetch()` calls via JavaScript's event loop. A long-poll request creates a Promise with a resolver stored in a pending-polls map. When a POST writes a new message, it resolves any pending polls for that channel. A `setTimeout` provides the deadline. This mirrors the existing WebSocket watcher pattern.

5. **TDD per TESTING_PHILOSOPHY.md.** Tests written first using `@cloudflare/vitest-pool-workers` + `SELF.fetch`. Tests cover: valid token reads/writes, invalid token 401s, long-poll timeout behavior, and the full round-trip (POST cleartext → GET cleartext → verify match).

## Subsystem Considerations

No existing subsystems are relevant. This work is entirely within the Cloudflare Worker/DO layer.

## Sequence

### Step 1: Add npm dependencies for server-side crypto

Install `tweetnacl` (XSalsa20-Poly1305 secretbox) and `@noble/hashes` (HKDF-SHA256, SHA-256, SHA-512) in the worker package.

```bash
cd workers/leader-board && npm install tweetnacl @noble/hashes
```

`tweetnacl` provides NaCl secretbox (XSalsa20-Poly1305), which is wire-compatible with Python's `nacl.secret.SecretBox`. `@noble/hashes` provides HKDF and SHA-2 primitives. Both are pure JS and work in Cloudflare Workers.

Location: `workers/leader-board/package.json`

### Step 2: Implement the gateway crypto module

Create `src/gateway-crypto.ts` with functions that replicate the Python `src/board/crypto.py` algorithms:

- **`hashToken(token: string): Promise<string>`** — SHA-256 hash of the token, returned as hex. Used to look up the encrypted key blob.
- **`decryptBlob(encryptedBlobB64: string, token: string): Uint8Array`** — Decrypt the base64-encoded encrypted blob using the token as the NaCl secretbox key. Returns the raw Ed25519 seed (32 bytes). The token must be 32 bytes (hex-encoded = 64 chars); decode from hex before using as key.
- **`deriveSymmetricKey(seed: Uint8Array): Promise<Uint8Array>`** — Replicate the Python `derive_symmetric_key`: SHA-512(seed) → take first 32 bytes → clamp (Ed25519→Curve25519 conversion) → HKDF-SHA256 with info=`"leader-board-message-encryption"` and empty salt → 32-byte symmetric key.
- **`decryptMessage(ciphertextB64: string, symmetricKey: Uint8Array): string`** — NaCl secretbox open on base64-decoded ciphertext. Returns plaintext UTF-8 string.
- **`encryptMessage(plaintext: string, symmetricKey: Uint8Array): string`** — NaCl secretbox seal on UTF-8 plaintext. Returns base64-encoded nonce+ciphertext.

The clamping for Ed25519→Curve25519 is: `bytes[0] &= 248; bytes[31] &= 127; bytes[31] |= 64;`

Add `// Chunk: docs/chunks/gateway_cleartext_api - Server-side crypto for cleartext gateway` backreference.

Location: `workers/leader-board/src/gateway-crypto.ts`

### Step 3: Write failing tests for the gateway crypto module

Create `test/gateway-crypto.test.ts` with tests that verify wire compatibility with the Python crypto:

1. **Round-trip encrypt/decrypt** — encrypt a message, decrypt it, verify plaintext matches
2. **Key derivation determinism** — given a known seed, verify `deriveSymmetricKey` produces the expected key (pre-compute the expected value using the Python code)
3. **Blob decrypt** — create an encrypted blob with a known token/key, verify `decryptBlob` recovers the original seed
4. **Cross-language compatibility** — encrypt a message with known key in Python, verify the TS code decrypts it (embed the base64 ciphertext as a test constant)

Location: `workers/leader-board/test/gateway-crypto.test.ts`

### Step 4: Add `readAfterBatch` to SwarmStorage

Add a new method to `SwarmStorage`:

```typescript
readAfterBatch(channel: string, cursor: number, limit: number = 50): StoredMessage[] {
  // SELECT ... WHERE channel = ? AND position > ? ORDER BY position ASC LIMIT ?
}
```

Returns up to `limit` messages after the cursor position. Default limit of 50 prevents unbounded reads. This is the batch equivalent of the existing `readAfter()` single-message method.

Add `// Chunk: docs/chunks/gateway_cleartext_api` backreference.

Location: `workers/leader-board/src/storage.ts`

### Step 5: Write failing tests for the cleartext gateway HTTP routes

Create `test/gateway-api.test.ts` with tests that exercise the full cleartext API through `SELF.fetch`. These tests need a setup helper that:
- Registers a swarm (WebSocket handshake with `register_swarm`)
- Generates a token, encrypts a known Ed25519 seed with it, stores the blob via `PUT /gateway/keys`

Test cases:

1. **POST stores an encrypted message** — `POST /gateway/{token}/channels/{channel}/messages?swarm={id}` with plaintext JSON body `{body: "hello"}`, expect 200 with `{position, channel}`
2. **GET retrieves decrypted messages** — after POST, `GET /gateway/{token}/channels/{channel}/messages?after=0&swarm={id}`, expect 200 with `{messages: [{position, body: "hello", sent_at}]}`
3. **Full round-trip** — POST cleartext, GET cleartext, verify the plaintext matches
4. **WebSocket client reads what gateway POST wrote** — POST via gateway, read via WebSocket, decrypt client-side, verify match (proves encryption compatibility)
5. **Gateway GET reads what WebSocket client wrote** — send encrypted via WebSocket, GET via gateway, verify plaintext matches
6. **Invalid token returns 401** — use a random token with no stored blob, expect 401
7. **Revoked token returns 401** — store blob, DELETE it, then try GET, expect 401
8. **Long-poll returns immediately if messages exist** — POST then GET with `?wait=5`, should return immediately
9. **Long-poll blocks then returns on new message** — GET with `?wait=5&after=0` on empty channel, POST in parallel, GET should return with the message
10. **Long-poll returns empty on timeout** — GET with `?wait=1&after=999` on empty channel, expect 200 with `{messages: []}` after ~1s

Location: `workers/leader-board/test/gateway-api.test.ts`

### Step 6: Add gateway route handling to SwarmDO

Extend `SwarmDO.fetch()` to handle `/gateway/{token}/channels/{channel}/messages` paths alongside the existing `/gateway/keys` routes.

Add a new private method `handleGatewayAPI(request, url)` that:

1. **Parses the URL:** Extract `token` and `channel` from the path. Validate channel name using the same regex as the WebSocket protocol (`/^[a-zA-Z0-9_-]{1,128}$/`).
2. **Resolves the token:** Call `hashToken(token)` → `storage.getGatewayKey(tokenHash)`. If not found, return 401 JSON `{error: "Invalid or revoked token"}`.
3. **Derives keys:** Call `decryptBlob(encryptedBlob, token)` → `deriveSymmetricKey(seed)`. Cache nothing — derive per request, discard after.
4. **Dispatches by method:**

   **GET** — Read `?after` cursor (default 0) and `?limit` (default 50, max 200). Call `storage.readAfterBatch(channel, cursor, limit)`. Decrypt each message body. If no messages and `?wait` is present (1-60 seconds), register a pending poll and await resolution or timeout. Return 200 JSON:
   ```json
   {
     "messages": [
       {"position": 1, "body": "plaintext", "sent_at": "..."},
       ...
     ]
   }
   ```

   **POST** — Parse JSON body `{body: "plaintext message"}`. Validate body is a non-empty string and within size limit. Encrypt the body using `encryptMessage(body, symmetricKey)`. Call `storage.appendMessage(channel, ciphertextB64)`. Wake any pending long-polls and WebSocket watchers on this channel. Return 200 JSON:
   ```json
   {"position": 1, "channel": "changelog"}
   ```

5. **Error handling:** Wrap crypto operations in try/catch — if decryption fails (corrupted blob, wrong token), return 401. This handles the case where a token exists in storage but the blob is corrupted.

Add `// Chunk: docs/chunks/gateway_cleartext_api - Cleartext gateway HTTP handler` backreference.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 7: Add long-poll infrastructure to SwarmDO

Add a `pendingPolls` map alongside the existing `watchers` map:

```typescript
private pendingPolls: Map<string, Set<{
  channel: string;
  cursor: number;
  resolve: (msgs: StoredMessage[]) => void;
}>> = new Map();
```

When a GET request has `?wait=N`:
1. First check for messages — if any exist, return immediately
2. Create a Promise and store its resolver in `pendingPolls` keyed by channel
3. Set a `setTimeout(N * 1000)` that resolves with empty array
4. `await` the Promise

Modify `wakeWatchers()` (or add a companion `wakePendingPolls()`) to resolve pending polls when new messages arrive on a channel. Read the messages for each poll using `readAfterBatch(channel, poll.cursor, limit)`, decrypt them, and resolve.

Important: clean up the timeout if the poll is resolved early (message arrived before timeout).

Location: `workers/leader-board/src/swarm-do.ts`

### Step 8: Update Worker entry point routing

Extend `src/index.ts` to route `/gateway/{token}/channels/...` paths to the correct DO:

```typescript
if (url.pathname.match(/^\/gateway\/[^/]+\/channels\//)) {
  // Gateway cleartext API — requires ?swarm param
  const id = env.SWARM_DO.idFromName(swarmId);
  const stub = env.SWARM_DO.get(id);
  return stub.fetch(request);
}
```

The `?swarm` query parameter is still required (consistent with all other routes). The `invite_cli_command` chunk will be responsible for embedding the swarm ID in invite URLs.

Add `// Chunk: docs/chunks/gateway_cleartext_api` backreference.

Location: `workers/leader-board/src/index.ts`

### Step 9: Run all tests and verify

Run the full test suite:
```bash
cd workers/leader-board && npm test
```

Verify:
- All new gateway-crypto tests pass (Step 3)
- All new gateway-api tests pass (Step 5)
- All existing tests remain green (WebSocket behavior unchanged)
- The non-WebSocket, non-gateway path still returns 426

### Step 10: Generate cross-language test vectors

Use the Python crypto module to generate a set of known test vectors (seed, symmetric key, plaintext, ciphertext, token, encrypted blob) and embed them as constants in `test/gateway-crypto.test.ts`. This ensures the TypeScript crypto implementation is byte-for-byte compatible with the Python client. Run both test suites to confirm.

Create a small script in the chunk directory (`docs/chunks/gateway_cleartext_api/generate-test-vectors.py`) that outputs the vectors as JSON.

Location: `docs/chunks/gateway_cleartext_api/generate-test-vectors.py`, `workers/leader-board/test/gateway-crypto.test.ts`

## Dependencies

- **`gateway_token_storage` chunk (ACTIVE):** Provides `SwarmStorage.putGatewayKey/getGatewayKey/deleteGatewayKey`, the `gateway_keys` table, and the `/gateway/keys` HTTP routes. This chunk builds directly on that storage layer.
- **`tweetnacl` npm package:** XSalsa20-Poly1305 (NaCl secretbox) for decrypting key blobs and encrypting/decrypting message bodies. Pure JS, no native dependencies, Cloudflare Workers compatible.
- **`@noble/hashes` npm package:** HKDF-SHA256 for symmetric key derivation, SHA-512 for Ed25519→Curve25519 conversion. From the same `noble` family as `@noble/ed25519` already in use.

## Risks and Open Questions

- **Crypto wire compatibility.** The Python client uses PyNaCl's `SecretBox` (XSalsa20-Poly1305). The TS implementation must produce byte-compatible ciphertext. The cross-language test vectors (Step 10) are the primary mitigation. If `tweetnacl`'s secretbox has any subtle differences from PyNaCl's, this will surface immediately in those tests.
- **Ed25519→Curve25519 conversion correctness.** The Python code uses `nacl.bindings.crypto_sign_ed25519_sk_to_curve25519`. We replicate this with SHA-512 + clamping. If the clamping or byte ordering differs, key derivation will silently produce wrong keys. Again, test vectors are the mitigation.
- **Long-poll and DO concurrency.** DOs are single-threaded but handle concurrent `fetch()` calls via the JavaScript event loop. A long-polling request holds an open Promise while other requests can still be processed. If Cloudflare imposes limits on concurrent pending requests per DO, long-poll could fail under load. Mitigation: cap `?wait` at 60 seconds and document that high-concurrency use cases should prefer WebSockets.
- **Token in URL path.** The token appears in the URL, which means it's visible in server logs, CDN logs, and browser history. This is acceptable per the investigation's threat model (the server is trusted to see the token in-flight), but operators should be aware. HTTPS ensures the URL is encrypted in transit.
- **No rate limiting.** These routes have no rate limiting. A brute-force attack against token hashes is infeasible (tokens are 32 random bytes = 256 bits of entropy), but an attacker could abuse the endpoints for DoS. Rate limiting is out of scope for this chunk.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->