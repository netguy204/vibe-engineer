

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The worker currently only accepts WebSocket upgrades — all non-WebSocket requests get a 426. This chunk adds three plain HTTP JSON routes to the Worker entry point (`src/index.ts`) that forward to new methods on `SwarmDO.fetch()`, and a new `gateway_keys` SQLite table managed by `SwarmStorage`.

**Key design choices:**

1. **Route in the Worker, handle in the DO.** The Worker entry point already routes by swarm ID. We extend its `fetch()` to dispatch `/gateway/keys` paths to the correct DO via `stub.fetch(request)` — the same pattern used for WebSocket upgrades. The DO's `fetch()` gains an HTTP branch alongside its WebSocket branch.

2. **New table, same storage class.** `SwarmStorage` gets a `gateway_keys` table with columns `(token_hash TEXT PRIMARY KEY, encrypted_blob TEXT NOT NULL, created_at TEXT NOT NULL)`. The `swarm_id` is implicit — each DO instance *is* a swarm, so the storage is already scoped. `ensureSchema()` creates this table alongside the existing ones.

3. **TDD per TESTING_PHILOSOPHY.md.** Tests are written first using the existing `@cloudflare/vitest-pool-workers` + `SELF.fetch` pattern. The round-trip test (store → retrieve → delete → 404) maps directly to the success criteria.

4. **No auth on these routes (yet).** The investigation notes that the CLI (`ve board invite`) will be the caller for PUT/DELETE, and the cleartext gateway (next chunk) for GET. Authentication is deferred to those chunks — this chunk provides the raw storage primitive.

## Subsystem Considerations

No existing subsystems (template_system, workflow_artifacts, orchestrator, etc.) are relevant to this chunk. This work is entirely within the Cloudflare Worker/DO layer which has no corresponding subsystem documentation.

## Sequence

### Step 1: Write failing tests for the gateway key storage routes

Create `test/gateway-keys.test.ts` with tests that exercise the full round-trip through HTTP:

1. **PUT stores a key blob** — `PUT /gateway/keys?swarm=<id>` with JSON body `{token_hash, encrypted_blob}`, expect 200 with `{ok: true}`.
2. **GET retrieves the blob** — `GET /gateway/keys/<token_hash>?swarm=<id>`, expect 200 with `{token_hash, encrypted_blob, created_at}`.
3. **GET returns 404 for unknown hash** — expect 404 with JSON error.
4. **DELETE removes the blob** — `DELETE /gateway/keys/<token_hash>?swarm=<id>`, expect 200 with `{ok: true}`.
5. **GET after DELETE returns 404** — the full revocation round-trip.
6. **DELETE of non-existent hash returns 404** — idempotency boundary.
7. **PUT with missing fields returns 400** — validation.

Use the existing `SELF.fetch` pattern from `test/index.test.ts`. These are plain HTTP requests (no WebSocket), which is the novel part — the Worker must route them to the DO without requiring an upgrade header.

Location: `workers/leader-board/test/gateway-keys.test.ts`

### Step 2: Add the `gateway_keys` table to SwarmStorage

Extend `SwarmStorage.ensureSchema()` to create:

```sql
CREATE TABLE IF NOT EXISTS gateway_keys (
  token_hash TEXT PRIMARY KEY,
  encrypted_blob TEXT NOT NULL,
  created_at TEXT NOT NULL
)
```

Add three new methods to `SwarmStorage`:

- `putGatewayKey(tokenHash: string, encryptedBlob: string): void` — INSERT OR REPLACE with current timestamp.
- `getGatewayKey(tokenHash: string): {token_hash: string, encrypted_blob: string, created_at: string} | null` — SELECT by primary key.
- `deleteGatewayKey(tokenHash: string): boolean` — DELETE, return true if a row was actually deleted.

Add a `// Chunk: docs/chunks/gateway_token_storage` backreference on each method.

Location: `workers/leader-board/src/storage.ts`

### Step 3: Add HTTP route handling to the Worker entry point

Modify `src/index.ts` to distinguish between WebSocket upgrades and plain HTTP requests. Currently, non-WebSocket requests to a known swarm get forwarded to the DO (which returns 426). Instead:

- If the URL path starts with `/gateway/keys`, forward to the DO via `stub.fetch(request)` regardless of upgrade header.
- Otherwise, keep the existing WebSocket-only behavior.

The swarm query parameter is still required for all requests (consistent with existing pattern).

Location: `workers/leader-board/src/index.ts`

### Step 4: Add HTTP route handling to SwarmDO.fetch()

Extend `SwarmDO.fetch()` to handle non-WebSocket requests on the `/gateway/keys` path:

- **PUT /gateway/keys** — Parse JSON body `{token_hash, encrypted_blob}`, validate both fields are non-empty strings, call `storage.putGatewayKey()`, return 200 JSON `{ok: true}`.
- **GET /gateway/keys/{token_hash}** — Extract token_hash from URL path, call `storage.getGatewayKey()`, return 200 JSON with the blob or 404 JSON error.
- **DELETE /gateway/keys/{token_hash}** — Extract token_hash from URL path, call `storage.deleteGatewayKey()`, return 200 JSON `{ok: true}` or 404 JSON error.

Return 405 for unsupported methods on this path. Return JSON `Content-Type` headers on all responses.

Add a `// Chunk: docs/chunks/gateway_token_storage` backreference on the HTTP handling method.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 5: Run tests and verify all pass

Run `npm test` in the worker directory. All new tests from Step 1 should now pass, and all existing tests should remain green (the WebSocket behavior is unchanged).

### Step 6: Verify existing tests still pass

Confirm that the WebSocket routing in `test/index.test.ts` is unaffected — specifically that `?swarm=<id>` without a `/gateway/keys` path and without an upgrade header still returns 426 (not routed to the new HTTP handler).

## Dependencies

No new dependencies. The existing `@cloudflare/vitest-pool-workers`, Durable Object SQLite storage, and `SELF.fetch` test pattern provide everything needed. No external libraries required — this is pure storage CRUD with no cryptography (encryption happens client-side in the `invite_cli_command` chunk).

## Risks and Open Questions

- **Auth deferred.** These routes have no authentication — any caller who knows a swarm ID can PUT/GET/DELETE gateway keys. The investigation design expects the CLI and cleartext gateway chunks to layer auth. If this proves problematic, a shared-secret header could be added later without changing the storage API.
- **SELF.fetch for non-WebSocket DO requests.** The existing test suite exclusively tests WebSocket upgrades via `SELF.fetch`. Plain HTTP requests forwarded to the DO should work identically (the DO's `fetch()` method handles both), but this is the first time it's tested — if the vitest pool-workers plugin handles non-WS DO routing differently, tests may need adjustment.

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

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->