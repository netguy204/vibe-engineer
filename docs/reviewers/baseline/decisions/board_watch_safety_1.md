---
decision: APPROVE
summary: "All success criteria satisfied — PID-based zombie watch prevention implemented with clean storage helpers, CLI integration for both watch and watch-multi, template SOP guidance, and comprehensive test coverage"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve board watch <channel>` kills any existing watch on the same channel before starting

- **Status**: satisfied
- **Evidence**: `src/cli/board.py` lines 248-258 — reads PID via `read_watch_pid`, checks liveness with `os.kill(pid, 0)`, sends SIGTERM, then cleans up the stale PID file. Same pattern applied to `watch_multi_cmd` (lines 331-340) for each channel.

### Criterion 2: A PID file or equivalent mechanism tracks the active watch process per channel

- **Status**: satisfied
- **Evidence**: `src/board/storage.py` lines 193-228 — four functions (`watch_pid_path`, `read_watch_pid`, `write_watch_pid`, `remove_watch_pid`) manage PID files at `{project_root}/.ve/board/cursors/{channel}.watch.pid`. The CLI writes on start and removes in a `try/finally` on exit.

### Criterion 3: Steward-watch command template includes guidance on ack discipline and multi-channel patterns

- **Status**: satisfied
- **Evidence**: `src/templates/commands/steward-watch.md.jinja2` — "OS-level safety net" note added after the existing single-watch warning in Step 2; new "Watch Safety SOP" section added between "Key Concepts" and "Error Handling" covering: (1) never ack before reading, (2) multi-channel requires separate tasks, (3) watch timeout doesn't kill the OS process. Rendered output in `.claude/commands/steward-watch.md` matches.

### Criterion 4: Tests verify that starting a second watch on the same channel terminates the first

- **Status**: satisfied
- **Evidence**: `tests/test_board_cli.py::test_watch_kills_running_process` — writes a PID file with a "live" PID, mocks `os.kill` to confirm the process is alive, invokes watch, asserts both signal 0 (liveness check) and SIGTERM were sent. Additional tests cover PID file creation during watch (`test_watch_creates_pid_file`), cleanup on exit (`test_watch_cleans_up_pid_on_exit`), stale PID handling (`test_watch_cleans_stale_pid_file`), and watch-multi per-channel PID tracking (`test_watch_multi_creates_pid_files_per_channel`). All 75 tests pass.
