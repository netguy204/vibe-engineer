

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Three independent bugs cause the gateway API 1101 error. All stem from the
`invite_token_instant_expiry` chunk fixing the invite-page crypto path without
propagating those same fixes to the gateway API test helpers, and from a
production-code mismatch in how the decrypted blob content is interpreted.

**Root cause analysis:**

The Python CLI (`src/cli/board.py`) creates invite blobs as follows:
1. `token = secrets.token_bytes(32)` — 32 random bytes
2. `token_hash = hashlib.sha256(token).hexdigest()` — hash raw bytes
3. `sym_key = derive_token_key(token)` — HKDF-SHA256 of raw bytes
4. `encrypted_blob = encrypt(seed.hex(), sym_key)` — encrypts **hex-encoded seed string**

The `invite_token_instant_expiry` chunk fixed the production crypto
(`gateway-crypto.ts`) to match steps 2–3 (raw-byte hashing, HKDF key
derivation) and fixed the `invite-page.test.ts` helpers. But it did NOT fix
the `gateway-api.test.ts` helpers, which still use the old broken crypto.
Additionally, the production `handleGatewayAPI` handler doesn't account for
the blob containing a hex-encoded seed string (step 4).

**Bug 1 — Test: `hashTokenText` hashes wrong input**
`gateway-api.test.ts` line 43–47 hashes the UTF-8 encoding of the hex string
(`TextEncoder.encode(tokenHex)`) instead of the raw token bytes
(`hexToBytes(tokenHex)`). This means the test stores the blob under a different
hash than what the production `hashToken()` computes, so the server returns 401.

**Bug 2 — Test: `encryptBlobWithToken` uses wrong key**
`gateway-api.test.ts` line 49–57 uses `hexToBytes(tokenHex)` as the raw NaCl
secretbox key instead of deriving via `HKDF-SHA256(token, "leader-board-invite-token")`.
The production `decryptBlob()` now uses the HKDF-derived key, so decryption fails.
Additionally, this helper encrypts raw seed bytes instead of the hex-encoded
seed string that the Python CLI produces.

**Bug 3 — Production: `handleGatewayAPI` seed format mismatch**
In `swarm-do.ts` line 365–366, `decryptBlob()` returns the plaintext bytes from
the blob. When the blob was created by the Python CLI, the plaintext is the
UTF-8 encoding of `seed.hex()` (64 bytes of hex characters). But
`deriveSymmetricKey()` is called directly on those 64 bytes instead of first
decoding them back to the 32-byte raw seed. This produces a wrong symmetric key.
When `decryptMessage()` (line 400) then tries to decrypt a message with this
wrong key, it throws — and that throw is OUTSIDE the try/catch block
(lines 355–372), causing an unhandled exception → Cloudflare error 1101.

**Fix strategy:**

1. Fix the test helpers to match the invite-page test helpers (already correct)
2. Add a hex-decode step in the production handler between `decryptBlob()` and
   `deriveSymmetricKey()`
3. Wrap `decryptMessage` / `encryptMessage` calls in error handling

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md: fix the test helpers first
(making them match the Python CLI protocol), confirm they still fail for the
right reason (production bug 3), then fix production code.

## Sequence

### Step 1: Fix `hashTokenText` in `gateway-api.test.ts`

Replace the UTF-8 hex-string hashing with raw-byte hashing, matching the
corrected `invite-page.test.ts` helper and production `hashToken()`.

**Change** in `workers/leader-board/test/gateway-api.test.ts`:
```typescript
// Before (wrong):
function hashTokenText(tokenHex: string): string {
  const tokenBytes = new TextEncoder().encode(tokenHex);
  const hash = sha256(tokenBytes);
  return bytesToHex(hash);
}

// After (correct):
function hashTokenText(tokenHex: string): string {
  const tokenBytes = hexToBytes(tokenHex);
  const hash = sha256(tokenBytes);
  return bytesToHex(hash);
}
```

Location: `workers/leader-board/test/gateway-api.test.ts` lines 43–47

### Step 2: Fix `encryptBlobWithToken` in `gateway-api.test.ts`

Two changes:
1. Derive the encryption key via HKDF (matching `deriveTokenKey` in production)
   instead of using raw token bytes as the NaCl key.
2. Encrypt `seed.hex()` as UTF-8 bytes (matching the Python CLI) instead of
   encrypting raw seed bytes.

Add a `deriveTokenKeyLocal` helper (same as in `invite-page.test.ts`):
```typescript
function deriveTokenKeyLocal(tokenHex: string): Uint8Array {
  const tokenBytes = hexToBytes(tokenHex);
  const info = new TextEncoder().encode("leader-board-invite-token");
  return hkdf(sha256, tokenBytes, new Uint8Array(0), info, 32);
}
```

Update `encryptBlobWithToken`:
```typescript
// Before (wrong):
function encryptBlobWithToken(seed: Uint8Array, tokenHex: string): string {
  const key = hexToBytes(tokenHex);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(seed, nonce, key);
  ...
}

// After (correct):
function encryptBlobWithToken(seed: Uint8Array, tokenHex: string): string {
  const key = deriveTokenKeyLocal(tokenHex);
  const seedHex = bytesToHex(seed);
  const plaintextBytes = new TextEncoder().encode(seedHex);
  const nonce = nacl.randomBytes(nacl.secretbox.nonceLength);
  const ciphertext = nacl.secretbox(plaintextBytes, nonce, key);
  ...
}
```

Location: `workers/leader-board/test/gateway-api.test.ts` lines 49–57

### Step 3: Run tests — confirm failures are now in production code

After fixing the test helpers, run `npx vitest run test/gateway-api.test.ts` from
`workers/leader-board/`. The test token hashing and blob encryption now match
the production code, so the token resolution succeeds. But `deriveSymmetricKey`
still receives hex-encoded bytes (64 bytes) instead of raw seed (32 bytes),
producing a wrong key. Tests that POST+GET messages should fail with decryption
errors. Tests that only check 401s (invalid/revoked token) should pass.

This confirms the production bug before we fix it.

### Step 4: Fix seed hex-decode in `handleGatewayAPI`

In `workers/leader-board/src/swarm-do.ts`, add a hex-decode step between
`decryptBlob` and `deriveSymmetricKey`. The blob plaintext is the UTF-8
encoding of the hex seed string; we need to decode it back to raw 32-byte seed.

Export `hexToBytes` from `gateway-crypto.ts` (currently private) so it can be
imported by `swarm-do.ts`, OR add a new exported helper `decodeSeedFromBlob`
that encapsulates the conversion. The cleaner approach is to keep the
conversion inside `gateway-crypto.ts` by creating a higher-level function:

```typescript
// In gateway-crypto.ts:
/**
 * Recover the raw 32-byte Ed25519 seed from the encrypted blob.
 * The blob stores seed.hex() as UTF-8, so we decode hex after decryption.
 */
export function recoverSeedFromBlob(encryptedBlobB64: string, token: string): Uint8Array {
  const plaintextBytes = decryptBlob(encryptedBlobB64, token);
  const seedHex = new TextDecoder().decode(plaintextBytes);
  return hexToBytes(seedHex);
}
```

Then update `handleGatewayAPI` to use `recoverSeedFromBlob` instead of calling
`decryptBlob` + `deriveSymmetricKey` with raw blob bytes:

```typescript
// Before:
const seed = decryptBlob(keyRecord.encrypted_blob, token);
symmetricKey = deriveSymmetricKey(seed);

// After:
const seed = recoverSeedFromBlob(keyRecord.encrypted_blob, token);
symmetricKey = deriveSymmetricKey(seed);
```

Location: `workers/leader-board/src/gateway-crypto.ts` (new function),
`workers/leader-board/src/swarm-do.ts` lines 365–366

### Step 5: Wrap message decryption in error handling

Currently `decryptMessage()` (line 400) and `encryptMessage()` (line 481) are
called outside the try/catch that covers token resolution. If the symmetric key
is wrong for any reason, the throw is unhandled → 1101.

Expand the existing try/catch or add a second try/catch around the GET/POST
message operations. The appropriate response for a decryption failure is 500
with a descriptive error, since the token was valid but the data is corrupted
or incompatible.

```typescript
// Wrap the message decryption in GET handler:
try {
  const decrypted = messages.map((msg) => ({
    position: msg.position,
    body: decryptMessage(msg.body, symmetricKey),
    sent_at: msg.sent_at,
  }));
  return new Response(JSON.stringify({ messages: decrypted }), { ... });
} catch {
  return new Response(
    JSON.stringify({ error: "Failed to decrypt messages" }),
    { status: 500, headers: jsonHeaders }
  );
}
```

Similarly wrap `encryptMessage` in the POST handler.

Location: `workers/leader-board/src/swarm-do.ts` lines 397–407 and 480–482

### Step 6: Update the gateway-crypto test vectors if needed

Check `workers/leader-board/test/gateway-crypto.test.ts` to verify the
cross-language test vectors still pass. The `decryptBlob` test uses a
Python-generated vector whose plaintext is likely the seed hex string. The
`deriveSymmetricKey` test passes raw seed bytes. If the existing vector test
for the full pipeline (blob → seed → symmetric key → decrypt message) expects
to call `deriveSymmetricKey(decryptBlob(...))` without hex-decode, it needs
updating to use `recoverSeedFromBlob` instead.

Location: `workers/leader-board/test/gateway-crypto.test.ts`

### Step 7: Run full test suite and verify

Run `npx vitest run` from `workers/leader-board/` to confirm:
- All 10 previously-failing `gateway-api.test.ts` tests pass
- All `gateway-crypto.test.ts` tests pass
- All `invite-page.test.ts` tests still pass
- Cross-path tests (WS writes → gateway reads, gateway writes → WS reads) pass,
  confirming encryption compatibility

### Step 8: Add backreference comments

Add chunk backreference comments to modified code:
- `recoverSeedFromBlob` in `gateway-crypto.ts`: `// Chunk: docs/chunks/gateway_message_read_fix - Hex-decode seed from blob`
- Error handling in `swarm-do.ts`: `// Chunk: docs/chunks/gateway_message_read_fix - Handle decryption errors`

## Dependencies

- `invite_token_instant_expiry` (ACTIVE) — provides the corrected `hashToken`,
  `deriveTokenKey`, and `decryptBlob` implementations that this chunk's fixes
  build on.
- `gateway_cleartext_api` (ACTIVE) — parent chunk that implemented the gateway
  HTTP routes being fixed.

## Risks and Open Questions

- **Cross-language vector drift**: The `gateway-crypto.test.ts` test vectors
  were generated by a Python script (`docs/chunks/gateway_cleartext_api/generate-test-vectors.py`).
  If the vector's blob plaintext is raw seed bytes (not hex-encoded), the full
  pipeline test will need updating. Verify the vector format in Step 6.
- **`handleInvitePage` consistency**: The invite page handler also calls
  `decryptBlob` (line 314 of swarm-do.ts). It doesn't call `deriveSymmetricKey`
  (it only needs the seed to verify the token is valid and to read metadata),
  so it's not affected by bug 3. But confirm this during implementation.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
