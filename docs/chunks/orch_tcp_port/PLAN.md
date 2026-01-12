# Implementation Plan

## Approach

Extend the orchestrator daemon to listen on both a Unix socket (for CLI communication) and a TCP port (for browser dashboard access). The implementation follows a **dual-listener** pattern where uvicorn serves the same Starlette app on two different transports.

**Key design decisions:**

1. **Auto-port by default**: When `--port` is not specified, use port 0 to let the OS assign an available port. This avoids port conflicts and makes the dashboard immediately accessible without configuration.

2. **Dual-listener architecture**: Run two uvicorn server instances concurrently—one on Unix socket for CLI, one on TCP for browsers. The Unix socket remains the primary interface for backward compatibility.

3. **No port persistence**: The port is ephemeral and printed at startup. Users who background the daemon should capture the output or restart to get a new port.

**Testing strategy (per TESTING_PHILOSOPHY.md):**
- Unit tests for the port discovery helper function
- Integration tests using TestClient to verify the TCP endpoint serves HTML
- Test that both listeners work simultaneously

## Sequence

### Step 1: Add `--port` and `--host` CLI options

Add the new flags to the `ve orch start` command in `src/ve.py`. Pass these values through to `start_daemon()`.

- `--port`: Optional integer, defaults to 0 (auto-select)
- `--host`: Optional string, defaults to "127.0.0.1"

Location: `src/ve.py`

### Step 2: Modify `start_daemon()` signature to accept port and host

Update `start_daemon()` to accept `port: int = 0` and `host: str = "127.0.0.1"` parameters. Pass these through to `_run_daemon_async()`.

Location: `src/orchestrator/daemon.py`

### Step 3: Add port discovery helper function

Create a helper function `find_available_port(host: str) -> int` that:
1. Creates a socket, binds to port 0, gets the assigned port
2. Closes the socket and returns the port number

This approach has a small race condition window but is the standard pattern for ephemeral ports.

Location: `src/orchestrator/daemon.py`

### Step 4: Modify `_run_daemon_async()` to run dual listeners

Update `_run_daemon_async()` to:
1. If port is 0, call `find_available_port()` to get an actual port
2. Create a second uvicorn server config for TCP (`host=host`, `port=port`)
3. Run both servers as concurrent tasks
4. Print the dashboard URL to stdout before redirecting to log file

The daemon will now serve:
- Unix socket at `.ve/orchestrator.sock` (for CLI)
- TCP at `host:port` (for browser)

Location: `src/orchestrator/daemon.py`

### Step 5: Print dashboard URL at startup

Before redirecting stdout to the log file in `start_daemon()`, print a message like:
```
Dashboard available at http://127.0.0.1:8080/
```

This must happen in the parent process before it exits, or use a mechanism to communicate the port from child to parent.

**Challenge**: The port discovery happens in the daemon child process, but the message needs to appear in the terminal. Solution: Write the port to a temporary file that the parent reads before exiting.

Location: `src/orchestrator/daemon.py`

### Step 6: Write tests for port discovery

Write a unit test for `find_available_port()` that verifies:
- Returns an integer > 0
- Returned port is actually available (can bind to it)

Location: `tests/test_orchestrator_daemon.py`

### Step 7: Write integration test for TCP endpoint

Create a test that:
1. Starts the daemon with a specific port (not auto-select to avoid race)
2. Verifies the dashboard HTML is served at `http://localhost:port/`
3. Stops the daemon

This may need to be marked as a manual test or use subprocess isolation.

Location: `tests/test_orchestrator_daemon.py`

## Dependencies

**Required chunks (complete):**
- `orch_foundation` - Daemon skeleton
- `orch_dashboard` - Dashboard endpoint at `/`

**External libraries (already present):**
- `uvicorn` - Supports both `uds` and `host/port` configurations
- `starlette` - The API app

No new dependencies required.

## Risks and Open Questions

1. **Port communication race**: The child process determines the port but the parent needs to print it. Using a temp file or pipe adds complexity. Alternative: always print the URL in the daemon log and direct users there.

   **Decision**: Use a synchronization file. The child writes the port to `.ve/orchestrator.port` before starting the server. The parent waits for this file to appear (with timeout) and reads it.

2. **Dual server shutdown**: Both servers need to shut down gracefully on SIGTERM. Need to ensure both `server.should_exit = True` calls happen.

3. **Port in use at startup**: If a specific port is requested and it's in use, uvicorn will fail. The error should be caught and reported clearly.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
