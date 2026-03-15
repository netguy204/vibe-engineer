<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Build the `ve board` CLI subcommand group following the established Click
command group pattern (DEC-001). The CLI is a thin layer over three new
internal modules:

1. **`src/board/crypto.py`** — Ed25519 key generation, Curve25519 conversion,
   HKDF key derivation, XChaCha20-Poly1305 encrypt/decrypt. Uses PyNaCl
   (libsodium bindings) which provides all required primitives in one package.

2. **`src/board/storage.py`** — Operator-global key storage (`~/.ve/keys/`)
   and project-local cursor storage (`.ve/board/cursors/`). Simple file I/O
   matching the SPEC's storage model.

3. **`src/board/client.py`** — WebSocket client that speaks the wire protocol
   from SPEC.md §Wire Protocol. Handles the auth handshake (challenge-response),
   then exposes methods for `send`, `watch`, `channels`, and `register_swarm`.
   Uses the `websockets` library for WebSocket connections.

The CLI module (`src/cli/board.py`) composes these three modules and adds
Click decorators. Each subcommand is a thin function: parse args → call
crypto/storage/client → format output.

**Dependency addition:** PyNaCl and websockets must be added to
`pyproject.toml` dependencies.

**Test strategy (per docs/trunk/TESTING_PHILOSOPHY.md):** TDD with tests
written before implementation. Tests focus on:
- Crypto: round-trip encrypt/decrypt, key derivation determinism
- Storage: cursor persistence across calls, key file creation
- Client: mock WebSocket for protocol frame validation
- CLI integration: CliRunner end-to-end against a mock/local server
- The end-to-end send→watch→ack cycle uses an in-process test server
  to avoid network dependencies

## Subsystem Considerations

No existing subsystems are directly relevant. This chunk introduces new
modules (`src/board/`) that don't overlap with existing subsystem scopes.
The CLI registration follows the same pattern as all other command groups
in `src/cli/__init__.py`.

## Sequence

All new source files carry the backreference:
`# Chunk: docs/chunks/leader_board_cli - Leader Board CLI client`

### Step 1: Add dependencies to pyproject.toml

Add `pynacl>=1.5.0` and `websockets>=12.0` to the `dependencies` list in
`pyproject.toml`. Run `uv sync` to install.

Location: `pyproject.toml`

### Step 2: Implement crypto module (TDD)

**Tests first** in `tests/test_board_crypto.py`:
- `test_generate_keypair` — returns 32-byte seed, 32-byte public key
- `test_derive_swarm_id` — base58 of first 16 bytes of pubkey, deterministic
- `test_derive_symmetric_key` — Ed25519 → Curve25519 → HKDF, deterministic
  for the same private key
- `test_encrypt_decrypt_roundtrip` — encrypt plaintext, decrypt ciphertext,
  assert equality
- `test_decrypt_wrong_key_fails` — decrypt with a different swarm key raises
- `test_ciphertext_format` — base64-decoded ciphertext starts with 24-byte
  nonce prefix

**Then implement** `src/board/__init__.py` (empty) and `src/board/crypto.py`:

```python
generate_keypair() -> (seed_bytes, public_key_bytes)
derive_swarm_id(public_key: bytes) -> str
derive_symmetric_key(seed: bytes) -> bytes
encrypt(plaintext: str, symmetric_key: bytes) -> str  # returns base64
decrypt(ciphertext_b64: str, symmetric_key: bytes) -> str
sign(message: bytes, seed: bytes) -> bytes
```

Uses PyNaCl's `nacl.signing.SigningKey`, `nacl.bindings.crypto_sign_ed25519_sk_to_curve25519`,
`nacl.utils.random`, and `nacl.secret.SecretBox`. HKDF via `hashlib` or
`cryptography.hazmat.primitives.kdf.hkdf` (already a transitive dep).

### Step 3: Implement storage module (TDD)

**Tests first** in `tests/test_board_storage.py`:
- `test_save_and_load_keypair` — save key files to temp dir, load them back,
  assert byte equality
- `test_load_keypair_missing` — returns None or raises when keys don't exist
- `test_save_and_load_cursor` — write cursor 42, read it back, assert 42
- `test_load_cursor_default` — missing cursor file returns 0
- `test_cursor_overwrite` — write 10, then 20, read back 20
- `test_list_swarms` — create two key pairs, list returns both swarm IDs

**Then implement** `src/board/storage.py`:

```python
# Operator-global key storage (~/.ve/keys/)
save_keypair(swarm_id: str, seed: bytes, public_key: bytes, keys_dir: Path | None = None)
load_keypair(swarm_id: str, keys_dir: Path | None = None) -> (bytes, bytes) | None
list_swarms(keys_dir: Path | None = None) -> list[str]

# Project-local cursor storage (.ve/board/cursors/)
save_cursor(channel: str, position: int, project_root: Path)
load_cursor(channel: str, project_root: Path) -> int  # 0 if missing
```

`keys_dir` defaults to `Path.home() / ".ve" / "keys"` but is injectable for
testing. Cursor paths are `{project_root}/.ve/board/cursors/{channel}.cursor`.

### Step 4: Implement WebSocket client module (TDD)

**Tests first** in `tests/test_board_client.py`:
- `test_auth_handshake` — mock WS: server sends challenge, client sends auth,
  server sends auth_ok
- `test_register_swarm_frame` — verify the register_swarm frame format
- `test_send_frame` — verify the send frame format and ack response parsing
- `test_watch_frame` — verify the watch frame format and message response
  parsing
- `test_channels_frame` — verify channels_list response parsing
- `test_auth_failure` — server returns error, client raises

Use `unittest.mock.AsyncMock` to mock the websocket connection. The client
should be structured as an async context manager.

**Then implement** `src/board/client.py`:

```python
class BoardClient:
    def __init__(self, server_url: str, swarm_id: str, seed: bytes):
        ...

    async def connect(self):
        """Open WS, perform auth handshake."""

    async def close(self):
        """Close WS connection."""

    async def register_swarm(self, public_key: bytes):
        """Send register_swarm frame (unauthenticated)."""

    async def send(self, channel: str, body_b64: str) -> int:
        """Send message, return assigned position."""

    async def watch(self, channel: str, cursor: int) -> dict:
        """Block until message, return {position, body, sent_at}."""

    async def list_channels(self) -> list[dict]:
        """Return list of channel info dicts."""
```

The `connect()` method opens `ws://{server_url}/ws?swarm={swarm_id}`, reads
the challenge frame, signs the nonce with the private key, sends the auth
frame, and waits for auth_ok.

### Step 5: Implement the CLI command group

**Tests first** in `tests/test_board_cli.py`:
- `test_board_group_exists` — `ve board --help` exits 0, shows subcommands
- `test_swarm_create` — with temp home dir, creates key files, prints swarm ID
- `test_send_command` — with mock client, encrypts and sends
- `test_watch_command` — with mock client, receives and decrypts, prints to
  stdout, does NOT advance cursor
- `test_ack_command` — advances cursor in project-local storage
- `test_channels_command` — lists channels from mock response

For CLI integration tests, mock the WebSocket connection at the `BoardClient`
level to avoid network dependencies. Use `monkeypatch` to override the home
directory for key storage tests.

**Then implement** `src/cli/board.py`:

```python
@click.group()
def board():
    """Leader board messaging commands."""
    pass

@board.group()
def swarm():
    """Swarm management commands."""
    pass

@swarm.command("create")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def swarm_create(server):
    """Generate a new swarm key pair and register with the server."""

@board.command("send")
@click.argument("channel")
@click.argument("body")
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def send(channel, body, swarm, server):
    """Encrypt and send a message to a channel."""

@board.command("watch")
@click.argument("channel")
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def watch(channel, swarm, server):
    """Watch a channel for the next message after the persisted cursor."""

@board.command("ack")
@click.argument("channel")
@click.argument("position", type=int)
def ack(channel, position):
    """Advance the persisted cursor for a channel."""

@board.command("channels")
@click.option("--swarm", required=True, help="Swarm ID")
@click.option("--server", default="ws://localhost:8787", help="Server URL")
def channels(swarm, server):
    """List channels in a swarm."""
```

### Step 6: Register the board command group

Add the import and registration in `src/cli/__init__.py`:
```python
from cli.board import board
cli.add_command(board)
```

Location: `src/cli/__init__.py`

### Step 7: End-to-end integration test

**Test** in `tests/test_board_e2e.py`:

Write an end-to-end test that exercises the full send→watch→ack cycle
without network by using a mock WebSocket server (or by mocking at the
`websockets.connect` level with a pair of in-memory queues).

Test scenario:
1. Create a swarm (generate keys, mock registration)
2. Send a message to channel "test-channel"
3. Watch channel "test-channel" from cursor 0
4. Verify decrypted message matches original plaintext
5. Ack position 1
6. Verify cursor file contains position 1
7. Watch again from cursor 1 (blocks — verify watch is issued with
   updated cursor after ack)

This test validates that crypto, storage, client, and CLI compose
correctly.

### Step 8: Verify and clean up

- Run full test suite: `uv run pytest tests/`
- Run `uv run ve board --help` to verify command registration
- Verify all success criteria from GOAL.md are covered by tests

## Dependencies

- **leader_board_spec** (ACTIVE) — SPEC.md §Leader Board defines the wire
  protocol, crypto scheme, storage model, and all behavioral rules this CLI
  implements. This chunk is the authoritative reference.
- **PyNaCl ≥ 1.5.0** — libsodium bindings for Ed25519, Curve25519 conversion,
  XChaCha20-Poly1305, and CSPRNG. Must be added to pyproject.toml.
- **websockets ≥ 12.0** — WebSocket client library. Must be added to
  pyproject.toml.

## Risks and Open Questions

- **No server to test against yet**: The `leader_board_core` and
  `leader_board_local_server` chunks are FUTURE. The CLI must be tested
  against mocks. The wire protocol compliance will be validated when those
  chunks land. This is acceptable because the CLI depends only on the spec,
  not on the server implementation.
- **PyNaCl's Curve25519 conversion API**: The spec requires
  `crypto_sign_ed25519_sk_to_curve25519`. PyNaCl exposes this via
  `nacl.bindings` — verify the exact function name at implementation time.
- **asyncio in Click**: Click commands are synchronous. The WebSocket client
  is async. Use `asyncio.run()` to bridge. This is standard practice but may
  need care around event loop lifecycle on Windows.
- **Base58 encoding**: The spec uses base58 for swarm IDs. PyNaCl doesn't
  include base58. Options: use `base58` package, or implement the small
  encoder inline. Prefer adding `base58` as a dependency for correctness.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->