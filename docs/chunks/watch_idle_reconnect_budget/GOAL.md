---
status: ACTIVE
ticket: null
parent_chunk: board_watch_reconnect_fix
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
- ref: src/board/client.py#StaleWatchError
  implements: "Idle timeout sentinel exception — distinguishes idle re-registration timeouts from genuine network failures"
- ref: src/board/client.py#BoardClient::watch_with_reconnect
  implements: "Single-channel watch with StaleWatchError branch that bypasses the reconnect budget on idle timeouts; adaptive stale_timeout backoff after 3 idle reconnects"
- ref: src/board/client.py#BoardClient::watch_multi
  implements: "Raises StaleWatchError (not ConnectionError) on stale timeout, enabling budget-exempt idle reconnect in the wrapper"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "Multi-channel watch with StaleWatchError branch exempt from the reconnect budget; idle_reconnects and current_stale_timeout tracking; reset on message delivery"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- shutdown_tz_normalization
---
# Chunk Goal

## Minor Goal

Prevent `ve board watch` from exhausting its reconnection budget on idle
channels. Currently, idle channels with no messages trigger a deterministic
failure cycle: re-register every 300s, force reconnect every 2 re-registers,
exhaust the 10-attempt budget in ~90 minutes, then terminate. Every steward
must restart the watch every ~1 hour of idle — a constant background tax.

### The problem

The watch client's reconnect logic conflates two distinct conditions:
1. **Transient network failure** — the WebSocket connection actually dropped
   and needs a fresh connection (should count against the reconnect budget)
2. **Idle heartbeat timeout** — the channel has no messages, the re-register
   probe gets no new data, and the client treats this as "stale" (should NOT
   count against the reconnect budget)

Both paths increment the same reconnect counter. After 10 attempts of either
kind, the watch terminates with "reconnect exhaustion."

### The fix (option 2 from reporter, preferred)

Don't count idle re-registrations against the 10-attempt reconnect budget.
Specifically, in `src/board/client.py`'s `watch_with_reconnect` method:

1. **Separate the reconnect counter from the idle-reconnect counter.** When
   the reconnect is triggered by a stale re-registration (the "Watch stale
   after 2 re-registrations" path), use a separate counter or reset the main
   counter — this is expected behavior on idle channels, not a failure.
2. **Reset the reconnect counter on successful message delivery.** If a
   message is eventually received, the connection is healthy — reset.
3. **Optionally**: after N idle reconnects, increase the re-register interval
   (e.g., from 300s to 600s) to reduce unnecessary reconnect churn on very
   idle channels.

### Cross-project context

Reported by the world-model steward. Affects every steward in the swarm —
the vibe-engineer steward in this session has restarted the watch dozens of
times due to this bug.

## Success Criteria

- Watch survives indefinitely on an idle channel (no messages for hours)
  without exhausting the reconnect budget
- Transient network failures still count against the reconnect budget and
  eventually terminate (safety valve preserved)
- Counter resets on successful message delivery
- Existing reconnect tests pass; new test covers the idle-reconnect path

## Relationship to Parent

Parent `board_watch_reconnect_fix` added the reconnect-with-retry logic and
the 10-attempt budget. This chunk refines the budget accounting to
distinguish idle timeouts from real failures.

## Relationship to Parent

<!--
DELETE THIS SECTION if parent_chunk is null.

If this chunk modifies work from a previous chunk, explain:
- What deficiency or change prompted this work?
- What from the parent chunk remains valid?
- What is being changed and why?

This context helps agents understand the delta and avoid breaking
invariants established by the parent.
-->

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->