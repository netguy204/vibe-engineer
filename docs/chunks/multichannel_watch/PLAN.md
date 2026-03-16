

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The existing wire protocol already supports multi-channel watch on a single
connection. Both the Python local server (`server.py`) and the Cloudflare DO
(`swarm-do.ts`) handle concurrent `WatchFrame` messages per WebSocket — each
watch frame spawns a separate blocking task (Python) or registers a separate
per-channel watcher (DO). The `MessageFrame` already tags responses with the
`channel` field, so no new frame types are needed.

The strategy is:

1. **Fix the DO hibernation limitation**: `WsAttachment.watching` currently
   stores a single `{channel, cursor}`. Change it to an array so multiple
   pending watches survive hibernation. This is the only server-side change.

2. **Add `watch_multi()` to `BoardClient`**: Send N watch frames (one per
   channel), then enter a receive loop that yields messages as they arrive
   from any channel. After receiving a message, re-send the watch frame for
   that channel with the updated cursor to continue watching.

3. **Add `ve board watch-multi` CLI command**: Accept multiple channels,
   resolve per-channel cursors, and stream decrypted messages tagged with
   channel names. This is a long-running command (blocks until Ctrl-C).

4. **Update the swarm-monitor template**: Replace N background `ve board watch`
   invocations with a single `ve board watch-multi` invocation.

No new protocol frames are required. The multi-channel behavior is achieved
entirely through the existing protocol's support for concurrent watch frames
on a single authenticated connection (per DEC-001, the CLI remains the entry
point; per DEC-005, no git operations are prescribed).

Testing follows TDD per `docs/trunk/TESTING_PHILOSOPHY.md`:
- Unit tests for `watch_multi()` client method
- CLI integration tests for `ve board watch-multi`
- Unit tests for the DO hibernation attachment change
- Existing single-channel `watch` tests must continue to pass

## Subsystem Considerations

No subsystems in `docs/subsystems/` are directly relevant to this chunk.
The leader board is not yet documented as a subsystem. The template system
subsystem is tangentially touched (swarm-monitor template update) but this
chunk USES it, not implements it.

## Sequence

### Step 1: Fix DO hibernation attachment for multi-channel watches

The `WsAttachment` interface in `workers/leader-board/src/swarm-do.ts`
currently stores `watching?: { channel: string; cursor: number }` (singular).
When multiple watch frames are sent on one connection, only the last one's
state is persisted for hibernation recovery.

Changes:
- Change `WsAttachment.watching` from a single object to an array:
  `watching?: Array<{ channel: string; cursor: number }>`
- Update `handleWatch()` to append to the array instead of overwriting
- Update `wakeWatchers()` hibernation recovery path to iterate the array
  and deliver messages for any matching channel, removing entries as they
  are delivered
- Update `removeWatcher()` to clear the full array
- Update the `webSocketMessage()` hibernation recovery in the auth flow to
  restore all watch entries, not just one

Location: `workers/leader-board/src/swarm-do.ts`

### Step 2: Add tests for DO multi-watch hibernation

Add test cases in `workers/leader-board/test/e2e.test.ts` that:
- Send two watch frames on one connection for different channels
- Send a message to each channel on a separate connection
- Verify that both messages are received on the original connection
- Verify that the message frames are tagged with the correct channel

Location: `workers/leader-board/test/e2e.test.ts`

### Step 3: Add `watch_multi()` to BoardClient

Add an async generator method to `src/board/client.py`:

```python
async def watch_multi(
    self,
    channels: dict[str, int],  # {channel_name: cursor}
) -> AsyncGenerator[dict, None]:
    """Watch multiple channels on a single connection.

    Sends a watch frame for each channel, then yields messages as they
    arrive from any channel. After yielding a message, automatically
    re-sends the watch frame for that channel with cursor = message.position.

    Yields dicts with keys: channel, position, body, sent_at.
    """
```

Implementation:
- Send one `WatchFrame` per channel (reuse existing frame format)
- Enter a receive loop: `await self._ws.recv()`
- On each message, yield it and re-send the watch frame for that channel
  with `cursor=message.position` so it blocks for the next message
- Handle errors per-channel (e.g., `channel_not_found` for one channel
  shouldn't kill the whole watch)

Also add `watch_multi_with_reconnect()` that wraps `watch_multi()` with
reconnect logic similar to `watch_with_reconnect()`. On reconnect, re-send
all watch frames with their latest known cursors.

Location: `src/board/client.py`

### Step 4: Add unit tests for `watch_multi()`

Write tests in `tests/test_board_client.py`:
- `test_watch_multi_sends_frames_and_yields_messages`: Mock WebSocket that
  returns messages from two channels; verify both are yielded with correct
  channel tags
- `test_watch_multi_resends_watch_after_message`: Verify that after yielding
  a message for channel A, the client re-sends a watch frame for channel A
  with the updated cursor
- `test_watch_multi_handles_per_channel_error`: One channel returns
  `channel_not_found`; the other continues watching
- `test_watch_multi_reconnect`: Simulate disconnect; verify all channels
  are re-watched with latest cursors after reconnect

Location: `tests/test_board_client.py`

### Step 5: Add `ve board watch-multi` CLI command

Add a new Click command in `src/cli/board.py`:

```python
@board.command("watch-multi")
@click.argument("channels", nargs=-1, required=True)
@click.option("--swarm", default=None)
@click.option("--server", default=None)
@click.option("--project-root", type=click.Path(...), default=".")
@click.option("--no-reconnect", is_flag=True)
def watch_multi_cmd(channels, swarm, server, project_root, no_reconnect):
    """Watch multiple channels on a single connection.

    Blocks and prints messages from any subscribed channel.
    Output format: [channel-name] message text
    """
```

Implementation:
- Resolve swarm config (same pattern as `watch_cmd`)
- Read per-channel cursors from `.ve/board/cursors/<channel>.cursor`
- Call `client.watch_multi()` (or `watch_multi_with_reconnect()`)
- For each yielded message: decrypt, print as `[channel] plaintext`,
  and advance the cursor file via `ve board ack` logic (or inline cursor
  write)
- Run until Ctrl-C (KeyboardInterrupt)

The existing `ve board watch` command remains unchanged — it continues to
watch a single channel and exit after one message.

Location: `src/cli/board.py`

### Step 6: Add CLI integration tests for `watch-multi`

Write tests in `tests/test_board_cli.py`:
- `test_watch_multi_command_output_format`: Verify output includes channel
  prefix `[channel-name]` for each message
- `test_watch_multi_advances_cursors`: Verify that after receiving messages,
  cursor files are updated for each channel independently
- `test_watch_multi_single_connection`: Verify that only one `BoardClient`
  connection is created (not N)

Use the same mocking patterns as existing `test_watch_command` tests.

Location: `tests/test_board_cli.py`

### Step 7: Update local Python server for concurrent watch cleanup

Review `src/leader_board/server.py` to confirm no changes are needed. The
server already spawns separate `asyncio.Task` per `WatchFrame` and the
`MessageFrame` includes the `channel` field, so multi-watch already works.

Verify by running existing server tests with a multi-watch scenario:
- Send two watch frames on one connection
- Append a message to each channel
- Confirm both messages are delivered on the same connection

If the existing test infrastructure doesn't cover this, add a test in
`tests/test_leader_board_server.py`.

Location: `src/leader_board/server.py`, `tests/test_leader_board_server.py`

### Step 8: Update swarm-monitor template

Update `src/templates/commands/swarm-monitor.md.jinja2` Phase 3 and Phase 4:

**Phase 3 (revised)**: Instead of launching N background `ve board watch`
commands, instruct the agent to run a single `ve board watch-multi` command
with all changelog channels. Use `run_in_background` for this single command.

**Phase 4 (revised)**: The `watch-multi` command outputs tagged messages
inline. The agent reads the background task output and acks each message.
Since `watch-multi` is long-running, the agent periodically checks the
background task output rather than waiting for completion.

Note: The swarm-monitor slash command is a Jinja2 template that renders
into `.claude/commands/swarm-monitor.md`. After editing the template, run
`ve init` to re-render.

Location: `src/templates/commands/swarm-monitor.md.jinja2`

### Step 9: Re-render templates and run full test suite

1. Run `uv run ve init` to re-render the swarm-monitor template
2. Run `uv run pytest tests/` to confirm all existing tests pass
3. Run the TypeScript tests for the CF worker:
   `cd workers/leader-board && npm test`
4. Verify that `ve board watch` (single channel) still works unchanged

## Dependencies

- `websocket_reconnect_tuning` chunk (ACTIVE) — provides the reconnect and
  backoff patterns that `watch_multi_with_reconnect()` will mirror
- `leader_board_hibernate_watch` chunk (ACTIVE) — provides the hibernation
  attachment pattern being extended

No new external libraries are required.

## Risks and Open Questions

- **DO hibernation array size**: If a client watches many channels (50+),
  the serialized attachment array could grow large. Cloudflare attachment
  size limit is 2KB. Mitigation: document a reasonable upper bound (e.g.,
  32 channels) and return an error frame if exceeded.

- **Message ordering across channels**: `watch_multi` yields messages in
  the order they arrive on the WebSocket. This is not guaranteed to be
  chronological across channels (channel A position 5 may arrive before
  channel B position 3). This is acceptable — the channel tag lets the
  consumer reason about per-channel ordering.

- **Cursor auto-advance in watch-multi**: The GOAL says existing
  `ve board watch` doesn't auto-advance cursors. For `watch-multi`,
  auto-advancing may be more ergonomic since the user won't want to
  manually ack each message in a multi-channel stream. Decision: auto-advance
  cursors in `watch-multi` (this is a different command with different UX
  expectations). If this feels like a significant architectural decision,
  it can be escalated to the operator.

- **CF Worker fan-out across DOs**: The GOAL mentions that channels may live
  on different DOs (keyed by swarm). However, all channels within a swarm
  are on the same DO (the DO is keyed by swarm ID, not by channel). So
  multi-channel watch within a single swarm requires no worker-level fan-out.
  Cross-swarm multi-channel watch is out of scope for this chunk.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
