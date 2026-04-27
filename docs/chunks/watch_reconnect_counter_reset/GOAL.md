---
status: ACTIVE
ticket: null
parent_chunk: watch_idle_reconnect_budget
code_paths:
  - src/board/client.py
  - tests/test_board_client.py
code_references:
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "Resets attempt counter to 0 after successful reconnect so the 10-attempt ceiling applies only to consecutive failures"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Same attempt-reset logic for the multi-channel watch variant"
  - ref: tests/test_board_client.py
    implements: "Tests for intermittent transients not accumulating and consecutive-failure safety valve"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- list_task_aware
- narrative_cli_commands
- wiki_diff_baseline_ref
- intent_complete_verification
- intent_create_gate
- intent_workflow_docs
---
# Chunk Goal

## Minor Goal

`ve board watch` survives indefinitely on a real-world channel that mixes
long idle periods with occasional transient WebSocket disconnects.

The parent chunk `watch_idle_reconnect_budget` separated idle re-registration
timeouts from the reconnect failure budget — idle reconnects do not count
toward the 10-attempt ceiling.

The `attempt` counter for real network failures (`_RETRYABLE_ERRORS` branch in
`BoardClient.watch_with_reconnect` and `watch_multi_with_reconnect`) resets to
0 after each successful reconnect. A successful reconnect demonstrates the
network is healthy — prior failures are not evidence of an ongoing fault.
The 10-attempt ceiling therefore applies to *consecutive* failures only, not
to lifetime failures accumulated across days of healthy uptime.

### Reported pattern

The world-model steward observed three watch deaths in three days from a
long-lived watch:

- 2026-04-24 ~19:50 (idle re-registration timeout — fixed by parent chunk)
- 2026-04-26 ~22:00 (~36 hr after restart — transient accumulation)
- 2026-04-27 ~midday (~24 hr after restart — transient accumulation)

Each restart accumulated 10 transient `WebSocket disconnected, reconnecting
(attempt N)` events over the watch's lifetime. Each reconnect succeeded,
but the monotonically increasing counter eventually reached the ceiling.

### Behavior

`attempt` resets to 0 in both `watch_with_reconnect` and
`watch_multi_with_reconnect` immediately after `backoff = 1.0` is reset
following a successful reconnect and re-subscribe. The 10-attempt ceiling
remains the safety valve for genuinely broken networks: 10 *consecutive*
failures without an intervening successful reconnect exit the watch with
code 3.

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

After a successful reconnect demonstrates network health, the failure counter
resets, treating subsequent failures as a fresh fault sequence. The failure
budget is a *consecutive-failure* budget, not a *lifetime* budget — the
correct semantics for a long-lived monitoring primitive.

The parent chunk's `idle_reconnects = 0` reset on message delivery follows the
same "reset on demonstrated health" principle, extended here to the
network-failure counter.
