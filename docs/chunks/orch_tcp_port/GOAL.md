---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/ve.py
- src/orchestrator/daemon.py
- tests/test_orchestrator_daemon.py
code_references:
  - ref: src/ve.py#start
    implements: "CLI command with --port and --host options for ve orch start"
  - ref: src/orchestrator/daemon.py#find_available_port
    implements: "Port 0 binding technique to find available TCP port"
  - ref: src/orchestrator/daemon.py#get_port_path
    implements: "Path helper for port file used in parent-child communication"
  - ref: src/orchestrator/daemon.py#start_daemon
    implements: "Daemon startup with port/host parameters and port file synchronization"
  - ref: src/orchestrator/daemon.py#_run_daemon_async
    implements: "Dual-listener architecture running Unix socket and TCP server concurrently"
  - ref: tests/test_orchestrator_daemon.py#TestFindAvailablePort
    implements: "Unit tests for port discovery helper function"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
friction_entries: []
created_after:
- orch_dashboard
---

# Chunk Goal

## Minor Goal

Add TCP port support to the orchestrator daemon so the web dashboard can be accessed directly from a browser without needing a reverse proxy like `socat`.

Currently the daemon only listens on a Unix socket (`.ve/orchestrator/orchestrator.sock`), which browsers cannot connect to directly. This chunk enables browser access by:

1. Adding a `--port` flag to `ve orch start` to specify a TCP port
2. When no port is specified, automatically selecting an available port and printing it to stdout
3. Maintaining the Unix socket for CLI client communication (backward compatible)

This is a direct follow-up to `orch_dashboard` which explicitly noted this limitation in its PLAN.md: "The daemon uses a Unix socket by default. For dashboard access via browser, operators will need to configure HTTP on a TCP port."

## Success Criteria

1. **`--port` flag accepted by `ve orch start`**
   - `ve orch start --port 8080` starts daemon listening on TCP port 8080 in addition to the Unix socket
   - Invalid port numbers are rejected with a clear error message

2. **`--host` flag for binding address**
   - `ve orch start --host 0.0.0.0` binds to all interfaces
   - Defaults to `127.0.0.1` for security (localhost only)

3. **Auto-selection when no port specified**
   - `ve orch start` (without `--port`) automatically finds an available port
   - The selected port is printed to stdout in a clear format (e.g., `Dashboard available at http://127.0.0.1:8080/`)
   - Uses port 0 binding technique to let the OS select an available port

4. **Dashboard accessible via browser**
   - After `ve orch start`, navigating to `http://localhost:<port>/` shows the dashboard
   - WebSocket connection at `ws://localhost:<port>/ws` works for real-time updates

5. **Unix socket remains functional**
   - CLI commands (`ve orch ps`, `ve orch status`, etc.) continue to work via Unix socket
   - Both TCP and Unix socket can be used simultaneously

6. **Tests pass**
   - Unit tests for port selection logic
   - Integration tests verifying TCP endpoint serves the dashboard