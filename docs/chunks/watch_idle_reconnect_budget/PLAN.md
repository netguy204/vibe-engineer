

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The root cause is that both `watch_with_reconnect` and `watch_multi_with_reconnect`
use a single `attempt` counter for two semantically different conditions:

1. **Genuine network failure** — WebSocket dropped, handshake failed, etc.
   Should count against the 10-attempt reconnect budget (safety valve).

2. **Idle stale timeout** — no messages arrived in `stale_timeout` seconds,
   so the client re-registers and—if that also times out—forces a full reconnect.
   Should NOT count against budget; this is expected behavior on quiet channels.

Both paths currently raise/catch `ConnectionError`, which lives in `_RETRYABLE_ERRORS`.
Python's `except` clause sees them identically, so `attempt` increments on every
idle reconnect, exhausting the budget in ~90 minutes of silence.

**Fix strategy**: introduce `StaleWatchError(ConnectionError)` as a sentinel for
idle-triggered reconnects. Because Python exception handling is ordered, placing an
`except StaleWatchError` branch *before* `except _RETRYABLE_ERRORS` routes idle
reconnects to a budget-free path while genuine failures continue to count.

Additionally, implement **adaptive stale-timeout backoff**: after 3 consecutive idle
reconnects, double the re-register interval (capped at 600 s). This reduces
unnecessary churn on very quiet channels. The interval resets when a message arrives.

No new external dependencies. All changes are confined to `src/board/client.py`
and `tests/test_board_client.py`.

## Sequence

### Step 1: Add `StaleWatchError` exception class

In `src/board/client.py`, immediately after `BoardError`, add:

```python
# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle timeout sentinel
class StaleWatchError(ConnectionError):
    """Raised when a watch re-registration cycle times out with no message.

    Distinct from genuine connection failures: the server is reachable but the
    channel is idle. Used to suppress budget accounting in reconnect wrappers.
    """
```

This subclasses `ConnectionError` so it remains retryable if it ever leaks out
of a handler that doesn't know about it, but is distinguishable by name.

---

### Step 2: Raise `StaleWatchError` from both stale paths

**In `watch_with_reconnect`** (inner timeout handler, ~line 248):
```python
# Before:
raise ConnectionError("Watch connection stale")
# After:
raise StaleWatchError("Watch connection stale")
```

**In `watch_multi`** (timeout handler, ~line 424):
```python
# Before:
raise ConnectionError("Watch connection stale")
# After:
raise StaleWatchError("Watch connection stale")
```

---

### Step 3: Update `watch_with_reconnect` — separate idle handler

At the top of the `while True` loop, add tracking variables before `attempt`:

```python
attempt = 0
idle_reconnects = 0
backoff = 1.0
max_backoff = 60.0
current_stale_timeout = stale_timeout  # may grow on repeated idle
```

Pass `current_stale_timeout` (not `stale_timeout`) into `asyncio.wait_for`.

Add a `StaleWatchError` branch **before** `except _RETRYABLE_ERRORS`:

```python
except StaleWatchError:
    # Idle timeout — reconnect without counting against the failure budget.
    idle_reconnects += 1
    if idle_reconnects >= 3:
        # Back off re-register interval to reduce churn on very quiet channels.
        current_stale_timeout = min(current_stale_timeout * 2, 600.0)
        logger.info(
            "Idle reconnect #%d, increasing stale_timeout to %.0fs channel=%s",
            idle_reconnects, current_stale_timeout, channel,
        )
    logger.info(
        "Idle reconnect (not counted against budget) channel=%s cursor=%d",
        channel, cursor,
    )
    # Reconnect without backoff sleep — the network is fine.
    try:
        await self.close()
    except Exception:
        pass
    await self.connect()
    backoff = 1.0  # reset failure backoff too
```

Reset idle state on successful message delivery — add before `return`:

```python
idle_reconnects = 0
current_stale_timeout = stale_timeout
```

Add backreference comment at method level:
```python
# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnects exempt from budget
```

---

### Step 4: Update `watch_multi_with_reconnect` — separate idle handler

At the top of the `while True` loop, add tracking variables:

```python
attempt = 0
idle_reconnects = 0
backoff = 1.0
max_backoff = 60.0
current_stale_timeout = stale_timeout
```

Pass `current_stale_timeout` to `watch_multi` (replace `stale_timeout=stale_timeout`
with `stale_timeout=current_stale_timeout` in the inner call).

Add a `StaleWatchError` branch **before** `except _RETRYABLE_ERRORS`:

```python
except StaleWatchError:
    idle_reconnects += 1
    if idle_reconnects >= 3:
        current_stale_timeout = min(current_stale_timeout * 2, 600.0)
        logger.info(
            "Idle reconnect #%d, increasing stale_timeout to %.0fs channels=%s",
            idle_reconnects, current_stale_timeout, list(cursors),
        )
    logger.info(
        "Idle reconnect (not counted against budget) channels=%s", list(cursors)
    )
    try:
        await self.close()
    except Exception:
        pass
    await self.connect()
    backoff = 1.0
```

Reset idle state when a message is delivered — the existing `attempt = 0; backoff = 1.0`
block already resets failure state; add alongside it:

```python
idle_reconnects = 0
current_stale_timeout = stale_timeout
```

Add backreference comment at method level:
```python
# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnects exempt from budget
```

---

### Step 5: Write tests (TDD — write failing tests first)

Following the project's TDD philosophy: write these tests, run them to confirm they
fail, then implement Steps 1–4.

**Test 1 — Idle does not exhaust budget in `watch_with_reconnect`**

Simulate N idle stale cycles (N > max_retries), then deliver a real message.
Assert the message is returned successfully rather than raising. This directly
verifies the primary success criterion.

```python
async def test_watch_with_reconnect_idle_does_not_exhaust_budget(keypair):
    """Idle stale timeouts do not count against the reconnect budget."""
    ...
```

**Test 2 — Real failures still exhaust budget in `watch_with_reconnect`**

Simulate max_retries+1 genuine `ConnectionClosedError`s. Assert the exception
propagates (budget is preserved as a safety valve).

```python
async def test_watch_with_reconnect_real_failure_exhausts_budget(keypair):
    """Genuine connection failures still count against max_retries."""
    ...
```

**Test 3 — Idle does not exhaust budget in `watch_multi_with_reconnect`**

Same scenario as Test 1 but using the multi-channel wrapper.

```python
async def test_watch_multi_with_reconnect_idle_does_not_exhaust_budget(keypair):
    """Idle stale timeouts do not count against budget in watch_multi_with_reconnect."""
    ...
```

**Test 4 — Counter resets on message delivery in `watch_multi_with_reconnect`**

Simulate some idle reconnects, deliver a message (resetting counters), simulate
more idle reconnects. Verify the budget hasn't accumulated across the boundary.

```python
async def test_watch_multi_with_reconnect_budget_resets_on_message(keypair):
    """Idle reconnect counter resets when a message is successfully delivered."""
    ...
```

All tests use the existing `_make_mock_ws` / `_async_ctx` helpers from
`tests/test_board_client.py`. No new conftest entries needed.

---

### Step 6: Run tests

```bash
uv run pytest tests/test_board_client.py -v -k "idle or budget"
```

All four new tests should pass. Then confirm no regressions:

```bash
uv run pytest tests/test_board_client.py -v
```

## Risks and Open Questions

- **`StaleWatchError` leaking past callers that don't handle it**: Since it
  subclasses `ConnectionError`, any outer retry loop that catches `ConnectionError`
  will still handle it — just as if it were a real failure. This is acceptable
  fallback behavior and is better than silently swallowing the error.

- **Adaptive backoff and the stale_timeout parameter**: Callers that set a
  custom `stale_timeout` will see it grow after 3 idle reconnects. This is
  intentional but could surprise callers who expected a fixed interval. The
  behavior is documented in the updated docstrings.

- **Connect failure during idle reconnect**: The stale handler calls `connect()`
  without a retry loop. If the connect itself fails (e.g., brief network blip),
  it will raise a `_RETRYABLE_ERRORS` exception which will be caught by the outer
  handler and counted against the budget — which is correct, since this is now a
  real failure.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
