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

The DO worker leaves WebSocket keepalive to the Cloudflare runtime's built-in ping/pong rather than running an application-level heartbeat. Per [Cloudflare's DO WebSocket best practices](https://developers.cloudflare.com/durable-objects/best-practices/websockets/):

- **Alarms prevent hibernation**: "Events such as alarms, incoming requests, and scheduled callbacks prevent hibernation." A heartbeat alarm would keep the DO awake continuously, defeating the Hibernation API in use via `ctx.acceptWebSocket()`.
- **Ping/pong is automatic**: "Incoming ping frames receive automatic pong responses" and "Ping/pong handling does not interrupt hibernation." The runtime handles keepalive at the protocol level without waking the DO.
- **Cost impact**: "Billable Duration (GB-s) charges do not accrue during hibernation." Without alarm-based heartbeats, the DO hibernates between events and only accrues GB-s when there is real work to do.

The arrangement that delivers this:

1. `SwarmDO::alarm` only runs storage compaction and re-schedules itself on the compaction interval — there is no heartbeat path.
2. `SwarmDO::ensureAlarm` schedules a compaction alarm only when none exists; no heartbeat-only schedule is created.
3. `protocol.ts` and `protocol.py` define `ServerFrame` without a `PingFrame` variant — application-level pings are no longer part of the wire protocol.
4. `src/leader_board/server.py#websocket_handler` runs without a heartbeat task or loop; the local server relies on the same protocol-level ping/pong.
5. `BoardClient` sets `ping_interval=20` / `ping_timeout=30` on its `websockets` connection so the client emits protocol-level pings the runtime auto-responds to without waking the DO.
6. `BoardClient::send`, `BoardClient::watch`, and `BoardClient::list_channels` call `recv()` directly rather than a ping-filtering wrapper, since no application-level ping frames remain to filter.
7. Client-side reconnect logic from `websocket_keepalive` remains as a safety net.

## Success Criteria

- No alarm is scheduled solely for heartbeat purposes (alarm only for compaction)
- DO hibernates during idle periods (verify by checking no alarm reschedule on WebSocket connect)
- WebSocket connections still survive idle periods (Cloudflare runtime handles pings)
- Client-side reconnect logic remains functional as a safety net
- Existing tests pass (update tests that rely on application-level PingFrame)

## Relationship to Parent

Parent chunk `websocket_keepalive` introduced both server-side alarm heartbeats and client-side reconnect. The server-side heartbeats conflicted with the Hibernation API and prevented cost-efficient idle behavior. This chunk owns the present arrangement: the server-side heartbeat is gone, the client-side reconnect remains.