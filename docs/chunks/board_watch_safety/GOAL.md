---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/storage.py
- src/cli/board.py
- src/templates/commands/steward-watch.md.jinja2
- tests/test_board_storage.py
- tests/test_board_cli.py
code_references:
- ref: src/board/storage.py#watch_pid_path
  implements: "Returns PID file path for a channel watch process"
- ref: src/board/storage.py#read_watch_pid
  implements: "Reads PID from watch PID file, returns None if missing or unparseable"
- ref: src/board/storage.py#write_watch_pid
  implements: "Writes current process PID to watch PID file"
- ref: src/board/storage.py#remove_watch_pid
  implements: "Removes watch PID file on exit, no-op if already gone"
- ref: src/cli/board.py#watch_cmd
  implements: "Kill-previous-watch logic and PID lifecycle in single-channel watch"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "Kill-previous-watch logic and PID lifecycle in multi-channel watch"
- ref: src/templates/commands/steward-watch.md.jinja2
  implements: "Watch Safety SOP guidance on ack discipline, multi-channel patterns, and timeout cleanup"
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

Add safety guards to `ve board watch` to prevent zombie watch processes and duplicate watchers on the same channel.

When a Claude Code background task times out (exit 144), the task wrapper is killed but the underlying `ve board watch` OS process may keep running and reconnecting. Starting a new watch then creates two competing consumers on the same channel, leading to missed or double-processed messages.

Changes:
1. **Auto-kill previous watch on same channel**: When `ve board watch <channel>` starts, it should check for and kill any existing `ve board watch` process on the same channel before beginning. This can use a PID file at `{board_root}/cursors/{channel}.watch.pid` or process table scanning.
2. **Steward SOP updates**: Add guidance to the steward-watch command template covering:
   - Never ack before reading — ack is "I processed this", not "clear the queue"
   - Multi-channel watch requires separate background tasks, restart each independently
   - Watch timeout does not kill the OS process — always clean up before restarting

This was reported by the Database Savings Plans Steward after encountering all three failure modes during a multi-cycle steward workflow.

## Success Criteria

- `ve board watch <channel>` kills any existing watch on the same channel before starting
- A PID file or equivalent mechanism tracks the active watch process per channel
- Steward-watch command template includes guidance on ack discipline and multi-channel patterns
- Tests verify that starting a second watch on the same channel terminates the first


