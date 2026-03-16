---
status: ACTIVE
ticket: null
parent_chunk: websocket_hibernation_compat
code_paths:
- src/board/client.py
- tests/test_board_client.py
code_references:
  - ref: src/board/client.py#BoardClient::watch_with_reconnect
    implements: "Backoff reset to 1.0s after successful reconnect; keepalive investigation findings documented in PLAN.md"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- gateway_cors_and_docs
---

# Chunk Goal

## Minor Goal

Two issues with the WebSocket reconnect behavior after the `websocket_hibernation_compat` changes:

1. **Backoff counter never resets**: After a successful reconnect, the exponential backoff counter stays at its current value (eventually capping at 30s). It should reset to the initial delay after a successful reconnection so subsequent disconnects start with a short retry. Currently `watch_with_reconnect` in `src/board/client.py` increments the attempt counter on each disconnect but never resets it on success.

2. **Investigate whether client-side pings keep Cloudflare WebSockets alive during hibernation**: The `websocket_hibernation_compat` chunk removed server-side heartbeats and relies on client-side `ping_interval` to keep connections alive. But field observations show connections still dropping every 2-5 minutes across multiple channels. Investigate whether:
   - The `websockets` library's `ping_interval` actually sends WebSocket-level pings (not application-level)
   - Cloudflare's proxy infrastructure honors these pings for idle timeout reset
   - The DO's hibernation eviction is what's closing the connection (the DO evicts from memory, but the docs say connections should survive hibernation — verify this is working)
   - A different `ping_interval` value (currently likely the default 20s) would help

## Success Criteria

- Backoff counter resets to initial delay after successful reconnect
- Investigation documents whether client-side pings prevent Cloudflare idle timeouts
- If pings don't prevent timeouts, implement an alternative keepalive mechanism
- A long-running watch (~30 min) shows fewer disconnects than the current ~8 per 90 minutes

## Relationship to Parent

Parent chunk `websocket_hibernation_compat` removed server-side heartbeats for cost efficiency (DO hibernation). This chunk addresses the resulting increase in disconnect frequency and fixes the backoff counter that was introduced by `websocket_keepalive`.