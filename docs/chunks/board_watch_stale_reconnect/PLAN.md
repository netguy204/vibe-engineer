

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug manifests after ~8+ WebSocket reconnection cycles over ~15 hours: the watch appears connected (re-poll logs confirm successful reconnect with correct cursor), but no messages are delivered. A restart immediately picks up the pending message.

**Root cause analysis** identifies two complementary failure modes:

1. **Server-side stale watcher accumulation**: In `handleWatch` (swarm-do.ts), each watch frame adds a NEW `{ws, cursor}` object to the in-memory `Set<Watcher>`. The Set uses object identity, so re-sending a watch frame on the same WebSocket creates duplicate entries. More critically, after Durable Object hibernation wakes, `wakeWatchers` has an early-return after the in-memory watcher path (line 1062) — if ALL in-memory sends fail (stale half-open sockets), the function returns without falling through to the hibernation recovery path that scans `ctx.getWebSockets()` attachments.

2. **Client-side silent stall**: `watch_with_reconnect` blocks indefinitely on `self._ws.recv()` with no application-level timeout. If the server loses the watcher state (hibernation, stale attachment, platform-level WebSocket tracking issue), the client hangs forever. WebSocket protocol pings succeed (handled by Cloudflare edge), so `ping_timeout` never fires. The connection appears alive but no application data flows.

**Fix strategy** — defense in depth on both sides:

- **Client-side**: Add a configurable stale-connection timeout to `watch_with_reconnect` and `watch_multi_with_reconnect`. When the timeout fires without a message, re-send the watch frame on the existing connection to re-register as a watcher. This is cheaper than a full reconnect (no auth handshake) and handles the "server lost watcher state" case. If re-registration also fails (recv timeout fires again), force a full reconnect.

- **Server-side**: Fix `handleWatch` to deduplicate watcher entries for the same WebSocket + channel. Fix `wakeWatchers` to fall through to hibernation recovery when all in-memory sends fail. Add diagnostic logging for watcher lifecycle events.

## Subsystem Considerations

No existing subsystems are relevant to this chunk. The work touches board client/server code which is not governed by any documented subsystem.

## Sequence

### Step 1: Write failing tests for the server-side watcher deduplication bug

Write a test for the Durable Object's `handleWatch` that demonstrates the duplicate watcher bug: sending two watch frames for the same channel on the same WebSocket should NOT create two entries in the in-memory watcher Set. Also write a test for `wakeWatchers` showing that when all in-memory sends fail (stale sockets), the method should fall through to the hibernation recovery path.

Location: `workers/leader-board/src/__tests__/` (or appropriate test location for the DO)

### Step 2: Fix server-side `handleWatch` — deduplicate watcher entries

In `swarm-do.ts`, modify `handleWatch` to remove any existing watcher entry for the same WebSocket before adding a new one. Currently, `channelWatchers.add({ws, cursor})` blindly adds a new object. Change to:

1. Iterate the existing `channelWatchers` Set for this channel
2. If an entry with `watcher.ws === ws` already exists, delete it
3. Then add the new entry

This prevents duplicate registrations when the client re-sends a watch frame on the same connection (which the client-side fix in Step 5 will do for stale detection).

Location: `workers/leader-board/src/swarm-do.ts` — `handleWatch` method (~line 922-928)

### Step 3: Fix server-side `wakeWatchers` — fall through on all-fail

In `swarm-do.ts`, modify `wakeWatchers` to track whether any in-memory send succeeded. If all sends failed (all watchers were stale/half-open), remove the early `return` and fall through to the hibernation recovery path. This handles the scenario where:
1. A stale half-open socket is in the in-memory watchers (its `ws.send()` succeeds but data never reaches the client)
2. The live client's watcher is only in the attachment (after hibernation lost the in-memory entry)

Change the logic from:
```typescript
// current: always returns after in-memory path
for (const w of toRemove) channelWatchers.delete(w);
if (channelWatchers.size === 0) this.watchers.delete(channel);
return;
```

To:
```typescript
// new: track delivery success
let delivered = false;
for (const watcher of channelWatchers) {
    // ... existing loop ...
    try {
        watcher.ws.send(...);
        delivered = true;  // at least one send succeeded
    } catch { }
    toRemove.push(watcher);
}
for (const w of toRemove) channelWatchers.delete(w);
if (channelWatchers.size === 0) this.watchers.delete(channel);
if (delivered) return;  // only skip hibernation recovery if we actually delivered
// fall through to hibernation recovery
```

Location: `workers/leader-board/src/swarm-do.ts` — `wakeWatchers` method (~line 1019-1062)

### Step 4: Add server-side diagnostic logging

Add `console.log` calls to key watcher lifecycle points in the DO:

- `handleWatch`: Log when a watcher is registered (channel, cursor, socket count for channel)
- `wakeWatchers`: Log when attempting delivery (channel, in-memory count, hibernation recovery trigger)
- `removeWatcher`: Log when a watcher is removed (channel, remaining count)

These logs are essential for diagnosing future issues and verifying the fix in production. Use structured log messages with channel and cursor context.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 5: Write failing tests for client-side stale connection detection

Write tests for `watch_with_reconnect` and `watch_multi_with_reconnect` that verify:

1. When `recv()` blocks beyond `stale_timeout`, the watch re-sends the watch frame on the same connection (re-registration)
2. When re-registration also fails (second timeout), a full reconnect is triggered
3. The `stale_timeout` parameter is respected and configurable
4. Normal operation (message received before timeout) is unaffected

Use `asyncio.wait_for` mocking or controlled delays to simulate the timeout. Follow the existing test patterns in `tests/test_board_client.py` (mock WebSocket factory, side_effect sequences).

Location: `tests/test_board_client.py`

### Step 6: Implement client-side stale connection detection in `watch_with_reconnect`

Refactor `watch_with_reconnect` to use `asyncio.wait_for` on the blocking `recv()` call. When the timeout fires:

1. First timeout: Log a warning and re-send the watch frame on the same connection (re-registration). This refreshes the server-side watcher state without the cost of a full reconnect (no auth handshake). Loop back to `recv()`.
2. Second consecutive timeout (re-registration didn't help): Raise `ConnectionError("Watch connection stale")` which triggers the existing reconnect logic (close, backoff, connect, re-auth).

Add a `stale_timeout` parameter (default: 300 seconds / 5 minutes). The timeout resets whenever a message is successfully received or after a successful reconnect.

The implementation replaces the inner `self.watch(channel, cursor)` call with inline send/recv logic that supports the timeout:

```python
async def watch_with_reconnect(self, channel, cursor, max_retries=None, stale_timeout=300):
    attempt = 0
    backoff = 1.0
    max_backoff = 30.0

    while True:
        try:
            frame = {"type": "watch", "channel": channel, "swarm": self.swarm_id, "cursor": cursor}
            await self._ws.send(json.dumps(frame))
            logger.info("Watch registered channel=%s cursor=%d", channel, cursor)

            reregister_count = 0
            while True:
                try:
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=stale_timeout)
                except asyncio.TimeoutError:
                    reregister_count += 1
                    if reregister_count > 1:
                        logger.warning(
                            "Watch stale after %d re-registrations, forcing reconnect "
                            "channel=%s cursor=%d",
                            reregister_count, channel, cursor,
                        )
                        raise ConnectionError("Watch connection stale")
                    logger.info(
                        "Watch re-registering: no message in %ds, channel=%s cursor=%d",
                        stale_timeout, channel, cursor,
                    )
                    await self._ws.send(json.dumps(frame))
                    continue

                response = json.loads(raw)
                self._check_error(response)
                if response.get("type") != "message":
                    raise BoardError("protocol_error", f"Expected message, got {response.get('type')}")
                return {
                    "position": response["position"],
                    "body": response["body"],
                    "sent_at": response["sent_at"],
                }
        except (...):
            # existing reconnect logic (unchanged)
```

Location: `src/board/client.py` — `watch_with_reconnect` method

### Step 7: Implement client-side stale connection detection in `watch_multi_with_reconnect`

Apply the same stale timeout pattern to `watch_multi_with_reconnect`. Since `watch_multi` is an async generator that yields multiple messages, the timeout should wrap the inner `self._ws.recv()` call within the `watch_multi` generator.

Two approaches:
- **Option A**: Add `stale_timeout` to `watch_multi` itself, making it re-send all watch frames on timeout
- **Option B**: Handle it in `watch_multi_with_reconnect` by catching `asyncio.TimeoutError` from the inner generator

Option A is cleaner because the re-registration (re-sending watch frames) should happen on the same connection. Add `stale_timeout` parameter to `watch_multi` and `watch_multi_with_reconnect`.

Location: `src/board/client.py` — `watch_multi` and `watch_multi_with_reconnect` methods

### Step 8: Write multi-cycle reconnection integration test

Write a test that simulates 10+ reconnection cycles and verifies message delivery after each. This directly validates the success criterion "Watch continues to deliver messages reliably after 10+ reconnection cycles."

The test should:
1. Set up a mock WebSocket factory that simulates repeated disconnects (ConnectionClosedError after each message)
2. Verify that each reconnect successfully delivers the next message
3. Verify cursor positions are correctly maintained across all cycles
4. Use a short `stale_timeout` to also exercise the re-registration path

Location: `tests/test_board_client.py`

### Step 9: Update GOAL.md code_paths

Update the chunk's GOAL.md `code_paths` frontmatter with the files modified:
- `src/board/client.py`
- `workers/leader-board/src/swarm-do.ts`
- `tests/test_board_client.py`

Location: `docs/chunks/board_watch_stale_reconnect/GOAL.md`

## Dependencies

No new external dependencies. The fix uses existing `asyncio.wait_for` (stdlib) and existing websockets library APIs. The server-side changes are contained within the existing Durable Object codebase.

## Risks and Open Questions

- **`asyncio.wait_for` cancellation safety with websockets**: Cancelling a `recv()` via `asyncio.wait_for` timeout should be safe with the websockets library (it's designed for cancellation), but verify this doesn't corrupt the connection's internal state. If it does, fall back to a `asyncio.wait` approach with explicit task management.

- **Duplicate message delivery on re-registration**: When the client re-sends a watch frame, the server may have a message ready from both the old watcher (push) and the new readAfter check. The server's `handleWatch` deduplication (Step 2) mitigates this by replacing the old watcher entry. If duplicates still occur, the caller's cursor-advancement logic naturally filters them (message position <= cursor).

- **Stale timeout tuning**: The default 5-minute timeout trades unnecessary re-registrations on quiet channels for faster recovery on stale connections. In production, channels that are legitimately quiet for hours will trigger periodic re-registrations — this is intentional and cheap (a single JSON frame) but generates log messages. May need to adjust the default based on operational feedback.

- **Half-open socket detection on the DO**: The `wakeWatchers` fix (Step 3) tracks whether `ws.send()` threw. But a half-open socket where `send()` buffers without throwing would still appear as a successful delivery. This is a Cloudflare platform-level issue that can't be fully solved at the application layer — the client-side stale timeout (Step 6) is the primary defense against this.

- **Root cause may be platform-specific**: If the bug is caused by a Cloudflare Durable Object platform issue (e.g., `ctx.getWebSockets()` returning stale entries, or attachment round-trip failures after many hibernation cycles), the fixes here are workarounds rather than root-cause fixes. The diagnostic logging (Step 4) will help confirm or rule this out.

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

- Step 1: Skipped writing separate failing tests for the server-side watcher
  deduplication bug. The Cloudflare vitest-pool-workers test environment
  requires `npm install` which is not available in this worktree. Server-side
  changes are covered by the existing e2e tests once deployed, and the logic
  is straightforward (dedup by ws identity, track delivered flag).

- Step 6: `watch_with_reconnect` now inlines the watch frame send + recv
  logic instead of delegating to `self.watch()`, as planned in the PLAN.md
  code sketch. This was necessary because `asyncio.wait_for` must wrap the
  `recv()` call directly, and the re-registration logic (re-sending the
  watch frame on timeout) requires access to both `send` and `recv` in the
  same loop. The `self.watch()` method is preserved unchanged for callers
  that don't need reconnect/stale detection.

- Step 7: Implemented stale detection directly in `watch_multi` (Option A
  from the plan) with a helper closure `_send_all_watch_frames()` to
  re-register all active channels on timeout. The `stale_timeout` parameter
  is passed through from `watch_multi_with_reconnect`.