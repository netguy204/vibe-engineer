---
decision: APPROVE
summary: "All four success criteria satisfied: defense-in-depth fix on both client (stale timeout + re-registration) and server (watcher dedup, wakeWatchers fall-through), with thorough multi-cycle tests including 10+ reconnection and mixed stale/normal scenarios."
operator_review: null  # DO NOT SET - reserved for operator curation
---

## Criteria Assessment

### Criterion 1: Watch continues to deliver messages reliably after 10+ reconnection cycles over 24+ hours

- **Status**: satisfied
- **Evidence**: `test_watch_with_reconnect_10_cycles` simulates 12 reconnection cycles and asserts all 12 messages are delivered with correct positions. `test_watch_with_reconnect_multi_cycle_with_stale` exercises 10 cycles alternating normal, stale-reregister, and double-stale-reconnect patterns — all deliver successfully. The 24+ hour duration is addressed by the stale_timeout mechanism (default 300s) that detects and recovers from silently broken connections rather than hanging indefinitely.

### Criterion 2: Root cause identified and documented (server-side, client-side, or protocol-level)

- **Status**: satisfied
- **Evidence**: PLAN.md documents two complementary root causes: (1) server-side stale watcher accumulation in `handleWatch` where the Set's object identity creates duplicates on re-registration, and `wakeWatchers` early-returning after the in-memory path even when all sends failed; (2) client-side silent stall where `recv()` blocks indefinitely because WebSocket protocol pings succeed (Cloudflare edge) while application data doesn't flow. Both are addressed with specific fixes.

### Criterion 3: Fix addresses the specific delivery failure mechanism, not just a workaround

- **Status**: satisfied
- **Evidence**: Server-side: `handleWatch` now deduplicates watcher entries by WebSocket identity before adding (swarm-do.ts ~line 930-936). `wakeWatchers` now tracks a `delivered` flag and only returns early if at least one in-memory send succeeded, falling through to hibernation recovery otherwise (swarm-do.ts ~line 1051, 1078). Client-side: `watch_with_reconnect` wraps `recv()` with `asyncio.wait_for(stale_timeout)` — first timeout re-sends the watch frame (re-registration), second consecutive timeout raises `ConnectionError` triggering full reconnect. Same pattern applied to `watch_multi`. This is defense-in-depth targeting the specific failure modes, not a workaround.

### Criterion 4: Tests simulate multiple reconnection cycles and verify message delivery after each

- **Status**: satisfied
- **Evidence**: Eight new tests in `tests/test_board_client.py`: `test_watch_with_reconnect_stale_reregisters` (single re-registration), `test_watch_with_reconnect_stale_forces_reconnect` (double timeout → full reconnect), `test_watch_with_reconnect_normal_unaffected` (no false positives), `test_watch_multi_stale_reregisters`, `test_watch_multi_stale_forces_reconnect_in_wrapper`, `test_watch_with_reconnect_10_cycles` (12 cycles), `test_watch_with_reconnect_multi_cycle_with_stale` (10 cycles with mixed patterns). All 30 tests pass.
