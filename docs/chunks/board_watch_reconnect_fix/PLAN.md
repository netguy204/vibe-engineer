

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug is a silent-death failure mode in long-running watches. When
`max_retries` is `None` (the default, and how the CLI calls both reconnect
methods), the reconnect loop runs forever. After enough stale-detection cycles,
the watch enters a state where it appears alive but delivers nothing — the worst
failure mode for a monitoring primitive.

The fix has three parts:

1. **Add a configurable `--max-reconnects` CLI flag** that flows through to
   `max_retries` in both `watch_with_reconnect` and
   `watch_multi_with_reconnect`. Default to 10 so that unbounded retries are
   opt-in (`--max-reconnects 0` for unlimited), not the default.

2. **Exit nonzero with a clear error message** when reconnect exhaustion
   occurs. The client methods already `raise` the last exception when
   `max_retries` is exceeded — the CLI just needs to catch it and produce a
   human-readable exit. Use a distinct exit code (exit 3) so callers can
   distinguish "reconnect exhaustion" from other errors.

3. **Re-subscribe after each successful reconnect.** After `connect()` succeeds
   in the reconnect path, the code already loops back to re-send the watch
   frame (the `while True` loop re-enters the top and sends the frame). This
   means subscriptions ARE correctly re-established. However, the
   `watch_multi_with_reconnect` method calls `watch_multi()` which calls
   `_send_all_watch_frames()` — this is correct. No subscription fix needed,
   but we'll add a log line to make the re-subscription explicit and observable
   for debugging.

Testing approach follows TESTING_PHILOSOPHY.md: write failing tests first for
the reconnect exhaustion behavior, then implement. Tests verify semantic
behavior (exit code, error message content, reconnect counting) rather than
structural properties.

## Subsystem Considerations

No existing subsystems are relevant to this chunk. The board client is not
governed by any documented subsystem.

## Sequence

### Step 1: Write failing tests for reconnect exhaustion exit behavior

Add tests to `tests/test_board_client.py`:

1. **`test_watch_with_reconnect_default_max_retries`** — Verify that
   `watch_with_reconnect` with default `max_retries=10` raises after 10
   consecutive failed reconnects (not unlimited).

2. **`test_watch_multi_reconnect_default_max_retries`** — Same for
   `watch_multi_with_reconnect`.

3. **`test_watch_with_reconnect_logs_resubscription`** — After a successful
   reconnect, verify that a log message confirms re-subscription to the
   channel.

Location: `tests/test_board_client.py`

### Step 2: Change default `max_retries` from `None` to 10

In `src/board/client.py`, update both method signatures:

- `watch_with_reconnect(..., max_retries: int | None = None, ...)` →
  `watch_with_reconnect(..., max_retries: int | None = 10, ...)`
- `watch_multi_with_reconnect(..., max_retries: int | None = None, ...)` →
  `watch_multi_with_reconnect(..., max_retries: int | None = 10, ...)`

The `None` sentinel still means "unlimited" for callers that explicitly opt in.
The default changes from unlimited to 10 — bounded by default.

Location: `src/board/client.py`

### Step 3: Add explicit re-subscription log after reconnect

In both `watch_with_reconnect` and `watch_multi_with_reconnect`, after the
reconnect succeeds (after `backoff = 1.0` reset), add:

```python
logger.info(
    "Re-subscribing to channel=%s after reconnect",
    channel,
)
```

For `watch_multi_with_reconnect`, log the channel count and cursor state.
This makes the re-subscription observable without changing behavior (the
re-subscription already happens when the loop re-enters and sends watch
frames).

Location: `src/board/client.py`

### Step 4: Add `--max-reconnects` CLI flag to `watch` and `watch-multi`

Add `@click.option("--max-reconnects", ...)` to both commands in
`src/cli/board.py`:

- Default: `10` (matches the new client default)
- `0` means unlimited (pass `None` to the client)
- Pass through to `client.watch_with_reconnect(channel, cursor, max_retries=max_reconnects)` and `client.watch_multi_with_reconnect(channel_cursors, max_retries=max_reconnects, ...)`

Location: `src/cli/board.py`

### Step 5: Handle reconnect exhaustion at the CLI layer with distinct exit code

In the `_watch()` and `_watch_multi()` async inner functions in
`src/cli/board.py`, catch the retryable exceptions that propagate when
`max_retries` is exhausted. Print a clear error message to stderr and exit
with code 3:

```python
except (ConnectionError, websockets.exceptions.ConnectionClosedError, OSError, ...) as exc:
    click.echo(f"Error: watch terminated after reconnect exhaustion: {exc}", err=True)
    sys.exit(3)
```

Use `_RETRYABLE_ERRORS` imported from `board.client` to stay consistent with
the exception tuple used internally.

Exit code semantics:
- `0`: Normal exit (message received, or clean shutdown)
- `1`: Configuration/setup error
- `3`: Reconnect exhaustion (watch died, callers should respawn)

Location: `src/cli/board.py`

### Step 6: Write CLI integration tests

Add tests to verify the end-to-end behavior:

1. **`test_watch_max_reconnects_flag_accepted`** — Verify the `--max-reconnects`
   flag is accepted by both `watch` and `watch-multi` commands (Click parsing).

2. **`test_watch_reconnect_exhaustion_exits_nonzero`** — Mock the client to
   simulate reconnect exhaustion and verify exit code 3 and error message on
   stderr.

Location: `tests/test_board_cli.py`

### Step 7: Verify existing tests pass

Run `uv run pytest tests/test_board_client.py tests/test_board_cli.py -x` to
ensure no regressions. The default `max_retries` change from `None` to `10`
may require updating existing tests that assumed unlimited retries — audit
each test that calls `watch_with_reconnect` or `watch_multi_with_reconnect`
without explicit `max_retries` and either add `max_retries=None` to preserve
behavior or verify the test works within 10 retries.

## Dependencies

No new dependencies. All required infrastructure exists:
- `_RETRYABLE_ERRORS` tuple in `src/board/client.py`
- `max_retries` parameter already plumbed in client methods
- Click option pattern established in `src/cli/board.py`

## Risks and Open Questions

- **Default value of 10 may be too low for legitimately low-traffic channels.**
  A channel with 30+ minute gaps between messages and a 5-minute stale timeout
  will hit ~12 reconnects per hour of silence. Default 10 would kill the watch
  within an hour. However, the stale-detection path only forces a reconnect
  after 2 consecutive re-registrations with no response — so 10 full reconnect
  cycles is actually 10 × (connect + 2 stale timeouts) ≈ 10 × 15 min = 2.5
  hours minimum. This is reasonable; operators on very-low-traffic channels can
  pass `--max-reconnects 0`.

- **Changing the default `max_retries` from `None` to 10** is a behavioral
  change for any code that calls these methods programmatically without
  specifying `max_retries`. The CLI is the primary consumer and currently passes
  no value, so it benefits immediately. Any other callers that relied on
  unlimited retries will need to pass `max_retries=None` explicitly.

- **Exit code 3 is arbitrary** but avoids collision with standard exit codes
  (0 = success, 1 = general error, 2 = misuse of command). Document this in
  the CLI help text.

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

- Step 7: Existing tests that used `mock_watch_multi(channels, count=1,
  auto_ack=True)` or `mock_watch(channel, cursor)` signatures failed
  because the CLI now passes `max_retries=` as a keyword argument. Fixed
  by adding `**kwargs` to all mock_watch_multi signatures (13 instances)
  and the single mock_watch signature. Also updated one
  `assert_called_once_with` call to include the new `max_retries=10`
  parameter.
-->