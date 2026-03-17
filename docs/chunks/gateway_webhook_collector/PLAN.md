


<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a new `/gateway/{token}/channels/{channel}/webhook` endpoint to the Cloudflare Workers Durable Object that accepts arbitrary HTTP payloads and marshals them into the existing encrypted message storage pipeline.

The strategy is to mirror the existing `POST .../messages` flow but replace the JSON body parsing with raw body capture. The raw bytes are base64-encoded and wrapped in a JSON envelope (`{"content_type": "...", "raw_body": "...", "source": "webhook"}`) before being passed to the same `encryptMessage()` → `storage.appendMessage()` path. This means the webhook endpoint produces messages that are indistinguishable from regular messages once stored — the envelope is just the plaintext content.

The implementation builds directly on:
- The routing in `SwarmDO.fetch()` (swarm-do.ts ~line 179) — add a second regex match for `/webhook`
- The `handleGatewayAPI()` handler (swarm-do.ts ~line 369) — either extend it or create a sibling handler
- The encryption flow: `hashToken()` → `recoverSeedFromBlob()` → `deriveSymmetricKey()` → `encryptMessage()`
- CORS patterns from `gateway_cors_and_docs` — identical headers on all responses

Following TDD per docs/trunk/TESTING_PHILOSOPHY.md: write failing tests first for each content type scenario, then implement the endpoint.

## Sequence

### Step 1: Write failing tests for the webhook endpoint

Add tests to `workers/leader-board/test/gateway-api.test.ts` using the existing `setupGateway()` helper. Write tests that POST to the `/webhook` path with various content types and assert on the response.

Tests to write (all should fail initially since the endpoint doesn't exist):

1. **JSON webhook** — POST with `Content-Type: application/json` and a JSON body. Assert 200 response with `{position, channel}`. Then GET via the `/messages` endpoint and verify the decrypted message is a JSON envelope containing `content_type`, `raw_body` (base64-encoded), and `source: "webhook"`.

2. **Form-encoded webhook** — POST with `Content-Type: application/x-www-form-urlencoded` and `key=value&foo=bar`. Verify the envelope wraps the raw form data.

3. **Plain text webhook** — POST with `Content-Type: text/plain` and a plain string. Verify envelope.

4. **XML webhook** — POST with `Content-Type: application/xml` and an XML string. Verify envelope.

5. **CORS on webhook** — OPTIONS request returns 204 with correct CORS headers. POST response includes `Access-Control-Allow-Origin: *`.

6. **Invalid token on webhook** — POST with a bad token returns 401.

7. **Oversized payload** — POST exceeding `GATEWAY_MESSAGE_MAX_BYTES` returns 400.

Location: `workers/leader-board/test/gateway-api.test.ts`

### Step 2: Add webhook route matching in SwarmDO.fetch()

In `workers/leader-board/src/swarm-do.ts`, add a new regex match in the `fetch()` method alongside the existing `/messages` match:

```typescript
// Chunk: docs/chunks/gateway_webhook_collector - Webhook collector route
const webhookMatch = url.pathname.match(
  /^\/gateway\/([^/]+)\/channels\/([^/]+)\/webhook$/
);
if (webhookMatch) {
  return this.handleWebhookAPI(request, url, webhookMatch[1], webhookMatch[2]);
}
```

Place this **before** the WebSocket upgrade check, adjacent to the existing `gatewayMatch` block.

Location: `workers/leader-board/src/swarm-do.ts` (~line 184)

### Step 3: Implement handleWebhookAPI handler

Create a new private method `handleWebhookAPI()` in the `SwarmDO` class. The method follows the same structure as `handleGatewayAPI()` but with different body handling:

```
handleWebhookAPI(request, url, token, channel):
  1. Set up CORS + JSON response headers (same pattern as handleGatewayAPI)
  2. Handle OPTIONS → 204 with CORS preflight headers
  3. Reject non-POST methods → 405
  4. Validate channel name with CHANNEL_NAME_RE
  5. Resolve token → symmetricKey (identical to handleGatewayAPI)
  6. Read raw body as ArrayBuffer
  7. Check size against GATEWAY_MESSAGE_MAX_BYTES → 400 if exceeded
  8. Base64-encode the raw body bytes
  9. Read Content-Type header (default to "application/octet-stream" if missing)
  10. Build envelope JSON string:
      {"content_type": "<header>", "raw_body": "<base64>", "source": "webhook"}
  11. encryptMessage(envelope, symmetricKey)
  12. storage.appendMessage(channel, ciphertext)
  13. Wake watchers + pending polls (same as POST messages)
  14. Ensure compaction alarm
  15. Return 200 with {position, channel}
```

For base64 encoding, use the `btoa(String.fromCharCode(...bytes))` pattern available in the Cloudflare Workers runtime, or a helper equivalent to the existing `bytesToBase64` in gateway-crypto.ts.

Add a chunk backreference comment:
```typescript
// Chunk: docs/chunks/gateway_webhook_collector - Generic webhook collector endpoint
```

Location: `workers/leader-board/src/swarm-do.ts`

### Step 4: Extract shared token resolution logic

The token-resolution block (hashToken → getGatewayKey → recoverSeedFromBlob → deriveSymmetricKey) is duplicated between `handleGatewayAPI` and `handleWebhookAPI`. Extract it into a private helper method:

```typescript
private resolveTokenKey(token: string, jsonHeaders: Record<string, string>):
  { symmetricKey: Uint8Array } | { errorResponse: Response }
```

Update both `handleGatewayAPI` and `handleWebhookAPI` to call this helper. This keeps the code DRY without changing any behavior.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 5: Run tests and verify all pass

Run the full gateway test suite:
```bash
cd workers/leader-board && npx vitest run test/gateway-api.test.ts
```

Verify:
- All new webhook tests pass
- All existing gateway tests still pass (no regressions)
- Each success criterion from GOAL.md is covered by at least one test

## Dependencies

- Chunks `gateway_cleartext_api` (ACTIVE) and `gateway_cors_and_docs` (ACTIVE) must be complete — they are, providing the base endpoint and CORS infrastructure this chunk extends.
- No new external libraries needed. Base64 encoding uses built-in Web APIs available in Cloudflare Workers runtime.

## Risks and Open Questions

- **Base64 encoding of large payloads**: The envelope wraps the entire raw body as base64, which inflates size by ~33%. Combined with JSON envelope overhead, the effective max webhook payload is ~750KB to stay within the 1MB `GATEWAY_MESSAGE_MAX_BYTES` limit after encryption. The size check should be applied to the **envelope string** (post-marshaling) rather than just the raw body, to ensure the encrypted message fits within storage limits.
- **Content-Type header fidelity**: Some proxies or CDNs may strip or modify the Content-Type header. The endpoint should default to `application/octet-stream` when the header is absent, rather than rejecting the request.
- **Binary payloads**: The `arrayBuffer()` → base64 path handles binary payloads correctly. No text encoding assumptions should be made about the raw body.

## Deviations

- Step 1: The "missing Content-Type defaults to application/octet-stream" test
  needed adjustment. The Workers/fetch runtime auto-sets Content-Type to
  `text/plain;charset=UTF-8` when sending a string body without an explicit
  header. Used `new Blob([bytes])` (with no type) to truly omit the header,
  which correctly triggers the `application/octet-stream` default.

- Step 3: Base64 encoding uses a chunked approach (8KB chunks) to avoid
  call-stack overflow on large payloads, rather than a single
  `String.fromCharCode(...spread)` call.
