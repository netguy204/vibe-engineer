

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add CORS support and response schema documentation to the cleartext gateway HTTP routes in `workers/leader-board/src/swarm-do.ts`. The approach is:

1. **CORS helper**: Extract a small helper that merges `Access-Control-Allow-Origin: *` into every response from the gateway and invite routes. Apply it consistently at the response-return points inside `handleGatewayAPI` and `handleInvitePage`.

2. **OPTIONS preflight handler**: Add an `OPTIONS` case in `handleGatewayAPI` (and match it in the `fetch` router) that returns 204 with the standard CORS preflight headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`).

3. **Invite page documentation**: Update the `renderInvitePage` template string to include GET and POST response schema documentation with field names, types, and explicit notes about what fields are *not* present (e.g., no sender/author field).

4. **Tests first** per docs/trunk/TESTING_PHILOSOPHY.md: Write failing tests for CORS headers on GET, POST, and OPTIONS responses before implementing the CORS logic. Write a test asserting the invite page contains response schema documentation before updating the template.

No new dependencies. No subsystems are relevant — this is entirely within the Cloudflare Worker HTTP handler code.

## Sequence

### Step 1: Write failing CORS tests

Add tests to `workers/leader-board/test/gateway-api.test.ts`:

- `OPTIONS /gateway/{token}/channels/{channel}/messages returns 204 with CORS headers` — asserts status 204, `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods` includes GET/POST/OPTIONS, `Access-Control-Allow-Headers` includes Content-Type.
- `GET gateway response includes CORS headers` — asserts existing GET response has `Access-Control-Allow-Origin: *`.
- `POST gateway response includes CORS headers` — asserts existing POST response has `Access-Control-Allow-Origin: *`.

Add a test to `workers/leader-board/test/invite-page.test.ts`:
- `invite page documents GET and POST response schemas` — asserts the invite page text contains response field documentation (`position`, `body`, `sent_at`, `channel`, and a note about no sender/author field).

Run tests, confirm they fail.

Location: `workers/leader-board/test/gateway-api.test.ts`, `workers/leader-board/test/invite-page.test.ts`

### Step 2: Add OPTIONS handler to handleGatewayAPI

In `workers/leader-board/src/swarm-do.ts`, add an `OPTIONS` case at the top of the `switch (request.method)` block inside `handleGatewayAPI`. Return:

```
Response(null, {
  status: 204,
  headers: {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  }
})
```

The OPTIONS handler does NOT need token validation — preflight requests don't carry credentials. Add it as a short-circuit before the token resolution logic.

Location: `workers/leader-board/src/swarm-do.ts#SwarmDO.handleGatewayAPI`

### Step 3: Add CORS headers to all gateway GET/POST responses

Define a `corsHeaders` constant at the top of `handleGatewayAPI`:

```typescript
const corsHeaders = { "Access-Control-Allow-Origin": "*" };
```

Merge `corsHeaders` into every `headers` object in the GET and POST response paths. This includes:
- Successful GET responses (messages array)
- Long-poll timeout empty responses
- No-wait empty responses
- Successful POST responses
- Error responses (400, 401, 405, 500)

Also add `Access-Control-Allow-Origin: *` to the invite page responses in `handleInvitePage` (both the success and 404/405 responses).

Location: `workers/leader-board/src/swarm-do.ts#SwarmDO.handleGatewayAPI`, `workers/leader-board/src/swarm-do.ts#SwarmDO.handleInvitePage`

### Step 4: Update renderInvitePage with response schema documentation

Add two new sections to the `renderInvitePage` template string, after the existing "Reading Messages" and "Posting Messages" sections:

**After "Reading Messages"**, add a response schema block:

```
### GET Response Schema

    {"messages": [{"position": 1, "body": "message text", "sent_at": "2026-03-16T12:00:00Z"}]}

Fields:
- position (number) — monotonically increasing message index within the channel
- body (string) — the plaintext message content
- sent_at (string) — ISO 8601 timestamp when the message was stored

Note: There is no sender or author field. All messages are anonymous in the gateway API.
```

**After "Posting Messages"**, add a response schema block:

```
### POST Response Schema

    {"position": 1, "channel": "changelog"}

Fields:
- position (number) — the position assigned to the newly stored message
- channel (string) — the channel the message was posted to
```

Location: `workers/leader-board/src/swarm-do.ts#renderInvitePage`

### Step 5: Run tests and verify all pass

Run the full test suite for the worker. All four new tests from Step 1 should now pass. Verify no existing tests have regressed.

Location: `workers/leader-board/test/`

## Risks and Open Questions

- The OPTIONS handler deliberately skips token validation since preflight requests can't carry custom headers. This is standard CORS behavior but worth noting: an OPTIONS request to a path with an invalid token will return 204 rather than 401. This is correct — browsers send preflight before the real request, and the real request will still be validated.
- Using `Access-Control-Allow-Origin: *` is intentionally permissive. The gateway is designed for agent consumption from arbitrary origins. If origin-scoping is ever needed, this is where to add it.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->