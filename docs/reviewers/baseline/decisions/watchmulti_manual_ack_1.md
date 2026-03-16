---
decision: APPROVE
summary: "All success criteria satisfied — auto_ack parameter flows correctly through client and CLI layers, tests cover all four criteria, all 58 tests pass"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: `ve board watch-multi --no-auto-ack ch1 ch2` delivers messages with position but doesn't advance cursor

- **Status**: satisfied
- **Evidence**: CLI adds `--no-auto-ack` flag (src/cli/board.py:267), passes `auto_ack=not no_auto_ack` to client (line 305-309), skips `save_cursor()` when flag is set (line 313-318). Tests: `test_watch_multi_no_auto_ack_skips_save_cursor` and `test_watch_multi_no_auto_ack_includes_position_in_output`.

### Criterion 2: After crash and restart, unacked messages re-deliver

- **Status**: satisfied
- **Evidence**: Client `watch_multi()` skips re-sending watch frame when `auto_ack=False` (src/board/client.py:342), so the server cursor stays at the pre-message position. CLI skips `save_cursor()`, so the persisted cursor also stays. On restart, both server and local cursor are at the pre-message position, causing re-delivery. `test_watch_multi_reconnect_auto_ack_false_preserves_cursors` verifies the reconnect wrapper still tracks cursors internally for session-level dedup while passing `auto_ack=False` through.

### Criterion 3: Default behavior (auto-ack) unchanged

- **Status**: satisfied
- **Evidence**: `auto_ack` defaults to `True` in both `watch_multi()` (line 254) and `watch_multi_with_reconnect()` (line 358). Existing mock signatures updated to include `auto_ack=True` default. `test_watch_multi_auto_ack_default_resends_cursor` and `test_watch_multi_default_auto_ack_saves_cursor` verify backward compatibility. All 37 pre-existing tests pass unchanged.

### Criterion 4: Output includes position field when `--no-auto-ack` is set

- **Status**: satisfied
- **Evidence**: src/cli/board.py:314 formats output as `[{channel}] position={position} {plaintext}` when `no_auto_ack` is set. `test_watch_multi_no_auto_ack_includes_position_in_output` asserts `"[ch-alpha] position=42 hello world"` in output.
