---
status: FUTURE
ticket: null
parent_chunk: watch_idle_reconnect_budget
code_paths: []
code_references: []
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["list_task_aware", "narrative_cli_commands", "wiki_diff_baseline_ref", "intent_complete_verification", "intent_create_gate", "intent_workflow_docs"]
---

# Chunk Goal

## Minor Goal

`ve board watch` survives indefinitely on a real-world channel that mixes
long idle periods with occasional transient WebSocket disconnects.

The previous chunk `watch_idle_reconnect_budget` separated idle re-registration
timeouts from the reconnect failure budget — idle reconnects no longer count
toward the 10-attempt ceiling. That fix is correct and remains in place.

The remaining bug: the `attempt` counter for *real* network failures
(`_RETRYABLE_ERRORS` branch in `BoardClient.watch_with_reconnect` and
`watch_multi_with_reconnect`) is **never reset** after a successful reconnect.
It only initializes to 0 at watch start. So every transient WebSocket close
across the entire watch lifetime accumulates against the same 10-attempt
ceiling. After ~10 unrelated transient drops — typically 24-48 hours of
real-world idle uptime — the watch exits with code 3 even though the
network and the channel are healthy.

### Reported pattern

The world-model steward filed a follow-up after the original fix shipped.
Three deaths in three days from a long-lived watch:

- 2026-04-24 ~19:50 (original filing — fixed by parent chunk)
- 2026-04-26 ~22:00 (~36 hr after restart — this bug)
- 2026-04-27 ~midday (~24 hr after restart — this bug)

The vibe-engineer steward's own watch in this session shows the same
shape: 5 transient `WebSocket disconnected, reconnecting (attempt N)`
events accumulated over the watch's lifetime, with `attempt` monotonically
increasing toward the ceiling. Each reconnect succeeded. Each one still
counts.

### Required fix

Reset `attempt = 0` after a successful reconnect + re-subscribe. The reset
belongs at the same place where `backoff = 1.0` is already reset (after the
`Re-subscribing to channel=...` log line in
`BoardClient.watch_with_reconnect`, and the analogous spot in
`watch_multi_with_reconnect`). A successful reconnect demonstrates the
network is healthy — the prior failures are no longer evidence of an
ongoing fault.

The 10-attempt ceiling remains the safety valve for genuinely broken
networks: 10 *consecutive* failures without an intervening success will
still exit the watch loudly. What changes is that 10 *unrelated*
transients across days of healthy uptime no longer compound.

### Code location

- `src/board/client.py#BoardClient::watch_with_reconnect` — single-channel
  watch reconnect loop. The `attempt += 1` happens at the top of the
  `_RETRYABLE_ERRORS` branch; reset belongs after the
  re-subscribe / `backoff = 1.0` reset.
- `src/board/client.py#BoardClient::watch_multi_with_reconnect` — same
  pattern for the multi-channel variant.

## Success Criteria

- A watch that experiences 10+ transient WebSocket disconnects across
  multiple days of uptime, each followed by a successful reconnect, does
  not exit with code 3.
- A watch that experiences 10 consecutive reconnect failures (no successful
  reconnect in between) still exits with code 3 — the safety valve is
  preserved.
- Existing reconnect-exhaustion tests continue to pass.
- A new test covers the "intermittent transients should not accumulate"
  case: trigger N+1 transient disconnects with successful reconnects in
  between, assert the watch is still alive.
- Idle-reconnect behavior from `watch_idle_reconnect_budget` is unchanged.

## Relationship to Parent

Parent `watch_idle_reconnect_budget` introduced the separation between
idle re-registration timeouts and real network failures by routing
`StaleWatchError` through a budget-exempt branch. That work remains
correct.

This chunk extends the budget accounting one step further: after a
successful reconnect demonstrates network health, the failure counter
should reset, treating subsequent failures as a fresh fault sequence.
Without this, the failure budget is effectively a *lifetime* budget rather
than a *consecutive-failure* budget — which is the wrong semantics for a
long-lived monitoring primitive.

The parent chunk's `idle_reconnects = 0` reset on message delivery is a
similar pattern; this chunk extends the same "reset on demonstrated
health" principle to the network-failure counter.
