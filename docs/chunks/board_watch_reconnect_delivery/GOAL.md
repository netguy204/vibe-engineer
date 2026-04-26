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

`ve board watch` re-checks for pending messages after a WebSocket reconnect, so messages that arrive during a disconnect window are not silently missed.

When the WebSocket disconnects and reconnects, the watch re-polls the channel from its current offset before resuming listening for server-push notifications. Any messages that arrived during the disconnect interval are delivered immediately after reconnect rather than sitting undelivered until the next push triggers them. This re-poll mirrors the initial-connection logic, applied again after every reconnect.

## Success Criteria

- After WebSocket reconnect, watch re-polls the channel from its current offset
- Messages that arrived during the disconnect window are delivered immediately after reconnect
- No duplicate delivery of messages already seen before the disconnect
- Tests verify: message arrives during simulated disconnect, watch delivers it after reconnect

