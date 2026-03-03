<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix involves two related but distinct issues in `src/orchestrator/daemon.py`:

1. **Stale file cleanup on SIGKILL fallback**: When `stop_daemon()` uses SIGKILL (line 721), only the PID file is cleaned up but the socket and port files are left behind. The atexit handlers (lines 438-440) only run on graceful shutdown — SIGKILL bypasses them entirely.

2. **Undocumented fd leak pattern**: The `_write_pid_file()` function intentionally leaves the file descriptor open (lines 266-286) to maintain an flock for the daemon's lifetime. This is a deliberate pattern but is undocumented and may confuse maintainers.

**Strategy:**

- Extract a helper function `_cleanup_state_files(project_dir)` that removes all three state files (PID, socket, port) with graceful handling of missing files
- Call this helper from `stop_daemon()` after successful termination (whether via SIGTERM or SIGKILL)
- Add a docstring to `_write_pid_file()` explaining the intentional fd leak
- Write tests that verify all state files are cleaned up after both graceful and forced shutdown

This is a pure correctness fix with no behavioral changes to graceful shutdown — atexit handlers still work as before.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS part of the daemon lifecycle management. The orchestrator subsystem governs daemon start/stop/status operations, and this fix ensures proper cleanup of state files. No deviations from subsystem patterns expected — this follows the existing `_remove_pid_file()` pattern and extends it to cover socket and port files.

## Sequence

### Step 1: Write failing tests for stale file cleanup

Create tests in `tests/test_daemon.py` (new file) that verify:

1. **Test `_cleanup_state_files` removes all files**: Create mock PID, socket, and port files, call cleanup, assert all are removed
2. **Test `_cleanup_state_files` handles missing files gracefully**: Call cleanup when some files don't exist, assert no exceptions
3. **Test `stop_daemon` cleans up all state files after SIGTERM**: Mock process termination, verify socket and port files are removed alongside PID file
4. **Test `stop_daemon` cleans up all state files after SIGKILL fallback**: Mock a process that ignores SIGTERM and requires SIGKILL, verify all files cleaned up

These tests must fail initially since `_cleanup_state_files` doesn't exist and `stop_daemon` doesn't clean up socket/port files.

Location: `tests/test_daemon.py`

### Step 2: Extract `_cleanup_state_files` helper

Create a new private function that removes all three state files:

```python
# Chunk: docs/chunks/orch_daemon_stale_files - Stale file cleanup on SIGKILL fallback
def _cleanup_state_files(project_dir: Path) -> None:
    """Remove all daemon state files (PID, socket, port).

    Called after daemon shutdown to clean up state files.
    Handles missing files gracefully - no error if files don't exist.

    Args:
        project_dir: The project directory (resolved to absolute path)
    """
    for get_path in (get_pid_path, get_socket_path, get_port_path):
        path = get_path(project_dir)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
```

Location: `src/orchestrator/daemon.py` (after `_remove_pid_file` function, around line 306)

### Step 3: Update `stop_daemon` to clean up all state files

Modify `stop_daemon()` to call `_cleanup_state_files()` instead of `_remove_pid_file()` after successful shutdown.

Current code at line 700, 715, 731:
```python
_remove_pid_file(pid_path)
```

Change to:
```python
_cleanup_state_files(project_dir)
```

The three locations in `stop_daemon` are:
- Line 700: Stale PID file cleanup (process not running)
- Line 715: After graceful SIGTERM shutdown
- Line 731: After SIGKILL fallback

All three should clean up all state files, not just the PID file.

Location: `src/orchestrator/daemon.py` lines 700, 715, 731

### Step 4: Document the intentional fd leak in `_write_pid_file`

Add a comment explaining why the file descriptor is intentionally not closed:

The current code at lines 283-286:
```python
        # Write new PID
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, f"{pid}\n".encode())
```

Add after this block (before the `except BlockingIOError` at line 288):
```python
        # NOTE: fd is intentionally NOT closed here.
        # The open file descriptor maintains the flock for the daemon's lifetime.
        # When the daemon process exits, the fd is closed by the OS and the lock
        # is released automatically. This prevents race conditions where another
        # instance could acquire the lock between close() and process exit.
```

Location: `src/orchestrator/daemon.py` around line 287

### Step 5: Add backreference to module header

Add a chunk backreference to the module header for this chunk:

Current header (lines 1-6):
```python
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_foundation - Daemon lifecycle, state persistence, and work unit tracking
# Chunk: docs/chunks/orch_scheduling - Async daemon runner with scheduler integration
# Chunk: docs/chunks/orch_tcp_port - TCP port support for browser dashboard access
# Chunk: docs/chunks/orch_url_command - URL command for getting orchestrator endpoint
# Chunk: docs/chunks/orch_task_detection - Task context detection for daemon startup
```

Add after line 6:
```python
# Chunk: docs/chunks/orch_daemon_stale_files - Stale file cleanup on SIGKILL fallback
```

Location: `src/orchestrator/daemon.py` line 7

### Step 6: Run tests and verify

Run the new tests to verify:
1. All new tests pass
2. Existing orchestrator tests still pass
3. Manual verification: start daemon, stop with SIGKILL, verify no stale files remain

## Dependencies

None. This chunk fixes existing code and requires no new dependencies or prior chunks.

## Risks and Open Questions

1. **Race condition on cleanup**: If another process is checking for the daemon via `is_daemon_running()` while cleanup is in progress, it may see inconsistent state (PID file exists but socket doesn't). This is low risk because:
   - The daemon is already dead when cleanup runs
   - `is_daemon_running()` checks process existence, not file existence
   - Existing code already has this race with PID-only cleanup

2. **Socket file may be in use by stale daemon**: If a daemon didn't exit cleanly (e.g., crash) and its socket file is still bound, the file can't be unlinked on some systems. However, `start_daemon()` already handles this case at lines 386-389 by cleaning up stale socket/port files before starting.

3. **Testing SIGKILL scenarios**: Testing the SIGKILL path requires mocking process signals, which can be tricky. The test will mock `os.kill` and `is_process_running` to simulate the SIGKILL fallback path without actually killing processes.

## Deviations

*To be populated during implementation.*