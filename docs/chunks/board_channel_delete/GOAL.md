---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/storage.ts
- workers/leader-board/src/protocol.ts
- workers/leader-board/src/swarm-do.ts
- src/board/client.py
- src/cli/board.py
- workers/leader-board/test/swarm-do.test.ts
- tests/test_board_cli.py
code_references:
- ref: workers/leader-board/src/storage.ts#SwarmStorage::deleteChannel
  implements: "Delete all messages for a channel from SQLite storage"
- ref: workers/leader-board/src/protocol.ts#DeleteChannelFrame
  implements: "Wire protocol frame for client channel deletion request"
- ref: workers/leader-board/src/protocol.ts#ChannelDeletedFrame
  implements: "Wire protocol frame for server channel deletion response"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleDeleteChannel
  implements: "Channel deletion handler: storage cleanup, watcher notification, pending poll cleanup"
- ref: src/board/client.py#BoardClient::delete_channel
  implements: "Python client method to delete a channel via WebSocket protocol"
- ref: src/cli/board.py#channel_delete_cmd
  implements: "CLI command with confirmation prompt and error handling"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_cursor_root_resolution
---

# Chunk Goal

## Minor Goal

Channels can be deleted from a swarm, both in the Durable Object backend and via the `ve board` CLI.

Channels are implicitly created when a message is first sent to them. Typos and experiments produce stale channels that pollute the channel list, confusing future consumers (stewards, monitors, operators running `ve board channels`). Channel deletion provides a way to remove them.

**Backend (SwarmDO):**
- A `DELETE /channels/{channel}` endpoint exists on the gateway/swarm API
- Deleting a channel removes all its messages and cursor state from storage
- The endpoint returns 404 if the channel doesn't exist, 200 on success

**CLI:**
- `ve board channel-delete <channel> [--swarm <id>]` deletes a channel
- The command requires confirmation or a `--yes` flag to prevent accidental deletion
- Success/failure is reported to stdout

## Success Criteria

- `DELETE /channels/{channel}` endpoint exists on the SwarmDO API
- Endpoint removes all messages and cursor data for the channel from Durable Object storage
- Endpoint returns 404 for non-existent channels, 200 on success
- `ve board channel-delete <channel>` CLI command works end-to-end
- CLI requires confirmation or `--yes` flag
- Deleted channels no longer appear in channel listings
- Tests cover: successful deletion, 404 on missing channel, channel no longer listed after deletion

