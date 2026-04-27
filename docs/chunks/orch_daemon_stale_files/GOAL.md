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

The orchestrator daemon removes all of its on-disk state files (PID, socket, port) on shutdown, regardless of the path taken to terminate the process. `stop_daemon()` calls `_cleanup_state_files()` after every termination branch — graceful SIGTERM, SIGKILL fallback, and stale-PID handling — so a SIGKILL that bypasses atexit handlers does not leave stale socket or port files behind. Without this, a stale socket file can block subsequent daemon starts and a stale port file can mislead callers about whether the daemon is running.

`_cleanup_state_files()` is tolerant of missing files so it can run as the unconditional last step of shutdown.

The intentional file-descriptor leak in `_write_pid_file()` — keeping the fd open for the daemon's lifetime to preserve the `flock` — is documented inline so the pattern is not mistaken for a leak bug.

## Success Criteria

1. `stop_daemon()` cleans up socket and port files in addition to PID file, even when using SIGKILL fallback (after line 731)
2. The cleanup handles missing files gracefully (no errors if files already removed)
3. The intentional PID file fd leak in `_write_pid_file()` is documented with a comment explaining why the fd is not closed (maintains flock for daemon lifetime)
4. Tests verify that all state files (PID, socket, port) are removed after daemon shutdown, including SIGKILL scenarios
5. No functional behavior changes - graceful shutdown via atexit handlers still works as before


