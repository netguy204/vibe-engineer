---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/daemon.py
- tests/test_daemon.py
code_references:
  - ref: src/orchestrator/daemon.py#_cleanup_state_files
    implements: "Helper function to remove all daemon state files (PID, socket, port) with graceful handling of missing files"
  - ref: src/orchestrator/daemon.py#stop_daemon
    implements: "Updated to call _cleanup_state_files after daemon termination (SIGTERM, SIGKILL, or stale PID)"
  - ref: src/orchestrator/daemon.py#_write_pid_file
    implements: "Added documentation explaining intentional fd leak to maintain flock for daemon lifetime"
  - ref: tests/test_daemon.py#TestCleanupStateFiles
    implements: "Unit tests for _cleanup_state_files helper function"
  - ref: tests/test_daemon.py#TestStopDaemonCleansAllFiles
    implements: "Integration tests verifying stop_daemon cleans all state files in all shutdown scenarios"
narrative: arch_consolidation
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- orch_api_retry
---

# Chunk Goal

## Minor Goal

Fix stale state file cleanup when the orchestrator daemon is stopped. Currently, when `stop_daemon()` falls back to SIGKILL (line 721), only the PID file is cleaned up (lines 700, 715, 731), but socket and port files are left behind. While atexit handlers (lines 438-440) clean these files on graceful shutdown, SIGKILL bypasses atexit handlers entirely, leaving stale files on disk.

This creates two problems:
1. Stale socket files can prevent subsequent daemon starts if not cleaned up
2. Stale port files can cause confusion about whether the daemon is running

Additionally, the PID file fd is intentionally leaked after writing (line 266-286) to maintain the flock for the daemon's lifetime, but this is undocumented and may confuse future maintainers.

This chunk ensures all state files are cleaned up regardless of shutdown method and documents the intentional fd leak pattern.

## Success Criteria

1. `stop_daemon()` cleans up socket and port files in addition to PID file, even when using SIGKILL fallback (after line 731)
2. The cleanup handles missing files gracefully (no errors if files already removed)
3. The intentional PID file fd leak in `_write_pid_file()` is documented with a comment explaining why the fd is not closed (maintains flock for daemon lifetime)
4. Tests verify that all state files (PID, socket, port) are removed after daemon shutdown, including SIGKILL scenarios
5. No functional behavior changes - graceful shutdown via atexit handlers still works as before


