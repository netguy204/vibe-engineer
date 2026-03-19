

# Implementation Plan

## Approach

Create a new Jinja2 template `src/templates/commands/orchestrator-monitor.md.jinja2`
that defines the `/orchestrator-monitor` slash command skill. This skill is a
prompt-only artifact (no Python code) — it instructs the agent how to poll
orchestrator status for injected chunks, handle each status, and manage the
`/loop` lifecycle.

The skill follows the established template pattern (DEC-001 via `ve init`
rendering): a Jinja2 source template with YAML frontmatter `description`, the
auto-generated header partial, and common tips partial. The rendered output
lands in `.claude/commands/orchestrator-monitor.md`.

After creating the skill, update `/steward-watch` (Step 6) to delegate to
`/orchestrator-monitor` instead of constructing inline loop logic. Also
register the new command in the CLAUDE.md template's orchestrator commands line.

**Testing approach**: This chunk produces only template files (prompt text),
not Python code with behavior. Per TESTING_PHILOSOPHY.md, template content is
not asserted on — we verify templates render without error and files are
created. The existing `ve init` rendering test suite covers this. No new tests
are needed for prompt-only slash commands, as there is no computation,
validation, or side effect to test beyond what the template system already
verifies.

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk USES the
  orchestrator subsystem — the skill instructs agents to call `ve orch ps`,
  `ve orch work-unit show`, and `ve orch work-unit status` commands. No
  orchestrator code is modified.
- **docs/subsystems/template_system** (DOCUMENTED): This chunk USES the
  template system to create a new Jinja2 command template following the
  established rendering pattern (`ve init` → `.claude/commands/`).

## Sequence

### Step 1: Create the orchestrator-monitor command template

Create `src/templates/commands/orchestrator-monitor.md.jinja2` with:

- YAML frontmatter with `description: "Monitor injected chunks through the orchestrator lifecycle to completion."`
- Standard Jinja2 header: `{% set source_template = "orchestrator-monitor.md.jinja2" %}` + `{% include "partials/auto-generated-header.md.jinja2" %}`
- Tips section with `{% include "partials/common-tips.md.jinja2" %}`
- `$ARGUMENTS` used for chunk names and flags

**Instructions body** covering these sections:

**Argument parsing:**
- Parse `$ARGUMENTS` for chunk name(s) and optional flags `--changelog-channel <channel>` and `--swarm <swarm_id>`
- If no chunk names provided, run `ve orch ps` to show current work units and ask operator which to monitor

**Immediate first check (Step 1 in skill):**
- Run `ve orch ps --json` and filter for the monitored chunks
- For each chunk, execute the status handler logic (same as the loop body below)
- This ensures the agent doesn't wait 3 minutes for the first status update

**Loop setup (Step 2 in skill):**
- Set up a `/loop 3m` with a prompt that polls `ve orch ps --json` for the monitored chunks
- The prompt should include the chunk names, changelog channel, and swarm ID so the loop body is self-contained

**Status handler logic** (used by both immediate check and loop body):

- **RUNNING / BLOCKED / READY**: No action. Report status if first check.
- **NEEDS_ATTENTION**:
  1. Run `ve orch work-unit show <chunk>` to get `attention_reason`
  2. Inspect the worktree branch: `git log --oneline orch/<chunk> ^main` and `git diff --stat main..orch/<chunk>`
  3. Decision tree:
     - If attention_reason indicates merge failure and branch has commits: attempt manual merge (`git merge orch/<chunk> --no-edit`), resolve conflicts if any, then `ve orch work-unit status <chunk> DONE`
     - If attention_reason indicates agent failure: reset to READY for retry (`ve orch work-unit status <chunk> READY`)
     - If unclear or complex: escalate to operator (post to changelog or alert)
- **DONE**:
  1. Check if branch needs pushing: `git log --oneline @{u}..HEAD` (if upstream tracking exists)
  2. Read chunk's GOAL.md `code_paths` — if any path starts with `workers/`, run deploy (`cd workers/leader-board && npm run deploy`)
  3. Post changelog entry if `--changelog-channel` and `--swarm` were provided: `ve board send <changelog_channel> "<summary>" --swarm <swarm_id>`
  4. Remove chunk from the monitored set
- **FAILED**: Post failure summary to changelog (if channel provided), remove from monitored set

**Loop lifecycle management:**
- When all monitored chunks reach terminal state (DONE or FAILED), cancel the loop via `CronDelete`
- Wrap the entire Instructions section in `{% raw %}...{% endraw %}` to prevent Jinja2 from interpreting the agent-facing template syntax

**Backreference comment** at template top:
```
{# Chunk: docs/chunks/orchestrator_monitor_skill - Orchestrator monitor slash command #}
```

Location: `src/templates/commands/orchestrator-monitor.md.jinja2`

### Step 2: Update steward-watch to reference /orchestrator-monitor

Edit `src/templates/commands/steward-watch.md.jinja2`, replacing Step 6's
inline loop construction with a delegation to the new skill.

Replace the current Step 6 body (which explains how to manually construct a
`/loop` prompt with inline orchestrator polling logic) with:

```
After injecting a chunk, run `/orchestrator-monitor <chunk_name>
--changelog-channel <changelog_channel> --swarm <swarm_id>` to set up
recurring orchestrator monitoring. This runs concurrently with the channel
watch — the monitor polls orchestrator status while the watch blocks on
inbound messages.

When multiple chunks are injected during the session, pass all chunk names
to a single `/orchestrator-monitor` invocation. The skill handles loop
lifecycle management (creation, update, and cancellation).
```

Add a backreference comment for this chunk near the existing chunk comments at
the top of the template.

Location: `src/templates/commands/steward-watch.md.jinja2`

### Step 3: Register in CLAUDE.md template

Edit `src/templates/claude/CLAUDE.md.jinja2` line 95 to add
`/orchestrator-monitor` to the orchestrator commands list:

Change:
```
Commands: `/orchestrator-submit-future`, `/orchestrator-investigate`
```
To:
```
Commands: `/orchestrator-submit-future`, `/orchestrator-investigate`, `/orchestrator-monitor`
```

Add a backreference comment for this chunk.

Location: `src/templates/claude/CLAUDE.md.jinja2`

### Step 4: Render and verify

Run `uv run ve init` to render all templates and verify:
1. `.claude/commands/orchestrator-monitor.md` is created
2. `.claude/commands/steward-watch.md` reflects the updated Step 6
3. `CLAUDE.md` lists `/orchestrator-monitor` in the orchestrator commands

### Step 5: Run existing tests

Run `uv run pytest tests/` to verify no regressions. The template rendering
tests should pass with the new template included. No new test files are needed
since this chunk produces only prompt text, not testable Python behavior.

## Risks and Open Questions

- **Deploy step is project-specific**: The DONE handler includes a conditional
  deploy step (`cd workers/leader-board && npm run deploy`) inherited from
  steward-watch. This is specific to projects using Durable Object workers.
  The skill should frame this as conditional: "if code_paths include workers/,
  run the project's deploy command." The exact deploy command may vary by
  project — the skill should instruct the agent to check the project's README
  or deploy configuration rather than hardcoding a specific command.

- **Loop prompt length**: The `/loop` prompt must be self-contained (include
  chunk names, channel, swarm). If many chunks are monitored simultaneously,
  the prompt could become long. This is acceptable since chunk names are short
  strings and the prompt is agent-consumed, not human-read.

- **CronCreate/CronDelete availability**: The skill assumes the agent has
  access to `CronCreate` and `CronDelete` tools (provided by the `/loop`
  skill). This is true in Claude Code environments with the loop skill
  registered.

## Deviations

