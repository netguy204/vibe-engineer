---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/swarm-monitor.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/commands/swarm-monitor.md.jinja2
  implements: "Swarm monitor command template with four-phase workflow (discover, cursor check, background watch, report)"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Skill registration for /swarm-monitor in the Available Commands steward section"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- steward_setup_bootstrap
- steward_watch_ack_note
---

# Chunk Goal

## Minor Goal

Create a new `/swarm-monitor` slash command that gives operators a single-command view across all changelog channels in a swarm. Currently, monitoring multiple project changelogs requires manually listing channels, checking cursors, and starting individual watches. This command automates that workflow:

1. **List changelog channels** — Run `ve board channels` and filter for `*-changelog` patterns
2. **Show cursor vs head** — For each changelog channel, display the cursor position and head position to identify unread messages
3. **Launch background watches** — Start `run_in_background` watches on all changelog channels that have unread messages or are at head (waiting for new ones)
4. **Report to operator** — As messages arrive on any watched channel, report them back to the operator inline

The skill should be a rendered Jinja2 command template at `src/templates/commands/swarm-monitor.md.jinja2`, following the same patterns as other command templates (auto-generated header, common tips partial, `{% raw %}` block for instructions).

## Success Criteria

- A new template exists at `src/templates/commands/swarm-monitor.md.jinja2`
- `ve init` renders it to `.claude/commands/swarm-monitor.md`
- The skill instructions correctly describe the channel discovery, cursor comparison, background watch, and reporting workflow
- The command uses the swarm's bound config from `~/.ve/board.toml` (no manual `--swarm` required unless overridden)