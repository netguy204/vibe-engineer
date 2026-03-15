

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add a `~/.ve/board.toml` config file that stores per-swarm server bindings and
the operator's default swarm. Introduce a `BoardConfig` dataclass in a new
`src/board/config.py` module with `load` / `save` functions. Wire all existing
`ve board` client commands to resolve `--server` and `--swarm` from this config
when flags are not explicitly provided. Add a `ve board bind` command to update
bindings.

**Key design choices:**

- **TOML format** — The goal specifies `board.toml`. Python ≥3.12 includes
  `tomllib` for reading. For writing, we'll use `tomli_w` (a lightweight,
  well-maintained TOML writer) rather than hand-formatting strings. This avoids
  bugs with quoting and escaping.
- **Config location** — `Path.home() / ".ve" / "board.toml"`, co-located with
  the existing `~/.ve/keys/` directory. The config is operator-global (not
  project-local), matching the swarm ownership model.
- **Resolution order** — Explicit CLI flags → config file → hardcoded fallback
  (`ws://localhost:8374` for server, `None` for swarm). This preserves backward
  compatibility: commands with no config and no flags behave exactly as today.
- **Integration with `swarm create`** — After successful registration and key
  storage, `swarm create` updates `board.toml` to add the new swarm with its
  server URL and sets `default_swarm` if none is set yet. This means the config
  is bootstrapped naturally — no separate setup step.
- **TDD** — Tests are written before implementation per
  docs/trunk/TESTING_PHILOSOPHY.md. Config load/save tests exercise real
  filesystem behavior in tmp directories. CLI tests mock config functions to
  test resolution logic.

No new architectural decisions are needed. This follows existing patterns:
config is a file in `~/.ve/` (like keys), CLI commands use Click options with
defaults, and the resolution logic is straightforward precedence.

## Sequence

### Step 1: Add `tomli_w` dependency

Add `tomli-w>=1.0.0` to `pyproject.toml` dependencies. This is needed for
writing TOML files. Reading uses stdlib `tomllib`.

Location: `pyproject.toml`

### Step 2: Write tests for `BoardConfig` load/save

Write tests in `tests/test_board_config.py` that verify:

- `load_board_config` returns a default (empty) config when no file exists
- `load_board_config` reads a valid TOML file and returns structured data
- `save_board_config` writes a TOML file that round-trips correctly
- `add_swarm` adds a swarm entry with server_url and sets `default_swarm` if
  it's the first swarm
- `add_swarm` does not overwrite `default_swarm` if one is already set
- `set_server_url` updates an existing swarm's server binding
- `set_default_swarm` changes the default swarm
- `set_default_swarm` raises an error for an unknown swarm ID
- `resolve_swarm` returns explicit value if provided, else `default_swarm`,
  else `None`
- `resolve_server` returns explicit value if provided, else the swarm's
  `server_url`, else the fallback `ws://localhost:8374`

These tests should use `tmp_path` to create real TOML files and exercise the
actual parsing/serialization — no mocking of file I/O.

Location: `tests/test_board_config.py`

### Step 3: Implement `BoardConfig` module

Create `src/board/config.py` with:

```python
@dataclass
class SwarmConfig:
    server_url: str

@dataclass
class BoardConfig:
    default_swarm: str | None
    swarms: dict[str, SwarmConfig]
```

Functions:
- `load_board_config(config_path: Path | None = None) -> BoardConfig` — reads
  `~/.ve/board.toml`, returns empty config if file absent
- `save_board_config(config: BoardConfig, config_path: Path | None = None)` —
  writes the TOML file atomically (write to tmp, rename)
- `add_swarm(config: BoardConfig, swarm_id: str, server_url: str) -> BoardConfig`
  — adds swarm entry, sets `default_swarm` if not already set
- `resolve_swarm(config: BoardConfig, explicit: str | None) -> str | None` —
  returns explicit or default_swarm
- `resolve_server(config: BoardConfig, swarm_id: str | None, explicit: str | None) -> str`
  — returns explicit, or swarm's server_url, or `ws://localhost:8374`

The config path defaults to `Path.home() / ".ve" / "board.toml"` but is
injectable for testing.

Add module-level backreference:
`# Chunk: docs/chunks/leader_board_user_config - Board user config and defaults`

Location: `src/board/config.py`

### Step 4: Write tests for `ve board bind` command

Add tests in `tests/test_board_config.py` (or extend `tests/test_board_cli.py`)
for the new CLI command:

- `ve board bind <swarm> <url>` updates the swarm's `server_url` in config
- `ve board bind <swarm> <url>` errors if swarm ID not found in config
- `ve board bind --default <swarm>` sets `default_swarm` without changing
  server URL
- `ve board bind --default <swarm>` errors if swarm ID not found in config

Use Click's `CliRunner` with a patched config path pointing to `tmp_path`.

Location: `tests/test_board_cli.py`

### Step 5: Implement `ve board bind` command

Add a `bind` subcommand to the board group in `src/cli/board.py`:

```
ve board bind <swarm> <url>     — update server URL for a swarm
ve board bind --default <swarm> — set the default swarm
```

The command loads the config, validates the swarm exists, makes the change,
and saves. If neither `<url>` nor `--default` is meaningful, print usage help.

Location: `src/cli/board.py`

### Step 6: Write tests for config-aware option resolution

Add tests that verify existing commands resolve options from config:

- `send` with `--swarm` omitted resolves from `default_swarm` in config
- `send` with `--server` omitted resolves from swarm's config entry
- `send` with explicit `--swarm` and `--server` ignores config
- Same patterns for `watch`, `channels`
- `swarm create` with no config file still works (backward compat)
- `swarm create` updates `board.toml` with the new swarm entry
- Commands with no config and no flags: `--server` falls back to
  `ws://localhost:8374`, `--swarm` is required (error if missing)

Mock `load_board_config` and `save_board_config` in CLI tests to control config
state without touching the filesystem.

Location: `tests/test_board_cli.py`

### Step 7: Wire config resolution into existing CLI commands

Modify `src/cli/board.py`:

1. Change `--swarm` from `required=True` to `required=False, default=None`
   on `send`, `watch`, and `channels` commands.
2. Change `--server` from `default="ws://localhost:8374"` to `default=None`
   on `swarm create`, `send`, `watch`, and `channels` commands.
3. At the top of each command function, load config and resolve:
   ```python
   config = load_board_config()
   swarm = resolve_swarm(config, swarm)
   if swarm is None:
       click.echo("Error: no swarm specified and no default_swarm in ~/.ve/board.toml", err=True)
       sys.exit(1)
   server = resolve_server(config, swarm, server)
   ```
4. Update `swarm_create` to call `add_swarm` after successful registration
   and key storage, then `save_board_config`.

The `start` and `ack` commands are unaffected — `start` uses its own
`--host`/`--port` flags, and `ack` doesn't need server or swarm.

Location: `src/cli/board.py`

### Step 8: Verify all existing tests still pass

Run `uv run pytest tests/test_board_cli.py tests/test_board_config.py` and
fix any regressions. Existing tests that pass explicit `--server` and `--swarm`
flags should continue to work unchanged because explicit flags override config.
Tests that mock `load_keypair` may need to also mock `load_board_config` to
prevent the resolution logic from trying to read a real `~/.ve/board.toml`.

Location: `tests/`

## Dependencies

- **leader_board_cli** (ACTIVE) — Provides the existing `ve board` command
  group and all client subcommands that this chunk modifies.
- **leader_board_local_server** (ACTIVE) — The `ws://localhost:8374` fallback
  default references this server.
- **tomli-w** — New pyproject.toml dependency for TOML writing. No other
  external dependencies needed (`tomllib` is stdlib in Python ≥3.12).

## Risks and Open Questions

- **Atomic writes on Windows** — `os.replace` is atomic on POSIX but has
  caveats on Windows. Since VE targets developer machines (primarily macOS and
  Linux per existing usage), this is acceptable. If Windows support becomes
  important, revisit with `tempfile.NamedTemporaryFile(delete=False)` +
  `os.replace`.
- **Config file corruption** — If the process is killed mid-write, the config
  could be truncated. The write-to-tmp-then-rename pattern in Step 3 mitigates
  this: the rename is atomic, so the file is either the old version or the new
  version, never partial.
- **Multiple swarm create calls** — Two concurrent `swarm create` invocations
  could race on updating `board.toml`. This is unlikely in practice (operator
  runs one at a time) and the worst case is a lost entry that can be recovered
  with `ve board bind`. Not worth adding file locking for.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->