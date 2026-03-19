---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/board.py
- tests/test_board_cli.py
code_references:
- ref: src/cli/board.py#watch_cmd
  implements: "Ephemeral --offset option that overrides persisted cursor for single-channel watch"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "Ephemeral --offset option that overrides all per-channel persisted cursors for multi-channel watch"
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

Add an optional `--offset <N>` argument to `ve board watch` (and `ve board watch-multi`) that overrides the persisted cursor position for that watch session. This lets operators replay old messages or skip ahead without modifying the durable cursor file.

The offset is ephemeral — it affects only the current watch invocation. The persisted cursor is not updated until `ve board ack` is called as usual. This is useful for debugging, re-processing missed messages, or inspecting message history.

Example usage:
```
ve board watch my-channel --offset 5    # start reading from position 5
ve board watch my-channel --offset 0    # replay from the beginning
```

## Success Criteria

- `ve board watch <channel> --offset <N>` starts reading from position N instead of the persisted cursor
- `ve board watch-multi` also accepts `--offset` with the same behavior (applied per-channel or globally)
- The persisted cursor file is NOT modified by `--offset` — only `ve board ack` advances it
- Omitting `--offset` preserves current behavior (read from persisted cursor)
- Tests verify watch with explicit offset delivers the correct message

