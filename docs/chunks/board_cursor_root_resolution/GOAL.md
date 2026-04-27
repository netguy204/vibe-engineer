---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/storage.py
- src/cli/board.py
- tests/test_board_storage.py
- tests/test_board_cli.py
code_references:
- ref: src/board/storage.py#find_git_root
  implements: "Walk parent directories to find .git root (directory or worktree file)"
- ref: src/board/storage.py#resolve_board_root
  implements: "Priority-chain root resolution: explicit override → .ve-task.yaml → .git → CWD fallback"
- ref: src/cli/board.py#watch_cmd
  implements: "Watch command wired to auto-resolve project root for cursor storage"
- ref: src/cli/board.py#watch_multi_cmd
  implements: "Watch-multi command wired to auto-resolve project root for cursor storage"
- ref: src/cli/board.py#ack_cmd
  implements: "Ack command wired to auto-resolve project root for cursor storage"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- ack_auto_increment
- gateway_webhook_collector
---
# Chunk Goal

## Minor Goal

`ve board ack` (and other cursor-writing commands) automatically resolve the project/task root before writing cursor files, eliminating CWD-relative cursor drift.

Without automatic resolution, ack would write the cursor to a CWD-relative `.ve/board/cursors/` path. When a steward `cd`s into a subdirectory (e.g., to run git/gh commands), ack calls would write the cursor to the wrong location, while the watch command would read from the original root cursor (which never advances) and re-deliver the same message repeatedly.

Root resolution algorithm:
1. Walk parent directories for `.ve-task.yaml` — if found, that directory is the task root
2. Otherwise, walk parent directories for `.git` — that directory is the project root
3. Cursors are written relative to the resolved root, not CWD

The `--project-root` flag remains available as an explicit override. Automatic resolution eliminates this class of bug by default.

## Success Criteria

- `ve board ack <channel>` resolves the project root automatically regardless of CWD
- Cursor files are always written to `{resolved_root}/.ve/board/cursors/`
- Running `cd subdir && ve board ack foo` writes to the same cursor file as `ve board ack foo` from the project root
- Existing `--project-root` flag still works as an explicit override
- Tests verify cursor writes from subdirectories resolve to project root


