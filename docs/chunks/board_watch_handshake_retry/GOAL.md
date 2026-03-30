---
status: HISTORICAL
ticket: null
parent_chunk: null
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
  - ref: src/board/client.py#_RETRYABLE_ERRORS
    implements: "Centralized retryable exception tuple including TimeoutError and SSLCertVerificationError"
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "Handshake retry loop during reconnect for single-channel watch"
  - ref: src/board/client.py#BoardClient::watch_multi_with_reconnect
    implements: "Handshake retry loop during reconnect for multi-channel watch"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- entity_shutdown_memory_wipe
---

# Chunk Goal

## Minor Goal

Make `ve board watch` retry on WebSocket handshake timeouts and SSL errors instead of crashing.

The reconnect logic handles `ConnectionClosedError` (mid-connection drops) but does not catch `TimeoutError` (handshake timeout) or `ssl.SSLCertVerificationError` during reconnection attempts. When these transient errors occur during a reconnect cycle, the watch process dies and must be manually restarted. This has been observed repeatedly in production steward sessions — the watch runs for hours/days, then a single handshake timeout kills it.

The fix should wrap the reconnection `websockets.connect()` call to catch `TimeoutError` and `ssl.SSLCertVerificationError` (and potentially `OSError` for network-level failures) and retry with exponential backoff, the same way `ConnectionClosedError` is already handled.

Observed failure modes from steward logs:
- `TimeoutError: timed out during opening handshake` — most common, killed watch 3 times in one week
- `ssl.SSLCertVerificationError: certificate verify failed` — killed watch once, transient cert issue

## Success Criteria

- `ve board watch` retries on `TimeoutError` during WebSocket handshake with exponential backoff
- `ve board watch` retries on `ssl.SSLCertVerificationError` with exponential backoff
- Retry backoff caps at a reasonable maximum (e.g., 60 seconds)
- After N consecutive connection failures (e.g., 10), the watch exits with a clear error rather than retrying forever
- Tests verify: handshake timeout triggers retry, SSL error triggers retry, max retries causes clean exit

