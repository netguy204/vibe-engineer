---
decision: APPROVE
summary: "All four success criteria satisfied — StaleWatchError sentinel cleanly separates idle timeouts from genuine failures, budget reset on message delivery works in both wrappers, and all 43 tests pass including 4 new idle-reconnect tests."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: Watch survives indefinitely on an idle channel (no messages for hours)

- **Status**: satisfied
- **Evidence**: `watch_with_reconnect` catches `StaleWatchError` in a dedicated branch (client.py:287) that reconnects without incrementing `attempt`. Simulated with 12 idle cycles (>max_retries=3) in `test_watch_with_reconnect_idle_does_not_exhaust_budget` — watch succeeds. Same pattern in `watch_multi_with_reconnect` (client.py:598) with `test_watch_multi_with_reconnect_idle_does_not_exhaust_budget`.

### Criterion 2: Transient network failures still count against the reconnect budget and eventually terminate (safety valve preserved)

- **Status**: satisfied
- **Evidence**: The `except _RETRYABLE_ERRORS` branch (client.py:309, 617) still increments `attempt` and raises when `attempt > max_retries`. `test_watch_with_reconnect_real_failure_exhausts_budget` confirms genuine `ConnectionClosedError`s exhaust the budget and propagate.

### Criterion 3: Counter resets on successful message delivery

- **Status**: satisfied
- **Evidence**: In `watch_with_reconnect`, on message receipt: `idle_reconnects = 0; current_stale_timeout = stale_timeout` (client.py:280-281). In `watch_multi_with_reconnect`, the inner `async for` resets `attempt = 0; backoff = 1.0; idle_reconnects = 0; current_stale_timeout = stale_timeout` (client.py:588-591). Validated by `test_watch_multi_with_reconnect_budget_resets_on_message`.

### Criterion 4: Existing reconnect tests pass; new test covers the idle-reconnect path

- **Status**: satisfied
- **Evidence**: All 43 tests pass (`uv run pytest tests/test_board_client.py -v`). Four new tests added under the `# Chunk: docs/chunks/watch_idle_reconnect_budget - Idle reconnect budget tests` marker (test_board_client.py:1991): `test_watch_with_reconnect_idle_does_not_exhaust_budget`, `test_watch_with_reconnect_real_failure_exhausts_budget`, `test_watch_multi_with_reconnect_idle_does_not_exhaust_budget`, `test_watch_multi_with_reconnect_budget_resets_on_message`.
