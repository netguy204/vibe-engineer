

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Extend the invite system across two layers:

1. **Server-side (Cloudflare DO):** Add a `listGatewayKeys()` storage method and a `deleteAllGatewayKeys()` method to `SwarmStorage`. Wire them into the existing `handleGatewayKeys` handler in `SwarmDO` — a `GET /gateway/keys` (no `token_hash` in path) returns all keys, and `DELETE /gateway/keys` (no `token_hash` in path) deletes all keys.

2. **CLI-side (Python):** Add `ve board invite list` and modify `ve board invite revoke` to support `--all`. The `invite` command becomes a Click group with two subcommands (`list` and the existing `create` flow). The existing `ve board revoke` continues to work for single-token revocation, and gains `--all` for bulk.

**Key design choices:**

- **Reuse existing gateway key HTTP routes.** The `handleGatewayKeys` handler in `swarm-do.ts` already dispatches on method + path structure. We add `GET /gateway/keys` (no token hash → list all) alongside the existing `GET /gateway/keys/{token_hash}` (retrieve one). Similarly, `DELETE /gateway/keys` (no token hash, with a query param like `?all=true`) deletes all keys. This keeps the route structure consistent.

- **Token hint for identification.** The list endpoint returns `token_hash`, `created_at`, and the first 8 characters of the token hash as a display hint. The server never stores the plaintext token, so the hash prefix is the best identifier available.

- **`invite` becomes a Click group.** Currently `invite` is a flat command. We restructure it so `ve board invite` is a group containing `create` (the existing flow) and `list`. This is a minor breaking change — the operator now types `ve board invite create` instead of `ve board invite`. Alternatively, we can add `invite-list` as a sibling command. Since the goal specifies `ve board invite list`, we'll use the group approach.

- **TDD per TESTING_PHILOSOPHY.md.** Tests are written first for both server-side and CLI changes.

- **Per DEC-001**: All capabilities are CLI-accessible via `ve`. Per DEC-005: No git operations are prescribed.

## Subsystem Considerations

No existing subsystems are relevant. This chunk extends the board CLI and the leader-board DO worker, neither of which has subsystem documentation.

## Sequence

### Step 1: Add `listGatewayKeys` and `deleteAllGatewayKeys` to `SwarmStorage`

Add two new methods to `workers/leader-board/src/storage.ts`:

```typescript
// Chunk: docs/chunks/invite_list_revoke - List all gateway keys
listGatewayKeys(): { token_hash: string; created_at: string }[] {
    this.ensureSchema();
    const rows = [
      ...this.sql.sql.exec(
        `SELECT token_hash, created_at FROM gateway_keys ORDER BY created_at ASC`
      ),
    ];
    return rows.map((row) => ({
      token_hash: row.token_hash as string,
      created_at: row.created_at as string,
    }));
}

// Chunk: docs/chunks/invite_list_revoke - Delete all gateway keys (bulk revocation)
deleteAllGatewayKeys(): number {
    this.ensureSchema();
    const countRows = [
      ...this.sql.sql.exec(`SELECT COUNT(*) as cnt FROM gateway_keys`),
    ];
    const count = countRows[0].cnt as number;
    if (count === 0) return 0;
    this.sql.sql.exec(`DELETE FROM gateway_keys`);
    return count;
}
```

Location: `workers/leader-board/src/storage.ts`

### Step 2: Wire list and bulk-delete into `handleGatewayKeys` in `SwarmDO`

Modify the `handleGatewayKeys` handler in `workers/leader-board/src/swarm-do.ts`:

- **GET without `token_hash` in path** (`GET /gateway/keys`): Call `this.storage.listGatewayKeys()` and return the list as JSON: `{ keys: [{ token_hash, created_at, hint }] }` where `hint` is the first 8 chars of `token_hash`.
- **DELETE without `token_hash` in path** (`DELETE /gateway/keys`): Call `this.storage.deleteAllGatewayKeys()` and return `{ ok: true, deleted: N }`.

The existing GET/DELETE with `token_hash` in the path continue to work unchanged. The dispatch logic uses `tokenHashFromPath` — when it's `null` (or empty string), the request is a list/bulk-delete; when present, it's the single-key operation.

Location: `workers/leader-board/src/swarm-do.ts`

### Step 3: Write server-side tests for list and bulk-delete

Add tests to `workers/leader-board/test/gateway-keys.test.ts`:

1. **List returns empty when no keys exist** — `GET /gateway/keys?swarm=X` returns `{ keys: [] }`
2. **List returns all stored keys** — PUT 3 keys, GET list, verify all 3 returned with `token_hash`, `created_at`, and `hint` fields
3. **List includes correct hint** — Verify `hint` is the first 8 characters of `token_hash`
4. **Bulk delete removes all keys** — PUT 3 keys, `DELETE /gateway/keys?swarm=X`, verify response includes `deleted: 3`, then GET list returns empty
5. **Bulk delete on empty returns zero** — `DELETE /gateway/keys?swarm=X` when no keys exist returns `{ ok: true, deleted: 0 }`

Test patterns follow the existing `gateway-keys.test.ts` style: use `SELF.fetch()` with `cloudflare:test`.

Location: `workers/leader-board/test/gateway-keys.test.ts`

### Step 4: Restructure `invite` from a command to a Click group with `create` and `list` subcommands

In `src/cli/board.py`:

1. Change `@board.command("invite")` to `@board.group()` named `invite`.
2. Move the existing `invite_cmd` function body into a new `@invite.command("create")` subcommand. The `create` subcommand retains all existing options (`--swarm`, `--server`, `--yes`).
3. Add `@invite.command("list")` subcommand:

```python
# Chunk: docs/chunks/invite_list_revoke
@invite.command("list")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
def invite_list_cmd(swarm, server):
    """List all active invite tokens for a swarm."""
    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)

    http_url = gateway_http_url(server)
    response = httpx.get(
        f"{http_url}/gateway/keys",
        params={"swarm": swarm},
    )

    if response.status_code != 200:
        click.echo(f"Error: server returned {response.status_code}", err=True)
        sys.exit(1)

    data = response.json()
    keys = data.get("keys", [])
    if not keys:
        click.echo("No active invite tokens.")
        return

    for key in keys:
        hint = key.get("hint", key["token_hash"][:8])
        created = key.get("created_at", "unknown")
        click.echo(f"{hint}  created={created}")
```

Location: `src/cli/board.py`

### Step 5: Add `--all` flag to the `revoke` command

Modify the existing `revoke_cmd` in `src/cli/board.py`:

1. Add `@click.option("--all", "revoke_all", is_flag=True, help="Revoke all tokens for this swarm")`.
2. Make the `token` argument optional: `@click.argument("token", required=False, default=None)`.
3. When `--all` is set: `DELETE {http_url}/gateway/keys?swarm={swarm_id}` (no token hash in path). Display count of revoked tokens.
4. When `--all` is not set and `token` is provided: existing single-token revoke behavior.
5. When neither: error with usage message.

```python
# Chunk: docs/chunks/invite_list_revoke
@board.command("revoke")
@click.argument("token", required=False, default=None)
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--all", "revoke_all", is_flag=True, help="Revoke all tokens for this swarm")
def revoke_cmd(token, swarm, server, revoke_all):
    """Revoke an invite token, immediately invalidating access."""
    if not revoke_all and token is None:
        click.echo("Error: provide a TOKEN argument or use --all", err=True)
        sys.exit(1)

    config = load_board_config()
    swarm = resolve_swarm(config, swarm)
    if swarm is None:
        click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
        sys.exit(1)
    server = resolve_server(config, swarm, server)
    http_url = gateway_http_url(server)

    if revoke_all:
        response = httpx.delete(
            f"{http_url}/gateway/keys",
            params={"swarm": swarm},
        )
        if response.status_code == 200:
            data = response.json()
            count = data.get("deleted", 0)
            click.echo(f"Revoked {count} invite token(s).")
        else:
            click.echo(f"Error: server returned {response.status_code}", err=True)
            sys.exit(1)
    else:
        # Existing single-token revoke
        token_bytes = bytes.fromhex(token)
        token_hash = hashlib.sha256(token_bytes).hexdigest()
        response = httpx.delete(
            f"{http_url}/gateway/keys/{token_hash}",
            params={"swarm": swarm},
        )
        if response.status_code == 200:
            click.echo("Invite revoked successfully.")
        elif response.status_code == 404:
            click.echo("Error: token not found or already revoked.", err=True)
            sys.exit(1)
        else:
            click.echo(f"Error: server returned {response.status_code}", err=True)
            sys.exit(1)
```

Location: `src/cli/board.py`

### Step 6: Write CLI tests for `invite list` and `revoke --all`

Add tests to `tests/test_board_invite.py`:

**`invite list` tests:**
1. **List with no tokens** — Mock GET returning `{ keys: [] }`, verify "No active invite tokens." output.
2. **List with populated tokens** — Mock GET returning 2 keys, verify each key's hint and creation time appear in output.
3. **List with missing swarm** — No `--swarm` and no default, verify error.
4. **List server error** — Mock GET returning 500, verify error.

**`revoke --all` tests:**
5. **Bulk revoke happy path** — Mock DELETE returning `{ ok: true, deleted: 3 }`, verify "Revoked 3 invite token(s)." output.
6. **Bulk revoke on empty swarm** — Mock DELETE returning `{ ok: true, deleted: 0 }`, verify "Revoked 0 invite token(s)." output.
7. **Bulk revoke server error** — Mock DELETE returning 500, verify error.
8. **Existing single-token revoke still works** — Verify the existing `revoke <token>` path is unchanged.
9. **Revoke with neither token nor --all errors** — Verify usage error.

**`invite create` regression tests:**
10. **Existing invite flow via `invite create`** — Same as the existing happy-path test but invoked as `invite create --swarm ...` instead of `invite --swarm ...`.

Test patterns follow the existing test file: `CliRunner`, `@patch` for `load_board_config`, `load_keypair`, and `httpx` methods.

Location: `tests/test_board_invite.py`

### Step 7: Update existing invite tests for the group restructure

The existing tests in `tests/test_board_invite.py` invoke `["invite", "--swarm", ...]`. After Step 4, these must change to `["invite", "create", "--swarm", ...]`. Update all existing test invocations to use the new subcommand path.

Location: `tests/test_board_invite.py`

### Step 8: Run tests and verify

1. Run `uv run pytest tests/test_board_invite.py -v` to confirm all CLI tests pass.
2. Run `uv run pytest tests/` to confirm no regressions across the project.
3. For server-side tests: `cd workers/leader-board && npx vitest run test/gateway-keys.test.ts` (if the worker test infrastructure is available in the worktree).

Add `# Chunk: docs/chunks/invite_list_revoke` backreference comments on all new functions/methods.

## Dependencies

- **`invite_cli_command` (ACTIVE)** — Parent chunk. Provides the existing `invite` and `revoke` commands, `derive_token_key`, and `gateway_http_url` that this chunk extends.
- **`gateway_token_storage` (ACTIVE)** — Provides the `gateway_keys` table and existing PUT/GET/DELETE routes. This chunk adds list and bulk-delete operations to the same table and routes.
- **`httpx`** — Already a project dependency. Used for new GET (list) and DELETE (bulk revoke) HTTP calls.
- No new dependencies required.

## Risks and Open Questions

- **`invite` group restructure is a breaking change.** Existing `ve board invite --swarm X --yes` invocations will break — they must become `ve board invite create --swarm X --yes`. This affects the `invite_instruction_page` chunk's invite URL output format (the URL itself doesn't change, just the CLI invocation). Mitigating: this is an internal tool with no external consumers yet, and the goal explicitly specifies the group syntax.
- **Route ambiguity between list and single-GET.** `GET /gateway/keys` (list all) vs `GET /gateway/keys/{token_hash}` (get one) are distinguished by whether a path segment follows `/keys`. The current dispatch uses `pathParts.length > 3` to detect a token hash. This logic is preserved — when `tokenHashFromPath` is null/empty, it's a list; otherwise, single-key get.
- **Bulk delete has no confirmation.** The `DELETE /gateway/keys` route (no token hash) deletes all keys. On the CLI side, `--all` provides the confirmation intent, but the server route has no auth. This matches the existing security model where the invite token is the security boundary, not server-side auth (noted in the parent chunk's risks).
- **No pagination for list.** If a swarm has thousands of tokens, the list response could be large. This is unlikely in practice (invite tokens are manually created), and pagination can be added later if needed.

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