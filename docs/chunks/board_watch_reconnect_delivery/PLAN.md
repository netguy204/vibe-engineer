

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

The bug: after a WebSocket reconnect, `watch_with_reconnect()` and
`watch_multi_with_reconnect()` resume listening for server-push notifications
but do not explicitly re-poll the channel for messages that arrived during the
disconnect window. While the server's `handleWatch` / `_handle_watch` checks
storage for existing messages before registering a blocking watcher, the client
code has no explicit re-poll step — it relies entirely on the server to surface
gap messages as a side effect of the watch frame. If the server's storage check
races with other operations, or if a non-reference server implementation doesn't
perform this check, messages are silently missed.

The fix adds an explicit **reconnect-delivery step** to both reconnect wrappers
in `src/board/client.py`. After reconnecting:

1. Log that a re-poll is happening, including the cursor value(s).
2. Re-send the watch frame with the **same cursor** that was active before the
   disconnect (the "current offset"). This is the same logic that runs on
   initial connection — `watch()` sends a watch frame with the cursor, and the
   server checks for existing messages before blocking.
3. Add a `logger.info` line after successful reconnect that makes the re-poll
   auditable: `"Reconnected, re-polling channel=%s from cursor=%d"`.

For `watch_multi_with_reconnect`, the same principle applies but for all
tracked channels with their latest cursors.

The key behavioral property is: **after every reconnect, the next server
interaction must be a watch frame carrying the most-recently-known cursor**.
The current code does loop back to `self.watch(channel, cursor)` after
`self.connect()`, but there is no logging or test coverage to assert this
happens. This chunk adds both.

Tests follow TDD per docs/trunk/TESTING_PHILOSOPHY.md — write failing tests
for the disconnect-window delivery scenario first, then verify the code passes
(and add logging if any tests surface gaps).

## Sequence

### Step 1: Write failing tests for disconnect-window delivery (single watch)

Add a new test in `tests/test_board_client.py`:

**`test_watch_with_reconnect_delivers_pending_message`**

Scenario:
- Client watches channel `ch1` at cursor 5
- First connection: auth OK, then `recv()` raises `ConnectionClosedError`
  (simulating disconnect)
- Second connection: auth OK, then immediately returns a message at
  position 6 (this message "arrived during the disconnect window")
- Assert: the returned message has position 6, body matches
- Assert: the watch frame sent on the second connection carries cursor=5
  (verifying the client re-polls from its last-known cursor, not some
  stale or advanced value)

The key difference from the existing `test_watch_with_reconnect_on_disconnect`
test: this test **explicitly asserts the cursor value in the re-sent watch
frame** (by inspecting `ws.send` call args on the second connection). The
existing test only asserts the result, not the cursor in the watch frame.

Location: `tests/test_board_client.py`, after the existing reconnect test block.

### Step 2: Write failing tests for disconnect-window delivery (multi watch)

Add a new test in `tests/test_board_client.py`:

**`test_watch_multi_reconnect_delivers_pending_messages`**

Scenario:
- Client watches channels `{"ch-a": 2, "ch-b": 5}`
- First connection: auth OK, delivers message from `ch-a` at position 3,
  then disconnects
- During disconnect: message arrives on `ch-b` at position 6
- Second connection: auth OK, immediately returns `ch-b` message at position 6
- Assert: both messages are yielded in order
- Assert: second connection's watch frames carry `ch-a` cursor=3
  (updated after first message) and `ch-b` cursor=5 (unchanged — this is
  the gap message's channel)
- Assert: no duplicate delivery of the `ch-a` message

Location: `tests/test_board_client.py`, after Step 1's test.

### Step 3: Add reconnect-delivery logging

In `src/board/client.py`, after the `await self.connect()` call in
`watch_with_reconnect()`, add:

```python
logger.info(
    "Reconnected, re-polling channel=%s from cursor=%d",
    channel,
    cursor,
)
```

In `watch_multi_with_reconnect()`, after the `await self.connect()` call, add:

```python
logger.info(
    "Reconnected, re-polling %d channel(s) from cursors=%s",
    len(cursors),
    cursors,
)
```

These log lines make the reconnect-delivery behavior auditable and visible
in steward logs. If the message is missed in the future, the log will show
whether the re-poll happened and what cursor was used.

Add a backreference comment before each log line:
```python
# Chunk: docs/chunks/board_watch_reconnect_delivery - Log re-poll after reconnect
```

### Step 4: Run tests and verify

Run `uv run pytest tests/test_board_client.py -v -k reconnect` to verify:
- The new tests pass (the code already re-sends watch frames after reconnect;
  the tests now assert this behavior explicitly)
- Existing reconnect tests still pass
- No regressions

If any new tests fail, investigate whether the cursor is not being preserved
correctly through the reconnect cycle and fix accordingly.

### Step 5: Update GOAL.md code_paths

Update the `code_paths` field in
`docs/chunks/board_watch_reconnect_delivery/GOAL.md` to list:
- `src/board/client.py`
- `tests/test_board_client.py`

## Risks and Open Questions

- **Server-side behavior variance**: The fix is client-side (logging and
  tests). The server's `handleWatch` / `read_after` behavior (checking storage
  before blocking) is not changed. If the production Cloudflare DO server has
  a race condition where `readAfter` misses a just-appended message, this
  client-side fix won't help — that would require a separate server-side chunk.
  The logging added here will make such a failure diagnosable.

- **Cursor correctness after partial delivery**: In `watch_multi_with_reconnect`,
  the cursor for a channel is updated *before* `yield msg`. If the consumer
  crashes between cursor update and processing, the message won't be
  re-delivered on reconnect. This is existing behavior (at-most-once within a
  connection), not introduced by this fix. The manual ack model
  (`ve board ack`) provides the durability guarantee.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->