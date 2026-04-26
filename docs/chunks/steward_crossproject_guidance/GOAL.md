---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Cross-project steward messaging guidance section in CLAUDE.md template"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- invite_list_revoke
---

# Chunk Goal

## Minor Goal

The CLAUDE.md template (`src/templates/claude/CLAUDE.md.jinja2`) carries a "Cross-project messaging" subsection under the Steward section, near the `/steward-send` reference, so agents in downstream projects can correctly resolve "tell the X steward" instructions.

The subsection establishes:

1. **Channel naming convention**: The channel is `<target-project>-steward`, where `<target-project>` is the steward being addressed — not the project sending from. Sending to the `vibe-engineer` steward from any project in the swarm goes to `vibe-engineer-steward`.
2. **Send command format**: `ve board send <target-project>-steward "<message>" --swarm <swarm_id>`.
3. **Common mistake**: Agents often find their local `STEWARD.md`, read its `channel` field, and send to their *own* project's steward channel instead of the target project's. The guidance derives the channel name from the target project, never from the local steward configuration.

## Success Criteria

- The CLAUDE.md template includes a "Cross-project messaging" subsection under Steward
- The guidance clearly explains the `<target-project>-steward` naming convention
- `ve init` renders the updated CLAUDE.md correctly
- An agent reading the rendered CLAUDE.md can correctly resolve "tell the vibe-engineer steward" from any project