

# Implementation Plan

## Approach

Add channel deletion across the full stack: storage → WebSocket protocol → SwarmDO handler → Python client → CLI command → tests.

The pattern follows existing operations like `channels` and `send`: define a new frame type in the protocol, add a storage method, wire up the handler in SwarmDO, expose it via `BoardClient`, and surface it through a `ve board channel-delete` CLI command.

Channel deletion removes **all messages** for a channel. Since channels are implicit (they exist by virtue of having messages), deleting all messages effectively removes the channel. The storage method will also need to clean up any in-memory watchers for the deleted channel.

Tests follow docs/trunk/TESTING_PHILOSOPHY.md: goal-driven tests tied to success criteria, semantic assertions over structural, and focus on boundary conditions (missing channel, empty channel, active watchers).

## Sequence

### Step 1: Add `deleteChannel()` to SwarmStorage

Location: `workers/leader-board/src/storage.ts`

Add a new method to `SwarmStorage`:

```typescript
deleteChannel(channel: string): number
```

- Execute `DELETE FROM messages WHERE channel = ?`
- Return the count of deleted rows (use before/after COUNT pattern like `compact()`)
- If count is 0, the caller can infer the channel didn't exist

This mirrors the deletion pattern already used in `compact()` but without the time/position guards — it deletes everything for the channel unconditionally.

### Step 2: Add `DeleteChannelFrame` to the wire protocol

Location: `workers/leader-board/src/protocol.ts`

1. Add a new client frame interface:
   ```typescript
   export interface DeleteChannelFrame {
     type: "delete_channel";
     channel: string;
     swarm: string;
   }
   ```

2. Add a new server response frame:
   ```typescript
   export interface ChannelDeletedFrame {
     type: "channel_deleted";
     channel: string;
   }
   ```

3. Add `DeleteChannelFrame` to the `PostAuthClientFrame` union type
4. Add `ChannelDeletedFrame` to the `ServerFrame` union type
5. Add a `"delete_channel"` case to `parsePostAuthFrame()` that validates the channel name and extracts the swarm field

### Step 3: Add `handleDeleteChannel()` to SwarmDO

Location: `workers/leader-board/src/swarm-do.ts`

1. Add a `"delete_channel"` case to the `handlePostAuth()` switch statement
2. Implement `handleDeleteChannel(ws, frame)`:
   - Call `this.storage.deleteChannel(frame.channel)`
   - If 0 rows deleted, send an error frame with code `"channel_not_found"`
   - If rows deleted, send a `channel_deleted` response frame
   - Clean up in-memory watchers: remove the channel's entry from `this.watchers` Map and close/notify any active watchers on that channel (send them an error frame with code `"channel_deleted"` so they know to stop)

### Step 4: Add `delete_channel()` to Python BoardClient

Location: `src/board/client.py`

Add an async method:

```python
async def delete_channel(self, channel: str) -> None:
```

- Send a `{"type": "delete_channel", "channel": channel, "swarm": self.swarm_id}` frame
- Await the response
- If response type is `"channel_deleted"`, return successfully
- If response type is `"error"` with code `"channel_not_found"`, raise `BoardError("channel_not_found", ...)`
- If unexpected response, raise `BoardError("protocol_error", ...)`

### Step 5: Add `ve board channel-delete` CLI command

Location: `src/cli/board.py`

Add a new Click command following the pattern of `channels_cmd`:

```python
@board.command("channel-delete")
@click.argument("channel")
@click.option("--swarm", default=None, help="Swarm ID")
@click.option("--server", default=None, help="Server URL")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def channel_delete_cmd(channel, swarm, server, yes):
    """Delete a channel and all its messages."""
```

Behavior:
- Resolve swarm/server/keypair using existing helpers (`load_board_config`, `resolve_swarm`, `load_keypair`)
- Unless `--yes` is provided, prompt with `click.confirm(f"Delete channel '{channel}' and all its messages?", abort=True)`
- Create a `BoardClient`, connect, call `delete_channel(channel)`
- On success: `click.echo(f"Deleted channel '{channel}'")`
- On `BoardError` with `channel_not_found`: print error message and `sys.exit(1)`
- Always close the client in a finally block

### Step 6: Write backend tests

Location: `workers/leader-board/test/swarm-do.test.ts`

Add tests covering:

1. **Successful deletion**: Send messages to a channel, send `delete_channel` frame, verify `channel_deleted` response. Then send `channels` frame and verify the deleted channel is absent from the list.
2. **404 on non-existent channel**: Send `delete_channel` for a channel that has never received messages, verify error response with code `channel_not_found`.
3. **Channel no longer listed after deletion**: Send messages to two channels, delete one, list channels, verify only the surviving channel appears.
4. **Watchers notified on deletion** (if feasible in test harness): Set up a watcher on a channel, delete the channel, verify the watcher receives an error notification.

### Step 7: Write CLI tests

Location: `tests/test_board_cli.py`

Add tests covering:

1. **Successful delete with --yes**: Mock `BoardClient.delete_channel`, invoke with `--yes`, verify exit code 0 and success message.
2. **Confirmation prompt (abort)**: Invoke without `--yes`, provide "n" input, verify `delete_channel` was not called.
3. **Channel not found**: Mock `BoardClient.delete_channel` to raise `BoardError("channel_not_found", ...)`, verify non-zero exit and error message.

Follow existing test patterns: use `runner.invoke()`, mock `BoardClient` and config helpers.

### Step 8: Update GOAL.md code_paths

Update `docs/chunks/board_channel_delete/GOAL.md` frontmatter `code_paths` with all files touched:

- `workers/leader-board/src/storage.ts`
- `workers/leader-board/src/protocol.ts`
- `workers/leader-board/src/swarm-do.ts`
- `src/board/client.py`
- `src/cli/board.py`
- `workers/leader-board/test/swarm-do.test.ts`
- `tests/test_board_cli.py`

## Risks and Open Questions

- **Active watchers during deletion**: When a channel is deleted while watchers are active, those watchers need to be notified cleanly. The plan sends them an error frame — but if watchers are hibernated (DO Hibernation API), we need to ensure they're woken and cleaned up. The `webSocketClose` handler on hibernated sockets should handle this gracefully, but verify during implementation.
- **Gateway HTTP API**: The goal mentions `DELETE /channels/{channel}` as a REST endpoint, but the existing pattern for channel operations is WebSocket-only (the gateway HTTP API is token-authenticated and scoped to individual channels). The WebSocket approach is more consistent with the existing architecture. If REST is needed later, it can be added as a gateway route. This plan implements channel deletion via the WebSocket protocol only.
- **Race condition**: A message sent to a channel concurrently with deletion could recreate the channel. This is acceptable — the delete is a best-effort cleanup tool, not a permanent ban on the channel name.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
