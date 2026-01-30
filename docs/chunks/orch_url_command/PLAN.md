<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The `ve orch url` command will be a simple CLI command that reads the port file (`.ve/orchestrator.port`) and prints the HTTP URL. This follows the existing pattern of thin CLI wrappers (soft convention from the orchestrator subsystem).

**Key Implementation Points:**

1. **Read from port file**: The orchestrator daemon already writes its TCP port to `.ve/orchestrator.port` via `get_port_path()` in `src/orchestrator/daemon.py`. This is the same source used by `start_daemon()` to report the port to the parent process.

2. **Pattern matching**: Follow the same structure as `ve orch status` - a simple command that reads local state and formats output. Unlike `ve orch ps` which needs to communicate with the running daemon, `ve orch url` only needs the port file.

3. **Error handling**: If the daemon is not running or the port file doesn't exist, provide a helpful error message directing users to `ve orch start`.

4. **Output format**: Print just the URL for easy scripting (e.g., `http://localhost:8080`), matching the format shown in `start`'s output. Support `--json` flag for consistency with other commands.

**Testing Strategy (per TESTING_PHILOSOPHY.md):**

- Test the happy path: port file exists, URL is printed
- Test error case: port file doesn't exist (daemon not running)
- Test JSON output format
- Test with custom host (stored in port file or derived from default)

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a new CLI command following the subsystem's patterns. Per the soft convention, "CLI commands are thin wrappers around HTTP calls" - however, `ve orch url` is an exception since it reads local state (port file) rather than calling the daemon. This is appropriate because:
  1. The port file is specifically designed for this purpose (communicating the port)
  2. Reading local state doesn't require the daemon to be running to tell you its URL
  3. Matches the pattern of `ve orch status` which also reads local state

## Sequence

### Step 1: Write failing tests for ve orch url command

Create tests in `tests/test_orchestrator_cli.py` that define the expected behavior:

1. `test_url_prints_url_when_running` - When port file exists, prints `http://<host>:<port>`
2. `test_url_error_when_not_running` - When port file doesn't exist, exits with error and helpful message
3. `test_url_json_output` - When `--json` flag provided, outputs `{"url": "http://..."}`

Tests will mock `get_port_path` and `is_daemon_running` to control behavior.

Location: `tests/test_orchestrator_cli.py`

### Step 2: Add helper function to read daemon URL

Add a `get_daemon_url()` function in `src/orchestrator/daemon.py` that:
1. Reads the port from the port file
2. Returns the full URL string (e.g., `http://127.0.0.1:8080`)
3. Returns `None` if port file doesn't exist

This function follows the pattern of `get_daemon_status()` - reading local state files.

Location: `src/orchestrator/daemon.py`

### Step 3: Implement ve orch url CLI command

Add the `url` command to the `orch` group in `src/ve.py`:

```python
@orch.command("url")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def orch_url(json_output, project_dir):
    """Print the orchestrator dashboard URL."""
    ...
```

The command will:
1. Check if daemon is running using `is_daemon_running()`
2. Read port using `get_daemon_url()` or `get_port_path()` + read
3. Print URL or JSON output
4. Exit with error if daemon not running

Location: `src/ve.py`

### Step 4: Verify tests pass and command works

Run the tests to confirm implementation is correct:
```bash
uv run pytest tests/test_orchestrator_cli.py -k "test_url" -v
```

Manual verification:
```bash
uv run ve orch start  # Start daemon
uv run ve orch url    # Should print URL
uv run ve orch url --json  # Should print JSON
uv run ve orch stop   # Stop daemon
uv run ve orch url    # Should show error
```

---

**BACKREFERENCE COMMENTS**

Add chunk backreference to the new CLI command:
```python
# Chunk: docs/chunks/orch_url_command - URL command for orchestrator
```

## Dependencies

- **orch_tcp_port (ACTIVE)**: This chunk established the port file mechanism (`get_port_path()`) and the dual-listener architecture. The URL command depends on this existing infrastructure.

## Risks and Open Questions

1. **Host binding ambiguity**: The port file only stores the port number, not the host. The daemon can be started with `--host 0.0.0.0` but we currently have no way to know this from the port file. For now, we'll default to `127.0.0.1` which is the daemon's default. If users need to access from a different host, they can use `--json` and construct the URL themselves.

   **Resolution**: Accept this limitation for V1. Could extend the port file format to include host in the future if needed (e.g., store `host:port` instead of just `port`).

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->