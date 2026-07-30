

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The parent chunk (`watch_handshake_timeout_retry`) added a retry loop inside
the `StaleWatchError` handler of both `watch_with_reconnect` and
`watch_multi_with_reconnect`. The production failure log and the GOAL confirm
that loop is incomplete or incorrect: a single opening-handshake `TimeoutError`
on a stale-driven reconnect propagates as fatal instead of being retried.

The key diagnostic insight is what the production log **doesn't show**: there is
no "Handshake timeout on idle reconnect, retrying" log line between "Idle
reconnect #4" and the fatal error. If the `except _RETRYABLE_ERRORS` clause in
the stale handler's inner retry loop were executing, that log would appear. Its
absence means the `TimeoutError` is escaping the `except` block — either because
the exception type isn't matched, or because the code path is reached through a
code branch that bypasses the retry block entirely.

**Strategy (TDD per TESTING_PHILOSOPHY.md)**:

1. Write tests for the **specific scenario not covered by the parent chunk's
   tests**: multiple successful idle reconnects (#1, #2, #3) followed by a
   stale-driven reconnect (#4+) whose opening handshake times out. The parent
   chunk's tests only exercise the first stale cycle.

2. Run the new tests. If they fail, that confirms the bug and guides the fix.
   If they pass, the code is already correct and the tests provide regression
   coverage for the production scenario.

3. Whether or not the new tests initially fail, **unify the two reconnect
   code paths** by extracting the connect-with-retry inner loop into a shared
   private helper `_connect_with_retry`. This is the architectural fix
   regardless of the test outcome: the GOAL demands "the same retry-with-backoff
   loop" — literal code reuse, not just semantic equivalence. Duplicate retry
   loops diverge over time, and the parent chunk's divergence is exactly what
   caused this gap.

4. The unified helper is called identically from both the `StaleWatchError`
   branch and the `_RETRYABLE_ERRORS` branch (the spontaneous-disconnect path).
   The spontaneous-disconnect path applies an initial back-off sleep **before**
   calling the helper; the stale path calls it immediately (no pre-sleep, since
   the network was previously reachable). This preserves the existing timing
   semantics while ensuring the retry logic is physically identical.

## Sequence

### Step 1: Write the new tests (TDD red phase)

Add a new test section in `tests/test_board_client.py` under the comment:

```
# ---------------------------------------------------------------------------
# Chunk: docs/chunks/watch_handshake_stale_retry - Stale-path handshake retry
# ---------------------------------------------------------------------------
```

Write four tests:

**Test A** — `test_watch_with_reconnect_stale_handshake_timeout_after_prior_cycles`

Scenario:
- Connections 1–4 (idle reconnects #1–#3): each does auth OK + 2 consecutive
  `asyncio.TimeoutError` → `StaleWatchError`, then reconnect succeeds
  (i.e., websockets.connect returns a valid ws for these calls)
- Connection 5 (idle reconnect #4 attempt 1): `websockets.connect` raises
  `TimeoutError("timed out during opening handshake")`
- Connection 6 (idle reconnect #4 attempt 2): reconnect succeeds, delivers
  the message

Assert: result is the delivered message. `asyncio.sleep` was called at least
once (backoff). `websockets.connect` was called exactly 6 times.

**Test B** — `test_watch_multi_with_reconnect_stale_handshake_timeout_after_prior_cycles`

Same scenario for `watch_multi_with_reconnect`. Yields exactly one message.

**Test C** — `test_watch_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles`

Scenario:
- Connections 1–4 (idle reconnects #1–#3): same as above, all succeed
- Connection 5+ (idle reconnect #4): `websockets.connect` always raises
  `TimeoutError`
- `max_retries=3`

Assert: `pytest.raises((TimeoutError, OSError))` propagates after the budget
is exhausted. The exception does NOT propagate before 3 handshake failures.

**Test D** — `test_watch_multi_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles`

Same scenario for `watch_multi_with_reconnect`.

Run `uv run pytest tests/test_board_client.py -x` after writing the tests. Note
whether they pass or fail.

### Step 2: Extract `_connect_with_retry` helper

Add a private method to `BoardClient` in `src/board/client.py`:

```python
# Chunk: docs/chunks/watch_handshake_stale_retry - Shared reconnect-with-retry
async def _connect_with_retry(
    self,
    attempt: int,
    backoff: float,
    max_retries: int | None,
    max_backoff: float,
) -> tuple[int, float]:
    """Close, then connect with retry on retryable errors.

    Returns ``(0, 1.0)`` on success (attempt and backoff both reset).
    Raises the last retryable exception once the failure budget is exhausted.

    Callers that want a no-sleep first attempt (stale path: network was
    reachable) call this directly.  Callers that want a pre-sleep before
    the first attempt (spontaneous disconnect path) apply the sleep and
    backoff update themselves before calling.
    """
    while True:
        try:
            await self.close()
        except Exception:
            pass
        try:
            await self.connect()
            return 0, 1.0  # reset on successful connect
        except _RETRYABLE_ERRORS as connect_exc:
            attempt += 1
            if max_retries is not None and attempt > max_retries:
                raise connect_exc
            jitter = random.uniform(0, backoff * 0.5)
            wait_time = min(backoff + jitter, max_backoff)
            logger.warning(
                "Handshake failed during reconnect in %.1fs "
                "(attempt %d) exc=%s",
                wait_time,
                attempt,
                type(connect_exc).__name__,
            )
            await asyncio.sleep(wait_time)
            backoff = min(backoff * 2, max_backoff)
```

Place this method between `close()` and `register_swarm()` (i.e., before the
public watch-related methods), so it reads naturally as an internal reconnect
primitive.

### Step 3: Update `watch_with_reconnect` stale handler

Replace the manual inner `while True` loop inside `except StaleWatchError:`
(currently in `watch_with_reconnect`) with a call to `_connect_with_retry`:

Before:
```python
    except StaleWatchError:
        idle_reconnects += 1
        ...
        try:
            await self.close()
        except Exception:
            pass
        # Chunk: docs/chunks/watch_handshake_timeout_retry - ...
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
        # Chunk: docs/chunks/watch_reconnect_counter_reset - ...
        attempt = 0
```

After:
```python
    except StaleWatchError:
        idle_reconnects += 1
        ...
        # Chunk: docs/chunks/watch_handshake_stale_retry - Stale-driven reconnect;
        # handshake TimeoutError routes through shared retry loop (same budget as
        # spontaneous disconnects).
        attempt, backoff = await self._connect_with_retry(
            attempt, backoff, max_retries, max_backoff
        )
```

Note: the `try: await self.close()` block can be dropped because
`_connect_with_retry` calls `close()` itself at the top of each iteration.

### Step 4: Update `watch_with_reconnect` spontaneous-disconnect handler

Replace the manual inner `while True` loop inside `except _RETRYABLE_ERRORS:`
(in `watch_with_reconnect`) with a call to `_connect_with_retry`:

Before:
```python
        # Chunk: docs/chunks/board_watch_handshake_retry - Retry connect() on handshake errors
        while True:
            try:
                await self.close()
            except Exception:
                pass
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
                    "Handshake failed during reconnect in %.1fs "
                    "(attempt %d) exc=%s",
                    wait_time,
                    attempt,
                    type(connect_exc).__name__,
                )
                await asyncio.sleep(wait_time)
                backoff = min(backoff * 2, max_backoff)
```

After:
```python
        # Chunk: docs/chunks/watch_handshake_stale_retry - Shared retry loop (same
        # path used by stale-driven reconnect).
        attempt, backoff = await self._connect_with_retry(
            attempt, backoff, max_retries, max_backoff
        )
```

The initial back-off sleep for the spontaneous-disconnect path (the
`await asyncio.sleep(wait_time)` that lives just before the inner loop) stays
in place. The outer `attempt += 1` and budget check at the very start of
`except _RETRYABLE_ERRORS:` also stay — they account for the disconnect itself.
Only the inner connect-loop is replaced.

### Step 5: Apply the same changes to `watch_multi_with_reconnect`

Repeat Steps 3 and 4 for the `except StaleWatchError:` and
`except _RETRYABLE_ERRORS:` blocks inside `watch_multi_with_reconnect`.
The pattern is identical; only the log message context differs (channels vs
channel).

### Step 6: Run all tests

```bash
uv run pytest tests/test_board_client.py -v
```

All 49 existing tests plus the 4 new tests must pass (53 total). If any
previously-passing test fails, investigate and fix before proceeding.

### Step 7: Update code references in GOAL.md

Populate `code_references` in `docs/chunks/watch_handshake_stale_retry/GOAL.md`
frontmatter to reflect the actual implementation:

```yaml
code_references:
  - ref: src/board/client.py#BoardClient::_connect_with_retry
    implements: "Shared connect-with-retry helper — both stale-driven and
      spontaneous reconnect paths call this, ensuring identical retry semantics"
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "StaleWatchError handler now delegates to _connect_with_retry;
      opening-handshake TimeoutError on stale-driven reconnect retried, not fatal"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Same _connect_with_retry delegation in watch_multi_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_stale_handshake_timeout_after_prior_cycles
    implements: "Multi-cycle stale scenario: handshake timeout on reconnect #4+
      survives in watch_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_stale_handshake_timeout_after_prior_cycles
    implements: "Same for watch_multi_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles
    implements: "Safety valve still fires after max_retries consecutive stale-path
      handshake failures in watch_with_reconnect"
  - ref: tests/test_board_client.py#test_watch_multi_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles
    implements: "Same for watch_multi_with_reconnect"
```

### Step 8: Update parent chunk's code_references

Edit `docs/chunks/watch_handshake_timeout_retry/GOAL.md`. The two `code_references`
entries that reference `watch_with_reconnect` and `watch_multi_with_reconnect`
stale-handler coverage were premature; those methods now delegate to the unified
helper. Update those two entries to note they are now superseded by this chunk,
and add a reference to `_connect_with_retry`:

```yaml
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "StaleWatchError handler — original retry loop introduced here,
      superseded by docs/chunks/watch_handshake_stale_retry which unified both
      branches through _connect_with_retry"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Same — superseded by docs/chunks/watch_handshake_stale_retry"
```

## Risks and Open Questions

- **If the new tests in Step 1 pass immediately**: the bug was already fixed by
  the parent chunk's retry loop and the tests serve purely as regression coverage.
  The `_connect_with_retry` extraction in Steps 2–5 is still correct — it
  eliminates the risk of future divergence between the two paths.

- **Log message changes**: extracting to `_connect_with_retry` merges the log
  message "Handshake timeout on idle reconnect, retrying in %.1fs" and "Handshake
  failed during reconnect in %.1fs" into one string. Use a format that is
  accurate for both callers, e.g. "Handshake failed during reconnect in %.1fs
  (attempt %d) exc=%s". This is a cosmetic change; no behavior is affected.

- **`close()` call order**: `_connect_with_retry` calls `close()` on every
  iteration (including the first). The stale handler's existing `try: await
  self.close()` can be dropped when delegating to the helper (the helper handles
  it). If the existing `close()` is kept, the result is a redundant but harmless
  double-close on the first iteration since `close()` checks `if self._ws`.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?
-->