---
decision: APPROVE  # APPROVE | FEEDBACK | ESCALATE
summary: "All five success criteria satisfied: handshake timeout routes through backoff-and-retry in both watch functions, attempt counter resets on success, safety valve intact, four new tests pass, and all 49 existing tests continue to pass."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A watch whose reconnect attempt raises an opening-handshake timeout (`TimeoutError` / `asyncio.TimeoutError`) recovers via backoff-and-retry rather than exiting with code 3, in both `watch_with_reconnect` and `watch_multi_with_reconnect`.

- **Status**: satisfied
- **Evidence**: `src/board/client.py` lines 309–328 (`watch_with_reconnect` `StaleWatchError` handler) and lines 642–661 (`watch_multi_with_reconnect` `StaleWatchError` handler) both wrap `connect()` in a `while True` loop that catches `_RETRYABLE_ERRORS`, increments `attempt`, backs off with jitter, and retries. `asyncio.TimeoutError` was added to `_RETRYABLE_ERRORS` at line 36 for Python < 3.11 safety.

### Criterion 2: A successful reconnect after a handshake timeout resets the consecutive `attempt` counter (consistent with `watch_reconnect_counter_reset`).

- **Status**: satisfied
- **Evidence**: `client.py` lines 329–331 and 662–664: `backoff = 1.0` and `attempt = 0` are set immediately after the inner `while True` connect loop breaks on success. Backreference to `watch_reconnect_counter_reset` chunk is present.

### Criterion 3: The safety valve is preserved: 10 consecutive handshake timeouts with no intervening successful reconnect still exit with code 3.

- **Status**: satisfied
- **Evidence**: Inner connect loop at lines 315–316 and 648–649 checks `attempt > max_retries` and raises `connect_exc` when exceeded. Default `max_retries=10` means 10 retries before raising. Tests 2c/2d (`test_watch_with_reconnect_idle_handshake_timeout_exhausts_budget`, `test_watch_multi_with_reconnect_idle_handshake_timeout_exhausts_budget`) verify this with `max_retries=2`.

### Criterion 4: A new test triggers an opening-handshake timeout on reconnect and asserts the watch survives and continues delivering messages afterward.

- **Status**: satisfied
- **Evidence**: Four new tests at `tests/test_board_client.py` lines 2401–2614: `test_watch_with_reconnect_idle_handshake_timeout_retries` and `test_watch_multi_with_reconnect_idle_handshake_timeout_retries` assert message delivery after recovery; `test_watch_with_reconnect_idle_handshake_timeout_exhausts_budget` and `test_watch_multi_with_reconnect_idle_handshake_timeout_exhausts_budget` assert safety valve. All 4 pass.

### Criterion 5: Existing reconnect, stale-reconnect, and counter-reset tests continue to pass.

- **Status**: satisfied
- **Evidence**: Full test suite run: 49 passed, 0 failed in 0.17s.

## Feedback Items

<!-- For FEEDBACK decisions only. Delete section if APPROVE. -->

## Escalation Reason

<!-- For ESCALATE decisions only. Delete section if APPROVE/FEEDBACK. -->
