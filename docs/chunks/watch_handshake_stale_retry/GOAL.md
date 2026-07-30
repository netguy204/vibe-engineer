---
status: ACTIVE
ticket: null
parent_chunk: watch_handshake_timeout_retry
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
  - ref: src/board/client.py#BoardClient::_connect_with_retry
    implements: "Shared connect-with-retry helper — both stale-driven and spontaneous
      reconnect paths call this, ensuring identical retry semantics"
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "StaleWatchError handler now delegates to _connect_with_retry;
      opening-handshake TimeoutError on stale-driven reconnect retried, not fatal"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Same _connect_with_retry delegation in watch_multi_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_stale_handshake_timeout_after_prior_cycles
    implements: "Multi-cycle stale scenario: handshake timeout on reconnect #4+
      survives in watch_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_stale_handshake_timeout_after_prior_cycles
    implements: "Same for watch_multi_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles
    implements: "Safety valve still fires after max_retries consecutive stale-path
      handshake failures in watch_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles
    implements: "Same for watch_multi_with_reconnect"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- plugin_hook_cli_bootstrap
---
# Chunk Goal

## Minor Goal

The handshake-timeout-as-transient semantic established by
`watch_handshake_timeout_retry` extends to **both** reconnect branches in
`BoardClient.watch_with_reconnect` and `watch_multi_with_reconnect`. A
WebSocket opening-handshake `TimeoutError` raised on the stale-driven
forced-reconnect path (the `StaleWatchError` branch) is caught and routed
through the same retry-with-backoff loop that recovers from spontaneous
disconnects on the `_RETRYABLE_ERRORS` branch, so a long-lived watch
survives stale-driven handshake blips just as it survives
disconnect-driven ones.

The single source of truth for "this exception is transient" applies
symmetrically: whether the reconnect was initiated by a
`ConnectionClosedError` (spontaneous) or a `StaleWatchError`
(stale-driven), a handshake `TimeoutError` increments the consecutive
`attempt` counter, backs off, and retries. The 10-consecutive-failure
safety valve still applies to both branches.

### Reported pattern (correction to seq 74)

The world-model steward initially confirmed `watch_handshake_timeout_retry`
closed the issue (seq 74), then retracted (seq 75): the same fatal exit
fired again 10 minutes later from the stale-driven path:

    Watch re-registering: no message in 600s, channel=world-model-steward
    Watch stale after 2 re-registrations, forcing reconnect
    Idle reconnect #4, increasing stale_timeout to 600s
    Error: watch terminated after reconnect exhaustion: timed out during
    opening handshake

Meanwhile the spontaneous-disconnect branch handles the same
`TimeoutError` cleanly:

    WebSocket disconnected, reconnecting in 1.2s (attempt 1) exc=ConnectionClosedError
    Handshake failed during reconnect in 3.0s (attempt 2) exc=TimeoutError
    Reconnected, re-polling channel=world-model-steward from cursor=13

The two reconnect paths share the same underlying WebSocket open, and the
`_connect_with_retry` helper now ensures identical retry semantics on both —
stale-driven and spontaneous-disconnect alike.

## Success Criteria

- A watch whose `StaleWatchError`-driven forced reconnect raises an
  opening-handshake `TimeoutError` / `asyncio.TimeoutError` recovers via
  backoff-and-retry rather than exiting with code 3, in both
  `watch_with_reconnect` and `watch_multi_with_reconnect`.
- The safety valve is preserved: 10 consecutive handshake timeouts on the
  stale-driven path with no intervening successful reconnect still exit
  with code 3 (matching the safety valve behavior on the spontaneous
  branch).
- A new test triggers an opening-handshake timeout specifically on the
  stale-driven forced-reconnect path and asserts the watch survives and
  continues delivering messages afterward, for both single-channel and
  multi-channel variants.
- All existing reconnect, stale-reconnect, counter-reset, and
  Branch-1-handshake-timeout tests continue to pass.

## Relationship to Parent

Parent `watch_handshake_timeout_retry` established the
handshake-timeout-as-transient semantic in
`BoardClient.watch_with_reconnect` and `watch_multi_with_reconnect`. Its
intent — "ve board watch tolerates a WebSocket opening-handshake timeout
during an idle or stale-driven reconnect" — covers both branches. The
stale-driven forced-reconnect path now routes through the shared
`_connect_with_retry` helper alongside the spontaneous-disconnect branch,
so the parent's intent fully governs the code. The parent's
`code_references` for both methods reflect this unified coverage via
`_connect_with_retry`.