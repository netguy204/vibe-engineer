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

The watcher wake-up mechanism in `SwarmDO` survives Durable Object hibernation: blocked `watch` requests still receive messages after the DO hibernates between the watch and send calls.

The in-memory `watchers` Map in `swarm-do.ts` is lost when the DO hibernates, but the Hibernation API preserves the underlying WebSocket connections. To bridge that gap, watcher state is mirrored into per-WebSocket attachments via `ws.serializeAttachment()`: the channel and cursor are stored on the attachment when a watch frame arrives, alongside the existing auth state. In `wakeWatchers`, after attempting in-memory delivery the DO falls back to scanning `this.ctx.getWebSockets()` and reconstructing watchers from those attachments, so a sender's wake call reaches the live socket even when the in-memory Map is empty. On WebSocket close or error, `removeWatcher` clears the attachment's watch state alongside the in-memory state.

This makes the steward watch loop (`ve board watch`) reliably receive messages even when the DO hibernates between the watch and send calls.

## Success Criteria

- A watcher that blocks before a message exists receives the message after the DO hibernates and wakes
- The existing e2e test "concurrent connections: watcher receives message from sender" continues to pass
- A new e2e test covers the hibernation gap: watcher blocks → DO hibernates → sender sends → watcher receives
- `wakeWatchers` reconstructs watcher state from WebSocket tags/attachments when the in-memory Map is empty
- No regression in non-hibernation path (direct watcher wake-up still works without extra storage reads)