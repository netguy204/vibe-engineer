---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
  - ref: src/board/client.py
    implements: "_RETRYABLE_ERRORS tuple extended with asyncio.TimeoutError for Python < 3.11 compatibility — ensures opening-handshake timeouts are caught by the retryable-error tuple on all supported Python versions"
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "Opening-handshake timeout retry loop inside the StaleWatchError handler — handshake timeout increments attempt, backs off, and retries rather than propagating"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Same opening-handshake timeout retry loop in watch_multi_with_reconnect's StaleWatchError handler"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_idle_handshake_timeout_retries
    implements: "Verifies watch_with_reconnect recovers from a handshake timeout on idle reconnect and delivers messages"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_idle_handshake_timeout_retries
    implements: "Verifies watch_multi_with_reconnect recovers from a handshake timeout on idle reconnect"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_idle_handshake_timeout_exhausts_budget
    implements: "Verifies the 10-consecutive-failure safety valve still applies to watch_with_reconnect after repeated handshake timeouts"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_idle_handshake_timeout_exhausts_budget
    implements: "Verifies the safety valve still applies to watch_multi_with_reconnect after repeated handshake timeouts"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- entity_migration_retry
---

# Chunk Goal

## Minor Goal

`ve board watch` tolerates a WebSocket opening-handshake timeout during an
idle or stale-driven reconnect, treating it as a transient connection error
rather than a fatal condition. The handshake timeout routes through the same
retry-with-backoff path that already recovers from `ConnectionClosedError`,
so a long-lived watch survives indefinitely across multi-day idle periods.

`BoardClient.watch_with_reconnect` and `watch_multi_with_reconnect` catch the
`websockets` opening-handshake timeout (`TimeoutError` /
`asyncio.TimeoutError` raised while establishing the connection) inside the
retryable-error branch. The handshake timeout increments the consecutive
`attempt` counter, backs off, and reconnects — exactly like other retryable
errors — instead of propagating as an unhandled exception that exits the
process with code 3. The 10-consecutive-failure safety valve from
`watch_reconnect_counter_reset` remains the boundary for a genuinely broken
network: a handshake that times out repeatedly with no successful reconnect
in between still exits with code 3.

### Reported pattern

The world-model steward reproduced this twice in two days on the
`world-model-steward` channel. The idle-reconnect-budget fixes
(`watch_idle_reconnect_budget`, `watch_reconnect_counter_reset`) are confirmed
live and working — idle reconnects no longer exhaust the failure budget, and
watches survive ~26–31 hours instead of ~100 minutes. After many successful
idle reconnects (75 and 153 respectively), a single reconnect's WebSocket
*opening handshake* timed out and the process exited 3:

    Error: watch terminated after reconnect exhaustion: timed out during
    opening handshake

The opening-handshake timeout is the same class of transient network blip that
other retryable errors represent. It now routes through the same retry-with-backoff
path rather than propagating as fatal.

### Former repro path (from logs, now fixed)

1. Idle channel, watch runs many hours.
2. Stale-reconnect cycle fires every ~20 min ("Watch stale after 2
   re-registrations, forcing reconnect" → "Idle reconnect #N").
3. After ~26–31h uptime, a forced reconnect's `websockets` handshake hits its
   open-timeout.
4. The exception propagated uncaught; the watch exited 3.

## Success Criteria

- A watch whose reconnect attempt raises an opening-handshake timeout
  (`TimeoutError` / `asyncio.TimeoutError`) recovers via backoff-and-retry
  rather than exiting with code 3, in both `watch_with_reconnect` and
  `watch_multi_with_reconnect`.
- A successful reconnect after a handshake timeout resets the consecutive
  `attempt` counter (consistent with `watch_reconnect_counter_reset`).
- The safety valve is preserved: 10 consecutive handshake timeouts with no
  intervening successful reconnect still exit with code 3.
- A new test triggers an opening-handshake timeout on reconnect and asserts
  the watch survives and continues delivering messages afterward.
- Existing reconnect, stale-reconnect, and counter-reset tests continue to
  pass.

## Relationship to Related Chunks

This is a new failure mode in the shared reconnect loop, not a correction to
prior work, so `parent_chunk` is null. It extends the set of errors treated as
retryable in `watch_with_reconnect` / `watch_multi_with_reconnect`:

- `board_watch_stale_reconnect` introduced stale detection and the
  re-registration / full-reconnect escalation.
- `watch_idle_reconnect_budget` separated idle re-registration timeouts from
  the failure budget.
- `watch_reconnect_counter_reset` reset the failure counter after a
  demonstrated-healthy reconnect, making the budget a consecutive-failure
  budget.

All three remain correct. This chunk closes the remaining gap: the handshake
timeout itself, which previously bypassed the retryable-error branch and
terminated the watch.