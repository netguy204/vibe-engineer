---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/leader_board/__init__.py
- src/leader_board/models.py
- src/leader_board/storage.py
- src/leader_board/memory_storage.py
- src/leader_board/core.py
- tests/test_leader_board_storage.py
- tests/test_leader_board_core.py
- tests/test_leader_board_adapter_contract.py
code_references:
- ref: src/leader_board/models.py#SwarmInfo
  implements: "Swarm registration domain model (swarm_id, public_key, created_at)"
- ref: src/leader_board/models.py#ChannelMessage
  implements: "Channel message domain model with monotonic position and opaque body"
- ref: src/leader_board/models.py#ChannelInfo
  implements: "Channel summary model (head/oldest position)"
- ref: src/leader_board/models.py#CursorExpiredError
  implements: "Cursor expired exception with earliest_position field"
- ref: src/leader_board/models.py#SwarmNotFoundError
  implements: "Swarm not found exception"
- ref: src/leader_board/models.py#ChannelNotFoundError
  implements: "Channel not found exception"
- ref: src/leader_board/models.py#AuthFailedError
  implements: "Auth verification failure exception"
- ref: src/leader_board/storage.py#StorageAdapter
  implements: "Adapter storage protocol — async interface for durable persistence"
- ref: src/leader_board/memory_storage.py#InMemoryStorage
  implements: "In-memory StorageAdapter reference implementation for tests"
- ref: src/leader_board/core.py#LeaderBoardCore
  implements: "Core business logic: swarm ops, channel ops, blocking read, compaction"
- ref: src/leader_board/core.py#LeaderBoardCore::register_swarm
  implements: "Swarm registration with duplicate detection"
- ref: src/leader_board/core.py#LeaderBoardCore::verify_auth
  implements: "Ed25519 signature verification against stored public keys"
- ref: src/leader_board/core.py#LeaderBoardCore::append
  implements: "Channel message append with validation and reader wake-up"
- ref: src/leader_board/core.py#LeaderBoardCore::read_after
  implements: "Cursor-based blocking read with expiration detection"
- ref: src/leader_board/core.py#LeaderBoardCore::compact
  implements: "30-day TTL compaction delegated to storage adapter"
- ref: src/leader_board/__init__.py
  implements: "Package public API exports"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- leader_board_spec
created_after:
- finalize_double_commit
---

# Chunk Goal

## Minor Goal

Implement the portable leader board core as a host-independent library. This
module owns:

- **Swarm state management** — swarm registration, public key storage
- **Append-only channel log** — messages assigned monotonic positions, never
  deleted on delivery
- **Cursor-based reads** — client supplies position, receives next message
  after it, blocks if none exists; "cursor expired" error when position is
  older than retained messages
- **30-day TTL compaction** — marks messages older than 30 days for removal
- **Asymmetric key auth verification** — verifies client signatures against
  stored public keys
- **FIFO message ordering**

The core treats message bodies as **opaque byte strings** — encryption and
decryption happen at the client layer, not in the core. The core has no
concept of channel "types" — steward vs. changelog is a client convention.

**No WebSocket code, no HTTP code, no filesystem code.** The core exposes an
interface that adapters call. The adapter is responsible for durable storage
of the log.

Use the spec produced by `leader_board_spec`.

## Success Criteria

- Core library exists with a clean adapter interface
- Swarm CRUD operations work (create, verify auth)
- Messages can be appended to channels and read back by cursor position
- Blocking read returns immediately when a message exists after the cursor
- "Cursor expired" error returned when cursor is behind compaction frontier
- Compaction removes messages older than 30 days
- All operations are tested without any network or filesystem dependencies
  (in-memory adapter for tests)

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