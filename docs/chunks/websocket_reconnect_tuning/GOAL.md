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

Two concerns with the WebSocket reconnect behavior under the `websocket_hibernation_compat` regime:

1. **Backoff reset on successful reconnect**: The exponential backoff counter resets to the initial delay after a successful reconnection so subsequent disconnects start with a short retry. Without the reset, the counter would stay at its accumulated value (eventually capping at 30s) and `watch_with_reconnect` in `src/board/client.py` would never recover its retry agility after a transient blip.

2. **Client-side ping behavior vs Cloudflare idle timeouts (investigation)**: `websocket_hibernation_compat` removed server-side heartbeats and relies on client-side `ping_interval` to keep connections alive, yet field observations show connections dropping every 2-5 minutes across multiple channels. The investigation covers:
   - Whether the `websockets` library's `ping_interval` sends WebSocket-level pings (not application-level)
   - Whether Cloudflare's proxy infrastructure honors these pings for idle timeout reset
   - Whether DO hibernation eviction is what closes the connection (the DO evicts from memory, but the docs say connections should survive hibernation — verify this works)
   - Whether a different `ping_interval` value (default 20s) would help

## Success Criteria

- Backoff counter resets to initial delay after successful reconnect
- Investigation documents whether client-side pings prevent Cloudflare idle timeouts
- If pings don't prevent timeouts, implement an alternative keepalive mechanism
- A long-running watch (~30 min) shows fewer disconnects than the current ~8 per 90 minutes

## Relationship to Parent

Parent chunk `websocket_hibernation_compat` removed server-side heartbeats for cost efficiency (DO hibernation). The backoff-reset behavior here addresses the resulting increase in disconnect frequency and corrects the counter introduced by `websocket_keepalive`.