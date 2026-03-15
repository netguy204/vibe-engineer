---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/test/e2e.test.ts
code_references:
- ref: workers/leader-board/src/swarm-do.ts#WsAttachment
  implements: "Extended attachment schema with optional watching field for hibernation-surviving watch state"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleWatch
  implements: "Persists watch channel/cursor into WebSocket attachment when registering a pending watcher"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::wakeWatchers
  implements: "Hibernation recovery fallback that scans all WebSockets via getWebSockets() and reconstructs watchers from attachments"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::removeWatcher
  implements: "Clears attachment watch state alongside in-memory state on WebSocket close/error"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::_clearWatchersForTest
  implements: "Test helper to simulate hibernation memory loss by clearing in-memory watchers Map"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- leader_board_durable_objects
- leader_board_user_config
---
# Chunk Goal

## Minor Goal

Fix the watcher wake-up mechanism in `SwarmDO` so that blocked `watch` requests survive Durable Object hibernation.

The `watchers` Map (`swarm-do.ts:34`) is plain in-memory state. When the DO hibernates between the watcher's blocking `watch` call and the sender's `send` call, the watchers Map is lost. The sender's `wakeWatchers` call finds no watchers to notify, even though the watcher's WebSocket connection is still alive (the Hibernation API preserves WebSocket connections, just not JS heap state).

The fix is to use the Hibernation API's WebSocket tags and attachments to make watcher state recoverable after hibernation:
- Tag watcher WebSockets with their channel (e.g., `this.ctx.acceptWebSocket(ws, ["watch:channel_name"])`) or re-tag when a watch frame arrives
- Store the cursor in `ws.serializeAttachment()` alongside the auth state
- In `wakeWatchers`, also check `this.ctx.getWebSockets("watch:channel_name")` and reconstruct watchers from tags + attachments

This ensures the steward watch loop (`ve board watch`) reliably receives messages even when the DO hibernates between the watch and send calls.

## Success Criteria

- A watcher that blocks before a message exists receives the message after the DO hibernates and wakes
- The existing e2e test "concurrent connections: watcher receives message from sender" continues to pass
- A new e2e test covers the hibernation gap: watcher blocks → DO hibernates → sender sends → watcher receives
- `wakeWatchers` reconstructs watcher state from WebSocket tags/attachments when the in-memory Map is empty
- No regression in non-hibernation path (direct watcher wake-up still works without extra storage reads)