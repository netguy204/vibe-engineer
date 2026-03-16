---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- src/leader_board/server.py
- src/leader_board/protocol.py
- src/cli/board.py
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/protocol.ts
- tests/test_board_client.py
- tests/test_leader_board_e2e.py
code_references:
- ref: src/board/client.py#BoardClient::_recv_data_frame
  implements: "Filter out server-side ping keepalive frames from data flow"
- ref: src/board/client.py#BoardClient::watch_with_reconnect
  implements: "Automatic reconnect with exponential backoff on WebSocket disconnect"
- ref: src/board/client.py#BoardClient::connect
  implements: "Configure client-side ping_interval/ping_timeout for dead connection detection"
- ref: src/leader_board/server.py#_heartbeat_loop
  implements: "Server-side periodic ping frame sending to prevent idle timeout"
- ref: src/leader_board/server.py#websocket_handler
  implements: "Spawns heartbeat task after auth, cancels on disconnect"
- ref: src/leader_board/protocol.py#PingFrame
  implements: "Wire protocol ping frame dataclass for keepalive"
- ref: src/cli/board.py#watch_cmd
  implements: "CLI watch command uses reconnect by default with --no-reconnect opt-out"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::alarm
  implements: "DO alarm sends pings to all connected WebSockets and conditionally runs compaction"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::ensureHeartbeatAlarm
  implements: "Reschedule alarm to heartbeat interval when WebSockets are connected"
- ref: workers/leader-board/src/protocol.ts#PingFrame
  implements: "TypeScript wire protocol ping frame interface"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- steward_deploy_step
---

# Chunk Goal

## Minor Goal

Fix frequent WebSocket disconnects on `ve board watch`. The connection drops after ~2-5 minutes of idle time with `websockets.exceptions.ConnectionClosedError: no close frame received or sent`. This affects all steward watch loops, requiring constant manual restarts.

The fix needs two sides:

1. **Server-side (DO worker)**: The Cloudflare Durable Object WebSocket likely gets evicted or the connection is dropped by Cloudflare's proxy after an idle timeout. The DO should send periodic WebSocket ping frames to keep the connection alive. Cloudflare's DO WebSocket API supports `webSocket.send()` for pings — the DO needs a `setInterval` or alarm-based heartbeat (e.g., every 30 seconds).

2. **Client-side (Python `ve board watch`)**: The `src/board/client.py` `watch()` method should add automatic reconnect logic so that transient disconnects don't crash the command. On disconnect, it should reconnect and re-subscribe from the current cursor position. The `websockets` library supports `ping_interval`/`ping_timeout` parameters that should also be configured.

## Success Criteria

- `ve board watch` maintains a connection for 10+ minutes without dropping
- If the connection does drop, the client automatically reconnects and resumes from the cursor
- Server sends periodic ping/heartbeat frames to prevent idle timeout
- No messages are lost during reconnect (cursor-based recovery)