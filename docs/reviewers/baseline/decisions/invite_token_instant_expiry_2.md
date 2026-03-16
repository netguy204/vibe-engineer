---
decision: FEEDBACK
summary: "Core crypto fixes correct but two callers not updated: gateway-api.test.ts helpers still use broken crypto (10 test failures), and swarm-do.ts passes hex-encoded seed bytes to deriveSymmetricKey instead of raw 32-byte seed"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve board invite create` followed by `curl <invite_url>` returns the instruction page (not "Invalid or expired")

- **Status**: satisfied
- **Evidence**: The core fixes in `gateway-crypto.ts` are correct: `hashToken()` now hashes raw bytes via `hexToBytes()` (line 61), and new `deriveTokenKey()` (line 73) uses HKDF-SHA256 matching Python's `derive_token_key()`. `decryptBlob()` now uses `deriveTokenKey()` (line 93). The invite-page.test.ts end-to-end test at line 297 confirms the create→fetch cycle works.

### Criterion 2: Root cause identified and documented in the chunk

- **Status**: satisfied
- **Evidence**: PLAN.md documents both bugs clearly: Bug 1 (token hash mismatch — hashing hex string as UTF-8 vs raw bytes) and Bug 2 (encryption key derivation mismatch — raw token as key vs HKDF-derived key). The generate-vectors.py chunk artifact provides authoritative Python-generated test vectors.

### Criterion 3: End-to-end test added covering the create → fetch cycle

- **Status**: satisfied
- **Evidence**: `invite-page.test.ts` line 297: "end-to-end: Python-compatible create → fetch cycle works" — creates token, computes hash/blob using Python-compatible logic (raw-byte hash, HKDF key), PUTs blob, GETs `/invite/{token}` without `?swarm=` param, asserts 200 with instruction page content. All 12 invite-page tests pass.

### Criterion 4: Existing tests still pass

- **Status**: gap
- **Evidence**: `gateway-api.test.ts` has 10 of 13 tests failing with 401 because the test helpers `hashTokenText()` (line 43) and `encryptBlobWithToken()` (line 49) were not updated to match the new crypto. Additionally, `swarm-do.ts:362-363` passes the raw decryptBlob output (UTF-8 hex string bytes) directly to `deriveSymmetricKey()` which expects raw 32-byte seed — this would break all gateway message encryption/decryption in production.

## Feedback Items

### Issue 1: gateway-api.test.ts helpers use broken crypto format

- **Location**: `workers/leader-board/test/gateway-api.test.ts:43-56`
- **Severity**: functional
- **Confidence**: high
- **Concern**: `hashTokenText()` at line 43 still uses `new TextEncoder().encode(tokenHex)` (hashing hex string as UTF-8 instead of raw bytes). `encryptBlobWithToken()` at line 49 still uses `hexToBytes(tokenHex)` as the secretbox key directly (no HKDF) and encrypts raw seed bytes instead of `seed.hex()` as UTF-8. This causes all 10 gateway API tests to fail with 401 — the same issue flagged in the previous review iteration.
- **Suggestion**: Apply the same pattern as `invite-page.test.ts`: (1) In `hashTokenText()`, change `new TextEncoder().encode(tokenHex)` to `hexToBytes(tokenHex)`. (2) Add a `deriveTokenKeyLocal()` helper using HKDF. (3) In `encryptBlobWithToken()`, use the HKDF-derived key and encrypt `bytesToHex(seed)` as UTF-8 instead of raw seed bytes.

### Issue 2: swarm-do.ts passes hex-encoded seed to deriveSymmetricKey

- **Location**: `workers/leader-board/src/swarm-do.ts:362-363`
- **Severity**: functional
- **Confidence**: high
- **Concern**: `decryptBlob()` now returns UTF-8 bytes of the hex-encoded seed (64 bytes, because Python encrypts `seed.hex()`), but `deriveSymmetricKey(seed)` at line 363 receives these 64 bytes directly instead of the raw 32-byte seed. This produces the wrong symmetric key, breaking all gateway message encryption/decryption. Same issue flagged in the previous review iteration.
- **Suggestion**: Decode the hex after decryption: `const plaintext = decryptBlob(keyRecord.encrypted_blob, token); const seed = hexToBytes(new TextDecoder().decode(plaintext)); symmetricKey = deriveSymmetricKey(seed);`
