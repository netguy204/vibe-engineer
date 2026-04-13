---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/board/storage.py
- src/cli/board.py
- tests/test_board_cli.py
code_references:
- ref: src/cli/board.py#_fetch_channel_head
  implements: "Private helper that queries the server for a channel's current head position"
- ref: src/cli/board.py#ack_cmd
  implements: "Head guard logic that rejects ack when new_position > channel head"
- ref: src/board/storage.py#ack_and_advance
  implements: "Remains pure-local by design; head guard intentionally lives in CLI layer"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- board_watch_reconnect_fix
---

# Chunk Goal

## Minor Goal

Prevent `ve board ack` from advancing the cursor beyond the channel's current
head position. An extraneous ack (fired when no message was actually received)
silently moves the cursor past the head, causing the next `ve board watch` to
block indefinitely waiting for a message at a position that doesn't exist yet.
This has caused missed messages in production steward sessions at least twice.

### What needs to change

In `ack_and_advance()` (`src/board/storage.py:242`), before saving the new
cursor position:

1. **Query the channel head** — use `BoardClient.list_channels()` to get the
   current head for the channel.
2. **Guard the advance** — if `new_position > head`, refuse to advance. Print
   a warning: `"ack rejected: cursor {current} is already at or past channel
   head {head}"` and return the current position unchanged.
3. **Also guard explicit position** — in the CLI `ack_cmd`
   (`src/cli/board.py:423`), when a position is explicitly passed, validate
   it against the channel head before saving.

### Design consideration

`ack_and_advance` is currently a pure local function (reads/writes cursor
files). Adding a server query makes it async and requires a `BoardClient`
connection. The cleanest approach is to add validation in the CLI layer
(`ack_cmd`) before calling the storage function, keeping storage functions
pure. The CLI already has access to the server connection context.

## Success Criteria

- `ve board ack <channel>` when cursor is already at head prints a warning
  and does not advance
- `ve board ack <channel> <position>` with position > head prints a warning
  and does not save
- Existing ack behavior unchanged when cursor < head (normal case)
- Tests cover: normal ack, ack-at-head rejection, explicit position beyond
  head rejection
