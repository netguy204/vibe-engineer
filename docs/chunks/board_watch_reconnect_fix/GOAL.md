---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- src/cli/board.py
- tests/test_board_client.py
- tests/test_board_cli.py
code_references:
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "Default max_retries=10 and re-subscription log after reconnect"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Default max_retries=10 and re-subscription log after reconnect for multi-channel watch"
  - ref: src/cli/board.py#watch_cmd
    implements: "--max-reconnects CLI flag and exit code 3 on reconnect exhaustion"
  - ref: src/cli/board.py#watch_multi_cmd
    implements: "--max-reconnects CLI flag and exit code 3 on reconnect exhaustion for multi-channel watch"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orchestrator_skill_path_fix
---
# Chunk Goal

## Minor Goal

Fix `ve board watch` to fail loudly instead of silently dying during long-lived
reconnect loops. After 4-5 hours of idle monitoring with repeated
`no message in 300s` re-registrations and reconnects, the watch can enter a
state where it appears connected but stops delivering messages. This is the
worst failure mode for a monitoring primitive — the operator assumes "no
messages" when the reality is "watch is broken."

### Reported behavior

- Watch runs on a low-traffic channel (30+ min gaps between messages)
- After multiple `Watch stale after 2 re-registrations, forcing reconnect`
  cycles (5+ reconnect attempts), the watch silently stops delivering
- No error output, no exit — the process hangs looking alive
- Observed on macOS Darwin 25.2.0 after ~4-5 hours of runtime

### Required fixes

1. **Fail loud on reconnect exhaustion** — After N consecutive failed
   re-registrations (configurable, default ~10), exit nonzero with a clear
   error message instead of silently hanging. This lets wrapping processes
   (steward watch loops, cron monitors) detect and respawn.

2. **Bound the reconnect attempt counter** — The current unbounded counter
   reaches 400+ attempts. After hitting the max, exit with a descriptive
   error code so callers can distinguish "no messages" (exit 0) from
   "watch died" (exit nonzero).

3. **Verify server subscription persists across reconnect** — Investigate
   whether the reconnect path correctly re-POSTs the subscribe request to
   the server, or whether a reconnect can succeed at the WebSocket level
   while losing the channel subscription. If subscriptions are lost on
   reconnect, re-subscribe after each successful reconnect.

### Code location

The watch reconnect logic is in `src/board/client.py`. Look for the
re-registration, stale detection, and reconnect paths.

## Success Criteria

- `ve board watch` exits nonzero after N consecutive failed reconnects
- Exit message clearly indicates reconnect exhaustion (not silent hang)
- Server subscription is verified/restored after each successful reconnect
- The `--max-reconnects` flag (or equivalent) is configurable
- Existing tests pass; new test for reconnect exhaustion behavior
- Long-running watches that successfully reconnect continue working