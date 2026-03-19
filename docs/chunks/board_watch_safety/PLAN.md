

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add PID-file-based process tracking to `ve board watch` so that starting a new
watch on a channel automatically kills any existing zombie watcher on that same
channel. The PID file lives alongside the existing cursor file at
`{board_root}/.ve/board/cursors/{channel}.watch.pid`.

The implementation reuses the `read_pid_file` / `is_process_running` pattern
already established in `src/orchestrator/daemon.py` (DEC-008 style — extract
shared helpers rather than duplicate). A simpler approach is appropriate here
compared to the daemon's `flock`-held-for-lifetime pattern: the watch process
is short-lived and non-exclusive by design (the agent is the serializer), so a
write-on-start / kill-on-start / cleanup-on-exit PID file is sufficient.

The steward-watch command template already warns about single-watch-per-channel
(Step 2). This chunk strengthens that with OS-level enforcement in the CLI
itself and adds SOP guidance on ack discipline and timeout cleanup.

Tests follow the project's TDD philosophy (TESTING_PHILOSOPHY.md): write
failing tests first for the PID management functions and CLI behavior, then
implement to make them pass.

## Sequence

### Step 1: Add PID file helpers to board/storage.py

Add three functions to `src/board/storage.py`:

- `watch_pid_path(channel: str, project_root: Path) -> Path` — returns
  `{project_root}/.ve/board/cursors/{channel}.watch.pid`
- `read_watch_pid(channel: str, project_root: Path) -> int | None` — reads
  PID from file, returns None if missing or unparseable
- `write_watch_pid(channel: str, pid: int, project_root: Path) -> None` —
  writes PID to the file (creates cursors dir if needed)
- `remove_watch_pid(channel: str, project_root: Path) -> None` — removes
  the PID file (no-op if already gone)

Reuse the same simple pattern as `load_cursor` / `save_cursor` — plain text
file with an integer. Do not import from `orchestrator.daemon`; these are
trivial 3-line functions and the board module should not depend on the
orchestrator module.

Add a `# Chunk: docs/chunks/board_watch_safety` backreference above these
functions.

Location: `src/board/storage.py`

### Step 2: Write failing tests for PID helpers

Write unit tests in `tests/test_board_storage.py` (new file) verifying:

- `watch_pid_path` returns the expected path
- `write_watch_pid` creates the file with correct content
- `read_watch_pid` returns the PID when file exists
- `read_watch_pid` returns None when file is missing
- `read_watch_pid` returns None when file contains garbage
- `remove_watch_pid` deletes the file
- `remove_watch_pid` is a no-op when file is missing

These tests use `tmp_path` and real filesystem — no mocks needed.

Location: `tests/test_board_storage.py`

### Step 3: Add kill-previous-watch logic to board CLI

In `src/cli/board.py`, modify `watch_cmd` to add kill-previous-watch logic
**before** the async `_watch()` call:

1. Call `read_watch_pid(channel, project_root)`
2. If a PID is returned and `os.kill(pid, 0)` confirms it's alive:
   - Send `SIGTERM` via `os.kill(pid, signal.SIGTERM)`
   - Print a warning: `"Killed existing watch process {pid} on channel '{channel}'"`
3. If the PID file exists but the process is dead, clean up the stale file
4. Write the current process PID via `write_watch_pid(channel, os.getpid(), project_root)`
5. Wrap the `asyncio.run(_watch())` in a try/finally that calls
   `remove_watch_pid(channel, project_root)` on exit

The `is_process_running` check uses `os.kill(pid, 0)` inline — a 3-line
pattern, not worth importing from the orchestrator module.

Add a `# Chunk: docs/chunks/board_watch_safety` backreference on the new
kill-previous-watch block.

Location: `src/cli/board.py`

### Step 4: Write failing tests for CLI kill-previous-watch behavior

Add tests to `tests/test_board_cli.py` verifying:

- **PID file created on watch start**: Mock the async watch, invoke
  `watch_cmd`, assert PID file exists with correct content after the command
  runs.
- **PID file cleaned up on normal exit**: Assert PID file is removed after
  the watch command completes.
- **Stale PID file cleaned up**: Write a PID file with a non-existent PID,
  invoke watch, assert no SIGTERM sent and PID file is overwritten.
- **Running process killed**: Write a PID file, mock `os.kill` to confirm
  the process is alive, invoke watch, assert SIGTERM was sent to the old PID.

These tests mock `asyncio.run` / `BoardClient` to avoid real WebSocket
connections (consistent with existing test patterns in `test_board_cli.py`).

Location: `tests/test_board_cli.py`

### Step 5: Add watch-multi PID file support

Apply the same kill-previous / write-PID / cleanup pattern to the
`watch_multi_cmd` in `src/cli/board.py`. Since watch-multi subscribes to
multiple channels, write a PID file for **each** channel and clean up all of
them on exit. This prevents a `watch-multi` on channels A,B from leaving
zombies that block a subsequent `watch A`.

Location: `src/cli/board.py`

### Step 6: Update steward-watch command template

Edit `src/templates/commands/steward-watch.md.jinja2` to add an SOP
guidance section. The template already has the "Single watch only" callout in
Step 2. Add the following enhancements:

**In Step 2 (Start the watch)**, add a note after the existing single-watch
warning:

> **OS-level safety net.** The `ve board watch` command now automatically
> kills any existing watch process on the same channel before starting.
> However, you should still explicitly stop previous background tasks via
> `TaskStop` — the PID-based kill is a fallback for zombie processes that
> survive task termination, not a replacement for clean task lifecycle
> management.

**Add a new section "### Watch Safety SOP"** between "Key Concepts" and
"Error Handling" covering:

1. **Never ack before reading** — ack means "I processed this", not "clear
   the queue". Acking before processing means a crash loses the message.
2. **Multi-channel watch requires separate tasks** — if watching N channels,
   run N separate background `ve board watch` commands (or one
   `ve board watch-multi`). Restart each independently on failure.
3. **Watch timeout does not kill the OS process** — when Claude Code's
   background task times out (exit 144), the `ve board watch` OS process may
   continue running and reconnecting. Always `TaskStop` the previous task
   AND let the CLI's PID-based kill handle any stragglers before starting a
   new watch.

Location: `src/templates/commands/steward-watch.md.jinja2`

### Step 7: Re-render templates and verify

Run `uv run ve init` to re-render the steward-watch template into
`.claude/commands/steward-watch.md`. Verify the rendered output includes the
new SOP guidance.

### Step 8: Run full test suite

Run `uv run pytest tests/` to verify all existing tests still pass and new
tests are green.

## Risks and Open Questions

- **Race between kill and restart**: There's a small window between sending
  SIGTERM and the old process actually exiting. The new watch could start
  before the old one finishes shutting down. This is acceptable because the
  WebSocket server handles duplicate subscriptions gracefully (last-writer-
  wins for cursor position), and the old process will exit shortly after
  receiving SIGTERM.
- **PID reuse**: In theory, the OS could recycle a PID, causing us to kill an
  unrelated process. This risk is minimal — PID reuse requires the original
  process to have exited (so the zombie is already gone) and the PID space on
  modern systems is large. The `os.kill(pid, 0)` check plus the fact that
  watch PIDs are short-lived makes this practically irrelevant.
- **watch-multi PID tracking**: Writing a PID file per channel means
  `watch-multi` on channels A,B creates both `A.watch.pid` and `B.watch.pid`
  pointing to the same process. This is intentional — it prevents either a
  single-channel or multi-channel watch from overlapping on any subscribed
  channel.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->