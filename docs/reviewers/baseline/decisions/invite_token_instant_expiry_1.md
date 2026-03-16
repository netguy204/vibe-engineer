---
decision: FEEDBACK
summary: "Core crypto fixes are correct but gateway-api.test.ts helpers and swarm-do.ts caller are not updated to match the new format, breaking the cleartext gateway API."
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: `ve board invite create` followed by `curl <invite_url>` returns the instruction page (not "Invalid or expired")

- **Status**: satisfied
- **Evidence**: `hashToken()` now hashes raw bytes (matching Python), `deriveTokenKey()` uses HKDF (matching Python). The invite page handler only uses `hashToken` for lookup, so the create→fetch cycle works. Confirmed by passing end-to-end test in `invite-page.test.ts`.

### Criterion 2: Root cause identified and documented in the chunk

- **Status**: satisfied
- **Evidence**: PLAN.md clearly documents both bugs: (1) token hash mismatch (hex string vs raw bytes) and (2) encryption key derivation mismatch (raw token vs HKDF). The `generate-vectors.py` chunk artifact demonstrates the correct Python behavior.

### Criterion 3: End-to-end test added covering the create → fetch cycle

- **Status**: satisfied
- **Evidence**: `invite-page.test.ts` has a new "end-to-end: Python-compatible create → fetch cycle works" test that generates a token, computes hash/blob using Python-compatible logic (raw-byte hash, HKDF key), PUTs the blob, then GETs `/invite/{token}` and verifies the instruction page. Test passes.

### Criterion 4: Existing tests still pass

- **Status**: gap
- **Evidence**: All 10 tests in `gateway-api.test.ts` now fail with 401 errors. These tests were not modified by this chunk but their helper functions (`hashTokenText()` and `encryptBlobWithToken()`) still use the old broken crypto format (hashing hex string instead of raw bytes, using raw token as secretbox key instead of HKDF). The server-side fix causes these unmodified test helpers to produce incompatible tokens.

## Feedback Items

### Issue 1: `gateway-api.test.ts` helpers not updated

- **Location**: `workers/leader-board/test/gateway-api.test.ts:43-56`
- **Concern**: The `hashTokenText()` and `encryptBlobWithToken()` helpers in `gateway-api.test.ts` still use the old broken crypto format (TextEncoder for hashing, raw token as secretbox key, encrypting raw seed bytes instead of `seed.hex()`). This causes all 10 gateway API tests to fail with 401. The same fix applied to `invite-page.test.ts` helpers must also be applied here.
- **Suggestion**: Update `hashTokenText()` to use `hexToBytes()` instead of `TextEncoder`, add a `deriveTokenKeyLocal()` helper (identical to the one added in `invite-page.test.ts`), update `encryptBlobWithToken()` to use HKDF-derived key and encrypt `bytesToHex(seed)` as UTF-8 instead of raw seed bytes.
- **Severity**: functional
- **Confidence**: high

### Issue 2: `swarm-do.ts` gateway API handler doesn't decode hex seed after decryption

- **Location**: `workers/leader-board/src/swarm-do.ts:362-363`
- **Concern**: The gateway API handler does `const seed = decryptBlob(...); symmetricKey = deriveSymmetricKey(seed);`. After the fix, `decryptBlob` returns the UTF-8 bytes of the hex-encoded seed (64 bytes), but `deriveSymmetricKey()` expects the raw 32-byte seed. This will produce the wrong symmetric key and break all gateway message encryption/decryption. The invite page handler is unaffected (it only looks up by hash, no decryption needed).
- **Suggestion**: Update `swarm-do.ts:362-363` to decode the hex: `const plaintext = decryptBlob(keyRecord.encrypted_blob, token); const seed = hexToBytes(new TextDecoder().decode(plaintext)); symmetricKey = deriveSymmetricKey(seed);`. Alternatively, export a higher-level function from `gateway-crypto.ts` that handles the full token→symmetric-key derivation.
- **Severity**: functional
- **Confidence**: high
