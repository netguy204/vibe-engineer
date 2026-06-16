---
status: ACTIVE
ticket: null
parent_chunk: watch_handshake_timeout_retry
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
- ref: src/board/client.py#BoardClient::_connect_with_retry
  implements: "Catches InvalidStatus; retries on 5xx, raises immediately on 4xx"
- ref: tests/test_board_client.py#test_watch_with_reconnect_5xx_handshake_retries
  implements: "watch_with_reconnect recovers from 5xx during handshake"
- ref: tests/test_board_client.py#test_watch_with_reconnect_4xx_handshake_is_fatal
  implements: "watch_with_reconnect propagates 4xx immediately"
- ref: tests/test_board_client.py#test_watch_with_reconnect_5xx_handshake_exhausts_budget
  implements: "watch_with_reconnect safety valve fires on sustained 5xx"
- ref: tests/test_board_client.py#test_watch_multi_with_reconnect_5xx_handshake_retries
  implements: "watch_multi_with_reconnect recovers from 5xx during handshake"
- ref: tests/test_board_client.py#test_watch_multi_with_reconnect_4xx_handshake_is_fatal
  implements: "watch_multi_with_reconnect propagates 4xx immediately"
- ref: tests/test_board_client.py#test_watch_multi_with_reconnect_5xx_handshake_exhausts_budget
  implements: "watch_multi_with_reconnect safety valve fires on sustained 5xx"
narrative: null
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- entity_canonical_clone
- entity_claude_autoattach
- entity_config_toml
- entity_worktree_attach
- watch_handshake_stale_retry
---

# Chunk Goal

## Minor Goal

The handshake-transient-as-retryable semantic covers **server-side 5xx
responses during the WebSocket opening handshake** alongside
`TimeoutError` / `ConnectionClosedError`. A
`websockets.exceptions.InvalidStatus` raised with an HTTP 5xx status code
is treated identically to those errors — it routes through the shared
`_connect_with_retry` helper, increments the consecutive `attempt`
counter, backs off, and retries — so a transient server outage during a
reconnect handshake does not kill a long-lived watch.

4xx responses (auth, not-found, malformed handshake request) remain
fatal. They represent a real configuration or identity problem that
retry cannot resolve, and surfacing them immediately is correct — the
operator needs to notice and fix the request, not wait for it to
"come back." The 10-consecutive-failure safety valve still applies to
the 5xx path, so a sustained server outage exits cleanly with code 3
rather than retrying forever.

### Reported pattern

The vibe-engineer steward's own watch died on this failure mode on
2026-06-16 (channel `vibe-engineer-steward`, cursor 76, after ~3 hours
of healthy uptime with multiple successful reconnects):

    [WARNING] board.client: WebSocket disconnected, reconnecting in 1.0s
              (attempt 1) exc=ConnectionClosedError
    Traceback (most recent call last):
      ...
      File ".../websockets/client.py", line 144, in process_response
        raise InvalidStatus(response)
    websockets.exceptions.InvalidStatus: server rejected WebSocket
              connection: HTTP 500

The disconnect-driven reconnect attempt's handshake itself was answered
with HTTP 500 by the server — a different exception type than
`TimeoutError` or `ConnectionClosedError`, not caught by the existing
retryable-error branch, propagated as fatal exit 3. This is the third
sibling failure mode in the same shared-reconnect-loop family:

| Handshake failure mode      | Treated as     | Owning chunk                       |
| --------------------------- | -------------- | ---------------------------------- |
| `TimeoutError`              | Retryable      | `watch_handshake_timeout_retry`    |
| Stale-driven `TimeoutError` | Retryable      | `watch_handshake_stale_retry`      |
| `InvalidStatus` HTTP 5xx    | Retryable here | this chunk                         |
| `InvalidStatus` HTTP 4xx    | Fatal          | (unchanged — correct as-is)        |

## Success Criteria

- A watch whose reconnect attempt raises
  `websockets.exceptions.InvalidStatus` with an HTTP 5xx status code
  recovers via backoff-and-retry rather than exiting with code 3, in
  both `BoardClient.watch_with_reconnect` and
  `watch_multi_with_reconnect`. The fix lives in `_connect_with_retry`
  (or the shared retryable-error tuple it consults) so both reconnect
  branches inherit it symmetrically.
- A watch whose reconnect attempt raises
  `websockets.exceptions.InvalidStatus` with an HTTP 4xx status code
  still exits fatally with a clear error message. 4xx remains a
  surface-to-operator condition, not a retry-and-hope condition.
- The 10-consecutive-failure safety valve from
  `watch_reconnect_counter_reset` is preserved: 10 consecutive 5xx
  handshake responses with no intervening successful reconnect still
  exit with code 3.
- A successful reconnect after a 5xx handshake resets the consecutive
  `attempt` counter.
- New tests cover: 5xx-during-handshake retry-and-recover for both
  `watch_with_reconnect` and `watch_multi_with_reconnect`; 4xx-during-
  handshake stays fatal for both; 5xx safety-valve exhaustion still
  exits 3.
- All existing reconnect, stale-reconnect, counter-reset,
  Branch-1-handshake-timeout, and Branch-2-handshake-timeout tests
  continue to pass.

## Relationship to Parent

Parent `watch_handshake_timeout_retry` established the
handshake-transient-as-retryable semantic in
`BoardClient.watch_with_reconnect` and `watch_multi_with_reconnect`,
naming `TimeoutError` as the concrete instance. Its sibling correction
`watch_handshake_stale_retry` extracted the shared
`_connect_with_retry` helper so both reconnect branches share retry
semantics symmetrically. Both remain correct.

The parent's intent — "treat transient handshake failures as
retryable, with the 10-consecutive-failure safety valve as the
boundary" — now fully governs the code: `InvalidStatus` with HTTP 5xx
is in the retryable set in `_connect_with_retry` alongside `TimeoutError`,
with the same backoff arithmetic and attempt-counter semantics. The 4xx
case stays explicitly outside the retryable set so genuine configuration
errors remain visible.