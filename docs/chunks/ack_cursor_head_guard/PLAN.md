
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a head-position guard to `ack_cmd` in `src/cli/board.py`. Validation lives
entirely in the CLI layer, keeping `ack_and_advance()` and `save_cursor()` in
`src/board/storage.py` as pure local functions (no server dependency).

The guard works as follows:
1. `ack_cmd` gains optional `--swarm` and `--server` flags (mirroring `send`,
   `watch`, `channels`).
2. It tries to resolve the swarm from config or flags. If no swarm can be
   resolved (no config, no flags), the guard is silently skipped and existing
   behavior is preserved (backward-compatible).
3. When a swarm is available: open a short-lived `BoardClient` connection, call
   `list_channels()`, look up `head_position` for the target channel (absent
   channel → treat as head = 0).
4. Guard: if `new_position > head`, print a warning to stderr and return without
   saving. Exit code stays 0 (not an error in the error-handling sense; it's a
   no-op with a message).
5. If the server cannot be reached (connection error), warn on stderr and fall
   back to saving — this prevents a transient outage from breaking the workflow.

Following TESTING_PHILOSOPHY.md we write failing tests first, then implement.

## Subsystem Considerations

No subsystem documentation exists for the board CLI / cursor management pattern.
The relevant chunks (`ack_auto_increment`, `board_cursor_root_resolution`) are
all ACTIVE implementation chunks. No subsystem changes required.

## Sequence

### Step 1: Write failing tests for the head guard

In `tests/test_board_cli.py`, add a new section:

```
# ---------------------------------------------------------------------------
# ack head guard tests
# Chunk: docs/chunks/ack_cursor_head_guard - Prevent ack past channel head
# ---------------------------------------------------------------------------
```

Write four tests (all should fail before Step 2):

**test_ack_head_guard_normal_advance** — cursor < head, ack succeeds.
- Set up a mock `BoardClient.list_channels` returning `[{"name": "ch",
  "head_position": 5, "oldest_position": 1}]`.
- Cursor at 3, ack without position.
- Assert exit_code == 0, cursor advanced to 4, no warning in output.

**test_ack_head_guard_at_head_rejected** — cursor is already at head.
- Mock: head_position = 5. Cursor at 5.
- `ve board ack ch` (no position).
- Assert exit_code == 0, cursor unchanged at 5, stderr contains "ack rejected"
  and mentions head position.

**test_ack_head_guard_explicit_position_beyond_head_rejected** — explicit
position > head.
- Mock: head_position = 3. No cursor file (starts at 0).
- `ve board ack ch 10`.
- Assert exit_code == 0, cursor unchanged at 0, stderr contains "ack rejected".

**test_ack_head_guard_no_swarm_skips_guard** — no swarm config, guard skipped.
- Patch `resolve_swarm` to return None.
- Cursor at 0, `ve board ack ch` (no position).
- Assert exit_code == 0, cursor advances to 1 (guard not applied).

All four tests need `--swarm` / `--server` (or mock via `load_board_config` /
`resolve_swarm`) and a `BoardClient` mock following the existing patterns in
the file.

### Step 2: Add `--swarm` and `--server` options to `ack_cmd`

In `src/cli/board.py`, modify the `ack_cmd` decorator:

```python
@board.command("ack")
@click.argument("channel")
@click.argument("position", type=int, required=False, default=None)
@click.option("--project-root", ...)
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
# Chunk: docs/chunks/ack_cursor_head_guard - Head guard options
def ack_cmd(channel, position, project_root, swarm, server):
```

Update the function signature accordingly. No behavioral change yet.

### Step 3: Implement the head guard in `ack_cmd`

Replace the body of `ack_cmd` with the guarded version:

```python
# Resolve project root (existing logic unchanged)
if project_root is not None and not project_root.exists():
    raise click.BadParameter(...)
project_root = resolve_board_root(project_root)

# --- HEAD GUARD ---
# Chunk: docs/chunks/ack_cursor_head_guard - Prevent ack past channel head
config = load_board_config()
resolved_swarm = resolve_swarm(config, swarm)
if resolved_swarm is not None:
    resolved_server = resolve_server(config, resolved_swarm, server)
    keypair = load_keypair(resolved_swarm)
    if keypair is not None:
        seed, _pub = keypair
        head = _fetch_channel_head(resolved_server, resolved_swarm, seed, channel)
        if head is not None:
            current = load_cursor(channel, project_root)
            new_pos = (position if position is not None else current + 1)
            if new_pos > head:
                click.echo(
                    f"ack rejected: cursor {current} is already at or past "
                    f"channel head {head}",
                    err=True,
                )
                return

# --- SAVE (original logic) ---
if position is not None:
    click.echo("Warning: ...", err=True)
    save_cursor(channel, position, project_root)
    click.echo(f"Cursor for '{channel}' advanced to {position}")
else:
    new_position = ack_and_advance(channel, project_root)
    click.echo(f"Cursor for '{channel}' advanced to {new_position}")
```

Extract the server query into a small private helper `_fetch_channel_head()`:

```python
def _fetch_channel_head(server: str, swarm_id: str, seed: bytes, channel: str) -> int | None:
    """Return head_position for channel, or None if unreachable.

    Returns 0 if the channel doesn't appear in the list (no messages sent yet).
    # Chunk: docs/chunks/ack_cursor_head_guard - Head guard server query
    """
    import asyncio
    from board.client import BoardClient, _RETRYABLE_ERRORS

    async def _query():
        client = BoardClient(server, swarm_id, seed)
        await client.connect()
        try:
            channels = await client.list_channels()
        finally:
            await client.close()
        for ch in channels:
            if ch["name"] == channel:
                return ch["head_position"]
        return 0  # channel not found → no messages, head = 0

    try:
        return asyncio.run(_query())
    except Exception:
        click.echo(
            f"Warning: could not verify channel head (server unreachable); "
            f"ack guard skipped.",
            err=True,
        )
        return None  # Caller skips guard when None
```

Place this helper just above `ack_cmd` in the file.

### Step 4: Run the tests to verify

```
uv run pytest tests/test_board_cli.py -k "ack_head_guard" -v
```

All four new tests should pass. Then run the full suite:

```
uv run pytest tests/test_board_cli.py -v
```

Existing ack tests (`test_ack_command`, `test_ack_auto_increment`,
`test_ack_auto_increment_from_zero`, `test_ack_with_position_deprecation_warning`)
must continue to pass. Because those tests don't pass `--swarm` and don't mock
`load_board_config`, `resolve_swarm` will return None → guard skipped → old
behavior preserved.

### Step 5: Add backreference comment to `ack_and_advance`

Add a note to `ack_and_advance` in `src/board/storage.py` pointing to this
chunk for context:

```python
# Chunk: docs/chunks/ack_cursor_head_guard - Head guard lives in CLI layer (ack_cmd);
#   this function stays pure-local intentionally.
def ack_and_advance(...):
```

### Step 6: Update code_paths in GOAL.md

Ensure `docs/chunks/ack_cursor_head_guard/GOAL.md` `code_paths` includes:
- `src/board/storage.py`
- `src/cli/board.py`
- `tests/test_board_cli.py`

(These are already listed, so verify only.)

## Dependencies

- `BoardClient.list_channels()` and `head_position` field — already implemented
  and used by `channels_cmd`. No new server-side changes needed.

## Risks and Open Questions

- **Channel not in list**: Treated as head = 0. Any ack attempt beyond position 0
  will be rejected. This is conservative and correct — if no messages have been
  sent, no ack is valid.

- **Server unreachable during ack**: Guard skipped with stderr warning. This
  prevents a network hiccup from blocking acknowledgment in cases where the
  guard isn't strictly needed. Acceptable trade-off per GOAL.md spirit.

- **`asyncio.run()` nesting**: `_fetch_channel_head` uses `asyncio.run()`. This
  will fail if called from within an already-running event loop. Current `ack_cmd`
  is synchronous so this is safe — same pattern used by `send_cmd`, `channels_cmd`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
