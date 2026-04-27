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

The leader-board worker routes `/invite/{token}` requests to the correct Durable Object without requiring a `?swarm=` query parameter. Because invite URLs don't carry a swarm ID, the worker entry point (`src/index.ts`) resolves the swarm from the token hash via a `TOKEN_SWARM_INDEX` KV namespace before forwarding to the DO. The KV index is maintained on every gateway key write, single-key delete, and bulk delete, so token→swarm lookups stay in sync with the gateway key store.

## Success Criteria

- `curl https://leader-board.zack-98d.workers.dev/invite/<valid_token>` returns the instruction page (not "Missing required 'swarm' query parameter")
- Invalid tokens return a clear error (not a routing error)
- Existing `/gateway/{token}/channels/...` routes continue to work

## Relationship to Parent

Parent chunk `invite_instruction_page` owns the `handleInvitePage` and `renderInvitePage` methods on the DO. This chunk owns the entry-point routing that delivers `/invite/{token}` requests to that handler, including the token→swarm KV index that makes swarm-less invite URLs routable.