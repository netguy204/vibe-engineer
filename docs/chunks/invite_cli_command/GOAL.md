---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/cli/board.py
- src/board/crypto.py
- src/board/config.py
- tests/test_board_invite.py
code_references:
- ref: src/cli/board.py#invite_create_cmd
  implements: "Generates invite token, encrypts swarm seed, uploads blob, outputs invite URL"
- ref: src/cli/board.py#revoke_cmd
  implements: "Revokes an invite token (or all tokens with --all) by deleting the encrypted blob from the server (moved to invite group by invite_revoke_subcommand)"
- ref: src/board/crypto.py#derive_token_key
  implements: "HKDF-SHA256 key derivation from random invite token with domain-separated info string"
- ref: src/board/config.py#gateway_http_url
  implements: "Converts ws:// or wss:// server URLs to http:// or https:// for gateway HTTP requests"
- ref: tests/test_board_invite.py
  implements: "Test suite covering invite/revoke happy paths, error cases, and round-trip verification"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- gateway_token_storage
created_after:
- swarm_monitor_command
---

# Chunk Goal

## Minor Goal

Implement `ve board invite` and `ve board revoke` CLI commands for the agent invite link system (see `docs/investigations/agent_invite_links`). Depends on `gateway_token_storage` for the server-side blob storage.

- **`ve board invite --swarm <id>`** — generates a cryptographically strong random token, encrypts the swarm private key using the token as the encryption key, uploads the encrypted blob to the server keyed by `hash(token)`, and outputs the invite URL (`https://<server>/invite/{token}`)
- **`ve board revoke <token>`** — deletes the encrypted blob from the server, immediately invalidating the token
- Must display an explicit opt-in warning explaining that the cleartext gateway trades E2E encryption for agent accessibility

## Success Criteria

- `ve board invite` generates a token, encrypts the key, uploads the blob, and prints the invite URL
- `ve board revoke` deletes the blob and confirms revocation
- An opt-in warning is displayed before creating the invite
- Round-trip test: invite → use token to retrieve blob → revoke → token returns 404