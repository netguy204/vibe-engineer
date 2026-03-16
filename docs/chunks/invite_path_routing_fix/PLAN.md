

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The root cause is a routing-layer mismatch: the worker entry point (`src/index.ts`) requires a `?swarm=` query parameter on every request to determine which Durable Object to route to, but `/invite/{token}` URLs by design carry only the token — no swarm ID.

The fix introduces a **Workers KV namespace as a secondary index** mapping `token_hash → swarm_id`. This index is maintained as a side-effect of gateway key CRUD operations (PUT writes, DELETE removes), and is read at the worker entry point to resolve invite tokens to their swarm before routing.

**Why KV?** The token → swarm mapping must be available *before* the worker knows which DO to contact (since DOs are keyed by swarm ID). Workers KV is the natural Cloudflare primitive for fast, globally-distributed reads at the worker level. The mapping is written infrequently (invite creation/revocation) and read on every invite page visit — a read-heavy pattern that KV is optimized for.

**Alternatives considered:**
- *Encode swarm_id in the URL* (`/invite/{swarm}/{token}`): Would break the established URL contract from the `agent_invite_links` investigation protocol.
- *Registry DO*: A well-known DO storing all token→swarm mappings. Adds an extra DO hop on every invite request and couples all swarms through a single coordination point.
- *Scan all DOs*: Not feasible — no enumeration API for DO instances.

**Testing approach:** Following the testing philosophy, we write failing tests first for the new behavior (invite works without `?swarm=`), then implement. Existing tests that pass `?swarm=` continue to work as a backward-compatible path.

## Sequence

### Step 1: Add KV namespace binding

Add a `TOKEN_SWARM_INDEX` KV namespace to `workers/leader-board/wrangler.toml` and update the `Env` interface in `workers/leader-board/src/swarm-do.ts` to include it.

Location: `workers/leader-board/wrangler.toml`, `workers/leader-board/src/swarm-do.ts`

Changes:
- Add `[[kv_namespaces]]` block with `binding = "TOKEN_SWARM_INDEX"` to wrangler.toml
- Add `TOKEN_SWARM_INDEX: KVNamespace` to the `Env` interface
- Store `env` in the `SwarmDO` constructor (currently unused, prefixed with `_env`)

### Step 2: Maintain KV index on gateway key CRUD

When gateway keys are created or deleted, maintain the KV secondary index in sync.

Location: `workers/leader-board/src/swarm-do.ts` (handleGatewayKeys method)

Changes in `handleGatewayKeys`:
- **PUT**: After `this.storage.putGatewayKey(...)`, call `await this.env.TOKEN_SWARM_INDEX.put(body.token_hash, swarmId)` to write the mapping
- **DELETE (single)**: After `this.storage.deleteGatewayKey(tokenHash)`, call `await this.env.TOKEN_SWARM_INDEX.delete(tokenHash)` to remove the mapping
- **DELETE (bulk)**: Before `this.storage.deleteAllGatewayKeys()`, list all keys via `this.storage.listGatewayKeys()` to get their token hashes, then delete each from KV after the bulk delete

Note: The `handleGatewayKeys` method must become `async` (it already returns `Promise<Response>` but doesn't currently `await` anything).

### Step 3: Write failing tests for swarm-less invite routing

Add new test cases to `workers/leader-board/test/invite-page.test.ts` that exercise the core fix: `/invite/{token}` without `?swarm=` should work.

Location: `workers/leader-board/test/invite-page.test.ts`

New tests:
- **"GET /invite/{token} works without swarm query parameter"**: Call `setupGateway(...)`, then fetch `/invite/{tokenHex}` (no `?swarm=`). Expect 200 with instruction page content.
- **"invalid token without swarm parameter returns 404"**: Fetch `/invite/{fakeToken}` (no `?swarm=`). Expect 404 with "Invalid or expired invite token".
- **"revoked token without swarm parameter returns 404"**: Setup gateway, revoke token, fetch `/invite/{tokenHex}` (no `?swarm=`). Expect 404.

Update the existing test **"missing swarm parameter returns 400"**: This test currently expects 400 when no swarm is provided. After the fix, an unknown token without `?swarm=` should return 404 (token not found in KV), not 400. Update the assertion accordingly.

### Step 4: Implement invite path early-exit in the worker entry point

Move the `/invite/{token}` route *before* the swarm-required guard in `src/index.ts`. When the path matches, hash the token, look up the swarm in KV, and route to the correct DO.

Location: `workers/leader-board/src/index.ts`

Changes:
- Import `hashToken` from `./gateway-crypto`
- Before the `if (!swarmId)` guard, add an early-exit block:
  ```typescript
  const inviteMatch = url.pathname.match(/^\/invite\/([^/]+)$/);
  if (inviteMatch) {
    const token = inviteMatch[1];
    const tokenHash = hashToken(token);
    const resolvedSwarmId = await env.TOKEN_SWARM_INDEX.get(tokenHash);
    if (!resolvedSwarmId) {
      return new Response("Invalid or expired invite token", {
        status: 404,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }
    const id = env.SWARM_DO.idFromName(resolvedSwarmId);
    const stub = env.SWARM_DO.get(id);
    return stub.fetch(request);
  }
  ```
- Remove the now-redundant `/invite/` match block from after the swarm guard (lines 44-47)

This preserves backward compatibility: if someone passes `?swarm=` with an invite URL, the early-exit fires first and resolves via KV regardless.

### Step 5: Run tests and verify

Run the full test suite to confirm:
- New tests pass (invite works without `?swarm=`)
- Existing tests pass (gateway API, key CRUD, WebSocket, etc.)
- The updated "missing swarm" test passes with the new expectation

Command: `cd workers/leader-board && npx vitest run`

## Dependencies

- Parent chunk `invite_instruction_page` must be ACTIVE (it is — `handleInvitePage` and `renderInvitePage` already exist on the DO)
- `gateway_token_storage` must be ACTIVE (it is — gateway key CRUD and the `swarm_id` column exist)

## Risks and Open Questions

- **KV eventual consistency**: Workers KV is eventually consistent for reads. In practice, a freshly created invite might not be resolvable for a brief window (typically seconds). This is acceptable for the invite use case — the operator creates the invite and shares the URL, and the recipient visits it later. If sub-second consistency is needed in the future, a Registry DO approach could replace KV.
- **KV test behavior**: The `@cloudflare/vitest-pool-workers` test framework uses miniflare under the hood, where KV is backed by in-memory storage and reads are immediately consistent. Tests should pass without consistency issues.
- **Bulk delete KV cleanup**: When `DELETE /gateway/keys` (no token_hash) bulk-deletes all keys, we need to iterate through `listGatewayKeys()` to know which KV entries to remove. This is a rare operation and the list is expected to be small.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->