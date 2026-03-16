---
status: ACTIVE
ticket: null
parent_chunk: invite_instruction_page
code_paths:
- workers/leader-board/src/index.ts
- workers/leader-board/src/swarm-do.ts
- workers/leader-board/wrangler.toml
- workers/leader-board/test/invite-page.test.ts
code_references:
- ref: workers/leader-board/src/index.ts
  implements: "Early-exit invite path routing via KV token→swarm lookup before swarm guard"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayKeys
  implements: "KV index maintenance on gateway key CRUD (put/delete/bulk-delete)"
- ref: workers/leader-board/src/swarm-do.ts#Env
  implements: "TOKEN_SWARM_INDEX KV namespace binding in Env interface"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: semantic
depends_on: []
created_after:
- invite_list_revoke
---

# Chunk Goal

## Minor Goal

Fix the invite path routing in the leader-board worker. When curling `https://leader-board.zack-98d.workers.dev/invite/<token>`, the request falls through to a generic handler that expects `?swarm=` as a query parameter, returning `{"error":"Missing required 'swarm' query parameter"}` instead of serving the invite instruction page.

The worker entry point (`src/index.ts`) needs to route `/invite/{token}` requests to the correct Durable Object. The challenge is that invite paths don't carry a swarm ID in the URL — the swarm must be resolved from the token by looking up the gateway key blob (which stores `swarm_id`). The routing logic needs to either:
- Look up the swarm from the token hash before forwarding to the DO, or
- Route to a known DO that can resolve the token internally

## Success Criteria

- `curl https://leader-board.zack-98d.workers.dev/invite/<valid_token>` returns the instruction page (not "Missing required 'swarm' query parameter")
- Invalid tokens return a clear error (not a routing error)
- Existing `/gateway/{token}/channels/...` routes continue to work

## Relationship to Parent

Parent chunk `invite_instruction_page` implemented the `handleInvitePage` and `renderInvitePage` methods on the DO, but the worker entry point routing doesn't correctly forward `/invite/{token}` requests to the DO because it can't determine the swarm without first resolving the token.