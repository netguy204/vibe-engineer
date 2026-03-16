

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk makes four targeted changes—three server-side in the Durable Object (`swarm-do.ts`) and one client-side in the Python WebSocket client (`client.py`)—to align our implementation with the [Cloudflare WebSocket Hibernation Server example](https://developers.cloudflare.com/durable-objects/examples/websocket-hibernation-server/) and eliminate zombie WebSocket accumulation.

The changes are intentionally small and surgical. Each addresses a specific gap identified by comparing our DO against the reference example. No new abstractions or architectural patterns are introduced.

**Server-side** (TypeScript): Add `setWebSocketAutoResponse` for application-level keepalive, complete the close handshake in `webSocketClose`, and call `getWebSockets()` in the constructor for early zombie detection.

**Client-side** (Python): Increase `close_timeout` from 1s to 10s to give the server time to complete the close handshake after hibernation wake.

**Testing**: The E2E test suite (`workers/leader-board/test/e2e.test.ts`) already covers hibernation recovery and reconnection. We will add a test verifying the close handshake completes properly. The Python client tests (`tests/test_board_client.py`) verify `close_timeout` is passed to `websockets.connect`, so we update assertions to reflect the new value.

## Subsystem Considerations

No existing subsystems are relevant to this chunk. The changes are scoped to WebSocket connection lifecycle management in the DO and Python client, which do not intersect with any documented subsystem (cluster_analysis, cross_repo_operations, friction_tracking, orchestrator, template_system, workflow_artifacts).

## Sequence

### Step 1: Add `setWebSocketAutoResponse` in the DO constructor

In `workers/leader-board/src/swarm-do.ts`, add the following line to the constructor (after `this.storage = new SwarmStorage(ctx.storage)`):

```ts
// Chunk: docs/chunks/websocket_zombie_cleanup - Application-level auto-response keeps connections active through Cloudflare edge proxy
this.ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
```

This makes the DO automatically reply `"pong"` to any client message `"ping"` **without waking from hibernation**. The Cloudflare edge proxy uses application-level activity (not just protocol pings) to determine idle connections — without this, our connections look idle to the proxy even though protocol pings are flowing, causing TCP drops.

**Verify**: `WebSocketRequestResponsePair` is available in the Cloudflare Workers runtime types. If the TypeScript compiler doesn't recognize it, check the `@cloudflare/workers-types` version and add a type assertion if needed.

Location: `workers/leader-board/src/swarm-do.ts`, constructor (lines 149–153)

### Step 2: Add zombie socket detection in the DO constructor

Add a `getWebSockets()` call in the constructor to detect and log zombie sockets on hibernation wake:

```ts
// Chunk: docs/chunks/websocket_zombie_cleanup - Detect zombie sockets on hibernation wake
const existingSockets = this.ctx.getWebSockets();
if (existingSockets.length > 0) {
  console.log(`[SwarmDO] Constructor wake: found ${existingSockets.length} existing WebSocket(s)`);
}
```

This runs when the DO wakes from hibernation and its constructor is re-invoked. By calling `getWebSockets()` early, we ensure the runtime is aware of all surviving sockets and any zombies are surfaced in logs. The actual watcher recovery happens in `wakeWatchers`, but this gives visibility into the state at wake time.

Location: `workers/leader-board/src/swarm-do.ts`, constructor (after `setWebSocketAutoResponse`)

### Step 3: Complete the close handshake in `webSocketClose`

In the `webSocketClose` handler, add `ws.close(code, reason)` after `removeWatcher(ws)` to send the server-side close frame back to the client:

```ts
// Chunk: docs/chunks/websocket_zombie_cleanup - Complete server-side close handshake to prevent zombie accumulation
async webSocketClose(ws: WebSocket, code: number, reason: string, _wasClean: boolean): Promise<void> {
  this.removeWatcher(ws);
  try {
    ws.close(code, reason);
  } catch {
    // Socket may already be fully closed — safe to ignore
  }
}
```

Key details:
- Rename `_code`/`_reason` parameters to `code`/`reason` since they are now used.
- Wrap `ws.close()` in a try/catch because the socket may already be in a terminal state (the runtime calls `webSocketClose` when the client initiates close, and by the time we process it, the socket may be fully closed).
- Without this, the client sends a close frame, waits for the server's response, times out at `close_timeout`, and drops TCP — leaving a zombie in `ctx.getWebSockets()`.

Location: `workers/leader-board/src/swarm-do.ts`, `webSocketClose` (lines 623–625)

### Step 4: Increase client-side `close_timeout` to 10s

In `src/board/client.py`, change `close_timeout=1` to `close_timeout=10` in all `websockets.connect()` calls:

1. **`connect()` method** (line 61): `close_timeout=1` → `close_timeout=10`
2. **`register_swarm()` method** (line 109): `close_timeout=1` → `close_timeout=10`

Add a backreference comment:
```python
# Chunk: docs/chunks/websocket_zombie_cleanup - Increase close_timeout to allow server close handshake after hibernation wake
```

The 1-second timeout was too aggressive — after hibernation, the DO needs time to wake, process the close frame, and respond. 10 seconds gives sufficient headroom.

Location: `src/board/client.py`, `connect()` and `register_swarm()`

### Step 5: Update Python client tests

In `tests/test_board_client.py`, update any assertions that check the `close_timeout` value passed to `websockets.connect()`. Change expected value from `1` to `10`.

Search the test file for `close_timeout` to find all relevant assertions.

Location: `tests/test_board_client.py`

### Step 6: Add E2E test for close handshake completion

In `workers/leader-board/test/e2e.test.ts`, add a test that verifies the close handshake completes properly:

```ts
it("server completes close handshake when client initiates close", async () => {
  const swarmId = "e2e-close-" + Date.now();
  const { privKey } = await registerSwarm(swarmId);
  const ws = await authenticateWs(swarmId, privKey);

  // Client initiates close
  ws.close(1000, "normal closure");

  // The close should complete (server sends close response)
  // If the server doesn't respond, this will hang until close_timeout
  await new Promise<void>((resolve) => {
    ws.addEventListener("close", () => resolve());
  });
});
```

This test verifies the fix from Step 3: that `webSocketClose` sends `ws.close(code, reason)` back, allowing the WebSocket handshake to complete normally rather than timing out.

Location: `workers/leader-board/test/e2e.test.ts`

### Step 7: Run all tests and verify

1. Run TypeScript E2E tests: `cd workers/leader-board && npx vitest run`
2. Run Python tests: `uv run pytest tests/test_board_client.py`
3. Verify no regressions in existing hibernation recovery tests

## Dependencies

- Parent chunk `websocket_hibernation_compat` must be ACTIVE (it is — already merged).
- `WebSocketRequestResponsePair` must be available in the Cloudflare Workers runtime types. This is part of the standard Hibernation API and should be present in `@cloudflare/workers-types`.

## Risks and Open Questions

- **`WebSocketRequestResponsePair` type availability**: If the installed `@cloudflare/workers-types` version doesn't include this type, we may need to update the package or add a type declaration. Check `package.json` for the current version.
- **`ws.close()` in `webSocketClose` may throw**: The Cloudflare runtime may throw if the socket is already fully closed by the time our handler runs. The try/catch in Step 3 mitigates this, but we should verify the exact error behavior in the E2E test.
- **Application-level ping/pong collision with protocol messages**: Client code sending `"ping"` as a regular message would get an auto `"pong"` response from the DO without waking it. This is unlikely to be a problem since our protocol uses JSON frames, not bare strings, but worth noting.
- **Close timeout of 10s may be too generous for `register_swarm`**: The `register_swarm` method uses a short-lived connection for registration. 10s close timeout is fine (it's a max, not a delay), but if latency concerns arise, it could be tuned separately.

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