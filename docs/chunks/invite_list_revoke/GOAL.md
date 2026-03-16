---
status: ACTIVE
ticket: null
parent_chunk: invite_cli_command
code_paths:
- src/cli/board.py
- workers/leader-board/src/storage.ts
- workers/leader-board/src/swarm-do.ts
- tests/test_board_invite.py
- workers/leader-board/test/gateway-keys.test.ts
code_references:
- ref: src/cli/board.py#invite
  implements: "Click group restructuring invite from command to group with subcommands"
- ref: src/cli/board.py#invite_list_cmd
  implements: "CLI command to list all active invite tokens for a swarm"
- ref: src/cli/board.py#revoke_cmd
  implements: "Extended revoke command with --all flag for bulk revocation"
- ref: workers/leader-board/src/storage.ts#SwarmStorage::listGatewayKeys
  implements: "Server-side storage method to enumerate all gateway keys"
- ref: workers/leader-board/src/storage.ts#SwarmStorage::deleteAllGatewayKeys
  implements: "Server-side storage method for bulk deletion of all gateway keys"
- ref: workers/leader-board/src/swarm-do.ts#SwarmDO::handleGatewayKeys
  implements: "Extended handler dispatching GET/DELETE without token_hash to list/bulk-delete"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- gateway_cleartext_api
- gateway_token_storage
- invite_cli_command
- invite_instruction_page
---

# Chunk Goal

## Minor Goal

Round out the invite system (see `docs/investigations/agent_invite_links`) with two additional CLI commands:

- **`ve board invite list --swarm <id>`** — List all active invite tokens for a swarm. This requires a server-side route to enumerate gateway key entries (e.g., `GET /gateway/keys?swarm_id=<id>`) and a CLI command that calls it and displays the results (token hash, creation time, and optionally a truncated token hint for identification).

- **`ve board invite revoke --all --swarm <id>`** — Enhance the existing `ve board revoke` to support bulk revocation of all tokens for a swarm, in addition to the existing single-token revocation.

These commands complete the invite lifecycle management: create → list → revoke (single or all).

## Success Criteria

- `ve board invite list` displays all active invite tokens for a given swarm
- Server-side route exists to enumerate gateway keys by swarm ID
- `ve board invite revoke --all` deletes all tokens for a swarm in one operation
- Existing single-token `ve board revoke` continues to work unchanged
- Tests cover list (empty, populated) and bulk revoke scenarios

## Relationship to Parent

Parent chunk `invite_cli_command` implemented `ve board invite` and `ve board revoke` for single tokens. This chunk extends the CLI with list and bulk-revoke operations that were not part of the original investigation scope but are needed for practical invite management.