---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/__init__.py
- src/board/crypto.py
- src/board/storage.py
- src/board/client.py
- src/cli/board.py
- src/cli/__init__.py
- pyproject.toml
- tests/test_board_crypto.py
- tests/test_board_storage.py
- tests/test_board_client.py
- tests/test_board_cli.py
- tests/test_board_e2e.py
code_references:
- ref: src/board/crypto.py#generate_keypair
  implements: "Ed25519 key pair generation (seed + public key)"
- ref: src/board/crypto.py#derive_swarm_id
  implements: "Base58 swarm ID derivation from public key"
- ref: src/board/crypto.py#derive_symmetric_key
  implements: "Ed25519→Curve25519→HKDF symmetric key derivation for E2E encryption"
- ref: src/board/crypto.py#encrypt
  implements: "XChaCha20-Poly1305 message encryption with nonce||ciphertext format"
- ref: src/board/crypto.py#decrypt
  implements: "XChaCha20-Poly1305 message decryption"
- ref: src/board/crypto.py#sign
  implements: "Ed25519 message signing for auth handshake"
- ref: src/board/storage.py#save_keypair
  implements: "Operator-global key persistence (~/.ve/keys/)"
- ref: src/board/storage.py#load_keypair
  implements: "Operator-global key retrieval"
- ref: src/board/storage.py#list_swarms
  implements: "List stored swarm IDs"
- ref: src/board/storage.py#save_cursor
  implements: "Project-local cursor persistence (.ve/board/cursors/)"
- ref: src/board/storage.py#load_cursor
  implements: "Project-local cursor retrieval with default 0"
- ref: src/board/client.py#BoardClient
  implements: "WebSocket client for Leader Board wire protocol (auth handshake, send, watch, channels, register_swarm)"
- ref: src/board/client.py#BoardError
  implements: "Server error representation"
- ref: src/cli/board.py#board
  implements: "CLI command group for 've board' subcommands"
- ref: src/cli/board.py#swarm_create
  implements: "ve board swarm create — key generation and server registration"
- ref: src/cli/board.py#send_cmd
  implements: "ve board send — encrypt and transmit message"
- ref: src/cli/board.py#watch_cmd
  implements: "ve board watch — block, receive, decrypt, print (no cursor advance)"
- ref: src/cli/board.py#ack_cmd
  implements: "ve board ack — advance persisted cursor"
- ref: src/cli/board.py#channels_cmd
  implements: "ve board channels — list channels in swarm"
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

Implement the `ve board` CLI subcommands.

**Operator-global commands:**
- `swarm create` — generates asymmetric key pair, registers public key with
  server, stores private key in `~/.ve/`. The swarm belongs to the operator,
  not any single project.

**Channel commands:**
- `send` — encrypts message body client-side using the swarm key before
  transmission, posts to a channel
- `watch` — supplies client's persisted cursor, blocks until a message exists
  after that position, decrypts the body client-side, prints plaintext to
  stdout, exits. Cursor is NOT auto-advanced so the client can re-read on crash.
- `ack` — advances the client's persisted cursor after durable processing
- `channels` — lists channels in the swarm

**Storage model:**
- Client-side cursor storage is **project-local** (each project tracks its own
  position on channels it watches)
- Key storage is **operator-global** in `~/.ve/`

The CLI must work identically against the local server and the Durable Objects
backend.

## Success Criteria

- `ve board swarm create` generates a key pair and registers with a server
- Private key stored in `~/.ve/`, not project-local
- `ve board send` encrypts and transmits a message
- `ve board watch` blocks, receives, decrypts, and prints to stdout
- `ve board ack` advances the persisted cursor
- `ve board channels` lists channels in the swarm
- End-to-end test against the local server adapter: send → watch → ack cycle
- Cursor persists across CLI invocations (project-local storage)
- Key persists across CLI invocations (operator-global storage)

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