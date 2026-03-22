---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- workers/leader-board/src/swarm-do.ts
- tests/test_board_client.py
code_references:
- ref: src/board/client.py#BoardClient::watch_with_reconnect
  implements: "Stale connection detection via asyncio.wait_for timeout and watch frame re-registration on existing connection"
- ref: src/board/client.py#BoardClient::watch_multi
  implements: "Stale connection detection for multi-channel watch with re-registration of all active watch frames on timeout"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "Pass-through of stale_timeout parameter to watch_multi for multi-channel reconnect wrapper"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleWatch
  implements: "Deduplicate watcher entries for same WebSocket before adding new registration"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::wakeWatchers
  implements: "Track delivery success and fall through to hibernation recovery when all in-memory sends fail"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::removeWatcher
  implements: "Diagnostic logging for watcher removal lifecycle events"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orch_implement_reentry_prompt
---

# Chunk Goal

## Minor Goal

Fix `ve board watch` silently stopping message delivery after many WebSocket reconnection cycles, even though the re-poll logs show successful reconnects from the correct cursor position.

The earlier `board_watch_reconnect_delivery` fix added re-polling after reconnect — and the logs confirm re-polls are happening (`Reconnected, re-polling channel=... from cursor=N`). But after enough reconnection cycles (observed at ~8+ over ~15 hours), the watch stops delivering messages entirely. A message written to the channel is not delivered despite the watch being connected. Killing and restarting the watch immediately picks up the pending message.

This suggests either:
1. **Server-side**: The subscription state on the Durable Object becomes stale after repeated reconnects — the watch connection is registered but the push notification path is broken
2. **Client-side**: The read loop after reconnection doesn't properly resume — the re-poll fires but the subsequent blocking read fails silently
3. **Protocol-level**: The WebSocket connection appears healthy but is in a half-open state where the server can't push to it

Investigation should examine both the Python client reconnection logic (`watch_with_reconnect`) and the Durable Object's watcher registration to determine where the delivery chain breaks after repeated reconnects.

Reported by palette steward after overnight watch failure.

## Success Criteria

- Watch continues to deliver messages reliably after 10+ reconnection cycles over 24+ hours
- Root cause identified and documented (server-side, client-side, or protocol-level)
- Fix addresses the specific delivery failure mechanism, not just a workaround
- Tests simulate multiple reconnection cycles and verify message delivery after each

