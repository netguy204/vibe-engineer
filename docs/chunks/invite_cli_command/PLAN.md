

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add `ve board invite` and `ve board revoke` commands to the existing `src/cli/board.py` module, following the established Click command patterns used by `send`, `watch`, `channels`, etc.

**Key design choices:**

1. **Token-as-encryption-key scheme.** Per the investigation (`docs/investigations/agent_invite_links`), the CLI generates a random token, uses it to derive a symmetric key via HKDF, encrypts the swarm's private seed, and uploads the encrypted blob indexed by `sha256(token)`. The server never sees the plaintext key. This reuses the existing `_hkdf_sha256` primitive from `src/board/crypto.py` but with a new derivation function that takes arbitrary bytes (not an Ed25519 seed).

2. **New `derive_token_key` function in crypto.py.** The existing `derive_symmetric_key` is tightly coupled to Ed25519 seed → Curve25519 conversion. The invite flow needs a simpler path: `random_token_bytes → HKDF-SHA256 → 32-byte key`. A new function avoids conflating the two derivation contexts.

3. **HTTP via `httpx`.** The invite/revoke commands communicate with the gateway key storage routes (PUT/GET/DELETE on `/gateway/keys`) via plain HTTP. The `httpx` library is already a project dependency (used by the orchestrator). Server URLs in `board.toml` use `ws://`/`wss://` scheme; we convert to `http://`/`https://` for these requests.

4. **Opt-in warning with confirmation.** Before creating an invite, the CLI displays a warning explaining that the cleartext gateway trades E2E encryption for agent accessibility, and requires explicit confirmation (or `--yes` to bypass).

5. **TDD per TESTING_PHILOSOPHY.md.** Tests are written first in `tests/test_board_invite.py` using Click's `CliRunner` and mocked HTTP responses. The round-trip test (invite → retrieve blob → decrypt → revoke → 404) verifies the core success criteria.

## Subsystem Considerations

No existing subsystems are relevant. This chunk operates within the board CLI and crypto layers, which have no corresponding subsystem documentation.

## Sequence

### Step 1: Write failing tests for invite and revoke commands

Create `tests/test_board_invite.py` with tests covering:

1. **`ve board invite --swarm <id>` happy path** — Mock `httpx.request` to return 200, verify:
   - Output contains an invite URL with a token
   - The mocked PUT was called with a JSON body containing `token_hash` and `encrypted_blob`
   - The `token_hash` is the SHA-256 of the token extracted from the URL
   - The `encrypted_blob` can be decrypted using the token to recover the original seed
2. **Opt-in warning is displayed** — Verify the warning text appears and that answering "n" aborts without uploading
3. **`--yes` flag bypasses confirmation** — Verify no prompt, upload proceeds
4. **Missing swarm errors** — No `--swarm` and no default, or keypair not found
5. **Upload failure** — Mock `httpx.request` returning 500, verify error message
6. **`ve board revoke <token>` happy path** — Mock DELETE returning 200, verify success message
7. **`ve board revoke` when token not found** — Mock DELETE returning 404, verify error message
8. **Round-trip test** — Invite produces a token; use that token to derive `token_hash` and decrypt the `encrypted_blob` captured from the mock; then revoke

Test patterns follow the existing `test_board_cli.py`:
- Use `CliRunner` with `runner.invoke(board, [...])`
- Use `@patch` to mock `load_keypair`, `load_board_config`, and `httpx.request`
- Use the `stored_swarm` fixture pattern for keypair setup

Location: `tests/test_board_invite.py`

### Step 2: Add `derive_token_key` to crypto.py

Add a new function that derives a 32-byte symmetric key from arbitrary token bytes:

```python
def derive_token_key(token: bytes) -> bytes:
    """Derive a 32-byte symmetric key from a random invite token.

    Uses HKDF-SHA256 with a distinct info string to prevent
    key confusion with derive_symmetric_key (which derives from
    Ed25519 seeds for message encryption).
    """
    return _hkdf_sha256(
        ikm=token,
        length=32,
        salt=b"",
        info=b"leader-board-invite-token",
    )
```

The distinct `info` parameter (`"leader-board-invite-token"` vs `"leader-board-message-encryption"`) ensures domain separation — even if the same bytes were used as both an Ed25519 seed and a token, the derived keys would differ.

Add a `# Chunk: docs/chunks/invite_cli_command` backreference on the function.

Location: `src/board/crypto.py`

### Step 3: Add a `gateway_http_url` helper to config.py

Add a utility function that converts a WebSocket server URL to its HTTP equivalent:

```python
def gateway_http_url(server_url: str) -> str:
    """Convert a ws:// or wss:// server URL to http:// or https://."""
    return server_url.replace("wss://", "https://").replace("ws://", "http://")
```

This is needed because `board.toml` stores `ws://`/`wss://` URLs for WebSocket connections, but the gateway key storage API uses plain HTTP.

Add a `# Chunk: docs/chunks/invite_cli_command` backreference.

Location: `src/board/config.py`

### Step 4: Implement the `invite` command

Add to `src/cli/board.py`:

```python
@board.command("invite")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def invite_cmd(swarm, server, yes):
    """Generate an invite link for agent access to a swarm."""
```

Implementation flow:

1. Resolve swarm and server from config (same pattern as `send_cmd`)
2. Load keypair; error if not found
3. Display the opt-in warning explaining the cleartext gateway security trade-off
4. If not `--yes`, prompt for confirmation via `click.confirm()`; abort if declined
5. Generate a 32-byte random token: `token = secrets.token_bytes(32)`
6. Derive symmetric key: `sym_key = derive_token_key(token)`
7. Encrypt the seed: `encrypted_blob = encrypt(seed.hex(), sym_key)` (encode seed as hex string for encrypt/decrypt round-trip)
8. Compute token hash: `token_hash = hashlib.sha256(token).hexdigest()`
9. Convert server URL to HTTP: `http_url = gateway_http_url(server)`
10. PUT to `{http_url}/gateway/keys?swarm={swarm_id}` with JSON `{"token_hash": token_hash, "encrypted_blob": encrypted_blob}`
11. Check response status; error on non-200
12. Output the invite URL: `{http_url}/invite/{token.hex()}`

Add `import hashlib`, `import secrets`, `import httpx` to the imports section.

Add a `# Chunk: docs/chunks/invite_cli_command` backreference on the function.

Location: `src/cli/board.py`

### Step 5: Implement the `revoke` command

Add to `src/cli/board.py`:

```python
@board.command("revoke")
@click.argument("token")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
def revoke_cmd(token, swarm, server):
    """Revoke an invite token, immediately invalidating access."""
```

Implementation flow:

1. Resolve swarm and server from config (swarm needed to route the request to the correct DO)
2. Convert token hex string to bytes: `token_bytes = bytes.fromhex(token)`
3. Compute hash: `token_hash = hashlib.sha256(token_bytes).hexdigest()`
4. Convert server URL to HTTP: `http_url = gateway_http_url(server)`
5. DELETE `{http_url}/gateway/keys/{token_hash}?swarm={swarm_id}`
6. If 200: print confirmation
7. If 404: print error that the token was not found or already revoked
8. Otherwise: print server error

Add a `# Chunk: docs/chunks/invite_cli_command` backreference on the function.

Location: `src/cli/board.py`

### Step 6: Run tests and verify all pass

Run `uv run pytest tests/test_board_invite.py -v` to confirm all new tests pass. Then run `uv run pytest tests/test_board_cli.py -v` to confirm existing board CLI tests remain green.

### Step 7: Run the full test suite

Run `uv run pytest tests/` to verify no regressions across the entire project.

## Dependencies

- **`gateway_token_storage` chunk (ACTIVE)** — Provides the PUT/GET/DELETE `/gateway/keys` routes on the leader-board Durable Object worker. This chunk's CLI is the client for those routes.
- **`httpx`** — Already a project dependency (used by `src/orchestrator/client.py`). Used for HTTP requests to the gateway.
- **`secrets`** — Python stdlib. Used for cryptographically strong token generation.
- **`hashlib`** — Python stdlib. Used for SHA-256 hashing of tokens.

## Risks and Open Questions

- **Server URL scheme conversion.** The `board.toml` stores `ws://`/`wss://` URLs. The simple string replacement (`ws://` → `http://`) works for standard URLs but could break for edge cases (e.g., a URL containing "ws://" in a path segment). This is acceptable for now since server URLs are always base URLs.
- **Token length.** Using 32 bytes (256 bits) of randomness for the token. This is well above the minimum for preventing brute-force attacks (the hash lookup would need to match SHA-256 of a 256-bit random value). The hex representation is 64 characters, which is long but manageable in URLs.
- **Seed encoding.** The seed (32 bytes) is encoded as a hex string before encryption because the existing `encrypt()` function takes a string. On the decryption side (the cleartext gateway chunk), the flow will be: `decrypt(blob, key)` → hex string → `bytes.fromhex()` → seed. This encoding is deterministic and lossless.
- **No auth on gateway key routes.** As noted in the `gateway_token_storage` plan, the storage routes have no authentication yet. Anyone who knows a swarm ID could DELETE gateway keys. This is deferred — the invite URL itself is the security boundary.

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