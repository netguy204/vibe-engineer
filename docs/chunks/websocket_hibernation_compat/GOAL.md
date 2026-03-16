---
status: ACTIVE
ticket: null
parent_chunk: websocket_keepalive
code_paths:
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/protocol.ts
- src/leader_board/server.py
- src/leader_board/protocol.py
- src/board/client.py
- tests/test_board_client.py
code_references:
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::alarm
  implements: "Compaction-only alarm — heartbeat removed so DO can hibernate"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::ensureAlarm
  implements: "Schedule compaction alarm if none exists (no heartbeat interval)"
- ref: workers/leader-board/src/protocol.ts#ServerFrame
  implements: "PingFrame removed from server frame union"
- ref: src/leader_board/protocol.py
  implements: "PingFrame removed from Python server frame union and serialization"
- ref: src/leader_board/server.py#websocket_handler
  implements: "Heartbeat task and loop removed from local server"
- ref: src/board/client.py#BoardClient::send
  implements: "Direct recv() instead of ping-filtering _recv_data_frame()"
- ref: src/board/client.py#BoardClient::watch
  implements: "Direct recv() instead of ping-filtering _recv_data_frame()"
- ref: src/board/client.py#BoardClient::list_channels
  implements: "Direct recv() instead of ping-filtering _recv_data_frame()"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- websocket_keepalive
---

# Chunk Goal

## Minor Goal

Remove the alarm-based server-side heartbeat from the DO worker and rely on the Cloudflare runtime's built-in WebSocket ping/pong instead. Per [Cloudflare's DO WebSocket best practices](https://developers.cloudflare.com/durable-objects/best-practices/websockets/):

- **Alarms prevent hibernation**: "Events such as alarms, incoming requests, and scheduled callbacks prevent hibernation." The `ensureHeartbeatAlarm()` added by `websocket_keepalive` keeps the DO awake continuously, defeating the Hibernation API that's already in use (`ctx.acceptWebSocket()`).
- **Ping/pong is automatic**: "Incoming ping frames receive automatic pong responses" and "Ping/pong handling does not interrupt hibernation." The runtime handles keepalive at the protocol level without waking the DO.
- **Cost impact**: "Billable Duration (GB-s) charges do not accrue during hibernation." With alarm-based heartbeats, the DO never hibernates, meaning continuous GB-s charges for every idle connection.

Changes needed:
1. **Remove `ensureHeartbeatAlarm()`** and the heartbeat logic from `alarm()` in `swarm-do.ts`
2. **Remove application-level PingFrame** from `protocol.ts` — use WebSocket-level pings instead
3. **Keep client-side reconnect logic** from `websocket_keepalive` (that part is correct and valuable)
4. **Keep client-side `ping_interval`/`ping_timeout`** on the `websockets` connection — the client sends protocol-level pings that the runtime auto-responds to without waking the DO
5. **Remove `_recv_data_frame` ping filtering** in `client.py` since there won't be application-level ping frames

The compaction alarm scheduling in `alarm()` should remain — it only runs when there's actual work (compaction), not on a heartbeat timer.

## Success Criteria

- No alarm is scheduled solely for heartbeat purposes (alarm only for compaction)
- DO hibernates during idle periods (verify by checking no alarm reschedule on WebSocket connect)
- WebSocket connections still survive idle periods (Cloudflare runtime handles pings)
- Client-side reconnect logic remains functional as a safety net
- Existing tests pass (update tests that rely on application-level PingFrame)

## Relationship to Parent

Parent chunk `websocket_keepalive` added both server-side alarm heartbeats and client-side reconnect. The server-side heartbeats conflict with the existing Hibernation API usage, preventing cost-efficient idle behavior. This chunk removes the server-side heartbeat while preserving the valuable client-side reconnect.