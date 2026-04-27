---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/board.py
- src/board/storage.py
- tests/test_board_cli.py
- tests/test_board_storage.py
code_references:
- ref: src/board/storage.py#collect_board_files
  implements: "Discovers board.toml and swarm key material for SCP transfer"
- ref: src/cli/board.py#scp_cmd
  implements: "CLI command that SCPs board config and keys to a remote host"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- leader_board_hibernate_watch
- readme_orch_steward_docs
---

# Chunk Goal

## Minor Goal

The `ve board scp <host>` command copies the user's board configuration and swarm key material to a remote host via SCP, letting users spread their board setup across multiple machines without manually locating and copying files.

The command copies:
- `~/.ve/board.toml` (board server configuration)
- Swarm key material (encryption keys used for channel communication)

The target destination mirrors the source layout under `~/.ve/` on the remote host.

## Success Criteria

- `ve board scp <host>` copies `board.toml` and key material to `<host>:~/.ve/`
- Command fails gracefully with a clear error if `~/.ve/board.toml` doesn't exist
- Command fails gracefully if SSH/SCP to the host fails
- Existing files on the remote are overwritten (user is syncing their config)
- Tests cover the command's argument parsing and file discovery logic