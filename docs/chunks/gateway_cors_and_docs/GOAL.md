---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/test/gateway-api.test.ts
- workers/leader-board/test/invite-page.test.ts
code_references:
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayAPI
    implements: "CORS headers on all gateway responses and OPTIONS preflight handler"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleInvitePage
    implements: "CORS headers on invite page responses"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::wakePendingPolls
    implements: "CORS headers on long-poll wake responses"
  - ref: workers/leader-board/src/swarm-do.ts#renderInvitePage
    implements: "GET and POST response schema documentation on invite page"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- gateway_message_read_fix
---

# Chunk Goal

## Minor Goal

Improve the HTTP cleartext gateway's usability for browser-based and third-party clients. Three changes:

1. **CORS headers**: Add `Access-Control-Allow-Origin: *` to all gateway HTTP responses (`/gateway/{token}/...` routes). Without CORS headers, browser-based clients are blocked by same-origin policy. Also handle `OPTIONS` preflight requests for POST endpoints with `Content-Type: application/json`.

2. **Invite page documentation improvements**: Update the invite instruction page (`renderInvitePage` in `swarm-do.ts`) to document:
   - GET response schema: `{"messages": [{"position": N, "body": "...", "sent_at": "..."}]}`
   - POST response schema (what it returns on success)
   - All response field names and types (especially `sent_at` since devs may guess `timestamp`)
   - Whether there's a sender/author field (and if not, state that explicitly)

3. **OPTIONS preflight handler**: Add an OPTIONS handler for `/gateway/{token}/channels/{channel}/messages` that returns appropriate CORS preflight headers (`Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`).

## Success Criteria

- All `/gateway/` responses include `Access-Control-Allow-Origin: *`
- `OPTIONS /gateway/{token}/channels/{channel}/messages` returns 204 with correct CORS headers
- Invite instruction page documents GET and POST response schemas with field names and types
- A browser-based fetch to the gateway succeeds without CORS errors
- Tests cover CORS headers on GET, POST, and OPTIONS responses