---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- docs/trunk/SPEC.md
code_references:
  - ref: docs/trunk/SPEC.md
    implements: "Leader Board specification section covering swarm model, E2E encryption, append-only log channels, cursor-based delivery, wire protocol, auth flow, core/adapter boundary, DO topology, steward SOP format, guarantees, and limits"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- finalize_double_commit
---

# Chunk Goal

## Minor Goal

Define the leader board specification as a new section of the VE SPEC. This is
the foundational design chunk that all implementation chunks depend on.

Cover:
- **Swarm model** — operator-global tenant boundary with asymmetric key pair
  (one operator manages one swarm across many repos, private key in `~/.ve/`)
- **End-to-end encryption** — message bodies encrypted client-side; server
  stores/routes opaque ciphertext; only channel name and cursor position
  visible to the server
- **Append-only log channel model** — each channel is an ordered log; clients
  supply a cursor position when watching and receive the next message after
  that position, blocking if none exists yet; server never deletes on delivery
- **30-day TTL compaction** — messages older than 30 days eligible for removal;
  "cursor expired" error with earliest available position when a client
  presents a stale cursor
- **Cursor-based at-least-once delivery** — clients persist cursor locally,
  advance only after durable processing; crash-and-resume re-reads from last
  persisted cursor
- **Wire protocol** — WebSocket JSON frames for watch-with-cursor/send/swarm
  operations
- **Auth flow** — client signs with private key, server verifies with stored
  public key
- **Core/adapter boundary** — portable core logic vs. host-specific adapters
- **Durable Object topology** — for the hosted multi-tenant variant
- **Steward SOP document format** — project-local document defining how the
  steward responds to inbound messages (autonomous fix-and-publish, queue for
  human, or custom behavior)

Note: steward channels and changelog channels are the same primitive — the only
difference is convention.

Reference the leader-board project at `../leader-board/docs/trunk/` for the
original design — adapt it to the swarm model, cursor-based log, and portable
core architecture.

## Success Criteria

- A new "Leader Board" section exists in docs/trunk/SPEC.md
- All topics listed above are covered with enough precision to write a
  conformance test suite
- Wire protocol message formats are fully specified with examples
- Core/adapter interface boundary is defined (what the core exposes, what
  adapters must implement)
- Steward SOP document schema is specified
- The spec is internally consistent and references the original leader-board
  design where it diverges

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