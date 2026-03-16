

# Implementation Plan

## Approach

Add a `--count N` option to `ve board watch-multi` that limits the number of
messages received before exiting. The implementation threads through three
layers:

1. **Client layer** (`src/board/client.py`): Add a `count` parameter to both
   `watch_multi()` and `watch_multi_with_reconnect()`. When `count > 0`, the
   generator yields at most `count` messages then returns. When `count == 0`,
   it streams indefinitely (current behavior, fully backwards-compatible).

2. **CLI layer** (`src/cli/board.py`): Add `--count` option to the
   `watch-multi` Click command. Wire it through to the client methods. Default
   is `1` (exit after first message), matching the event-driven agent pattern.

3. **Skill template** (`src/templates/commands/swarm-monitor.md.jinja2`):
   Update the swarm-monitor skill to use `--count 1` with `run_in_background`,
   replacing the indefinite stream with an event-driven re-launch loop.

The `--count` default of `1` is a **behavioral change** from the current
indefinite streaming default, but this is intentional: the GOAL specifies
default 1, and current callers (swarm-monitor) will be updated in the same
chunk. No external consumers depend on the default being "indefinite".

TDD approach per TESTING_PHILOSOPHY.md: write failing tests for count-limited
behavior first, then implement the feature.

## Sequence

### Step 1: Write failing client tests for count-limited watch_multi

Location: `tests/test_board_client.py`

Add tests:
- **`test_watch_multi_count_limits_messages`**: Set up a mock WebSocket that
  would deliver 3 messages. Call `watch_multi(channels, count=2)`. Assert only
  2 messages are yielded and the generator returns cleanly.
- **`test_watch_multi_count_zero_streams_all`**: Confirm `count=0` yields all
  available messages (backwards-compatible behavior).
- **`test_watch_multi_count_default_one`**: Confirm that calling `watch_multi`
  without explicit count yields exactly 1 message (the new default).

Follow the existing test patterns: mock `self._ws.recv()` to return
pre-built JSON frames, mock `self._ws.send()` to capture outbound frames.

### Step 2: Implement count parameter in watch_multi

Location: `src/board/client.py` — `BoardClient.watch_multi()`

Add `count: int = 1` parameter. Track a `delivered` counter. After yielding
a message and re-sending the watch frame, increment `delivered`. If
`count > 0 and delivered >= count`, return from the generator.

The `while active_channels:` loop gains an additional exit condition:
```python
delivered += 1
if count > 0 and delivered >= count:
    return
```

Add chunk backreference comment above the method.

### Step 3: Propagate count through watch_multi_with_reconnect

Location: `src/board/client.py` — `BoardClient.watch_multi_with_reconnect()`

Add `count: int = 1` parameter. Track total messages delivered across
reconnects. Pass `count=0` to the inner `watch_multi()` call (the reconnect
wrapper manages its own counting to handle reconnects correctly). After
yielding each message, increment the wrapper's counter and return when the
limit is reached.

This ensures that if a reconnect happens mid-stream with `--count 5`, the
total across reconnects still caps at 5.

Add a test: **`test_watch_multi_reconnect_respects_count`** — disconnects
after 1 message, reconnects, delivers 1 more, total count=2 should stop.

### Step 4: Write failing CLI tests for --count flag

Location: `tests/test_board_cli.py`

Add tests:
- **`test_watch_multi_count_flag_exits_after_n`**: Invoke with `--count 2`,
  mock yields 3 messages, assert only 2 appear in output and exit code is 0.
- **`test_watch_multi_count_zero_streams_all`**: Invoke with `--count 0`,
  mock yields 3 messages (then generator returns), assert all 3 in output.
- **`test_watch_multi_default_count_one`**: Invoke without `--count`, mock
  yields 2 messages, assert only 1 appears in output (verifying default=1).

Follow existing test patterns: patch `BoardClient`, use `mock_watch_multi`
async generators, use `runner.invoke()`.

### Step 5: Add --count option to watch-multi CLI command

Location: `src/cli/board.py` — `watch_multi_cmd()`

Add Click option:
```python
@click.option("--count", default=1, type=int,
              help="Exit after N messages (0 = stream indefinitely)")
```

Pass `count` to `client.watch_multi()` or
`client.watch_multi_with_reconnect()`. The existing `async for msg in gen:`
loop doesn't need to change — the generator itself handles the limit.

Update the docstring to mention the `--count` behavior.

### Step 6: Update swarm-monitor skill template

Location: `src/templates/commands/swarm-monitor.md.jinja2`

Update Phase 3 to use `--count 1`:
```
ve board watch-multi <channel1> <channel2> ... --count 1 --swarm <swarm_id>
```

Update Phase 4 to describe the event-driven loop pattern:
1. Launch `watch-multi --count 1` with `run_in_background`
2. Agent gets notified when the command exits (one message received)
3. Process and display the message
4. Re-launch `watch-multi --count 1` with `run_in_background`
5. Repeat until operator stops the session

Remove language about "periodically check the background task output" and
"the monitoring continues until the operator stops the session or the
background task exits unexpectedly" — the new pattern is deterministic
exit-on-message, not indefinite streaming.

Update Key Concepts to explain the `--count` flag and the re-launch pattern.

### Step 7: Run tests and verify

Run `uv run pytest tests/test_board_client.py tests/test_board_cli.py -v` to
confirm all new and existing tests pass. The existing watch-multi tests
should continue passing since the mock generators only yield finite messages
(which will be consumed before any count limit applies, or the count limit
will match the existing behavior).

### Step 8: Update GOAL.md code_paths

Location: `docs/chunks/watchmulti_exit_on_message/GOAL.md`

Update the `code_paths` frontmatter to list:
```yaml
code_paths:
  - src/board/client.py
  - src/cli/board.py
  - src/templates/commands/swarm-monitor.md.jinja2
  - tests/test_board_client.py
  - tests/test_board_cli.py
```

## Risks and Open Questions

- **Default change from indefinite to count=1**: The GOAL explicitly requests
  default=1, which changes the CLI's default behavior. This is safe because
  the only known consumer (swarm-monitor) is updated in the same chunk, and
  the `watch-multi` command is not yet widely used (it was just introduced in
  the parent chunk `multichannel_watch`).

- **Count tracking across reconnects**: The reconnect wrapper must track total
  delivered messages across reconnects, not per-connection. The inner
  `watch_multi` should stream indefinitely (`count=0`) while the reconnect
  wrapper manages the cap. This avoids the edge case where a reconnect resets
  the count.

- **Existing tests**: The mock generators in existing tests yield a finite
  number of messages (2-3). With `count` defaulting to 1, these tests will now
  only see 1 message. The existing tests will need their mock generators or
  assertions updated, OR they need to pass explicit `count=0` to preserve
  the original streaming behavior. This will be handled during Step 4/5 by
  reviewing and adjusting existing tests as needed.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
