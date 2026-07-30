---
status: ONGOING
trigger: "Three silent board failures in 12h cost the operator an overnight GPU window; wiki librarian asked the steward to design a guaranteed-delivery protocol."
proposed_chunks:
  - prompt: "BoardClient.send returns success only after the channel head has durably incremented to include the message. On post-transmit timeout/disconnect, send retries idempotently using a client-generated message-id; the server treats a duplicate message-id on the same channel as a no-op that returns the existing position. Callers no longer have to choose between possible loss and possible duplication."
    chunk_directory: null
    depends_on: []
  - prompt: "ve board watch exposes a liveness contract to the owning agent: a heartbeat or sequence-gap signal raised when the underlying stream stops delivering, distinguishable from a genuinely quiet channel. The signal surfaces to the agent (not just a log line) so a silently dead watch is no longer indistinguishable from idle. Implementation likely combines server-side periodic heartbeat frames with client-side gap detection on the channel head; agent-visible failure is delivered via the watch's stdout stream / exit code so wrapping skills can react."
    chunk_directory: null
    depends_on: []
  - prompt: "ve board offers an optional delivered/read receipt tier for messages that need confirmation a counterparty session consumed them, beyond head-commit confirmation. Senders opt in per-message; the server records which watchers have acked past the receipt-bearing offset and exposes this via a query so the sender can verify delivery to specific consumers, not just durability."
    chunk_directory: null
    depends_on: [0, 1]
created_after: ["entity_wiki_memory"]
---

## Trigger

Filed by the wiki librarian (loop-token program) at the operator's request, in
response to three silent failures in ~12 hours on swarm `SLPRuNDf1A6j4XcKqp287V`
(2026-06-09/10) that cost the operator a pre-cleared overnight GPU window:

1. **Send lost after transmit.** `ve board send` raised
   `websockets.ConnectionClosedError` ("no close frame received or sent") in
   `board/client.py send()` *after* the ciphertext was transmitted but *before*
   the position ack was received. The message was briefly visible to a live
   watcher (the librarian read it back at the expected offset) but was never
   durably committed — the channel head later showed it absent. **Read-after-send
   is therefore not a reliable confirmation**; only a subsequent durable head
   increment is.

2. **Background watch died silently.** The loop-token-steward's in-session
   background watch (`ve board watch ... --max-reconnects 0`) died ~21:30
   without the owning agent noticing. A directive sent at 21:43 sat unread for
   ~9.5h until a human/librarian intervened. The watch process can also enter
   reconnect loops that resubscribe correctly (the librarian's own watch
   survived via an outer `while true` wrapper plus the
   `watch_handshake_timeout_retry`/`watch_handshake_stale_retry` lineage) —
   but nothing notifies the agent when its watch silently stops delivering.

3. **Send believed-sent, never committed.** A wrap-up message the steward
   "sent" never landed on the channel head — same failure class as (1), on
   their side.

The operator's ask, verbatim, is to design a guaranteed-delivery protocol
"perhaps with the sender not registering send until the head increments."
Suggested shape (refine as appropriate):

- **Send** — after transmitting, poll the channel head (or re-read the
  expected position); report success only once the head has durably
  incremented to include the message. On ack-timeout, retry with an
  idempotency key / message-id so retries can't double-post.
- **Watch** — a liveness contract: heartbeat or sequence-gap detection
  surfaced *to the owning agent* (not just a log line), so a dead watch is
  distinguishable from a quiet channel. Possibly a "watch with lease" the
  server tracks, with redelivery-from-cursor on reconnect (cursors already
  exist — the gap is agent-visible failure signaling).
- **Receipts** — a delivered/read receipt tier for directives where the
  sender needs to know a counterparty session actually consumed the message.

Current operator-side workarounds the protocol should obsolete: verify
every important send via `ve board channels` head-increment polling; wrap
watches in outer restart loops; treat agent narration ("I sent it") as
unverified until the head confirms it.

## Success Criteria

This investigation is **SOLVED** when the design space below has explicit
operator-blessed decisions on:

- **Idempotency key location and lifetime.** Client-generated message-id
  attached to the encrypted envelope vs. server-assigned; per-channel
  deduplication window vs. permanent; collision semantics.
- **Send confirmation model.** Pure poll-the-head (simple, no protocol
  change) vs. server-side post-commit ack frame (one extra round-trip but
  no extra read amplification).
- **Watch liveness primitive.** Server-emitted heartbeat frames at a
  configurable interval vs. client-side timeout on head-stagnation vs. both.
  How a missed heartbeat surfaces to the agent: stdout sentinel line,
  non-zero exit, dedicated error frame on the watch stream.
- **Lease semantics for watch.** Whether the server tracks watch leases
  (and redelivers from cursor on reconnect) or whether cursor management
  stays purely client-side as today.
- **Receipt tier scope.** Per-message opt-in, dedicated channel suffix
  (e.g. `*-receipts`), or first-class addition to channel head metadata.
  Whether receipts identify specific watchers or just "some watcher".
- **Backward compatibility.** Whether legacy clients/senders coexist with
  the new contract during the migration window, and how the worker
  (`workers/leader-board/src/swarm-do.ts`) handles mixed-version sessions.

Implementation work — broken out into the proposed chunks above — proceeds
only after these decisions are recorded here.

## Testable Hypotheses

### H1: `BoardClient.send`'s post-transmit/pre-ack ConnectionClosedError window is reproducible by killing the WebSocket at a controlled point

- **Rationale**: Incidents 1 and 3 share the failure signature.
  Reproducing it deterministically validates that the proposed
  idempotency + head-poll fix targets the actual failure mode rather than
  a related-but-different race.
- **Test**: Patch `BoardClient.send` to raise `ConnectionClosedError`
  between `await ws.send(ciphertext)` and the position-ack read; assert
  the channel head does *not* include the message; assert a retry with
  the same client-generated message-id results in exactly one head
  increment.
- **Status**: UNTESTED

### H2: A `--max-reconnects 0` watch dies silently because its only failure signal is the process exit code, which the in-session-background-task wrapper doesn't surface to the owning agent

- **Rationale**: Incident 2 specifically used `--max-reconnects 0`. The
  steward's own watches (`--max-reconnects` default, plus outer
  while-true) survive via reconnect, so the bug surface is the
  `--max-reconnects 0` configuration's interaction with the
  background-task lifecycle.
- **Test**: Inspect the
  `gstack`/`claude-code` background-task wrapper for whether exit codes
  are surfaced as `<task-notification>` events; confirm whether a clean
  exit (code 0 or 3) is propagated promptly to the agent vs. silently
  absorbed.
- **Status**: UNTESTED

### H3: Server-emitted periodic heartbeat frames are the minimal-overhead path to agent-visible watch liveness

- **Rationale**: Cursor-gap detection on the client requires either
  polling the head or comparing wall-clock to last-message-time, both of
  which conflate "quiet channel" with "dead watch." A server heartbeat
  every N seconds disambiguates the two without extra client load.
- **Test**: Estimate heartbeat overhead per Durable Object on the actual
  steady-state watch fleet; compare against an equivalent client-side
  head-poll cadence.
- **Status**: UNTESTED

### H4: Receipts can be modeled as a per-channel cursor-watermark query without a new message tier

- **Rationale**: Each watcher already advances a cursor on ack. The
  highest cursor across all current watchers on a channel is an existing
  signal that "at least one consumer is past offset X." Exposing this as
  a query may obsolete a dedicated receipts tier for most callers.
- **Test**: Sketch the query (e.g. `ve board channels --watchers-at-or-past
  <offset>`); confirm whether the worker tracks per-watcher cursors
  durably or only in memory.
- **Status**: UNTESTED

## Exploration Log

### 2026-06-10: Investigation opened

Filed by the steward in autonomous mode from the wiki librarian's inbound
report (vibe-engineer-steward seq 76). No exploration performed yet —
investigation queued for operator-led design decisions. The proposed-chunks
decomposition above (send / watch / receipts) is a *starting* split; the
operator may refine boundaries (e.g. split idempotency + head-poll into
separate chunks, or fold receipts into the head-metadata work) once the
Success Criteria decisions land.

## Findings

*(none yet — investigation just opened.)*

## Proposed Chunks

The three areas below are tracked in the frontmatter `proposed_chunks` array
and are listed here for narrative readability. Indices match the frontmatter
order.

1. **Durable-send confirmation with idempotent retry** (`proposed_chunks[0]`).
   Send returns success only after the channel head includes the message;
   client-generated message-id makes retries safe.
   - Priority: High (immediate failure mode for important sends)
   - Dependencies: None
   - Notes: Smallest change with biggest reliability win. Probably the
     first chunk to land.

2. **Watch liveness contract** (`proposed_chunks[1]`). Agent-visible signal
   when a watch silently stops delivering.
   - Priority: High (caused the 9.5h missed-directive incident)
   - Dependencies: None
   - Notes: Heartbeat vs. gap-detect vs. both is a design decision. The
     surfacing mechanism (stdout sentinel, exit code, error frame) is a
     second design decision and may interact with how the steward's
     `run_in_background` task notifications work.

3. **Delivered/read receipt tier** (`proposed_chunks[2]`). Sender-visible
   confirmation that a counterparty session consumed a directive.
   - Priority: Medium (useful but partial workarounds exist)
   - Dependencies: chunks 0 and 1 (the durable-send + liveness contracts
     are the substrate receipts build on)
   - Notes: H4 above proposes this may be a cursor-watermark query rather
     than a new message tier — worth resolving before committing to a
     decomposition.

## Resolution Rationale

*(pending — investigation is ONGOING.)*
