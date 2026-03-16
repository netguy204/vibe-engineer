---
status: ACTIVE
ticket: null
parent_chunk: websocket_hibernation_compat
code_paths:
- workers/leader-board/src/swarm-do.ts
- src/board/client.py
- workers/leader-board/test/e2e.test.ts
- tests/test_board_client.py
code_references:
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::constructor
    implements: "Application-level auto-response (setWebSocketAutoResponse) and zombie socket detection (getWebSockets) on hibernation wake"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::webSocketClose
    implements: "Complete server-side close handshake to prevent zombie WebSocket accumulation"
  - ref: src/board/client.py#BoardClient::connect
    implements: "Increased close_timeout from 1s to 10s for server close handshake after hibernation wake"
  - ref: src/board/client.py#BoardClient::register_swarm
    implements: "Increased close_timeout from 1s to 10s for registration connection"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- watchmulti_exit_on_message
---

# Chunk Goal

## Minor Goal

Fix three gaps identified by comparing our DO against the [Cloudflare WebSocket Hibernation Server example](https://developers.cloudflare.com/durable-objects/examples/websocket-hibernation-server/), plus increase the client-side close timeout. Together these changes should eliminate zombie WebSocket accumulation and reduce connection drops.

### 1. Add `setWebSocketAutoResponse` in the constructor

The example sets up application-level auto-responses in the constructor:
```js
this.ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
```
This makes the DO automatically reply `"pong"` to any client sending `"ping"` **without waking from hibernation**. This is separate from WebSocket protocol-level pings. The Cloudflare edge proxy may use application-level activity to determine whether a connection is idle — without this, our connections look idle to the proxy even though protocol pings are flowing, leading to the TCP drops we've been seeing (`close_code=None`, raw EOF).

### 2. Complete the close handshake in `webSocketClose`

The example's close handler calls `ws.close(code, reason)` to complete the server-side close handshake. Our handler only calls `this.removeWatcher(ws)` and never sends the close response. This means:
- The client sends a close frame, waits for the server's close response
- Server never responds → client's `close_timeout` expires → client drops TCP
- The DO never fully closes the socket → it stays in `ctx.getWebSockets()` as a zombie
- After hibernation recovery, `getWebSockets()` returns the zombie, which gets re-added to watchers

Fix: Add `ws.close(code, reason)` in the `webSocketClose` handler after `removeWatcher`.

### 3. Run `getWebSockets()` in the constructor for cleanup

The example calls `ctx.getWebSockets()` in the constructor to restore state on wake. We only call it in `wakeWatchers`. Moving it to the constructor (or adding a constructor call) ensures zombie sockets are detected and cleaned up early — before they accumulate and cause the HTTP 500s we saw on reconnect.

### 4. Increase client-side `close_timeout` from 1s to 10s

In `src/board/client.py`, `websockets.connect()` uses `close_timeout=1`. This is too aggressive — the server needs time to wake from hibernation and process the close frame. Increase to 10s so the server can complete the close handshake properly. Also increase the `close_timeout` in the reconnect path's `self.close()` call.

## Success Criteria

- DO constructor calls `setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"))`
- `webSocketClose` handler calls `ws.close(code, reason)` after removing the watcher
- Constructor calls `ctx.getWebSockets()` to detect and log/clean zombie sockets on wake
- Client `close_timeout` increased to 10s
- Connection drop frequency decreases (target: <1 per hour on idle channels vs current ~6 per hour)
- No zombie sockets accumulate in `ctx.getWebSockets()` after client reconnects
- All existing tests pass

## Relationship to Parent

Parent chunk `websocket_hibernation_compat` removed server-side heartbeats for cost efficiency but introduced connection instability. This chunk addresses the root causes: missing application-level auto-response (edge proxy thinks connections are idle), incomplete close handshake (zombie accumulation), and aggressive client close timeout (server can't respond in time).