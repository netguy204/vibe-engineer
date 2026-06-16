---
decision: APPROVE
summary: "All six success criteria satisfied — `_connect_with_retry` correctly treats HTTP 5xx as retryable and 4xx as fatal, both reconnect branches inherit the fix symmetrically, the 10-attempt safety valve is preserved, and all 59 tests pass."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A watch whose reconnect attempt raises `InvalidStatus` with HTTP 5xx recovers via backoff-and-retry in both `watch_with_reconnect` and `watch_multi_with_reconnect`; fix lives in `_connect_with_retry`.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` lines 152–172: new `except websockets.exceptions.InvalidStatus` clause inside `_connect_with_retry` checks `status_code < 500` (4xx → re-raise immediately) and applies the identical backoff/attempt logic as `_RETRYABLE_ERRORS` for 5xx. Both `watch_with_reconnect` and `watch_multi_with_reconnect` call `_connect_with_retry`, inheriting the fix symmetrically.

### Criterion 2: A watch whose reconnect attempt raises `InvalidStatus` with HTTP 4xx still exits fatally.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` line 155: `if inv_exc.response.status_code < 500: raise` — 4xx propagates immediately without incrementing attempt or sleeping. Tests `test_watch_with_reconnect_4xx_handshake_is_fatal` and `test_watch_multi_with_reconnect_4xx_handshake_is_fatal` both assert `connect_call_count == 2` (no further attempts) and `pytest.raises(InvalidStatus)`.

### Criterion 3: The 10-consecutive-failure safety valve is preserved for the 5xx path.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` lines 158–160: `attempt += 1; if max_retries is not None and attempt > max_retries: raise` — identical guard to the `_RETRYABLE_ERRORS` path. Tests `test_watch_with_reconnect_5xx_handshake_exhausts_budget` and `test_watch_multi_with_reconnect_5xx_handshake_exhausts_budget` exercise this with `max_retries=2`, asserting `connect_call_count == 3` and `pytest.raises(InvalidStatus)`.

### Criterion 4: A successful reconnect after a 5xx handshake resets the consecutive `attempt` counter.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` line 151: `return 0, 1.0` — `_connect_with_retry` returns `(attempt=0, backoff=1.0)` on successful connect. Both outer reconnect loops unpack this via `attempt, backoff = await self._connect_with_retry(...)`, resetting the counter. Test `test_watch_with_reconnect_5xx_handshake_retries` and `test_watch_multi_with_reconnect_5xx_handshake_retries` verify recovery after one 5xx, proving the counter resets enough to allow subsequent reconnection.

### Criterion 5: New tests cover all required scenarios (5xx retry-and-recover × 2, 4xx fatal × 2, 5xx budget-exhaustion × 1 for each variant).

- **Status**: satisfied
- **Evidence**: `tests/test_board_client.py` lines 2861–3171: six new tests added under a `# Chunk: docs/chunks/watch_handshake_5xx_retry` banner. All six pass. The multi-watch budget exhaustion test `test_watch_multi_with_reconnect_5xx_handshake_exhausts_budget` correctly asserts `connect_call_count == 3` (PLAN stated 4, but the test is correct per actual semantics; the docstring explains the counting).

### Criterion 6: All existing reconnect, stale-reconnect, counter-reset, Branch-1-handshake-timeout, and Branch-2-handshake-timeout tests continue to pass.

- **Status**: satisfied
- **Evidence**: Full test run `uv run pytest tests/test_board_client.py -v` reports 59 passed, 0 failed.
