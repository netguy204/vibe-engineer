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

`ve board watch` keeps delivering messages reliably across many WebSocket reconnection cycles. The watch detects stale connections, re-registers cleanly, and falls through to hibernation recovery when in-memory delivery fails.

Client side (`BoardClient.watch_with_reconnect` / `watch_multi`):

- Each blocking read uses `asyncio.wait_for` with a `stale_timeout` (default 300s). On timeout, the client re-sends the watch frame on the existing connection to re-register, which is cheaper than a full reconnect.
- A second consecutive timeout escalates to a full reconnect via `StaleWatchError`.
- `watch_multi_with_reconnect` passes `stale_timeout` through to the multi-channel path so every active watch frame gets re-registered together on stale detection.

Server side (Durable Object `SwarmDO`):

- `handleWatch` deduplicates watcher entries for the same WebSocket. Re-sending a watch frame on the same connection replaces the existing entry instead of creating a duplicate that would split delivery state.
- `wakeWatchers` tracks whether any in-memory send actually succeeded and falls through to the hibernation recovery path when every in-memory delivery attempt fails, so a stale-but-registered watcher does not silently swallow new messages.
- `removeWatcher` logs lifecycle events for diagnostic visibility into watcher churn.

## Success Criteria

- Watch continues to deliver messages reliably after 10+ reconnection cycles over 24+ hours
- Root cause identified and documented (server-side, client-side, or protocol-level)
- Fix addresses the specific delivery failure mechanism, not just a workaround
- Tests simulate multiple reconnection cycles and verify message delivery after each

