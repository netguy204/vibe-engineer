
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `SwarmDO` Durable Object stores pending watchers in a plain in-memory `Map<string, Set<Watcher>>` (swarm-do.ts:34). When the DO hibernates, this Map is lost from the JS heap, but the Hibernation API preserves WebSocket connections. The fix uses two Hibernation API mechanisms that survive hibernation:

1. **WebSocket tags** — `this.ctx.acceptWebSocket(ws, tags)` and `this.ctx.getWebSockets(tag)` allow tagging sockets and retrieving them by tag after wake-up. We cannot re-tag after accept, so we tag at accept time with a general tag and then use attachments to track watch state.

2. **WebSocket attachments** — `ws.serializeAttachment(obj)` / `ws.deserializeAttachment()` persist structured data on the WebSocket across hibernation. The attachment already stores auth state; we extend it to also store watcher channel and cursor.

**Strategy**: When a `watch` frame registers a pending watcher, we persist the channel and cursor into the WebSocket attachment alongside the existing auth state. In `wakeWatchers`, when the in-memory Map has no watchers for a channel, we fall back to scanning all connected WebSockets via `this.ctx.getWebSockets()`, checking their attachments for matching watch state, and delivering messages to recovered watchers.

This approach avoids needing per-channel tags (which would require re-accepting the WebSocket, which is not supported after initial accept). Instead, all hibernation-accepted WebSockets are retrievable via `this.ctx.getWebSockets()` (no tag = all sockets), and the attachment discriminates which ones are watching which channel.

Per docs/trunk/TESTING_PHILOSOPHY.md, we write tests that verify the semantic goal ("message delivered after hibernation") rather than structural assertions about internal state. The e2e test will simulate the hibernation gap by directly exercising the DO's watcher recovery path.

## Sequence

### Step 1: Extend the attachment schema to include watch state

Update the attachment type throughout `swarm-do.ts` to support an optional `watching` field:

```typescript
interface WsAttachment {
  state: "handshake" | "authenticated";
  nonce?: string;
  watching?: { channel: string; cursor: number };
}
```

Update `webSocketMessage` (line 69) to deserialize using this expanded type. No behavioral change yet — `watching` will be `undefined` for all existing connections.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 2: Persist watch state in attachment when registering a watcher

In `handleWatch` (line 191), after adding the watcher to the in-memory Map (lines 230-235), also persist the watch state to the WebSocket attachment:

```typescript
// After adding to in-memory map:
const attachment = ws.deserializeAttachment() as WsAttachment;
attachment.watching = { channel: frame.channel, cursor: frame.cursor };
ws.serializeAttachment(attachment);
```

This ensures the channel and cursor survive hibernation. The in-memory Map remains the primary path for non-hibernation wake-ups.

Location: `workers/leader-board/src/swarm-do.ts`, `handleWatch` method

### Step 3: Clear watch state from attachment when a watcher is fulfilled

In `wakeWatchers` (line 267), after successfully sending a message to a watcher and marking it for removal, also clear the `watching` field from the attachment so the WebSocket is no longer considered a pending watcher:

```typescript
// After sending message to watcher:
const att = watcher.ws.deserializeAttachment() as WsAttachment;
delete att.watching;
watcher.ws.serializeAttachment(att);
```

Also clear `watching` in `handleWatch` when a message is available immediately (the non-blocking path, lines 217-227) — in this case no attachment was set, so no action needed. But to be safe, ensure the attachment does NOT have a stale `watching` field if `handleWatch` is called multiple times on the same WebSocket.

Location: `workers/leader-board/src/swarm-do.ts`, `wakeWatchers` method

### Step 4: Add hibernation-recovery fallback to `wakeWatchers`

Modify `wakeWatchers` to recover watchers from WebSocket attachments when the in-memory Map is empty or missing the channel. After checking the in-memory Map, add a recovery path:

```typescript
private wakeWatchers(channel: string, newPosition: number): void {
  // 1. Try in-memory watchers first (fast path, no hibernation)
  const channelWatchers = this.watchers.get(channel);
  if (channelWatchers && channelWatchers.size > 0) {
    // ... existing logic (unchanged) ...
    return;
  }

  // 2. Hibernation recovery: scan all connected WebSockets
  // Chunk: docs/chunks/leader_board_hibernate_watch - Recover watchers after hibernation
  const allSockets = this.ctx.getWebSockets();
  for (const ws of allSockets) {
    const attachment = ws.deserializeAttachment() as WsAttachment;
    if (attachment?.watching?.channel === channel && attachment.watching.cursor < newPosition) {
      const msg = this.storage.readAfter(channel, attachment.watching.cursor);
      if (msg) {
        try {
          ws.send(serializeFrame({ type: "message", ... }));
          // Clear watch state after delivery
          delete attachment.watching;
          ws.serializeAttachment(attachment);
        } catch {
          // WebSocket may have closed
        }
      }
    }
  }
}
```

**Key design choice**: The in-memory Map check comes first as a fast path. The `getWebSockets()` scan only runs when the Map has nothing for this channel, which is exactly the post-hibernation case. This ensures no regression in the non-hibernation path.

Location: `workers/leader-board/src/swarm-do.ts`, `wakeWatchers` method

### Step 5: Update `removeWatcher` to also clear attachment watch state

In `removeWatcher` (line 303), after removing from the in-memory Map, also clear the `watching` field in the attachment so a hibernation recovery doesn't find stale state:

```typescript
private removeWatcher(ws: WebSocket): void {
  // Clear in-memory state
  for (const [channel, watchers] of this.watchers) { ... }

  // Clear attachment watch state
  try {
    const attachment = ws.deserializeAttachment() as WsAttachment;
    if (attachment?.watching) {
      delete attachment.watching;
      ws.serializeAttachment(attachment);
    }
  } catch {
    // WebSocket may already be closed/invalid
  }
}
```

Location: `workers/leader-board/src/swarm-do.ts`, `removeWatcher` method

### Step 6: Verify existing tests still pass

Run the existing test suite to confirm no regressions:

```bash
cd workers/leader-board && npx vitest run
```

The "concurrent connections: watcher receives message from sender" test exercises the non-hibernation path (in-memory Map is populated, no hibernation occurs). It must continue to pass unchanged.

### Step 7: Write the hibernation-gap e2e test

Add a new test to `test/e2e.test.ts` that exercises the recovery path. The test must verify the semantic goal: a watcher blocked before a message exists receives the message after the DO's in-memory state is lost.

**Test approach**: The `@cloudflare/vitest-pool-workers` test environment runs the DO in-process. We can simulate the hibernation gap by:
1. Registering a watcher (which populates the in-memory Map)
2. Directly accessing the DO instance and clearing its `watchers` Map to simulate hibernation memory loss
3. Sending a message from another connection
4. Asserting the watcher receives the message via attachment-based recovery

If direct DO instance access is not available in the test environment, an alternative approach:
- Use `env.SWARM_DO.get(id)` to get a DO stub, then call a test-only endpoint, OR
- Structure the test so that the watcher connection spans a DO cold-start boundary

The test structure:

```typescript
it("watcher receives message after hibernation clears in-memory state", async () => {
  const swarmId = "e2e-hibernate-" + Date.now();
  const { privKey } = await registerSwarm(swarmId);

  const sender = await authenticateWs(swarmId, privKey);
  const watcher = await authenticateWs(swarmId, privKey);

  // Create channel
  sender.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "Zmlyc3Q=" }));
  await nextMessage(sender); // ack

  // Watcher blocks at cursor 1
  watcher.send(JSON.stringify({ type: "watch", channel: "ch", swarm: swarmId, cursor: 1 }));

  // Simulate hibernation: clear in-memory watchers
  // (approach depends on test environment capabilities)

  // Sender sends another message — wakeWatchers must recover from attachments
  sender.send(JSON.stringify({ type: "send", channel: "ch", swarm: swarmId, body: "c2Vjb25k" }));
  await nextMessage(sender); // ack

  // Watcher should receive the message despite in-memory Map being empty
  const msg = await nextMessage(watcher);
  expect(msg.type).toBe("message");
  expect(msg.position).toBe(2);
  expect(msg.body).toBe("c2Vjb25k");

  sender.close();
  watcher.close();
});
```

Location: `workers/leader-board/test/e2e.test.ts`

### Step 8: Run the full test suite and verify all tests pass

```bash
cd workers/leader-board && npx vitest run
```

All existing tests plus the new hibernation test must pass.

## Dependencies

- `leader_board_durable_objects` (ACTIVE) — provides the SwarmDO implementation being modified
- `leader_board_user_config` (ACTIVE) — provides the config layer (no code changes needed here)
- Cloudflare Hibernation API (`this.ctx.getWebSockets()`, `ws.serializeAttachment()`) — already available in the `@cloudflare/workers-types` dependency

## Risks and Open Questions

- **`this.ctx.getWebSockets()` without a tag**: The Cloudflare docs confirm that calling `getWebSockets()` with no arguments returns all accepted WebSockets. However, we need to verify this works correctly in the `@cloudflare/vitest-pool-workers` test environment, which simulates the DO runtime.

- **Simulating hibernation in tests**: The `@cloudflare/vitest-pool-workers` pool runs DOs in-process. There may not be a built-in way to trigger actual hibernation. The test may need to simulate it by clearing the in-memory Map via a test hook or by accepting that the test exercises the recovery code path indirectly. If the DO class needs a `_clearWatchersForTest()` method, it should be clearly marked as test-only and not part of the public interface. Alternatively, we can expose a method gated on a test flag.

- **Multiple watches on the same WebSocket**: The current design allows a WebSocket to only watch one channel at a time (the `watching` attachment field is a single object, not an array). This matches the current protocol (a watch frame blocks until fulfilled, then the client sends another watch). If multi-channel watching is ever needed, the attachment schema would need to change to an array. This is acceptable for now.

- **`getWebSockets()` performance**: Scanning all WebSockets on every `wakeWatchers` call post-hibernation is O(n) where n is total connected sockets. For the leader board use case (a handful of steward connections), this is negligible. If the swarm ever supports thousands of concurrent watchers, a per-channel tag strategy would be needed (which would require changes to how WebSockets are accepted).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->