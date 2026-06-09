

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Apply the mechanical porting recipe from
`docs/chunks/plugin_runtime_context/PORTING_GUIDE.md` to the 15
orchestrator/steward/swarm/entity/migration command templates, producing
static plugin commands in `commands/` (DEC-010: plugin command files are
static markdown; render-time resolution becomes runtime context detection).

The worked example is `commands/chunk-create.md`. Each port follows the same
shape:

1. **Frontmatter**: `name` matches the file stem; `description` is expanded
   so it works for proactive/skill invocation — it states what the command
   does AND its trigger conditions ("Use when ..."). `allowed-tools` lists
   the two preamble probes (`Bash(ve --help:*)`, `Bash(cat:*)`) plus one
   `Bash(ve <subcommand>:*)` entry per distinct `ve` invocation the body
   instructs.
2. **Drop render machinery**: the `{% set source_template %}` line, the
   auto-generated-header include, the common-tips include (its content is
   already in the canonical Runtime context section), and the
   `{% raw %}`/`{% endraw %}` markers. Jinja2 `{# Chunk: ... #}` comments
   from prior chunks become HTML comments so historical backreferences
   survive.
3. **Backreference + canonical preamble**: immediately after the
   frontmatter, add
   `<!-- Chunk: docs/chunks/plugin_orch_commands - Static plugin port of <name> -->`,
   then the canonical `## Context` (three `!`-probe lines) and
   `## Runtime context` sections verbatim from the porting guide.
4. **Body verbatim**: the numbered instructions, `$ARGUMENTS`, and embedded
   examples carry over without behavioral change. Exception required by the
   recipe: bodies reference bare `ve ...`, never `uv run ve` — the
   "if working in the vibe-engineer source repo, use `uv run`" asides in
   entity-startup/entity-episodic and the `uv run ve chunk list` invocation
   in audit-intent are converted to bare `ve`.

None of the 15 templates contain `{% if task_context %}` blocks or
`ve_config` interpolation, so steps 4–5 of the porting recipe (runtime
conditionals) are no-ops here; the canonical preamble still ships verbatim
on every command for convention uniformity.

**Cross-project messaging guidance travels with the command bodies.** The
guidance currently in the AGENTS.md managed block (derive the channel name
from the TARGET project — `<target-project>-steward` — not the sender's
local steward channel, including the documented common mistake of reading
the local STEWARD.md `channel` field) is embedded directly in the bodies of
`steward-send`, `swarm-request-response`, and `swarm-monitor`, because the
AGENTS.md block shrinks in `plugin_init_slimdown`.

Tests: `tests/test_plugin_commands.py#TestCommandInvariants` is
parameterized over every `commands/*.md` file and automatically covers all
15 new files (frontmatter name/description, no Jinja2 syntax, no
AUTO-GENERATED header). No new test code is needed; the suite must pass.
This honors docs/trunk/TESTING_PHILOSOPHY.md by reusing the standing
invariant coverage built for the mass ports rather than duplicating
per-file assertions.

Out of scope (owned by sibling chunks): core workflow commands
(`plugin_core_commands`), deleting `src/templates/commands/`
(`plugin_init_slimdown`), promoting inline agent prompts to named subagents
(`plugin_subagents`).

## Sequence

### Step 1: Port the orchestrator commands

Create from their `src/templates/commands/*.md.jinja2` sources:

- `commands/orchestrator-inject.md` — ve invocations: `ve chunk list`,
  `ve orch status`, `ve orch start`, `ve orch inject`
- `commands/orchestrator-monitor.md` — `ve orch ps`,
  `ve orch work-unit`, `ve board send`
- `commands/orchestrator-investigate.md` — `ve orch status`,
  `ve orch work-unit`, `ve orch attention`, `ve orch stop`,
  `ve orch start`, `ve chunk activate`
- `commands/orchestrator-submit-future.md` — `ve orch status`,
  `ve orch start`, `ve chunk list`, `ve orch ps`, `ve orch inject`

Expand each description with trigger conditions (e.g. monitor: "Use when
the operator asks to monitor injected chunks, track background work, or
after injecting a chunk").

### Step 2: Port the steward commands, embedding channel-naming guidance

- `commands/steward-setup.md` — `ve board channels`, `ve board send`
- `commands/steward-watch.md` — `ve board watch`, `ve board send`,
  `ve board ack`, `ve orch inject`, `ve orch ps`
- `commands/steward-send.md` — `ve board send`; embed the full
  cross-project channel-naming guidance (target-project convention +
  common-mistake warning) in the body's target-resolution step
- `commands/steward-changelog.md` — `ve board watch`, `ve board ack`

### Step 3: Port the swarm commands, embedding channel-naming guidance

- `commands/swarm-monitor.md` — `ve board channels`,
  `ve board watch-multi`; note the target-project channel-naming
  convention in Key Concepts
- `commands/swarm-request-response.md` — `ve board channels`,
  `ve board watch`, `ve board send`, `ve board ack`; embed the
  target-project guidance where the channel pair is derived

### Step 4: Port the entity commands

- `commands/entity-startup.md` — `ve entity list`, `ve entity startup`,
  `ve entity recall`, `ve entity touch`, `ve entity episodic`
- `commands/entity-shutdown.md` — `ve entity list`, `ve entity shutdown`
- `commands/entity-episodic.md` — `ve entity episodic`,
  `ve entity recall`

Drop the "use `uv run` in the vibe-engineer source repo" asides per the
bare-`ve` rule.

### Step 5: Port the migration/audit commands

- `commands/audit-intent.md` — `ve chunk list` (the body's
  `uv run ve chunk list` becomes `ve chunk list`). The inline sub-agent
  prompt template ports verbatim — plugin_subagents will survey it later.
- `commands/migrate-managed-claude-md.md` — `ve migration create`,
  `ve init`

### Step 6: Verify

- `grep -nE '\{%|\{\{|\{#' commands/*.md` matches nothing
- `uv run pytest tests/test_plugin_commands.py` passes (all parameterized
  invariants over the now-17 command files)
- Spot-check rendering of the `!`-probe lines and frontmatter parse

### Step 7: Update chunk metadata and commit

Populate `code_paths`/`code_references` in GOAL.md and commit the 15 new
command files plus chunk docs.

## Dependencies

- `plugin_runtime_context` (ACTIVE, merged at main) — supplies the
  canonical preamble, the porting guide, and the standing test invariants.
- `plugin_scaffold` (ACTIVE) — supplies the `commands/` directory and
  plugin manifest.

## Risks and Open Questions

- The canonical preamble includes the `.ve-config.yaml` probe even though
  none of these 15 commands consume config keys. The porting guide says the
  preamble ships verbatim on every command; uniformity wins over trimming.
- `audit-intent`'s prerequisite checks reference vibe-engineer-source paths
  (`src/templates/chunk/GOAL.md.jinja2`, `from models import ChunkStatus`).
  These are pre-existing content concerns, not porting concerns — the body
  ports verbatim per recipe step 6 (the port changes how context is
  resolved, not what the command does).
- Several commands embed inline agent/loop prompt templates
  (orchestrator-monitor's `/loop` prompt, audit-intent's sub-agent prompt,
  steward-setup's autonomous behavior template). They port verbatim;
  `plugin_subagents` decides later which deserve promotion.

## Deviations

- **steward-changelog cursor path corrected.** The template said cursors live
  at `.ve/cursors/<channel>.cursor`; the code
  (`src/board/storage.py`) stores them at
  `.ve/board/cursors/<channel>.cursor` (the path swarm-monitor already
  uses). Propagating a known-wrong path into the new canonical source was
  worse than a verbatim port, so the ported file carries the verified path.
- **audit-intent prerequisite checks rewritten for consuming projects.** The
  template's checks (2) and (3) probed vibe-engineer-source paths
  (`grep src/templates/chunk/GOAL.md.jinja2`,
  `python3 -c "from models import ChunkStatus..."`) that fail in every
  consuming project — the plugin's actual audience. Replaced with
  equivalent checks that work where the command runs:
  `grep COMPOSITE docs/trunk/CHUNKS.md` and
  `ve chunk list --status COMPOSITE` (verified: exits 0 when supported,
  1 for an unknown status). The check's intent (refuse to audit an
  unprepared project) is unchanged.
- **`uv run ve` asides removed** (planned): entity-startup, entity-episodic,
  and audit-intent now use bare `ve` per the porting recipe.
- **Prior chunk backreferences preserved** as HTML comments (the
  chunk-create pilot dropped them; keeping them preserves archaeology and
  costs nothing).
