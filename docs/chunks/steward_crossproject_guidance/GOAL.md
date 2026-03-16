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

Add cross-project steward messaging guidance to the CLAUDE.md template (`src/templates/claude/CLAUDE.md.jinja2`) so that agents in downstream projects can correctly resolve "tell the X steward" instructions.

The guidance should explain:

1. **Channel naming convention**: The channel is `<project>-steward` where `<project>` is the steward you're addressing, NOT the project you're sending from. E.g., to tell the vibe-engineer steward from lite-edit, send to `vibe-engineer-steward`.
2. **Send command format**: `ve board send <project>-steward "<message>"`
3. **Common mistake**: Agents in downstream projects may find their local `STEWARD.md` and send to their own steward channel instead of the target project's channel. The guidance should explicitly warn against this.

This belongs in the Steward section of the CLAUDE.md template, near the `/steward-send` command reference.

## Success Criteria

- The CLAUDE.md template includes a "Cross-project messaging" subsection under Steward
- The guidance clearly explains the `<target-project>-steward` naming convention
- `ve init` renders the updated CLAUDE.md correctly
- An agent reading the rendered CLAUDE.md can correctly resolve "tell the vibe-engineer steward" from any project