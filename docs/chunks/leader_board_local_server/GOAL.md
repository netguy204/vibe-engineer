---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/leader_board/protocol.py
- src/leader_board/fs_storage.py
- src/leader_board/server.py
- src/leader_board/__init__.py
- tests/test_leader_board_protocol.py
- tests/test_leader_board_fs_storage.py
- tests/test_leader_board_server.py
- tests/test_leader_board_e2e.py
code_references:
- ref: src/leader_board/protocol.py#InvalidFrameError
  implements: "Frame parsing error type for malformed/unknown frames"
- ref: src/leader_board/protocol.py#parse_client_frame
  implements: "JSON string → typed ClientFrame parsing with validation"
- ref: src/leader_board/protocol.py#serialize_server_frame
  implements: "ServerFrame → compact JSON serialization for wire protocol"
- ref: src/leader_board/fs_storage.py#FileSystemStorage
  implements: "Filesystem-backed StorageAdapter with JSONL message logs, file locking, and atomic compaction"
- ref: src/leader_board/server.py#websocket_handler
  implements: "WebSocket connection lifecycle: challenge/auth handshake, swarm-scoped message loop"
- ref: src/leader_board/server.py#_handle_watch
  implements: "Async watch frame handler dispatched via create_task for concurrency"
- ref: src/leader_board/server.py#_compaction_loop
  implements: "Background compaction scheduler on 30-day TTL"
- ref: src/leader_board/server.py#_enumerate_all_channels
  implements: "Filesystem enumeration of all (swarm, channel) pairs for compaction"
- ref: src/leader_board/server.py#create_app
  implements: "Starlette application factory wiring storage, core, and compaction lifespan"
- ref: src/leader_board/server.py#run_server
  implements: "Convenience entry point for CLI integration via uvicorn.run"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- leader_board_core
created_after:
- finalize_double_commit
---

# Chunk Goal

## Minor Goal

Implement a local WebSocket server adapter that wraps the portable core. This
is a simple server that accepts WebSocket connections, routes them through the
core, and persists swarm/channel state to the local filesystem.

Used for **development iteration and self-hosting**. Must speak the identical
wire protocol that the Durable Objects adapter will speak.

## Success Criteria

- Server starts and accepts WebSocket connections on a configurable port
- Implements the full wire protocol from the leader board spec
- Swarm and channel state persisted to local filesystem (survives restart)
- End-to-end test: send a message, watch with cursor, receive the message
- Wire protocol is byte-identical to what the DO adapter will implement
- Compaction runs on the 30-day TTL schedule

## Rejected Ideas

<!-- DELETE THIS SECTION when the goal is confirmed if there were no rejected
ideas.

This is where the back-and-forth between the agent and the operator is recorded
so that future agents understand why we didn't do something.

If there were rejected ideas in the development of this GOAL with the operator,
list them here with the reason they were rejected.

Example:

### Store the queue in redis

We could store the queue in redis instead of a file. This would allow us to scale the queue to multiple nodes.

Rejected because: The queue has no meaning outside the current session.

---

-->