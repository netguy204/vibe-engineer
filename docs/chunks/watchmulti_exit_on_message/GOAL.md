---
status: ACTIVE
ticket: null
parent_chunk: multichannel_watch
code_paths:
- src/board/client.py
- src/cli/board.py
- src/templates/commands/swarm-monitor.md.jinja2
- tests/test_board_client.py
- tests/test_board_cli.py
code_references:
- ref: src/board/client.py#BoardClient::watch_multi
  implements: "Count-limited message delivery in multi-channel watch generator"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "Count tracking across reconnects for total message cap"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "--count CLI flag wired through to client methods"
- ref: src/templates/commands/swarm-monitor.md.jinja2
  implements: "Event-driven loop pattern using --count 1 with run_in_background"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- multichannel_watch
---

# Chunk Goal

## Minor Goal

Add a `--count N` flag (default 1) to `ve board watch-multi` so it exits after receiving N messages. This makes `watch-multi` compatible with the event-driven `run_in_background` pattern that agents use: launch watch, get task completion notification on message, process, ack, re-launch.

Currently `watch-multi` streams continuously and never exits, so agents using `run_in_background` never get notified. The only workaround is polling the output file or falling back to N single watches (losing the single-connection benefit).

Changes:
- **CLI**: Add `--count N` flag to `ve board watch-multi` (default 1). With `--count 1`, print one message (with channel tag) and exit. With `--count 0`, stream indefinitely (current behavior).
- **Client**: `watch_multi` (or a new `watch_multi_one`) method that subscribes to all channels but returns after the first message instead of yielding continuously.
- **Swarm-monitor skill**: Update to use `watch-multi --count 1` in `run_in_background`, preserving the event-driven loop.

## Success Criteria

- `ve board watch-multi ch1 ch2 --count 1` blocks until any channel has a message, prints it with channel tag, and exits
- `ve board watch-multi ch1 ch2 --count 0` streams indefinitely (backwards compatible)
- Swarm-monitor skill works with `run_in_background` using `--count 1`
- Existing single-channel `ve board watch` unchanged

## Relationship to Parent

Parent chunk `multichannel_watch` implemented continuous streaming. This chunk adds the exit-after-N-messages mode needed for agent event-driven workflows, which is how all current steward and monitor skills operate.