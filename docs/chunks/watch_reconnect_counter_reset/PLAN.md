

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The fix is a one-liner repeated in two places: add `attempt = 0` immediately
after `backoff = 1.0` in the successful-reconnect path of both
`watch_with_reconnect` and `watch_multi_with_reconnect`.

The framing comes from the parent chunk `watch_idle_reconnect_budget`: a
successful reconnect is evidence of a healthy network. Just as that chunk
treated idle re-registrations as budget-exempt, this chunk treats a successful
reconnect as a budget reset. The "10 attempts" ceiling remains meaningful only
against *consecutive* failures; once the network proves itself reachable the
counter must start fresh.

We follow the project's TDD practice (TESTING_PHILOSOPHY.md): write the two
failing tests first, then apply the two-line fix, then update the stale comment
in the existing backoff-reset test.

No new dependencies, no new architectural decisions. No subsystems are relevant.

## Sequence

### Step 1: Write failing tests

Add two new `@pytest.mark.asyncio` tests to `tests/test_board_client.py`,
immediately after the existing `# Chunk: docs/chunks/watch_idle_reconnect_budget`
block (around line 1991):

---

**Test A — `test_watch_with_reconnect_intermittent_transients_do_not_accumulate`**

Goal: verify that N+1 transient disconnects spread across N+1 individual
connections — each followed by a successful reconnect — do not exhaust the
budget.  With the bug the test raises; with the fix it returns the final
message.

Setup:
- `max_retries=3`
- 5 transient disconnects (N+1 = 5 > max_retries=3)
- Mock factory: connections 1–5 each return `challenge + auth_ok` (consumed
  by `connect()`), then `ConnectionClosedError` on the next `recv()` inside
  the watch loop.  Connection 6 returns `challenge + auth_ok + message`.
- Patch `asyncio.sleep` and `random.uniform` so timing is deterministic.

Assertions:
- `result["position"]` is the expected value.
- `sleep_mock.call_count == 5` (one sleep per transient failure).

---

**Test B — `test_watch_multi_reconnect_intermittent_transients_do_not_accumulate`**

Goal: same semantics for `watch_multi_with_reconnect`.  The multi-channel
variant already resets `attempt` on *message receipt*, but a rapid sequence of
reconnects without an intervening message can still accumulate the counter.

Setup:
- `max_retries=3`, `count=1`
- 5 transient `ConnectionClosedError`s, each on a fresh connection, no
  messages delivered until the final connection.
- Connection 6 returns `challenge + auth_ok` followed by the `watch_multi`
  message sequence.

Because `watch_multi_with_reconnect` spawns `watch_multi` as an inner async
generator, the mock must satisfy the full protocol:
  1. Each reconnect connection provides `challenge + auth_ok`.
  2. The inner `watch_multi` immediately raises `ConnectionClosedError` on
     the first `recv()` (before any message).
  3. The final connection provides `challenge + auth_ok`, then the server
     sends the watch `message` frame.

Assertions:
- One dict is yielded with `channel`, `position`, `body`, `sent_at`.
- `sleep_mock.call_count == 5`.

Run `uv run pytest tests/test_board_client.py -k "intermittent_transients" -x`
and confirm both tests **fail** (budget exhausted / raise before fix).

### Step 2: Fix `watch_with_reconnect` in `src/board/client.py`

Locate the end of the `except _RETRYABLE_ERRORS` handler in
`BoardClient.watch_with_reconnect`.  After the existing `backoff = 1.0` reset
(the line tagged `# Chunk: docs/chunks/websocket_reconnect_tuning - Reset
backoff after successful reconnect`), add:

```python
# Chunk: docs/chunks/watch_reconnect_counter_reset - Reset attempt counter after successful reconnect
attempt = 0
```

This is the only code change needed for the single-channel variant.  The reset
is placed *after* the inner reconnect loop (which handles handshake retries) so
it only fires when `connect()` genuinely succeeded.

### Step 3: Fix `watch_multi_with_reconnect` in `src/board/client.py`

Locate the analogous spot in `BoardClient.watch_multi_with_reconnect` — the
`backoff = 1.0` line at the end of its `except _RETRYABLE_ERRORS` handler
(tagged `# Chunk: docs/chunks/board_watch_reconnect_fix`).  Add the same reset
immediately after:

```python
# Chunk: docs/chunks/watch_reconnect_counter_reset - Reset attempt counter after successful reconnect
attempt = 0
```

Note: this handler's `backoff = 1.0` is distinct from the `except
StaleWatchError` handler's `backoff = 1.0` — only the `_RETRYABLE_ERRORS` one
is relevant here.

### Step 4: Update the stale comment in the existing backoff-reset test

In `tests/test_board_client.py`, find the comment inside
`test_watch_with_reconnect_resets_backoff_after_success`:

```python
    # The attempt counter is NOT reset, preserving max_retries semantics.
```

Replace it with:

```python
    # The attempt counter IS reset after each successful reconnect (attempt=0),
    # so the ceiling applies only to consecutive failures, not lifetime failures.
```

This makes the comment accurate without changing any assertions (the test's
sleep-duration assertions are unaffected by attempt reset behavior).

### Step 5: Run the full test suite and confirm green

```bash
uv run pytest tests/test_board_client.py -x
```

All existing reconnect-exhaustion tests must continue to pass (consecutive
failures still exit with the right exception).  The two new tests must now pass.

### Step 6: Update `code_paths` in the chunk GOAL.md

Add the touched files to the `code_paths` list in
`docs/chunks/watch_reconnect_counter_reset/GOAL.md`:

```yaml
code_paths:
  - src/board/client.py
  - tests/test_board_client.py
```

## Risks and Open Questions

- The existing test `test_watch_with_reconnect_resets_backoff_after_success`
  has 5 total connections with 4 transient failures before a final message.
  With max_retries=10 and only 4 failures, the test passes regardless of
  whether attempt resets.  Confirm that no assertion implicitly relies on the
  bug (e.g., checking sleep count / backoff values that would change if attempt
  resets sooner).  Inspection shows the assertions only validate backoff
  durations (all 1.0s), which are unaffected.

- `watch_multi_with_reconnect` already resets `attempt = 0` on *message
  receipt* (line ~588).  The new reset-on-reconnect is additive and doesn't
  conflict; it covers the case where no message arrives before the next
  disconnect.

## Deviations

### Safety valve tests updated to reflect new semantics

The plan stated "All existing reconnect-exhaustion tests must continue to pass."
Four existing tests could not pass unchanged:

- `test_watch_with_reconnect_max_retries`
- `test_watch_with_reconnect_default_max_retries`
- `test_watch_with_reconnect_real_failure_exhausts_budget`
- `test_watch_multi_reconnect_default_max_retries`

All four used a factory where every connection returned `[challenge, auth_ok,
CCE]`, meaning `connect()` always succeeded but the watch `recv()` always
failed immediately.  With the fix, `attempt` resets to 0 after each successful
`connect()`, so these tests looped indefinitely.

**Reason this is correct**: the fix intentionally changes the semantics of
`max_retries`.  The safety valve now protects against consecutive `connect()`
handshake failures — not against consecutive watch-recv failures after a
healthy auth handshake.  A successful `connect()` (challenge + auth_ok) proves
the network is reachable; the prior failures are stale evidence.  Subsequent
recv failures start a fresh sequence.

The four tests were updated: the initial connection still succeeds (so the
watch can start), but subsequent reconnect attempts fail on the challenge recv,
making `connect()` itself fail.  This correctly exercises the surviving safety
valve path.  Docstrings were updated to describe the new semantics.