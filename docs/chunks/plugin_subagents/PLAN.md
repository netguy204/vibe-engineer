

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Promote the inline agent prompts that clear the promotion bar into named
plugin agents under `agents/` (the plugin root is the repo root per
DEC-010), then rewire the referencing commands to invoke the agents by name
instead of embedding their full prompts. Plugin agents are static markdown
files with YAML frontmatter (`name`, `description`, `tools`) whose body is
the agent's system prompt — the same static-file constraint that governs
`commands/` (no Jinja2, no render-time variants) applies.

The survey of all 37 ported commands found six inline-agent candidates.
Against the promotion bar in GOAL.md (promote only roles invoked from more
than one command or with substantial inline prompts), two clear it:

1. **chunk-executor** — `commands/narrative-execute.md` Phase 4 embeds a
   substantial background-agent prompt that drives a chunk through the full
   plan → implement → review (max 3 cycles) → complete lifecycle and reports
   SUCCESS/FAILURE. This is the canonical "execute one chunk in a parallel
   session" role.
2. **intent-auditor** — `commands/audit-intent.md` carries a full
   `## Sub-agent prompt template` section (~80 lines: detection criteria,
   action rules, the veto rule, symmetric verification, inconsistency entry
   format, return format, constraints). This is by far the largest inline
   agent prompt in the corpus.

Four candidates were surveyed and deliberately NOT promoted; the rationale
is recorded in the Survey Outcome section below, which satisfies the
GOAL.md success criterion that the survey outcome be recorded in the chunk
docs.

Parameterization note: plugin agents are static, so per-invocation values
(chunk name, narrative name, batch ID, the 5-chunk scope list) cannot be
baked into the agent file. The agent bodies are written to take these
values from the invoking task message, and the rewired commands instruct
the orchestrating agent to pass them when launching the subagent.

Testing follows the pattern `tests/test_plugin_commands.py` established for
commands: file-level invariants over the static plugin sources. A new
`tests/test_plugin_agents.py` asserts the agent files' frontmatter is valid
(name matches stem, non-empty description, tools declared), that no Jinja2
syntax appears, and that the rewired commands reference the agents by name
while no longer embedding the promoted prompt bodies inline.

## Survey Outcome

Considered and promoted:

- `commands/narrative-execute.md` Phase 4 inline background-agent prompt →
  **chunk-executor**. Substantial prompt (full lifecycle loop with review
  retry policy and a structured SUCCESS/FAILURE report contract).
- `commands/audit-intent.md` `## Sub-agent prompt template` →
  **intent-auditor**. Largest inline prompt in the corpus; self-contained
  audit protocol with load-bearing rules (veto rule, symmetric
  verification) that should be versioned once.

Considered and deliberately NOT promoted:

- `commands/chunks-resolve-references.md` step 2 fan-out: the per-agent
  prompt is a one-line delegation ("run `/chunk-update-references <path>`").
  The role's behavior is already versioned once in the
  `chunk-update-references` command; a named agent would add a layer with
  no content. Below the promotion bar.
- `commands/chunk-complete.md` step 6 fan-out: same shape — a one-line
  per-directory delegation to `/chunk-resolve-references`. Below the bar.
- `commands/orchestrator-monitor.md` Step 2 `/loop 3m` polling prompt: this
  is substantial but it is not a subagent role — it is the body of a
  recurring cron loop that must embed per-session runtime values
  (chunk names, changelog channel, swarm id) and is executed by the `/loop`
  mechanism, not the Agent tool. Plugin agents model subagent roles, not
  cron payloads. Not promoted.
- `commands/steward-setup.md` autonomous-mode behavior template: this is
  content written into the *target project's* STEWARD.md during setup —
  project-owned configuration the operator edits afterward — not a prompt
  the command uses to launch a subagent. Promoting it would move
  project-owned content into the plugin. Not promoted.

## Sequence

### Step 1: Create `agents/chunk-executor.md`

Write the agent definition with frontmatter:

- `name: chunk-executor`
- `description`: runs a single chunk through the full plan → implement →
  review → complete lifecycle in a parallel session; used by
  narrative-execute's wave execution. Phrased so the model can also select
  it proactively when asked to execute one chunk end-to-end in the
  background.
- `tools: Bash, Read, Edit, Write, Grep, Glob, SlashCommand` — it must run
  the `/chunk-plan`, `/chunk-implement`, `/chunk-review`, `/chunk-complete`
  slash commands and do everything implementation requires.

Body: the system prompt ported from narrative-execute Phase 4 — expect the
chunk name (and optionally the narrative name) in the task message; run
`/chunk-plan`, `/chunk-implement`, `/chunk-review` with up to 3
implement/review cycles, then `/chunk-complete`; report SUCCESS (chunk
ACTIVE) or FAILURE (which step, what went wrong). Add a
`<!-- Chunk: docs/chunks/plugin_subagents ... -->` backreference comment.

Location: `agents/chunk-executor.md`

### Step 2: Create `agents/intent-auditor.md`

Write the agent definition with frontmatter:

- `name: intent-auditor`
- `description`: audits a batch of ~5 ACTIVE chunks against the
  intent-ownership principles in docs/trunk/CHUNKS.md; rewrites
  retrospective framing, logs over-claims, historicalizes dead chunks;
  designed for audit-intent's parallel fan-out.
- `tools: Bash, Read, Edit, Write, Grep, Glob` — it edits GOAL.md files and
  writes inconsistency entries but never commits (constraint stays in the
  body).

Body: the full sub-agent protocol moved verbatim-in-substance from
audit-intent's `## Sub-agent prompt template`: scope taken from the task
message (batch ID + list of GOAL.md paths), detection criteria, action
rules, veto rule, symmetric verification, inconsistency entry format,
return format, constraints. Add the chunk backreference comment.

Location: `agents/intent-auditor.md`

### Step 3: Remove `agents/.gitkeep`

The placeholder from plugin_scaffold is obsolete once real agent files
exist.

### Step 4: Rewire `commands/narrative-execute.md`

Replace the Phase 4 inline prompt block with an instruction to launch the
**chunk-executor** plugin agent for each chunk in the wave (Agent tool,
`run_in_background: true`, all launches for a wave in a single message),
passing the chunk name and narrative name in the task message. Keep the
wave mechanics, the wait-and-check-results logic, and the SUCCESS/FAILURE
contract description (the orchestrating agent still needs to know what to
expect back). Add a `docs/chunks/plugin_subagents` backreference comment.

### Step 5: Rewire `commands/audit-intent.md`

Replace the `## Sub-agent prompt template` section (and the prompt body it
contains) with a short section explaining that each batch is handled by the
**intent-auditor** plugin agent: spawn 10 in parallel in a single message,
passing each its batch ID and 5-chunk scope list in the task message.
Update Step 3's reference to the prompt template accordingly. Keep the
"Notes for the orchestrating agent" section — it governs the orchestrator,
not the sub-agent — but update any sentence that refers to "the sub-agent
prompt template" to refer to the agent. Add the chunk backreference
comment.

### Step 6: Add `tests/test_plugin_agents.py`

Mirror the invariant style of `tests/test_plugin_commands.py`
(reusing `_parse_frontmatter` / `REPO_ROOT` from `test_plugin_manifest`):

- parametrized over `agents/*.md`: frontmatter `name` matches file stem,
  `description` non-empty, `tools` non-empty, no Jinja2 syntax, no
  AUTO-GENERATED header.
- `agents/` contains at least `chunk-executor.md` and `intent-auditor.md`
  (GOAL success criterion).
- `commands/narrative-execute.md` references `chunk-executor` and no longer
  embeds the inline lifecycle prompt (assert a distinctive phrase from the
  old inline block, e.g. "You are executing chunk", is gone from the
  command and present in the agent).
- `commands/audit-intent.md` references `intent-auditor` and no longer
  embeds the sub-agent protocol (assert a distinctive phrase, e.g.
  "Veto rule", lives in the agent, not the command).
- intent-auditor body carries the load-bearing rules (veto rule, symmetric
  verification) so the promotion didn't drop them.

### Step 7: Verify

- `uv run pytest tests/test_plugin_agents.py tests/test_plugin_commands.py
  tests/test_plugin_manifest.py` — the new tests pass and the existing
  command invariants still hold after the command edits.
- `uv run ve chunk validate plugin_subagents`.

## Dependencies

- plugin_core_commands (narrative-execute ported) and plugin_orch_commands
  (audit-intent ported) — both ACTIVE on this branch after fast-forwarding
  to main.
- The parallel chunk plugin_init_slimdown owns `src/project.py`,
  `src/templates/`, and src tests — this chunk must not touch those areas.

## Risks and Open Questions

- **Agent invocation naming**: plugin agents may surface to the model
  namespaced (e.g., `vibe-engineer:chunk-executor`) depending on Claude
  Code's plugin loading. The commands reference agents by their simple
  names and describe them as "the chunk-executor plugin agent", which the
  Agent tool resolves at runtime; if namespacing matters it is a
  plugin-manager concern, not a file-content one.
- **Static agents vs per-invocation parameters**: agent files cannot embed
  the chunk/batch being processed. Mitigated by writing agent bodies to
  read their scope from the task message and having the commands state
  exactly what to pass.
- **SlashCommand availability in subagents**: chunk-executor's body
  instructs running `/chunk-plan` etc. If a host disallows slash commands
  in subagents, the agent falls back to following the corresponding
  command docs directly; the body notes this.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->
