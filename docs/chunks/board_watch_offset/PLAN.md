
<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a `--offset <N>` Click option to both `watch_cmd` and `watch_multi_cmd` in `src/cli/board.py`. When provided, the offset value replaces the cursor loaded from `load_cursor()` for that invocation only. The persisted cursor file is never written or modified by `--offset` — cursor persistence remains exclusively the responsibility of `ve board ack` (for `watch`) and `save_cursor` after auto-ack (for `watch-multi`).

This is a purely CLI-layer change. The board client (`BoardClient.watch`, `BoardClient.watch_multi`) already accepts cursor positions as integer arguments — no changes needed in `src/board/client.py` or `src/board/storage.py`.

For `watch-multi`, `--offset` applies uniformly to all channels (overriding each channel's persisted cursor with the same value). Per-channel offsets are out of scope.

Tests follow the existing pattern in `tests/test_board_cli.py`: mock the board client and verify that the correct cursor value is passed through to the client methods.

## Sequence

### Step 1: Write failing tests for `watch --offset`

Add two tests to `tests/test_board_cli.py`:

1. **`test_watch_with_offset_overrides_cursor`** — Invoke `watch` with `--offset 5`. Patch `load_cursor` to return 0. Assert that `client.watch_with_reconnect` (or `client.watch`) is called with cursor=5, not cursor=0. This verifies the offset overrides the persisted cursor.

2. **`test_watch_with_offset_does_not_modify_cursor`** — Invoke `watch` with `--offset 5` against a project root with a cursor file set to 0. After the command completes, assert `load_cursor` still returns 0. This verifies the offset is ephemeral.

Follow the existing test pattern: use `runner.invoke`, `patch("cli.board.load_keypair")`, `patch("cli.board.BoardClient")`, etc. Use `stored_swarm` fixture for encryption setup.

Location: `tests/test_board_cli.py`

### Step 2: Write failing tests for `watch-multi --offset`

Add two tests:

1. **`test_watch_multi_with_offset_overrides_cursors`** — Invoke `watch-multi ch1 ch2 --offset 3`. Patch `load_cursor` to return different values per channel. Assert that `client.watch_multi` (or `watch_multi_with_reconnect`) receives `{"ch1": 3, "ch2": 3}` as the channel_cursors dict.

2. **`test_watch_multi_with_offset_does_not_prevent_auto_ack`** — Invoke `watch-multi ch1 --offset 0` (without `--no-auto-ack`). Assert that `save_cursor` is still called for received messages. This verifies offset only affects the starting position, not the auto-ack behavior.

Location: `tests/test_board_cli.py`

### Step 3: Add `--offset` option to `watch_cmd`

In `src/cli/board.py`, add a Click option to the `watch` command:

```python
@click.option("--offset", type=int, default=None, help="Start reading from this position instead of the persisted cursor")
```

Update the function signature to accept `offset: int | None`. After `load_cursor()`, if `offset is not None`, replace the cursor value:

```python
cursor = load_cursor(channel, project_root)
if offset is not None:
    cursor = offset
```

Add a backreference comment: `# Chunk: docs/chunks/board_watch_offset - Ephemeral offset override for watch`

Location: `src/cli/board.py`, `watch_cmd` function

### Step 4: Add `--offset` option to `watch_multi_cmd`

Add the same Click option to the `watch-multi` command. After building `channel_cursors`, if `offset is not None`, override all values:

```python
channel_cursors = {}
for ch in channels:
    channel_cursors[ch] = load_cursor(ch, project_root)

if offset is not None:
    channel_cursors = {ch: offset for ch in channels}
```

Add a backreference comment: `# Chunk: docs/chunks/board_watch_offset - Ephemeral offset override for watch-multi`

Location: `src/cli/board.py`, `watch_multi_cmd` function

### Step 5: Run tests and verify

Run `uv run pytest tests/test_board_cli.py -x` to verify all new tests pass and no existing tests regress.

## Risks and Open Questions

- **Negative offsets**: The wire protocol uses uint64 positions starting at 1, with 0 as the "before first message" sentinel. Negative values would be invalid. Click's `type=int` allows negatives, but the server would reject them. For simplicity, we do not add client-side validation — the server's error response is sufficient. If this becomes a friction point, validation can be added later.

- **watch-multi per-channel offsets**: The goal states `--offset` applies "per-channel or globally" for `watch-multi`. This plan implements global-only (same offset for all channels). Per-channel syntax (e.g., `--offset ch1=5 --offset ch2=3`) adds complexity without a clear use case. Global is sufficient for the debugging/replay scenarios described in the goal.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->