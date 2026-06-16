

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The entire fix lives in `BoardClient._connect_with_retry` in `src/board/client.py`.
`_connect_with_retry` is the shared helper called by both `watch_with_reconnect`
and `watch_multi_with_reconnect` for every reconnect attempt (spontaneous disconnect
path and stale-driven path alike). By catching `websockets.exceptions.InvalidStatus`
there — checking the status code and retrying on 5xx, re-raising on 4xx — both
reconnect branches inherit the fix symmetrically without any change to the outer
reconnect loops or to `_RETRYABLE_ERRORS`.

`InvalidStatus` cannot be added directly to `_RETRYABLE_ERRORS` because retryability
depends on the HTTP status code embedded in the exception. A separate `except`
branch inside `_connect_with_retry`'s inner loop is the right granularity.

The existing backoff arithmetic (jitter, exponential growth, `max_backoff` cap) and
attempt-counter semantics apply unchanged to the 5xx path. The 10-consecutive-failure
safety valve (`max_retries` check) applies to the 5xx path identically to
`TimeoutError`.

Tests follow the established pattern from `watch_handshake_timeout_retry` and
`watch_handshake_stale_retry`: mock `websockets.connect`, script a sequence of
connections with `InvalidStatus` raised on specific calls, assert recovery or fatal
propagation, assert `sleep_mock.call_count` and `connect_call_count`.

## Sequence

### Step 1: Study how `InvalidStatus` is constructed in the test environment

Before writing tests, verify the exception's interface. Run a quick in-repo check:

```python
import websockets.exceptions
from unittest.mock import MagicMock
r = MagicMock()
r.status_code = 500
e = websockets.exceptions.InvalidStatus(r)
assert e.response.status_code == 500
```

This confirms that passing a `MagicMock()` with a `.status_code` attribute is
sufficient to construct a testable `InvalidStatus` without needing a real HTTP
response object.

### Step 2: Write failing tests for 5xx-retry in `watch_with_reconnect`

Add the following tests to `tests/test_board_client.py`, inside a new section
block delimited by a comment banner referencing this chunk. All tests follow the
`make_ws_factory` + `connect_call_count` pattern established by sibling tests.

**Test A — `test_watch_with_reconnect_5xx_handshake_retries`**

Scenario:
- Connection 1 (initial): auth OK, then `ConnectionClosedError` to trigger disconnect.
- Connection 2 (reconnect attempt 1): `websockets.connect` raises
  `InvalidStatus(response.status_code=500)`.
- Connection 3 (reconnect attempt 2): auth OK, delivers message.

Asserts:
- `result["position"]` matches the delivered message.
- `sleep_mock.call_count >= 1` (backoff fired for the 5xx).
- `connect_call_count == 3`.

**Test B — `test_watch_with_reconnect_4xx_handshake_is_fatal`**

Scenario:
- Connection 1 (initial): auth OK, then `ConnectionClosedError`.
- Connection 2 (reconnect attempt): raises `InvalidStatus(response.status_code=403)`.

Asserts:
- `pytest.raises(websockets.exceptions.InvalidStatus)` (propagates immediately, no
  retry).
- `connect_call_count == 2` (no further attempts).

**Test C — `test_watch_with_reconnect_5xx_handshake_exhausts_budget`**

Scenario:
- Connection 1 (initial): auth OK, then `ConnectionClosedError`.
- All subsequent calls raise `InvalidStatus(response.status_code=503)`.
- `max_retries=2`.

Asserts:
- `pytest.raises(websockets.exceptions.InvalidStatus)` propagates after the budget
  is exhausted.
- `connect_call_count == 4` (initial + 3 reconnect attempts — the 3rd exhausts
  `max_retries=2` because attempt increments before the check, matching the existing
  semantics in `_connect_with_retry`).

### Step 3: Write the same three failing tests for `watch_multi_with_reconnect`

Mirror Tests A, B, C above for `watch_multi_with_reconnect`:

- **`test_watch_multi_with_reconnect_5xx_handshake_retries`** — yields one message
  after recovering from a 5xx on attempt 2.
- **`test_watch_multi_with_reconnect_4xx_handshake_is_fatal`** — `InvalidStatus`
  with 403 propagates immediately.
- **`test_watch_multi_with_reconnect_5xx_handshake_exhausts_budget`** — 5xx
  sustained, budget exhausted, exception propagates.

The multi variants use `async for` + `results.append(m)` and assert on
`len(results)` and `connect_call_count`, matching the existing multi-watch test
conventions.

### Step 4: Implement the fix in `_connect_with_retry`

In `src/board/client.py`, add a new `except` clause inside `_connect_with_retry`'s
inner `try` block, **before** the existing `except _RETRYABLE_ERRORS` clause:

```python
except websockets.exceptions.InvalidStatus as inv_exc:
    # 4xx = fatal configuration/identity error; surface immediately
    if inv_exc.response.status_code < 500:
        raise
    # 5xx = transient server outage; treat identically to TimeoutError
    attempt += 1
    if max_retries is not None and attempt > max_retries:
        raise
    jitter = random.uniform(0, backoff * 0.5)
    wait_time = min(backoff + jitter, max_backoff)
    logger.warning(
        "Handshake rejected HTTP %d during reconnect in %.1fs "
        "(attempt %d) exc=%s",
        inv_exc.response.status_code,
        wait_time,
        attempt,
        type(inv_exc).__name__,
    )
    await asyncio.sleep(wait_time)
    backoff = min(backoff * 2, max_backoff)
```

Python exception clauses are checked in order; since `InvalidStatus` is not a
subtype of anything in `_RETRYABLE_ERRORS`, clause ordering does not matter for
correctness, but placing `InvalidStatus` first makes the intent clearer.

Add a backreference comment immediately before the `except websockets.exceptions.InvalidStatus` clause:

```python
# Chunk: docs/chunks/watch_handshake_5xx_retry - HTTP 5xx during handshake retryable; 4xx fatal
```

### Step 5: Verify all six new tests pass and existing tests continue to pass

Run the full test suite:

```bash
uv run pytest tests/test_board_client.py -v
```

Confirm:
- All six new tests pass.
- All pre-existing reconnect, stale, timeout, counter-reset, and handshake-timeout
  tests continue to pass.

## Dependencies

No new external dependencies. `websockets.exceptions.InvalidStatus` is already
imported via `import websockets.exceptions` in both source and test files.

## Risks and Open Questions

- **`InvalidStatus.response` attribute name**: The implementation assumes
  `inv_exc.response.status_code`. The websockets library has used this attribute
  layout since ≥10.x. Step 1 validates this before the test suite is written; if
  the attribute path differs in the installed version, adjust accordingly.
- **`_connect_with_retry` re-raise semantics**: When `max_retries` is exhausted on
  the `InvalidStatus` path, the bare `raise` re-raises `inv_exc` (the
  `InvalidStatus`). Existing tests for the spontaneous-disconnect path assert
  `pytest.raises((TimeoutError, OSError))`. The new safety-valve test for 5xx must
  use `pytest.raises(websockets.exceptions.InvalidStatus)` specifically — do not
  widen it to a union.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
