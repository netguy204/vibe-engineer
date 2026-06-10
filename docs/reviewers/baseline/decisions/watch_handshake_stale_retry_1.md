---
decision: APPROVE
summary: "All four success criteria satisfied — _connect_with_retry unifies both reconnect branches, safety valve preserved, four new tests cover multi-cycle stale scenarios, and all 53 tests pass."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A watch whose `StaleWatchError`-driven forced reconnect raises an opening-handshake TimeoutError / asyncio.TimeoutError recovers via backoff-and-retry rather than exiting with code 3, in both watch_with_reconnect and watch_multi_with_reconnect.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` lines 345-350 (`watch_with_reconnect` stale handler) and lines 631-636 (`watch_multi_with_reconnect` stale handler) both call `await self._connect_with_retry(attempt, backoff, max_retries, max_backoff)`. `_connect_with_retry` (lines 126-166) catches `_RETRYABLE_ERRORS` (which includes both `TimeoutError` and `asyncio.TimeoutError`) and retries with exponential backoff instead of propagating fatal.

### Criterion 2: The safety valve is preserved: 10 consecutive handshake timeouts on the stale-driven path with no intervening successful reconnect still exit with code 3 (matching the safety valve behavior on the spontaneous branch).

- **Status**: satisfied
- **Evidence**: `_connect_with_retry` increments the shared `attempt` counter on each failure and raises when `attempt > max_retries`. On a successful connect it returns `(0, 1.0)` resetting the budget. Tests C and D (`test_watch_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles` and `test_watch_multi_with_reconnect_stale_handshake_timeout_safety_valve_with_prior_cycles`) verify the valve fires after `max_retries=3` consecutive stale-path failures.

### Criterion 3: A new test triggers an opening-handshake timeout specifically on the stale-driven forced-reconnect path and asserts the watch survives and continues delivering messages afterward, for both single-channel and multi-channel variants.

- **Status**: satisfied
- **Evidence**: Tests A and B (`test_watch_with_reconnect_stale_handshake_timeout_after_prior_cycles` lines 2623-2690 and `test_watch_multi_with_reconnect_stale_handshake_timeout_after_prior_cycles` lines 2694-2756) reproduce the exact production sequence: 3 prior idle cycles succeed, then idle reconnect #4's opening handshake raises `TimeoutError`, retries, and the watch survives to deliver the message.

### Criterion 4: All existing reconnect, stale-reconnect, counter-reset, and Branch-1-handshake-timeout tests continue to pass.

- **Status**: satisfied
- **Evidence**: `uv run pytest tests/test_board_client.py` reports 53 passed (49 pre-existing + 4 new). Zero failures.
