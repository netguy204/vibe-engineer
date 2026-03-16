---
decision: APPROVE
summary: "All success criteria satisfied — template follows established patterns, renders correctly, skill registered in CLAUDE.md, and workflow instructions cover all four phases"
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: A new template exists at `src/templates/commands/swarm-monitor.md.jinja2`

- **Status**: satisfied
- **Evidence**: File exists at `src/templates/commands/swarm-monitor.md.jinja2` with 127 lines. Follows the exact structural pattern of existing steward commands (YAML frontmatter, `{% set source_template %}`, `{% include %}` for auto-generated header and common tips, chunk backreference comment, `{% raw %}` block wrapping instructions).

### Criterion 2: `ve init` renders it to `.claude/commands/swarm-monitor.md`

- **Status**: satisfied
- **Evidence**: `.claude/commands/swarm-monitor.md` exists with 134 lines. Contains the auto-generated header ("AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY"), common tips section, and all instruction content. No `{% raw %}` tags appear in the rendered output — Jinja2 consumed them correctly.

### Criterion 3: The skill instructions correctly describe the channel discovery, cursor comparison, background watch, and reporting workflow

- **Status**: satisfied
- **Evidence**: The template contains four clearly defined phases: (1) Discover changelog channels via `ve board channels` with `*-changelog` filtering and error handling, (2) Show cursor vs head with a summary table example and unread count calculation, (3) Launch background watches using `run_in_background` for channels with unread messages or at head, (4) Report incoming messages inline with channel identification, ack to advance cursor, and re-launch watch. Also includes Key Concepts section covering `run_in_background`, cursor management, channel naming convention, and concurrent watches.

### Criterion 4: The command uses the swarm's bound config from `~/.ve/board.toml` (no manual `--swarm` required unless overridden)

- **Status**: satisfied
- **Evidence**: Phase 1 explicitly states "By default this uses the bound swarm from `~/.ve/board.toml`. If the operator provided a `--swarm <id>` argument, pass it through." The `--swarm` parameter is shown as optional in all command examples.
