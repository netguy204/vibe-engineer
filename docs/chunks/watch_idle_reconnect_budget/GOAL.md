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

`ve board watch` survives indefinitely on idle channels without exhausting
its reconnection budget. Idle channels with no messages still trigger a
re-registration cycle (every 300s, forcing a reconnect every 2
re-registrations), but those idle reconnects are accounted separately from
the 10-attempt budget that protects against genuine network failure. Without
this separation, every steward in the swarm needed to restart the watch
about once an hour of idle time — a constant background tax.

### The two reconnect conditions

The watch client distinguishes two conditions that previously shared a
single counter:

1. **Transient network failure** — the WebSocket connection actually
   dropped and needs a fresh connection. Counts against the reconnect
   budget.
2. **Idle heartbeat timeout** — the channel has no messages, the
   re-register probe gets no new data, and the client treats the
   connection as "stale". Does NOT count against the reconnect budget.

A `StaleWatchError` sentinel raised by the inner watch path lets
`watch_with_reconnect` and `watch_multi_with_reconnect` route idle
timeouts through a budget-exempt branch.

### The accounting rules

In `src/board/client.py`:

1. **Separate counters.** Stale re-registrations increment an
   `idle_reconnects` counter that is independent of the main reconnect
   budget — idle behavior is expected, not a failure.
2. **Reset on message delivery.** A successfully received message marks
   the connection as healthy and resets both counters.
3. **Adaptive backoff.** After 3 idle reconnects, the stale timeout
   doubles (capped at 600s) to reduce reconnect churn on very idle
   channels.

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

Parent `board_watch_reconnect_fix` introduced the reconnect-with-retry
logic and the 10-attempt budget. The budget accounting now distinguishes
idle timeouts from real failures, so the safety valve still terminates
on genuine connection trouble while idle channels survive indefinitely.

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