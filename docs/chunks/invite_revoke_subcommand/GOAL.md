---
status: HISTORICAL
ticket: null
parent_chunk: invite_list_revoke
code_paths:
- src/cli/board.py
- tests/test_board_invite.py
code_references:
- ref: src/cli/board.py#revoke_cmd
  implements: "Revoke command moved from board group to invite group"
- ref: src/cli/board.py#revoke_deprecated
  implements: "Deprecated alias at old ve board revoke location"
narrative: null
investigation: agent_invite_links
subsystems: []
friction_entries: []
bug_type: implementation
depends_on: []
created_after:
- invite_list_revoke
---

# Chunk Goal

## Minor Goal

Move the `ve board revoke` command to `ve board invite revoke` so all invite operations are grouped under the `invite` subcommand. Currently `revoke` exists as a top-level `board` command while `create` and `list` are under `ve board invite`, making `revoke` undiscoverable.

The fix: move `revoke_cmd` from `@board.command("revoke")` to `@invite.command("revoke")`, preserving the existing `--all` flag for bulk revocation. Optionally keep a deprecated alias at the old location that warns and delegates.

## Success Criteria

- `ve board invite revoke <token>` revokes a single token
- `ve board invite revoke --all --swarm <id>` bulk-revokes all tokens
- `ve board invite --help` shows `create`, `list`, and `revoke` subcommands
- Old `ve board revoke` either removed or emits a deprecation warning

## Relationship to Parent

Parent chunk `invite_list_revoke` restructured `invite` into a Click group with `create` and `list` subcommands but left `revoke` as a separate top-level `board` command. This chunk moves it into the group for discoverability.