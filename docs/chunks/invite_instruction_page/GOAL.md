---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- workers/leader-board/src/index.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/src/storage.ts
- workers/leader-board/test/invite-page.test.ts
code_references:
  - ref: workers/leader-board/src/swarm-do.ts#renderInvitePage
    implements: "Renders plain-text instruction page with curl examples, response schemas, channel list, and security info"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleInvitePage
    implements: "Validates invite token, fetches swarm metadata/channels, returns rendered instruction page with CORS headers"
  - ref: workers/leader-board/src/swarm-do.ts#SwarmDO::fetch
    implements: "Route matching for /invite/{token} path"
  - ref: workers/leader-board/src/index.ts
    implements: "Worker entry point route forwarding for /invite/{token} to SwarmDO"
  - ref: workers/leader-board/src/storage.ts#SwarmStorage::putGatewayKey
    implements: "Extended with swarm_id parameter for invite token routing"
  - ref: workers/leader-board/src/storage.ts#SwarmStorage::getGatewayKey
    implements: "Extended to return swarm_id field for invite page handler"
  - ref: workers/leader-board/test/invite-page.test.ts
    implements: "Integration tests for invite instruction page endpoint"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- gateway_cleartext_api
created_after:
- swarm_monitor_command
---
# Chunk Goal

## Minor Goal

Serve an agent-facing instruction page at `/invite/{token}` on the leader-board worker (see `docs/investigations/agent_invite_links`). Depends on `gateway_cleartext_api` for the HTTP endpoints the instructions reference.

When an agent follows an invite URL, this page serves a plain text/markdown document describing:
- The swarm and available channels
- The HTTP API protocol with example `curl` commands for reading and posting messages
- The security model (what the token grants, how revocation works)

This is the "last mile" of the invite flow — the page that turns a pasted URL into actionable instructions any agent can follow, regardless of runtime.

## Success Criteria

- GET `/invite/{token}` returns a plain text instruction page for valid tokens
- The page includes working `curl` examples using the token
- Invalid/revoked tokens return a clear error
- Content is agent-readable (plain text or markdown, no HTML/JS dependencies)