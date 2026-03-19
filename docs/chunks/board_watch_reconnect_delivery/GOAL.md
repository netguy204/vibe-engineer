---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
- ref: src/board/client.py#BoardClient::watch_with_reconnect
  implements: "Re-poll logging after single-channel WebSocket reconnect"
- ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
  implements: "Re-poll logging after multi-channel WebSocket reconnect"
- ref: tests/test_board_client.py#test_watch_with_reconnect_delivers_pending_message
  implements: "Test that single-channel watch re-polls from correct cursor after reconnect"
- ref: tests/test_board_client.py#test_watch_multi_reconnect_delivers_pending_messages
  implements: "Test that multi-channel watch re-polls all channels with correct cursors after reconnect"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- orch_daemon_root_resolution
- swarm_request_response
---

# Chunk Goal

## Minor Goal

Fix `ve board watch` to re-check for pending messages after a WebSocket reconnect, so messages that arrive during a disconnect window are not silently missed.

Currently, when the WebSocket disconnects and reconnects, the watch resumes listening for new server-push notifications but does not check whether any messages were written to the channel during the disconnect interval. If a message arrived while disconnected, it sits undelivered until the next message triggers a push — or forever if no further messages arrive.

After reconnecting, the watch should re-poll the channel from its current offset to detect and deliver any messages that arrived during the gap. This is the same logic that runs on initial connection — it just needs to run again after each reconnect.

Reported by Database Savings Plans Steward. Workaround: kill and restart the watch with the same `--offset`.

## Success Criteria

- After WebSocket reconnect, watch re-polls the channel from its current offset
- Messages that arrived during the disconnect window are delivered immediately after reconnect
- No duplicate delivery of messages already seen before the disconnect
- Tests verify: message arrives during simulated disconnect, watch delivers it after reconnect

