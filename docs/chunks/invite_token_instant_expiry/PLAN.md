
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Two bugs in `workers/leader-board/src/gateway-crypto.ts` cause the TypeScript
server to be unable to look up or decrypt invite tokens created by the Python CLI.
Both are format mismatches where the TypeScript code diverged from the Python
`src/board/crypto.py` implementation it was supposed to replicate.

**Bug 1 — Token hash mismatch (lookup failure):**
- Python (`src/cli/board.py:431`): `hashlib.sha256(token).hexdigest()` — hashes
  the raw 32-byte token.
- TypeScript (`gateway-crypto.ts:60`): `new TextEncoder().encode(token)` — hashes
  the hex string as UTF-8 (64 bytes of ASCII, not 32 bytes of raw data).
- Result: The CLI uploads blob keyed by `SHA256(raw_bytes)`, but the server
  looks up by `SHA256(utf8(hex_string))` → hash never matches → 404.

**Bug 2 — Encryption key derivation mismatch (decryption failure):**
- Python (`src/cli/board.py:425`): `derive_token_key(token)` uses HKDF-SHA256
  with `info=b"leader-board-invite-token"` to derive the secretbox key.
- TypeScript (`gateway-crypto.ts:75`): `hexToBytes(token)` uses the raw 32-byte
  token directly as the secretbox key — no HKDF.
- Result: Even if hash lookup were fixed, decryption would fail because the keys
  differ.

**Fix strategy:** Correct the TypeScript server to match the Python CLI. The
Python side is the canonical implementation — it uses raw-byte hashing (correct
crypto hygiene) and HKDF key derivation (domain separation). The TypeScript
test vectors were self-generated to match the broken TypeScript code and must
be regenerated from Python.

Per docs/trunk/TESTING_PHILOSOPHY.md, we write the failing cross-language
round-trip test first (TDD), then fix the code to make it pass.

## Sequence

### Step 1: Generate correct cross-language test vectors from Python

Write a small Python script (stored as a chunk artifact at
`docs/chunks/invite_token_instant_expiry/generate-vectors.py`) that:

1. Uses a deterministic token (`bb` * 32) and seed (`aa` * 32)
2. Computes `token_hash = hashlib.sha256(bytes.fromhex(token_hex)).hexdigest()`
3. Computes `token_key = derive_token_key(bytes.fromhex(token_hex))`
4. Encrypts the seed hex string using a fixed nonce (for deterministic output):
   `SecretBox(token_key).encrypt(seed_hex.encode(), fixed_nonce)`
5. Prints all values as a JSON object suitable for pasting into the TS test file

Run the script and capture the output. These vectors become the source of truth.

Location: `docs/chunks/invite_token_instant_expiry/generate-vectors.py` (chunk artifact)

### Step 2: Write failing TypeScript tests for correct behavior

In `workers/leader-board/test/gateway-crypto.test.ts`:

1. Add a new `describe("cross-language invite token vectors")` block with the
   Python-generated vectors from Step 1.
2. Add test: `hashToken` of the token hex string must equal the Python-computed
   hash (which hashes raw bytes). This will FAIL with current code.
3. Add test: `decryptBlob` with the Python-encrypted blob and token must recover
   the seed. This will FAIL because decryptBlob uses raw token as key, not HKDF.

Verify both tests fail before proceeding.

Location: `workers/leader-board/test/gateway-crypto.test.ts`

### Step 3: Fix `hashToken()` to hash raw bytes

In `workers/leader-board/src/gateway-crypto.ts`, change `hashToken()`:

**Before:**
```typescript
export function hashToken(token: string): string {
  const tokenBytes = new TextEncoder().encode(token);
  // ...
}
```

**After:**
```typescript
export function hashToken(token: string): string {
  const tokenBytes = hexToBytes(token);
  // ...
}
```

This makes the function hash the same 32 raw bytes as Python's
`hashlib.sha256(token).hexdigest()`.

Location: `workers/leader-board/src/gateway-crypto.ts#hashToken`

### Step 4: Add `deriveTokenKey()` and fix `decryptBlob()`

In `workers/leader-board/src/gateway-crypto.ts`:

1. Add a new exported function `deriveTokenKey(token: string): Uint8Array`:
   - `hexToBytes(token)` → 32 raw bytes
   - HKDF-SHA256 with `salt=empty`, `info="leader-board-invite-token"`, `length=32`
   - This mirrors Python's `derive_token_key()` in `src/board/crypto.py`

2. Update `decryptBlob()` to use `deriveTokenKey(token)` instead of
   `hexToBytes(token)` as the secretbox key:

**Before:**
```typescript
const key = hexToBytes(token);
```

**After:**
```typescript
const key = deriveTokenKey(token);
```

Location: `workers/leader-board/src/gateway-crypto.ts#deriveTokenKey`, `#decryptBlob`

### Step 5: Update existing test vectors in `gateway-crypto.test.ts`

The existing `VECTORS` object in `gateway-crypto.test.ts` has a `token_hash_hex`
and `encrypted_blob_b64` that were generated with the broken TypeScript logic.
Update them with the Python-generated values from Step 1:

- `token_hash_hex`: Replace with Python's `SHA256(raw_bytes).hex()`
- `encrypted_blob_b64`: Replace with Python's HKDF-encrypted blob

The `seed_hex`, `symmetric_key_hex`, and message encryption vectors are
unaffected (they don't involve token hashing or token key derivation).

Verify the cross-language tests from Step 2 now pass.

Location: `workers/leader-board/test/gateway-crypto.test.ts`

### Step 6: Update `invite-page.test.ts` helper functions

The `invite-page.test.ts` file has its own `hashTokenText()` and
`encryptBlobWithToken()` helpers that replicate the broken behavior:

1. **`hashTokenText()`**: Currently hashes hex string as UTF-8. Change to
   hash raw bytes via `hexToBytes()`, matching the fixed `hashToken()`.

2. **`encryptBlobWithToken()`**: Currently uses raw token bytes as secretbox
   key. Change to use HKDF-derived key, matching the fixed `decryptBlob()`.
   Import `hkdf` from `@noble/hashes/hkdf.js` and `sha256` to replicate
   `deriveTokenKey()` logic, or import `deriveTokenKey` from the source.

After fixing helpers, all existing invite-page tests should continue to pass
because they create and verify tokens using the same (now-corrected) functions.

Location: `workers/leader-board/test/invite-page.test.ts`

### Step 7: Add end-to-end cross-language integration test

Add a new test in `workers/leader-board/test/invite-page.test.ts` that
simulates the full Python CLI → server flow:

1. Generate a token and compute hash/blob using **Python-compatible logic**
   (raw-byte hash, HKDF-derived key) — not the test helpers.
2. PUT the blob to `/gateway/keys`
3. GET `/invite/{token_hex}` (without `?swarm=` param, using KV routing)
4. Assert 200 and the instruction page content is returned

This is the definitive end-to-end test from the success criteria: "create token
via CLI → curl invite URL → verify instruction page is returned."

Location: `workers/leader-board/test/invite-page.test.ts`

### Step 8: Run all test suites and verify

1. Run TypeScript tests: `cd workers/leader-board && npm test`
   - All gateway-crypto tests pass (with updated vectors)
   - All invite-page tests pass (with fixed helpers)
   - New cross-language integration test passes
2. Run Python tests: `uv run pytest tests/test_board_invite.py`
   - All existing Python tests still pass (Python code is unchanged)

## Risks and Open Questions

- **Test vector generation with fixed nonce**: NaCl secretbox normally uses
  random nonces. The Python vector script must use a fixed nonce to produce
  deterministic encrypted blobs. PyNaCl's `SecretBox.encrypt()` accepts an
  explicit nonce parameter, so this is straightforward.
- **No deployed data migration needed**: The hash and encryption mismatches
  mean no valid tokens have ever been successfully created in production
  (they all fail immediately). There is no existing data to migrate.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->