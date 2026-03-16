

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Create a new Jinja2 command template at `src/templates/commands/swarm-monitor.md.jinja2`
following the exact same structural pattern as existing steward commands (e.g.,
`steward-changelog.md.jinja2`, `steward-watch.md.jinja2`):

- YAML frontmatter with `description`
- `{% set source_template %}` and `{% include "partials/auto-generated-header.md.jinja2" %}`
- Chunk backreference comment
- `{% include "partials/common-tips.md.jinja2" %}` for Tips section
- `{% raw %}` block wrapping the agent instructions

The template is pure prose — no Python code changes needed. The existing
`ve init` pipeline (via `render_to_directory` in `src/project.py#Project::_init_commands`)
already discovers all `*.jinja2` files in `src/templates/commands/` and renders
them to `.claude/commands/`, stripping the `.jinja2` suffix. So adding the
template file is sufficient for `ve init` to produce `.claude/commands/swarm-monitor.md`.

The CLAUDE.md template (`src/templates/claude/CLAUDE.md.jinja2`) must also be
updated to register `/swarm-monitor` as an available skill, so it appears in the
skill listing and the agent knows to invoke it.

**Testing**: Per TESTING_PHILOSOPHY.md, we don't assert on template prose. The
meaningful behavior to test is that `ve init` renders the new template to the
expected output path. Existing test infrastructure for `ve init` should already
cover this via the general "commands are rendered" test pattern — verify this
and add a targeted test only if needed.

## Subsystem Considerations

- **docs/subsystems/template_system** (STABLE): This chunk USES the template system.
  The new template follows all template system invariants: `.jinja2` suffix, rendered
  through the canonical system via `ve init`, uses `{% include %}` for partials.
  No deviations introduced.

## Sequence

### Step 1: Create the swarm-monitor command template

Create `src/templates/commands/swarm-monitor.md.jinja2` with the following structure:

**Frontmatter:**
```yaml
---
description: Monitor all changelog channels in a swarm
---
```

**Header boilerplate** (same as all other command templates):
```
{% set source_template = "swarm-monitor.md.jinja2" %}
{% include "partials/auto-generated-header.md.jinja2" %}
{# Chunk: docs/chunks/swarm_monitor_command - Swarm monitor slash command #}
```

**Tips section** with `{% include "partials/common-tips.md.jinja2" %}`.

**Instructions section** wrapped in `{% raw %}...{% endraw %}`, containing
the four-phase workflow:

#### Phase 1: Discover changelog channels

- Run `ve board channels` (which uses the bound swarm from `~/.ve/board.toml`
  by default, or `--swarm <id>` if overridden by the operator)
- Parse the output and filter for channels matching the `*-changelog` pattern
- Display the discovered channels to the operator

#### Phase 2: Show cursor vs head for each channel

- For each changelog channel, read the local cursor file at
  `.ve/board/cursors/<channel>.cursor` (treat missing as 0)
- Compare cursor position against the `head=N` value from `ve board channels` output
- Display a table/summary showing: channel name, cursor position, head position,
  and unread count (head - cursor)
- Highlight channels with unread messages

#### Phase 3: Launch background watches

- For each changelog channel that has unread messages OR is at head (waiting for
  new messages), start a `ve board watch <channel>` using `run_in_background`
- Report to the operator which channels are being watched

#### Phase 4: Report incoming messages

- As background watches complete (a message arrives on a channel), display the
  message to the operator inline, including which channel it came from
- After displaying, ack the message (`ve board ack <channel> <position>`) to
  advance the cursor
- Optionally re-launch a background watch on that channel to continue monitoring

The instructions should also cover:
- **Error handling**: If `ve board channels` fails, report and stop
- **No changelog channels**: If no `*-changelog` channels are found, inform the
  operator and stop
- **Server URL**: Note that `--server <url>` can be added if using a non-default
  backend

Location: `src/templates/commands/swarm-monitor.md.jinja2`

### Step 2: Register the skill in CLAUDE.md template

Add `/swarm-monitor` to the steward commands section in
`src/templates/claude/CLAUDE.md.jinja2`, alongside the existing steward commands:

```
- `/swarm-monitor` - Monitor all changelog channels in a swarm
```

This goes in the "### Steward" subsection of "## Available Commands".

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 3: Render and verify

Run `uv run ve init` to render the new template. Verify:

1. `.claude/commands/swarm-monitor.md` exists
2. The file contains the auto-generated header
3. The CLAUDE.md file lists the new skill
4. The `{% raw %}` tags are not present in the rendered output (they should
   be consumed by Jinja2)

### Step 4: Verify test coverage

Check existing `ve init` tests to confirm the new template is covered by the
general rendering pipeline. The test infrastructure should already test that
all templates in `src/templates/commands/` render to `.claude/commands/`. If
this pattern isn't covered by existing tests, add a test that verifies
`.claude/commands/swarm-monitor.md` is created after `ve init`.

Run `uv run pytest tests/` to ensure all tests pass.

## Dependencies

- `steward_setup_bootstrap` and `steward_watch_ack_note` chunks (already ACTIVE
  per `created_after`) — these established the `ve board` CLI, cursor management,
  and steward command template patterns this chunk builds on
- No new libraries or infrastructure required

## Risks and Open Questions

- **Channel naming convention**: The plan assumes `*-changelog` is the reliable
  pattern for identifying changelog channels. This matches observed data
  (`vibe-engineer-changelog`, `lite-edit-changelog`, etc.) but is a convention,
  not a hard guarantee. The template should note this assumption.
- **Many concurrent background watches**: If a swarm has many changelog channels,
  launching many simultaneous `run_in_background` watches could be resource-heavy
  for the agent. The template should be pragmatic about this (e.g., suggest the
  operator can select a subset if needed).
- **Cursor file location**: The steward-watch template references
  `.ve/board/cursors/<channel>.cursor` while steward-changelog references
  `.ve/cursors/<channel>.cursor`. Need to verify the correct path during
  implementation and use the one that matches the actual `ve board watch` behavior.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->