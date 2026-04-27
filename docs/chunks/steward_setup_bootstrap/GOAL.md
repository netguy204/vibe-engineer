---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/steward-setup.md.jinja2
code_references:
  - ref: src/templates/commands/steward-setup.md.jinja2
    implements: "Steward setup skill template with board.toml auto-suggest defaults and bootstrap channel messages"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_scp_command
---

# Chunk Goal

## Minor Goal

The `steward-setup` skill (`.claude/commands/steward-setup.md`) reduces friction during steward initialization with two behaviors:

1. **Bootstrap channel messages**: After writing `STEWARD.md` and before validation, the skill sends bootstrap messages to both the steward channel and the changelog channel using `ve board send`. This ensures the channels are created on the swarm before the first watch attempt, preventing errors when `ve board watch` targets a channel that doesn't exist yet.

2. **Auto-suggest swarm and server from bind config**: Rather than requiring the operator to manually provide the swarm ID and server URL, the skill reads `~/.ve/board.toml` to find the `default_swarm` and its `server_url`, presenting these as defaults during the interview. The operator can still override, but this removes friction for the common case where they've already bound a swarm.

## Success Criteria

- After running `/steward-setup`, the steward channel and changelog channel both exist on the swarm (verified by successful `ve board send` bootstrap messages)
- When `~/.ve/board.toml` exists and contains a `default_swarm`, the interview pre-fills the swarm ID and server URL as defaults
- When `~/.ve/board.toml` does not exist or has no default swarm, the interview falls back to asking the operator for manual input (no errors)
- The skill template renders correctly via `ve init`