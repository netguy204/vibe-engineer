---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- src/cli/board.py
- src/leader_board/server.py
- src/templates/commands/swarm-monitor.md.jinja2
- workers/leader-board/src/swarm-do.ts
- tests/test_board_client.py
- tests/test_board_cli.py
- tests/test_leader_board_server.py
- workers/leader-board/test/e2e.test.ts
code_references:
- ref: src/board/client.py#BoardClient::watch_multi
  implements: "Multi-channel watch async generator - sends watch frames for all channels and yields messages as they arrive"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "Reconnect wrapper for watch_multi with cursor tracking across reconnects"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "CLI command 've board watch-multi' accepting multiple channels with tagged output"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleWatch
  implements: "Updated to store per-channel watch entries in attachment array for hibernation"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::wakeWatchers
  implements: "Updated to iterate multi-channel watch array and remove only delivered channel entries"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::removeWatcher
  implements: "Updated to clear all channel watches on disconnect"
- ref: src/templates/commands/swarm-monitor.md.jinja2
  implements: "Updated swarm-monitor to use single watch-multi connection instead of N separate watches"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- websocket_reconnect_tuning
---

# Chunk Goal

## Minor Goal

A single WebSocket connection can subscribe to multiple channels and wake when any of them receives a message. Without multi-channel watch support, monitoring N channels would require N concurrent WebSocket connections (one per channel), which does not scale as swarms grow.

Three pieces support this capability:

1. **Protocol**: The wire protocol supports subscribing to multiple channels on a single connection. The server accepts a list of channels (with per-channel cursors) in the watch frame, and delivers messages tagged with which channel they came from. This spans both the Python local server (`src/leader_board/`) and the Cloudflare DO worker.

2. **CLI command**: `ve board watch-multi <channel1> <channel2> ...` accepts multiple channels and tags each message with its source channel, e.g., `[vibe-engineer-changelog] message text`.

3. **`/swarm-monitor` skill**: The `swarm-monitor` skill uses the multi-channel watch in place of one background watch per changelog channel, collapsing N connections to 1.

Design consideration: since each channel lives on a different Durable Object (keyed by swarm), the multi-channel subscription is implemented at the worker entry point level (fan-out to multiple DOs) rather than within a single DO.

## Success Criteria

- `ve board watch-multi ch1 ch2 ch3` blocks on a single connection and returns messages from any subscribed channel
- Output includes channel name for each message
- `/swarm-monitor` updated to use multi-channel watch
- One connection serves N channels (not N connections)
- Existing single-channel `ve board watch` continues to work unchanged