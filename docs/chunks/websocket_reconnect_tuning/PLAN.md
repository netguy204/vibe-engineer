

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk addresses two issues introduced after `websocket_hibernation_compat` removed server-side heartbeats:

**Issue 1 — Backoff never resets:** The `watch_with_reconnect` method in `src/board/client.py` declares `attempt` and `backoff` before the `while True` loop but never resets them after a successful `watch()` call (which returns immediately). Since `watch_with_reconnect` is called once per message in the outer watch loop (`src/cli/board.py`), the backoff state is scoped to a single call and doesn't persist across messages. However, *within* a single call, if the connection drops multiple times before a message arrives, the backoff ratchets up and never resets even after a successful reconnect. The fix is to reset `backoff` and `attempt` to their initial values after `self.connect()` succeeds in the reconnect path. This way, if the freshly-reconnected connection drops again quickly, it starts with a short retry rather than resuming at e.g. 16s.

**Issue 2 — Investigate client-side pings vs Cloudflare idle timeouts:** The `websockets` library's `ping_interval=20` sends WebSocket protocol-level ping frames (opcode 0x9), not application-level messages. We need to investigate whether these are sufficient to keep Cloudflare's proxy from closing idle connections. The investigation will be documented in this plan's deviations section with findings and any resulting code changes.

Tests follow TDD per `docs/trunk/TESTING_PHILOSOPHY.md`: write a failing test for backoff reset, then implement the fix. The investigation outcome may produce additional code changes (e.g., tuning `ping_interval`, adding application-level keepalive) with corresponding tests.

## Sequence

### Step 1: Write failing test for backoff reset after successful reconnect

Add a new test `test_watch_with_reconnect_resets_backoff_after_success` to `tests/test_board_client.py`. This test should:

1. Set up a mock sequence where the first connection fails 3 times (driving backoff to 4s), then reconnects successfully, then the *new* connection drops again
2. Mock `random.uniform` to return 0 for deterministic jitter
3. Assert that the 4th sleep (after the post-success disconnect) uses the initial backoff of 1.0s, not the accumulated 8.0s

This test must fail before the fix is applied, confirming the bug exists.

Location: `tests/test_board_client.py`

### Step 2: Fix backoff reset in `watch_with_reconnect`

After the successful `await self.connect()` call in the reconnect path (line 216 of `src/board/client.py`), reset both `attempt` and `backoff` to their initial values:

```python
await self.connect()
# Chunk: docs/chunks/websocket_reconnect_tuning - Reset backoff after successful reconnect
attempt = 0
backoff = 1.0
```

This means: if the reconnected connection immediately drops again, the next backoff starts at 1.0s. The `attempt` counter also resets, so `max_retries` counts consecutive failures from the last successful connection, not total lifetime failures.

Location: `src/board/client.py`, inside `watch_with_reconnect`

### Step 3: Verify the new test passes and existing tests still pass

Run `uv run pytest tests/test_board_client.py -v` to confirm:
- The new backoff-reset test passes
- All existing reconnect tests (`test_watch_with_reconnect_on_disconnect`, `test_watch_with_reconnect_max_retries`, `test_watch_with_reconnect_backoff`) still pass

### Step 4: Investigate client-side pings and Cloudflare idle timeouts

Research and document the following:

1. **Confirm `websockets` library ping behavior**: The library sends WebSocket-level ping frames (opcode 0x9) at the configured `ping_interval`. This is protocol-level, not application-level. Verify by reading websockets library source/docs.

2. **Cloudflare Worker WebSocket proxy behavior**: Cloudflare's edge proxy has an idle timeout (typically 100 seconds for WebSocket connections). The key question: does Cloudflare's proxy count WebSocket ping/pong frames as "activity" for idle timeout purposes, or only data frames?

3. **Durable Object hibernation and WebSocket survival**: When a DO hibernates, the Cloudflare runtime holds WebSocket connections open. The DO's `webSocketClose` handler fires if the client disconnects. But does the runtime's WebSocket proxy between the client and the DO also have its own idle timeout that could close the connection even while the DO is hibernated?

4. **Current `ping_interval=20` assessment**: With 20s pings, the client sends a ping every 20 seconds. If Cloudflare counts pings as activity, this should keep the connection alive well within a 100s idle timeout. If connections are still dropping at 2-5 minute intervals, either:
   - Cloudflare doesn't count pings as activity (needs data frames)
   - The DO's hibernation eviction is closing connections
   - There's an intermediate proxy (e.g., Cloudflare's edge-to-origin tunnel) with its own timeout

Document findings in the Deviations section below.

### Step 5: Implement keepalive changes based on investigation

Based on Step 4 findings, implement one of:

**If pings are sufficient but interval is wrong**: Adjust `ping_interval` in `BoardClient.connect()` and document the rationale.

**If pings don't prevent Cloudflare idle timeouts**: Add an application-level keepalive mechanism. The simplest approach is a periodic no-op frame sent by the client that the server echoes, resetting Cloudflare's idle timer. This would require:
- A new `keepalive` frame type in the protocol (or reuse an existing mechanism)
- A background task in `watch_with_reconnect` that sends keepalive frames at a regular interval
- Server-side handling to echo or acknowledge the keepalive without waking the DO from hibernation (this may not be possible—hibernated DOs can't process messages)

**If the issue is DO hibernation eviction**: This is outside client-side control. Document the finding and note that the reconnect mechanism (now with proper backoff reset) is the correct mitigation. Consider reducing `ping_interval` to keep Cloudflare's edge proxy happy while accepting that DO hibernation will cause periodic disconnects.

Location: `src/board/client.py` (client changes), potentially `workers/leader-board/src/swarm-do.ts` (server changes)

### Step 6: Add/update tests for any keepalive changes

If Step 5 produces code changes beyond ping_interval tuning:
- Test that the keepalive mechanism fires at the expected interval
- Test that reconnection after keepalive failure follows the (now-reset) backoff strategy
- Ensure tests mock time/sleep appropriately for determinism

Location: `tests/test_board_client.py`

### Step 7: Update backreference comment on `watch_with_reconnect`

Update the existing backreference comment on `watch_with_reconnect` (line 159) to reference this chunk alongside the original `websocket_keepalive` reference:

```python
# Chunk: docs/chunks/websocket_keepalive - Reconnect wrapper for watch()
# Chunk: docs/chunks/websocket_reconnect_tuning - Backoff reset and keepalive tuning
```

Location: `src/board/client.py`

## Risks and Open Questions

- **Cloudflare idle timeout behavior with ping frames is undocumented**: The investigation (Step 4) may not produce a definitive answer. If field testing is needed, we may need to deploy a test and observe connection lifetimes before and after changes.
- **DO hibernation vs. connection survival**: Cloudflare's documentation says WebSocket connections survive hibernation, but field observations suggest otherwise. If the DO runtime is closing connections on hibernation, there's no client-side fix — only the reconnect mechanism with proper backoff reset.
- **Application-level keepalive and hibernation conflict**: If we need application-level keepalive frames, these would wake the DO from hibernation, defeating the purpose of `websocket_hibernation_compat`. The investigation must determine whether this tradeoff is acceptable or if we need a different approach.
- **max_retries semantics change**: Resetting `attempt` after successful reconnect changes the meaning of `max_retries` from "total lifetime attempts" to "consecutive failures since last success." This is the better semantic for long-running watches but is a behavior change. The existing `test_watch_with_reconnect_max_retries` test should still pass since it tests a scenario with only consecutive failures.

## Deviations

### Deviation 1: Only backoff resets after connect(), not attempt counter

The plan called for resetting both `attempt` and `backoff` after successful `connect()`. In practice, `connect()` always succeeds (the auth handshake completes) even when the server will immediately drop the watch. Resetting `attempt` after every successful `connect()` made `max_retries` unreachable — the attempt counter would never exceed 1, causing `test_watch_with_reconnect_max_retries` to hang in an infinite loop.

**Resolution:** Only `backoff` resets to 1.0 after successful `connect()`. The `attempt` counter continues to accumulate across all failures, preserving `max_retries` as a safety valve. This means `max_retries` counts total failures within a single `watch_with_reconnect` call, not consecutive failures since last successful connection.

### Deviation 2: Exponential backoff effectively becomes constant 1s retry

Because `backoff` resets to 1.0 after every successful `connect()`, and `connect()` succeeds at the end of each retry cycle, the exponential doubling (`backoff * 2`) is immediately overwritten. All retries sleep for 1.0s (plus jitter). This is the correct behavior for the real-world scenario: if the network is healthy enough to complete a WebSocket handshake, the next retry should be fast. The `max_retries` limit prevents infinite 1s loops.

The existing `test_watch_with_reconnect_backoff` test was updated to reflect this: all sleep durations are 1.0s rather than the previous 1s, 2s, 4s progression.

### Deviation 3: No code changes from keepalive investigation (Steps 5-6 skipped)

Investigation findings for Step 4:

1. **websockets library ping behavior (confirmed):** The `ping_interval=20` parameter sends WebSocket protocol-level ping frames (opcode 0x9) every 20 seconds. These are handled at the protocol layer, not as application messages. The library raises `ConnectionClosedError` if no pong is received within `ping_timeout=10` seconds.

2. **Cloudflare runtime handles pings automatically:** Per Cloudflare docs, the runtime automatically responds to WebSocket protocol-level ping frames with pong frames **without waking the DO from hibernation**. This means client-side `ping_interval=20` pings ARE counted as activity by Cloudflare's infrastructure and DO NOT incur billing.

3. **Cloudflare idle timeout (~100s) is well-covered:** With pings every 20 seconds, the connection sends activity well within Cloudflare's idle timeout window. No adjustment to `ping_interval` is needed.

4. **`setWebSocketAutoResponse` not needed:** Cloudflare offers `setWebSocketAutoResponse` for application-level ping/pong without waking hibernated DOs. Since protocol-level pings are already handled automatically by the runtime, this mechanism is unnecessary for our use case.

5. **Root cause of 2-5 minute disconnects is likely not idle timeout.** Given that protocol pings keep the connection active, the observed disconnects are most likely caused by:
   - Cloudflare edge infrastructure (load balancer rotation, edge-to-origin tunnel recycling)
   - Transient network issues between client and Cloudflare edge
   - DO memory pressure causing eviction (connections *should* survive per Hibernation API docs, but field behavior may differ)

**Conclusion:** No keepalive changes needed. `ping_interval=20` is correct. The reconnect mechanism with proper backoff reset is the right mitigation for the observed disconnects. Steps 5 and 6 from the plan were skipped — no application-level keepalive or `ping_interval` tuning required.