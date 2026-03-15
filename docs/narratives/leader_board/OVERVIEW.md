---
status: ACTIVE
advances_trunk_goal: 'Required Properties: A well-documented project is already structured
  for agent-independent work. It must be possible to appoint a long-lived agent steward
  over such a project and send it messages from other contexts without requiring the
  sender to context-switch.'
proposed_chunks:
- prompt: "Define the leader board specification as a new section of the VE SPEC.\
    \ Cover: the swarm model (operator-global tenant boundary with asymmetric key\
    \ pair \u2014 one operator typically manages one swarm across many repos, private\
    \ key stored in ~/.ve/, not project-local), end-to-end encryption (message bodies\
    \ are encrypted client-side before transmission; the server stores and routes\
    \ opaque ciphertext; only the channel name and cursor position are visible to\
    \ the server \u2014 the swarm's key pair or a derived symmetric key handles encryption\
    \ so all swarm members can decrypt), the append-only log channel model (each channel\
    \ is an ordered log; clients supply a cursor position when watching and receive\
    \ the next message after that position, blocking if none exists yet; the server\
    \ never deletes on delivery), server-side compaction with a 30-day TTL (messages\
    \ older than 30 days are eligible for removal; cursors are client-side so the\
    \ server has no visibility into them \u2014 the TTL is a heuristic; when a client\
    \ presents a cursor older than the oldest retained message, the server returns\
    \ a \"cursor expired\" error with the earliest available position so the client\
    \ can decide whether to resume from there or alert the operator), the cursor-based\
    \ at-least-once delivery guarantee (clients persist their cursor locally and advance\
    \ it only after durably processing a message; crash-and-resume re-reads from last\
    \ persisted cursor), the wire protocol (WebSocket JSON frames for watch-with-cursor/send/swarm\
    \ operations), the auth flow (client signs with private key, server verifies with\
    \ stored public key), the core/adapter architectural boundary (portable core logic\
    \ vs. host-specific adapters), the Durable Object topology for the hosted variant,\
    \ and the steward SOP document format (a project-local document that defines how\
    \ the steward responds to inbound messages \u2014 autonomous fix-and-publish,\
    \ queue for human, or custom behavior). Note that steward channels and changelog\
    \ channels are the same primitive \u2014 the only difference is convention. Reference\
    \ the leader-board project at ../leader-board/docs/trunk/ for the original design\
    \ \u2014 adapt it to the swarm model, cursor-based log, and portable core architecture.\n"
  chunk_directory: leader_board_spec
  depends_on: []
- prompt: "Implement the portable leader board core as a host-independent library.\
    \ This module owns swarm state management, the append-only channel log (messages\
    \ assigned monotonic positions, never deleted on delivery), cursor-based reads\
    \ (client supplies position, receives next message after it, blocks if none exists),\
    \ asymmetric key auth verification, and FIFO message ordering. The core treats\
    \ message bodies as opaque byte strings \u2014 encryption and decryption happen\
    \ at the client layer, not in the core. The core has no concept of channel \"\
    types\" \u2014 steward vs. changelog is a client convention. No WebSocket code,\
    \ no HTTP code, no filesystem code \u2014 the core exposes an interface that adapters\
    \ call. The adapter is responsible for durable storage of the log. Use the spec\
    \ produced by the specification chunk.\n"
  chunk_directory: leader_board_core
  depends_on:
  - 0
- prompt: 'Implement a local WebSocket server adapter that wraps the portable core.
    This is a simple server (e.g., Node.js or Python) that accepts WebSocket connections,
    routes them through the core, and persists swarm/channel state to the local filesystem.
    Used for development iteration and self-hosting. Must speak the identical wire
    protocol that the Durable Objects adapter will speak.

    '
  chunk_directory: leader_board_local_server
  depends_on:
  - 1
- prompt: 'Implement the Cloudflare Durable Objects adapter that wraps the portable
    core. One DO class per swarm. The Worker routes incoming WebSocket connections
    to the correct swarm DO based on the auth handshake. This is the hosted multi-tenant
    deployment that the project maintainer operates for all VE users. Must speak the
    identical wire protocol as the local server adapter.

    '
  chunk_directory: leader_board_durable_objects
  depends_on:
  - 1
- prompt: "Implement the ve board CLI subcommands. Operator-global commands: swarm\
    \ create (generates asymmetric key pair, registers public key with server, stores\
    \ private key in ~/.ve/ \u2014 the swarm belongs to the operator, not any single\
    \ project). Channel commands: send (encrypts message body client-side using the\
    \ swarm key before transmission, posts to a channel), watch (supplies client's\
    \ persisted cursor, blocks until a message exists after that position, decrypts\
    \ the body client-side, prints plaintext to stdout, exits \u2014 cursor is NOT\
    \ auto-advanced so the client can re-read on crash), ack (advances the client's\
    \ persisted cursor after durable processing), and channels (lists channels in\
    \ the swarm). Client-side cursor storage is project-local (each project tracks\
    \ its own position on channels it watches). Key storage is operator-global in\
    \ ~/.ve/. The CLI must work identically against the local server and the Durable\
    \ Objects backend.\n"
  chunk_directory: leader_board_cli
  depends_on:
  - 0
- prompt: "Create Claude Code steward skills that teach agents the leader board workflow\
    \ patterns. /steward-setup: interviews the operator to produce the project's steward\
    \ SOP document (stored in docs/trunk/STEWARD.md or similar). The SOP defines the\
    \ steward's name, its channel, the changelog channel, and critically, how it should\
    \ respond to inbound messages \u2014 autonomous fix-and-publish, queue work for\
    \ a human operator, or custom behavior. The interview captures the operator's\
    \ intent for this specific project. Swarm creation is NOT part of setup \u2014\
    \ the operator has already created the swarm via ve board swarm create and holds\
    \ the private key in ~/.ve/. /steward-watch: the watch-respond-rewatch loop using\
    \ run_in_background \u2014 read the SOP, watch with cursor, receive message, triage\
    \ according to SOP, act, post outcome to changelog channel, ack to advance cursor,\
    \ rewatch. /steward-send: send a message to a steward's channel from any agent\
    \ context. /steward-changelog: watch a project's changelog channel with the requester's\
    \ own cursor (used to close the loop after sending a message). These are VE template-rendered\
    \ skills installed by ve init.\n"
  chunk_directory: leader_board_steward_skills
  depends_on:
  - 4
- prompt: "Introduce a user global config file at ~/.ve/board.toml storing the\
    \ operator's default coordination server URL and default swarm ID. All ve\
    \ board client commands resolve --server and --swarm from this config when\
    \ flags are not provided. Add a ve board bind command that writes the server\
    \ URL (and optionally default swarm) to the config — this is how an operator\
    \ points their CLI at the hosted Durable Objects coordination server or back\
    \ to localhost.\n"
  chunk_directory: leader_board_user_config
  depends_on:
  - 4
  - 2
created_after:
- explicit_chunk_deps
---
## Advances Trunk Goal

This narrative advances the Required Properties section of docs/trunk/GOAL.md:

> A well-documented project is already structured for agent-independent work.
> It must be possible to appoint a long-lived agent steward over such a project
> and send it messages from other contexts without requiring the sender to
> context-switch.

A vibe-engineered project already has the documentation structure that enables
an agent to work independently — trunk docs, chunk lifecycle, subsystems,
investigations. What's missing is the communication primitive: a way for an
operator (or another agent) to send a message to a project's steward without
leaving their current context. Leader board provides that primitive.

## Driving Ambition

An operator is working on Project A and notices a deficiency in Tool B (a
vibe-engineered project with its own steward agent). Today, the operator must
context-switch: open Tool B's repo, create a chunk or file an issue, return to
Project A. This breaks flow and discourages reporting.

Leader board enables the operator to fire off a message — `ve board send
tool-b "the template renderer swallows whitespace errors"` — and return
immediately to their work. Tool B's steward agent, parked in a
watch-respond-rewatch loop, receives the message and triages it according to
its **standard operating procedure** — a project-local document that the
operator wrote (via an interactive interview) when appointing the steward.
One project's SOP might say "fix issues autonomously and publish results."
Another might say "queue work items for the human to drive later." The
steward acts accordingly and posts the outcome to Tool B's changelog channel.

The operator (or any interested observer) can watch the changelog to close the
loop: "steward received your report, created investigation
`whitespace_errors`, findings pending." Multiple observers can watch the same
changelog — it's a fan-out channel. This gives the requester confidence their
message was handled without ever leaving their current context.

The system is a lightweight message-passing service built on a single
primitive: the **append-only channel log**. Each channel is an ordered log of
messages. Clients watch by supplying a cursor (their last-seen position) and
block until a new message appears. The server never deletes messages on
delivery — clients own their cursors and advance them only after durably
processing each message. This makes at-least-once delivery a client-side
guarantee: crash before advancing your cursor, and you re-read the message on
restart.

**Steward channels** and **changelog channels** are the same primitive. The
only difference is convention: a steward channel has one consumer (the
steward), while a changelog channel has many consumers, each tracking their
own independent cursor.

1. **Portable core** — The routing, queuing, and auth logic is
   host-independent. It can be wrapped in a local WebSocket server (for
   development and self-hosting) or in Cloudflare Durable Objects (for the
   hosted multi-tenant service).

2. **Swarm isolation with end-to-end encryption** — Each operator gets a
   "swarm" with an asymmetric key pair, stored globally in `~/.ve/`. A swarm
   spans all the operator's projects. Channels exist within swarms. Message
   bodies are encrypted client-side before transmission — the server stores
   and routes opaque ciphertext. The only metadata visible to the server is
   channel names and cursor positions. Even the service operator cannot read
   message contents or impersonate a swarm. This makes it safe to run a
   single hosted instance for all VE users across organizations.

3. **CLI-native integration** — The watcher is a blocking process that
   supplies a cursor, waits for the next message, prints it, and exits.
   Claude Code's `run_in_background` turns this into an async notification.
   The agent doesn't poll — it parks a watcher, does other work, gets
   notified on message arrival, processes, acks to advance the cursor, and
   rewatches.

## Chunks

1. **Specification** — Define the wire protocol, swarm model (operator-global),
   asymmetric auth flow, end-to-end encryption (server sees only ciphertext),
   core/adapter boundary, Durable Object topology, and the steward SOP
   document format as a new SPEC section. Adapts the original leader-board
   design (at ../leader-board/) to the swarm model, cursor-based log, and
   portable core architecture.

2. **Portable core** — Host-independent library: swarm state, append-only
   channel log with monotonic positions, cursor-based reads, auth
   verification. No channel "types" in the core — steward vs. changelog is
   client convention. No WebSocket/HTTP/filesystem code — adapters handle
   storage and transport. Depends on chunk 1.

3. **Local server adapter** — Wraps the core in a WebSocket server with
   filesystem persistence. For development and self-hosting. Speaks the
   identical wire protocol as the DO adapter. Depends on chunk 2.

4. **Durable Objects adapter** — Wraps the core in CF Workers + DO. One DO
   per swarm. Hosted multi-tenant deployment. Identical wire protocol.
   Depends on chunk 2. Can parallelize with chunk 3.

5. **CLI client** — `ve board` subcommands. Operator-global: `swarm create`
   (key pair generation, stored in `~/.ve/`). Channel operations: `send`
   (encrypt + transmit), `watch` (receive + decrypt, with cursor), `ack`
   (advance cursor), `channels`. Encryption/decryption happens entirely
   client-side. Cursor storage is project-local; key storage is
   operator-global. Works identically against local and hosted backends.
   Depends on chunk 1 (needs protocol). Can parallelize with chunks 2–4.

6. **Steward skills** — Claude Code skills: `/steward-setup` (interviews the
   operator and produces the project's SOP document — steward name, channels,
   and response behavior; swarm already exists), `/steward-watch` (read SOP,
   watch with cursor, receive, triage per SOP, act, post to changelog, ack,
   rewatch), `/steward-send` (send to a steward from any context),
   `/steward-changelog` (watch a changelog with requester's own cursor).
   Installed via `ve init` template rendering. Depends on chunk 5.

## Completion Criteria

When complete, an operator working in Project A can run
`ve board send tool-b "description of deficiency"` and immediately return to
their work. A steward agent watching Tool B's channel receives the message,
triages it using VE's existing workflow (creates a chunk, investigation, or
asks a follow-up), and posts the outcome to Tool B's changelog. The operator
watches the changelog and sees the resolution — loop closed, no
context-switch required at any point.

Specifically:

- An operator can appoint a steward over a project by running `/steward-setup`,
  which interviews them and produces an SOP document defining the steward's
  behavior for that project.
- A steward agent can autonomously run the watch-respond-rewatch loop using
  the provided skills, following its SOP without human intervention on the
  mechanics.
- After triaging an inbound message per its SOP, the steward posts the outcome
  to the project's changelog channel. Requesters and other observers watching
  the changelog see what happened.
- Messages sent while no steward is watching are durably queued and delivered
  when the steward next connects (cursor-based at-least-once delivery).
- Multiple organizations can use the same hosted service with cryptographic
  isolation between swarms. Message contents are end-to-end encrypted — the
  server never sees plaintext.
- The entire system works against a local server for development, with
  identical behavior when pointed at the hosted backend.
