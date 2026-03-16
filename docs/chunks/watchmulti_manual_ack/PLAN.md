

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Add an `auto_ack` parameter (default `True`) to the client-layer `watch_multi()` and `watch_multi_with_reconnect()` methods. When `auto_ack=False`, the client skips re-sending the watch frame with the updated cursor after yielding a message—the cursor stays where it was, so the server will re-deliver the same message on reconnect.

At the CLI layer, add a `--no-auto-ack` flag to `ve board watch-multi`. When set, it:
1. Passes `auto_ack=False` to the client
2. Skips the `save_cursor()` call after each message
3. Includes the message position in the output so the consumer can later call `ve board ack <channel> <position>`

The existing `ve board ack` command already handles manual cursor advancement—no changes needed there.

Default behavior (auto-ack) remains unchanged, preserving backward compatibility for the swarm-monitor use case.

Following docs/trunk/TESTING_PHILOSOPHY.md, tests are written first (TDD) and focus on behavioral semantics: verifying that cursors are/aren't advanced, that output includes position when expected, and that re-delivery works after simulated crash.

## Sequence

### Step 1: Write client-layer tests for `auto_ack=False`

Add tests to `tests/test_board_client.py`:

1. **`test_watch_multi_auto_ack_false_skips_cursor_resend`**: When `auto_ack=False`, after yielding a message the client does NOT re-send a watch frame with the updated cursor. Verify by checking that only the initial watch frames are sent (no re-sends after message delivery).

2. **`test_watch_multi_auto_ack_default_resends_cursor`**: Confirm existing behavior—when `auto_ack` is not specified (defaults to `True`), the client re-sends watch frames with updated cursor after each message. This is a characterization test ensuring we don't break existing behavior.

3. **`test_watch_multi_reconnect_auto_ack_false_preserves_cursors`**: When `auto_ack=False` and reconnect occurs, the reconnect wrapper still updates its internal cursor tracking (so it doesn't re-deliver already-yielded messages within the same session), but the yielded messages still carry position for external acking.

Location: `tests/test_board_client.py`

### Step 2: Implement client-layer `auto_ack` parameter

Modify `BoardClient.watch_multi()` in `src/board/client.py`:

- Add `auto_ack: bool = True` parameter
- When `auto_ack=False`, skip the re-send of the watch frame after yielding (lines 333-341 in current code). The message is still yielded with its position.
- The initial watch frames are always sent (they establish the subscription).

Modify `BoardClient.watch_multi_with_reconnect()`:

- Add `auto_ack: bool = True` parameter
- Pass `auto_ack` through to inner `watch_multi()` call
- The reconnect wrapper's internal cursor tracking (`cursors[msg["channel"]] = msg["position"]`) should still update when `auto_ack=False`—this is session-level tracking for reconnect, not durable acking. On reconnect, the wrapper re-subscribes from the last position it saw, preventing duplicate delivery within the same process lifetime.

Location: `src/board/client.py`

### Step 3: Write CLI-layer tests for `--no-auto-ack`

Add tests to `tests/test_board_cli.py`:

1. **`test_watch_multi_no_auto_ack_skips_save_cursor`**: With `--no-auto-ack`, `save_cursor()` is never called after message delivery. Verify via mock assertion.

2. **`test_watch_multi_no_auto_ack_includes_position_in_output`**: With `--no-auto-ack`, output format changes to `[channel] position=N message text` so the consumer knows what to ack.

3. **`test_watch_multi_default_auto_ack_saves_cursor`**: Without `--no-auto-ack`, existing behavior is preserved—`save_cursor()` is called and output does NOT include position.

4. **`test_watch_multi_no_auto_ack_passes_auto_ack_false_to_client`**: Verify that `--no-auto-ack` flag results in `auto_ack=False` being passed to the client method.

Location: `tests/test_board_cli.py`

### Step 4: Implement CLI `--no-auto-ack` flag

Modify `watch_multi_cmd()` in `src/cli/board.py`:

- Add `@click.option("--no-auto-ack", is_flag=True, help="Don't auto-advance cursor; include position in output for manual acking")`
- Add `no_auto_ack` parameter to the function signature
- In `_watch_multi()`:
  - Pass `auto_ack=not no_auto_ack` to both `client.watch_multi()` and `client.watch_multi_with_reconnect()`
  - When `no_auto_ack` is set:
    - Change output format to `[{channel}] position={position} {plaintext}` (position included for ack)
    - Skip the `save_cursor()` call
  - When `no_auto_ack` is not set: preserve existing behavior exactly
- Update the docstring to document the new flag
- Add a backreference comment: `# Chunk: docs/chunks/watchmulti_manual_ack - Manual ack mode`

Location: `src/cli/board.py`

### Step 5: Run tests and verify

Run the full test suite to confirm:
- All new tests pass
- All existing tests pass (backward compatibility)
- `uv run pytest tests/test_board_client.py tests/test_board_cli.py -v`

## Dependencies

- Parent chunk `watchmulti_exit_on_message` must be complete (it is—status ACTIVE). Its `--count` flag and count-limited delivery are the foundation this chunk builds on.
- The existing `ve board ack` command already handles manual cursor advancement. No changes needed.

## Risks and Open Questions

- **Reconnect cursor semantics with `auto_ack=False`**: The reconnect wrapper must still track cursors internally for session-level deduplication, even when not durably acking. This is a subtle distinction—internal cursor tracking prevents the same message from being yielded twice within a process lifetime, while the consumer handles durable acking via `ve board ack`. The design ensures both properties hold.
- **Output format change**: Adding `position=N` to output when `--no-auto-ack` is set changes the parseable format. Consumers that parse `[channel] message` will need to account for the new prefix. This is acceptable because it only activates with an explicit opt-in flag.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
