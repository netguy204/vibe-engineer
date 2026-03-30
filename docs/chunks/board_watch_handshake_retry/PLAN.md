

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Widen the exception tuple in `watch_with_reconnect()` and `watch_multi_with_reconnect()` to also catch `TimeoutError` and `ssl.SSLCertVerificationError`. These errors occur at the `websockets.connect()` / handshake level and currently propagate uncaught, killing the watch process.

The fix follows the existing pattern: the same `except` block that handles `ConnectionClosedError` and `OSError` will also handle these two new exception types. The exponential backoff, jitter, max-retry logic, and logging already exist — we just need to widen the net.

Additionally, the `await self.connect()` call inside the reconnect loop (line 298 for single, line 549 for multi) is unprotected. If a handshake error occurs during reconnection itself, it bypasses the retry loop entirely. The fix wraps these `connect()` calls so handshake errors during reconnection feed back into the retry loop rather than crashing.

The backoff cap will be raised from 30s to 60s per the success criteria, and a default `max_retries=10` sentinel will be documented (callers already pass this via CLI).

Tests follow TDD per docs/trunk/TESTING_PHILOSOPHY.md: mock `websockets.connect` to raise `TimeoutError` and `ssl.SSLCertVerificationError`, verify retry behavior and clean exit after max retries.

## Subsystem Considerations

No existing subsystems are relevant to this change. This is a targeted bug fix within the board client's reconnect logic.

## Sequence

### Step 1: Define the handshake-retryable exception tuple

In `src/board/client.py`, add `import ssl` at the top. Define a module-level tuple constant `_RETRYABLE_ERRORS` containing all exception types that should trigger a reconnect:
- `websockets.exceptions.ConnectionClosedError`
- `websockets.exceptions.ConnectionClosedOK`
- `ConnectionError`
- `OSError`
- `TimeoutError` (NEW — handshake timeout)
- `ssl.SSLCertVerificationError` (NEW — transient cert failures)

This centralizes the exception list so both `watch_with_reconnect()` and `watch_multi_with_reconnect()` share the same set and future additions only need one change.

Location: `src/board/client.py`, module level after imports

### Step 2: Update `watch_with_reconnect()` exception handling

Replace the inline exception tuple (lines 260-265) with `_RETRYABLE_ERRORS`.

Wrap the `await self.connect()` call (line 298) in a `try/except _RETRYABLE_ERRORS` block so that handshake errors during reconnection feed back into the retry loop with `continue` rather than propagating out. Increment `attempt` and check `max_retries` before retrying. Log the handshake error distinctly from mid-connection errors.

Raise `max_backoff` from `30.0` to `60.0`.

Location: `src/board/client.py`, `watch_with_reconnect()` method

### Step 3: Update `watch_multi_with_reconnect()` exception handling

Apply the same changes as Step 2:
- Replace inline exception tuple (lines 525-530) with `_RETRYABLE_ERRORS`
- Wrap the `await self.connect()` call (line 549) in `try/except _RETRYABLE_ERRORS` for handshake retry
- Raise `max_backoff` from `30.0` to `60.0`

Location: `src/board/client.py`, `watch_multi_with_reconnect()` method

### Step 4: Write tests — handshake timeout triggers retry

Add test `test_watch_with_reconnect_retries_on_handshake_timeout` to `tests/test_board_client.py`.

Mock `websockets.connect` to raise `TimeoutError` on the first reconnect attempt, then succeed on the second. Verify:
- The watch recovers and returns a message
- `asyncio.sleep` was called (backoff happened)
- The error was logged

Add a parallel test `test_watch_multi_reconnect_retries_on_handshake_timeout` for `watch_multi_with_reconnect()`.

### Step 5: Write tests — SSL error triggers retry

Add test `test_watch_with_reconnect_retries_on_ssl_error`.

Mock `websockets.connect` to raise `ssl.SSLCertVerificationError` on the first reconnect attempt, then succeed. Verify recovery.

Add parallel test for `watch_multi_with_reconnect()`.

### Step 6: Write tests — max retries causes clean exit

Add test `test_watch_with_reconnect_handshake_max_retries_exit`.

Mock `websockets.connect` to always raise `TimeoutError`. Set `max_retries=3`. Verify:
- The exception propagates after 3 attempts
- `asyncio.sleep` was called 3 times with increasing backoff
- The backoff caps at 60s

### Step 7: Update GOAL.md code_paths

Add `src/board/client.py` and `tests/test_board_client.py` to the `code_paths` frontmatter in `docs/chunks/board_watch_handshake_retry/GOAL.md`.

## Dependencies

None. The `ssl` module is in Python's standard library. The `websockets` library is already a dependency.

## Risks and Open Questions

- **`ssl.SSLCertVerificationError` may indicate a permanent misconfiguration** rather than a transient issue. The max-retries cap (default 10) bounds exposure, and logging each attempt ensures the operator can diagnose persistent cert problems. We accept retrying a few times for the transient case.
- **Wrapping `connect()` in the retry loop changes control flow.** Currently, if `connect()` fails during reconnection, the exception propagates immediately. After this change, it retries. This is strictly better for the observed failure modes but could mask permanent server-down scenarios — again bounded by max_retries.

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

- Steps 2-3: The plan called for wrapping `connect()` in `try/except` with `continue` to feed back into the outer retry loop. However, `continue` returns to the top of the `while True` where `self._ws.send()` is called — but after a failed `connect()`, `self._ws` is `None`. Instead, used an inner `while True` loop around `connect()` that retries with its own backoff and attempt counting until connection succeeds or `max_retries` is exhausted. This keeps the control flow self-contained within the reconnect block.
- Step 1: Added `import websockets.exceptions` explicitly because the `websockets` library (version used) does not auto-import the `exceptions` submodule at package level.
- Step 7: code_paths were already correct in the GOAL.md frontmatter.