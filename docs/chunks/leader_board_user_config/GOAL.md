---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/board/config.py
- src/cli/board.py
- pyproject.toml
- tests/test_board_config.py
- tests/test_board_cli.py
code_references:
- ref: src/board/config.py#BoardConfig
  implements: "Board config dataclass holding default_swarm and per-swarm server bindings"
- ref: src/board/config.py#SwarmConfig
  implements: "Per-swarm config entry storing server_url"
- ref: src/board/config.py#load_board_config
  implements: "Reads ~/.ve/board.toml and returns BoardConfig, empty config if absent"
- ref: src/board/config.py#save_board_config
  implements: "Atomic write of BoardConfig to ~/.ve/board.toml"
- ref: src/board/config.py#add_swarm
  implements: "Adds swarm entry and sets default_swarm if first swarm"
- ref: src/board/config.py#resolve_swarm
  implements: "Resolves swarm ID: explicit flag → default_swarm → None"
- ref: src/board/config.py#resolve_server
  implements: "Resolves server URL: explicit flag → swarm config → ws://localhost:8374"
- ref: src/cli/board.py#bind_cmd
  implements: "ve board bind command for updating swarm server binding or default swarm"
- ref: src/cli/board.py#swarm_create
  implements: "Updated to write new swarm entry to board.toml after registration"
- ref: src/cli/board.py#send_cmd
  implements: "Updated to resolve --swarm and --server from board.toml config"
- ref: src/cli/board.py#watch_cmd
  implements: "Updated to resolve --swarm and --server from board.toml config"
- ref: src/cli/board.py#channels_cmd
  implements: "Updated to resolve --swarm and --server from board.toml config"
narrative: leader_board
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- leader_board_cli
- leader_board_local_server
created_after:
- leader_board_cli
- leader_board_core
- leader_board_local_server
- leader_board_spec
- leader_board_steward_skills
---
# Chunk Goal

## Minor Goal

A user-global config file at `~/.ve/board.toml` stores the operator's
default swarm and per-swarm server bindings. All `ve board` client commands
(`send`, `watch`, `ack`, `channels`, `swarm create`) read these defaults
instead of hardcoding a server URL. The `ve board bind` command binds a
swarm to a server URL — this is how an operator points a swarm at the
hosted Durable Objects coordination server (or back to localhost for
development).

Client commands resolve `--server` from the swarm's bound server in
`board.toml` and resolve `--swarm` from `board.toml`'s `default_swarm` when
flags are not provided. Explicit `--server` and `--swarm` flags override
the config values.

### Config structure

```toml
default_swarm = "abc123..."

[swarms.abc123]
server_url = "wss://board.example.com"

[swarms.def456]
server_url = "ws://localhost:8374"
```

Each swarm created via `ve board swarm create` gets an entry under `[swarms]`
recording the server it was registered against. The key storage in
`~/.ve/keys/` remains unchanged — `board.toml` adds the server binding and
default swarm, not a second copy of keys.

## Success Criteria

- `~/.ve/board.toml` is created/updated by `ve board swarm create` — the new
  swarm is added under `[swarms]` with its `server_url`, and `default_swarm`
  is set if this is the first swarm (or no default is set yet)
- `ve board bind <swarm> <url>` updates the `server_url` for an existing swarm
  (e.g., to migrate from local to hosted)
- `ve board bind --default <swarm>` sets the `default_swarm` without changing
  the server URL
- All existing client commands (`send`, `watch`, `ack`, `channels`) resolve
  `--server` from the swarm's config entry and `--swarm` from `default_swarm`
  when flags are not provided
- Explicit `--server` and `--swarm` flags override config values
- When no config exists and no flags are provided, commands fall back to
  `ws://localhost:8374` (current default) and require `--swarm`
- `ve board start` (local server) is unaffected — it binds based on its own
  `--host`/`--port` flags, not the client config