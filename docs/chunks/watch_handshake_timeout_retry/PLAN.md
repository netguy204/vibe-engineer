<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The watch reconnect loop (`watch_with_reconnect` and `watch_multi_with_reconnect`)
already handles `_RETRYABLE_ERRORS` (including `TimeoutError`) via a
retry-with-backoff branch. The gap is in the **idle reconnect path** (`except
StaleWatchError`): when a stale-triggered reconnect calls `await self.connect()`,
any exception raised there is inside an `except` handler. Python's exception
handling rules prevent sibling `except` clauses from catching it — a
`TimeoutError` from the WebSocket opening handshake therefore propagates
uncaught out of the `while True:` loop, terminating the process with exit
code 3.

The fix is minimal and surgical: wrap the `connect()` call inside each
`StaleWatchError` handler with the same retry-with-backoff inner loop that the
`_RETRYABLE_ERRORS` branch already uses. A handshake timeout during an idle
reconnect increments `attempt`, backs off, and retries — exactly as any
`_RETRYABLE_ERRORS` would. On eventual success the `attempt` counter is reset
to 0 (consistent with `watch_reconnect_counter_reset`), and normal watch
operation resumes.

A defensive addition: `asyncio.TimeoutError` is added to `_RETRYABLE_ERRORS`.
On Python < 3.11, `asyncio.TimeoutError` is not a subclass of the built-in
`TimeoutError` (it is a subclass of `concurrent.futures.TimeoutError`), so
without this any path that uses `asyncio.wait_for` during reconnect escapes
the existing retry net on older Python versions.

No new architectural decisions are required. This extends two pre-existing
patterns: the `_RETRYABLE_ERRORS` guard from `board_watch_handshake_retry` and
the consecutive-failure reset from `watch_reconnect_counter_reset`.

## Sequence

### Step 1: Add `asyncio.TimeoutError` to `_RETRYABLE_ERRORS`

**File**: `src/board/client.py`

Extend the `_RETRYABLE_ERRORS` tuple (currently around line 27) to include
`asyncio.TimeoutError`:

```python
# Chunk: docs/chunks/board_watch_handshake_retry - Centralized retryable exception tuple
# Chunk: docs/chunks/watch_handshake_timeout_retry - asyncio.TimeoutError for Python < 3.11 safety
_RETRYABLE_ERRORS = (
    websockets.exceptions.ConnectionClosedError,
    websockets.exceptions.ConnectionClosedOK,
    ConnectionError,
    OSError,
    TimeoutError,
    asyncio.TimeoutError,
    ssl.SSLCertVerificationError,
)
```

On Python 3.11+ `asyncio.TimeoutError is TimeoutError`, making this a
duplicate. Python's `isinstance` deduplicates exception tuples at runtime —
harmless. On Python < 3.11 this adds real coverage.

### Step 2: Write failing tests (TDD — red phase)

Add a new section in `tests/test_board_client.py` below the existing
`watch_idle_reconnect_budget` tests (around line 2186), marked with:

```python
# Chunk: docs/chunks/watch_handshake_timeout_retry - Opening-handshake timeout on idle reconnect
```

**Test 2a — `test_watch_with_reconnect_idle_handshake_timeout_retries`**

Scenario: the initial connection succeeds. Stale detection fires (two
consecutive `asyncio.TimeoutError` on `recv`), triggering an idle reconnect.
The first `connect()` call raises `TimeoutError("timed out during opening
handshake")`. The second `connect()` call succeeds and the watch delivers a
message.

Assert:
- The message is delivered (watch did not exit code 3).
- `asyncio.sleep` was called at least once (backoff fired for the handshake
  timeout).
- `websockets.connect` was called exactly 3 times (initial + idle-reconnect
  attempt-1-fails + idle-reconnect-attempt-2-succeeds).

**Test 2b — `test_watch_multi_with_reconnect_idle_handshake_timeout_retries`**

Same scenario for `watch_multi_with_reconnect`: idle stale fires, first
`connect()` raises `TimeoutError`, second succeeds, message delivered.

Assert:
- Exactly one message is yielded.
- `websockets.connect` called 3 times.

**Test 2c — `test_watch_with_reconnect_idle_handshake_timeout_exhausts_budget`**

Scenario: stale fires once (idle reconnect), then every subsequent `connect()`
call raises `TimeoutError`. `max_retries=2`.

Assert:
- `TimeoutError` (or its `OSError` parent) propagates after `max_retries`
  consecutive handshake timeouts — the safety valve still applies.

**Test 2d — `test_watch_multi_with_reconnect_idle_handshake_timeout_exhausts_budget`**

Same safety-valve scenario for `watch_multi_with_reconnect` with `max_retries=2`.

Assert:
- `TimeoutError` propagates.

Run tests; confirm all four are red (fail with `TimeoutError` or
`ConnectionError`/`OSError` propagating instead of recovering).

```bash
uv run pytest tests/test_board_client.py -k "idle_handshake" -x -q
```

### Step 3: Fix `watch_with_reconnect` — guard `connect()` in the `StaleWatchError` handler

**File**: `src/board/client.py`, `except StaleWatchError:` block in
`watch_with_reconnect` (currently around line 302–307).

Replace:
```python
# Reconnect without backoff sleep — the network is fine.
try:
    await self.close()
except Exception:
    pass
await self.connect()
backoff = 1.0  # reset failure backoff too
```

With a retry inner loop:

```python
# Reconnect without backoff sleep — the network is fine.
# If the opening handshake times out, route through the failure budget.
try:
    await self.close()
except Exception:
    pass
# Chunk: docs/chunks/watch_handshake_timeout_retry - Catch opening-handshake timeout on idle reconnect
while True:
    try:
        await self.connect()
        break  # Connected successfully
    except _RETRYABLE_ERRORS as connect_exc:
        attempt += 1
        if max_retries is not None and attempt > max_retries:
            raise connect_exc
        jitter = random.uniform(0, backoff * 0.5)
        wait_time = min(backoff + jitter, max_backoff)
        logger.warning(
            "Handshake timeout on idle reconnect, retrying in %.1fs "
            "(attempt %d) exc=%s",
            wait_time,
            attempt,
            type(connect_exc).__name__,
        )
        await asyncio.sleep(wait_time)
        backoff = min(backoff * 2, max_backoff)
backoff = 1.0  # reset failure backoff after successful connect
# Chunk: docs/chunks/watch_reconnect_counter_reset - Reset attempt counter after demonstrated-healthy reconnect
attempt = 0
```

### Step 4: Fix `watch_multi_with_reconnect` — same guard in its `StaleWatchError` handler

**File**: `src/board/client.py`, `except StaleWatchError:` block in
`watch_multi_with_reconnect` (currently around line 611–617).

Apply the same replacement as Step 3 verbatim (same retry loop, same
`backoff = 1.0` / `attempt = 0` resets after success).

### Step 5: Run the full test suite (TDD — green phase)

```bash
uv run pytest tests/test_board_client.py -x -q
```

All four new tests must go green. All pre-existing reconnect, stale-reconnect,
idle-budget, and counter-reset tests must continue to pass.

## Risks and Open Questions

- **`attempt = 0` reset timing**: After the idle-reconnect connect loop
  succeeds (possibly after some handshake-timeout retries), resetting
  `attempt = 0` is intentional: a successful reconnect is evidence the network
  is healthy, so the consecutive-failure counter should restart. This is the
  `watch_reconnect_counter_reset` invariant applied uniformly.

- **Backoff value at entry to idle path**: The idle reconnect handler resets
  `backoff = 1.0` on success. If `connect()` fails first, backoff is updated
  from whatever `backoff` is currently (could be `1.0` after a prior success,
  or higher if prior `_RETRYABLE_ERRORS` retries didn't fully reset). This is
  the correct behaviour — we inherit the current backoff state rather than
  double-resetting it.

- **Python exception tuple deduplication**: `(TimeoutError, asyncio.TimeoutError)`
  on Python 3.11+ is equivalent to `(TimeoutError,)` for `isinstance` checks.
  Python handles this transparently.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
