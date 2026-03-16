---
decision: APPROVE
summary: "All success criteria satisfied: heartbeat alarm removed, compaction-only alarm preserved, PingFrame cleaned from protocol/server/client, client-side reconnect untouched, all 16 tests pass"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: No alarm is scheduled solely for heartbeat purposes (alarm only for compaction)

- **Status**: satisfied
- **Evidence**: `HEARTBEAT_INTERVAL_MS` constant and `ensureHeartbeatAlarm()` deleted from `swarm-do.ts`. `alarm()` now only runs compaction and reschedules at `COMPACTION_INTERVAL_MS`. `ensureAlarm()` simplified to only schedule compaction alarm if none exists, with no WebSocket-count branching.

### Criterion 2: DO hibernates during idle periods (verify by checking no alarm reschedule on WebSocket connect)

- **Status**: satisfied
- **Evidence**: On WebSocket connect, `ensureAlarm()` is called instead of `ensureHeartbeatAlarm()`. `ensureAlarm()` only creates a compaction alarm if none already exists — it does not force-reschedule to a short heartbeat interval. The `lastCompactionAt` field and time-elapsed guard were also removed since every alarm tick is now a compaction tick.

### Criterion 3: WebSocket connections still survive idle periods (Cloudflare runtime handles pings)

- **Status**: satisfied
- **Evidence**: Client-side `ping_interval=20` and `ping_timeout=10` preserved in `client.py:57` (`BoardClient.connect()`). These drive protocol-level WebSocket pings that the Cloudflare runtime auto-responds to without waking the DO.

### Criterion 4: Client-side reconnect logic remains functional as a safety net

- **Status**: satisfied
- **Evidence**: `watch_with_reconnect()` method in `client.py` untouched. Reconnect tests in `test_board_client.py` preserved (backreference comment at line 172 still references `websocket_keepalive`, which is correct since that chunk created the reconnect logic).

### Criterion 5: Existing tests pass (update tests that rely on application-level PingFrame)

- **Status**: satisfied
- **Evidence**: Ping-filtering tests (`test_watch_ignores_ping_frames`, `test_send_ignores_ping_frames`) and server heartbeat tests (`TestServerHeartbeat`) removed since the behavior no longer exists. All 16 remaining tests pass. E2E tests also cleaned up.
