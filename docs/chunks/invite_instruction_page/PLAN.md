<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a new route handler `handleInvitePage` to `SwarmDO` in `workers/leader-board/src/swarm-do.ts`, matching `GET /invite/{token}`. The handler validates the token against stored gateway keys, queries swarm metadata and channel list from storage, and renders a plain-text instruction page with working `curl` examples.

The instruction page is generated inline (no template engine) as a plain-text/markdown string. The content is dynamically assembled from:
- Swarm metadata (`storage.getSwarm()`)
- Channel list (`storage.listChannels()`)
- The token itself (for `curl` example URLs)
- The server's own origin (from the request URL)

Routing is added at both levels:
1. **Worker entry point** (`src/index.ts`): Match `/invite/{token}` and forward to the DO — but unlike gateway API routes, the swarm ID must be derived from the token (hash → key lookup → swarm_id), so the entry point forwards to a special handler that looks up swarm membership across DOs, or we embed the swarm ID in the stored key record.
2. **SwarmDO** (`src/swarm-do.ts`): New `handleInvitePage` method.

**Key design insight**: The existing `/gateway/keys` PUT stores `{token_hash, encrypted_blob}` but not the `swarm_id` — however, the worker entry point requires `?swarm=` to route to the correct DO. The invite URL (`/invite/{token}`) has no swarm param by design (agents shouldn't need to know it). To solve this, we'll add a `swarm_id` field to the `gateway_keys` table and a lightweight lookup table in Worker-level KV or a global index DO. The simplest approach: **store swarm_id alongside the key blob**, then add a global KV namespace that maps `hash(token)` → `swarm_id` so the worker entry point can resolve which DO to forward to.

**Testing**: Following `docs/trunk/TESTING_PHILOSOPHY.md`, tests will use `SELF.fetch` in Vitest (same pattern as `gateway-api.test.ts`). Tests verify:
- Valid token returns 200 with text/plain content containing curl examples
- Invalid/revoked token returns a clear error
- Content includes the actual token in curl commands
- Content lists available channels

## Sequence

### Step 1: Extend gateway_keys storage to include swarm_id

**Location**: `workers/leader-board/src/storage.ts`

Add a `swarm_id` column to the `gateway_keys` table schema. Update `putGatewayKey` to accept and store a `swarm_id` parameter. Update `getGatewayKey` to return the `swarm_id` field. This is backward-compatible — SQLite `ALTER TABLE ADD COLUMN` with a default handles existing rows.

Modify the schema init:
```sql
ALTER TABLE gateway_keys ADD COLUMN swarm_id TEXT NOT NULL DEFAULT ''
```

Since DO SQL uses `CREATE TABLE IF NOT EXISTS`, we need to handle the migration carefully. Add the column via a separate `ALTER TABLE` wrapped in a try/catch (column may already exist). Update `putGatewayKey(tokenHash, encryptedBlob, swarmId)` and `getGatewayKey` to include `swarm_id`.

### Step 2: Update gateway key PUT handler to accept swarm_id

**Location**: `workers/leader-board/src/swarm-do.ts`

Update `handleGatewayKeys` PUT case to extract `swarm_id` from the request body and pass it to `storage.putGatewayKey`. The swarm_id is available because the worker entry point already has the `?swarm=` parameter — pass it through. Also update the `handleGatewayKeys` to pass the swarm_id from the URL to the storage call.

### Step 3: Add KV binding for token→swarm routing

**Location**: `workers/leader-board/wrangler.jsonc` (or `wrangler.toml`)

Add a KV namespace binding (e.g., `INVITE_TOKENS`) to the worker config. This KV maps `hash(token)` → `swarm_id` for cross-DO routing. The PUT handler in `handleGatewayKeys` writes this mapping; the DELETE handler removes it.

Alternatively, if adding KV is too heavy, use a simpler approach: encode the swarm_id in the invite URL itself. The investigation shows `ve board invite` already knows the swarm_id — the URL could be `/invite/{token}?swarm={swarm_id}`. This is simpler and avoids new infrastructure. The token alone is the credential; the swarm_id is a routing hint (not a secret).

**Decision**: Use the query-parameter approach (`/invite/{token}?swarm={swarm_id}`). This avoids new KV infrastructure and matches the existing pattern where all worker routes require `?swarm=`. The `ve board invite` CLI already has the swarm_id and controls the URL output. The swarm_id is not secret (it's the public key hash).

### Step 4: Write failing tests for the invite instruction page

**Location**: `workers/leader-board/test/invite-page.test.ts`

Create a new test file following the patterns in `gateway-api.test.ts`. Tests to write:

1. **`GET /invite/{token} returns instruction page for valid token`** — Set up a gateway (reuse `setupGateway` helper), GET `/invite/{token}?swarm={swarmId}`, assert 200 with `Content-Type: text/plain` (or `text/markdown`), body contains the token in curl examples.

2. **`instruction page lists available channels`** — Post some messages to create channels, then GET the invite page, assert channel names appear in the output.

3. **`instruction page includes working curl command patterns`** — Assert body contains `curl` and the gateway API URL pattern `/gateway/{token}/channels/`.

4. **`invalid token returns 404 with clear error`** — GET `/invite/{fake_token}?swarm={swarmId}`, assert 404 with error message.

5. **`revoked token returns 404`** — Set up gateway, delete the key, GET invite page, assert 404.

6. **`missing swarm parameter returns 400`** — GET `/invite/{token}` without `?swarm=`, assert 400 (handled by existing worker entry point logic).

### Step 5: Add route matching in worker entry point

**Location**: `workers/leader-board/src/index.ts`

Add a route match for `/invite/{token}` before the WebSocket upgrade check. Extract token from path, forward request to the SwarmDO stub (using the `?swarm=` query param for DO routing, same as existing gateway routes).

```typescript
// Route invite page requests
if (url.pathname.match(/^\/invite\/[^/]+$/)) {
  return stub.fetch(request);
}
```

### Step 6: Add route matching in SwarmDO.fetch

**Location**: `workers/leader-board/src/swarm-do.ts`

Add a match for `/invite/{token}` in the `fetch` method, before the WebSocket upgrade check. Extract the token and delegate to a new `handleInvitePage` method.

```typescript
const inviteMatch = url.pathname.match(/^\/invite\/([^/]+)$/);
if (inviteMatch) {
  return this.handleInvitePage(request, url, inviteMatch[1]);
}
```

### Step 7: Implement handleInvitePage handler

**Location**: `workers/leader-board/src/swarm-do.ts`

New private method `handleInvitePage(request: Request, url: URL, token: string): Promise<Response>`.

Logic:
1. Hash the token and look up the gateway key record.
2. If not found, return 404 `{ error: "Invalid or expired invite token" }` (plain text for consistency with agent consumption).
3. Fetch swarm metadata via `storage.getSwarm()`.
4. Fetch channel list via `storage.listChannels()`.
5. Construct the base URL from `url.origin` and the swarm query param.
6. Render the instruction text (see Step 8).
7. Return `Response` with `Content-Type: text/plain; charset=utf-8`.

Only accept GET requests; return 405 for other methods.

### Step 8: Compose the instruction page content

**Location**: `workers/leader-board/src/swarm-do.ts` (inline in `handleInvitePage`, or extracted to a helper function `renderInvitePage`)

The page content is a plain-text document (Markdown-flavored for readability). Template variables:
- `{origin}` — the server base URL (e.g., `https://leader-board.example.com`)
- `{token}` — the invite token (hex string)
- `{swarm}` — the swarm ID
- `{channels}` — list of available channels with head positions

Content structure:
```
# Swarm Invite — {swarm_id}

You have been invited to participate in a swarm via the HTTP gateway.
Your token grants read and write access to all channels.

## Available Channels

{for each channel: "- {name} ({head_position} messages)"}
(If no channels exist yet: "No channels exist yet. Post a message to create one.")

## Reading Messages

  curl '{origin}/gateway/{token}/channels/{channel}/messages?after=0&swarm={swarm}'

Query parameters:
- after={position} — return messages after this position (default: 0)
- limit={n} — max messages to return (default: 50, max: 200)
- wait={seconds} — long-poll: block up to N seconds for new messages (1-60)

## Posting Messages

  curl -X POST '{origin}/gateway/{token}/channels/{channel}/messages?swarm={swarm}' \
    -H 'Content-Type: application/json' \
    -d '{"body": "your message here"}'

## Polling Loop

To continuously watch a channel:

  CURSOR=0
  while true; do
    RESP=$(curl -s '{origin}/gateway/{token}/channels/{channel}/messages?after=$CURSOR&wait=30&swarm={swarm}')
    # Process messages, update CURSOR to latest position
    sleep 1
  done

## Security

- Your token is the sole credential. Keep it secret.
- The token grants access to ALL channels in this swarm.
- To revoke access, the swarm operator deletes the token server-side.
- Messages are encrypted in transit (TLS) and at rest on the server.
```

Use the first channel name (or "changelog" as a default) in the curl examples.

### Step 9: Run tests and iterate

Run `npx vitest run test/invite-page.test.ts` in the `workers/leader-board/` directory. Fix any failures. Ensure all existing gateway tests still pass by running the full suite.

### Step 10: Update code_paths in GOAL.md

Update the chunk's GOAL.md frontmatter `code_paths` to reference the files touched:
- `workers/leader-board/src/index.ts`
- `workers/leader-board/src/swarm-do.ts`
- `workers/leader-board/src/storage.ts`
- `workers/leader-board/test/invite-page.test.ts`

## Dependencies

- **gateway_cleartext_api** (ACTIVE): Provides the HTTP message endpoints that the instruction page documents. The curl examples reference `/gateway/{token}/channels/{channel}/messages`.
- **gateway_token_storage** (ACTIVE): Provides the token→encrypted-blob storage that this handler uses to validate tokens. The `swarm_id` column addition extends this schema.
- **invite_cli_command** (ACTIVE): The CLI generates the invite URL. The URL format (`/invite/{token}?swarm={swarm_id}`) must align between CLI output and this handler's route matching.

## Risks and Open Questions

- **Swarm routing without KV**: The plan uses `?swarm=` in the invite URL for simplicity. If the operator prefers a cleaner URL without the query param, we'd need a KV or global index for token→swarm resolution. Starting simple and can iterate.
- **Schema migration**: Adding `swarm_id` column to `gateway_keys` on existing DOs requires careful handling. The `ALTER TABLE ADD COLUMN` approach with try/catch is safe for SQLite but should be tested.
- **invite_cli_command alignment**: The CLI currently outputs URLs like `https://server/invite/{token}`. It will need updating to include `?swarm={swarm_id}`. This is out-of-scope for this chunk but noted as a required follow-up. Alternatively, this chunk could include the CLI change since it's a one-line fix.
- **Content-Type choice**: `text/plain` vs `text/markdown` — agents don't need a renderer, so `text/plain` is safest. Markdown formatting is just for human readability if they happen to view it.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.
-->