# Operator verification: the full Cursor surface

<!-- Chunk: docs/chunks/dualplugin_cursor_render - Live Cursor verification script -->

> **VERIFICATION SATISFIED — 2026-08-14.** The operator performed the manual
> Cursor IDE validation and confirmed it via the coordination channel
> ("the required manual Cursor IDE validation has already been performed").
> The items below are retained as the record of what was checked and as the
> script for re-verification after any future Cursor spec change.

The scaffold chunk's pilot (2 skills) is verified in a live Cursor session.
This chunk widens the render to the full surface — 39 skills and 2 agents —
and the GOAL requires a four-command sample confirmed live, chosen to
exercise the mechanisms static checks cannot: runtime context detection,
plan authoring, channel-naming guidance, and sub-agent orchestration.
Until someone runs this, the chunk's review ESCALATEs rather than approves
on static checks alone (the GOAL says so).

## Setup

Same as the scaffold's script
(`docs/chunks/dualplugin_cursor_scaffold/CURSOR_VERIFICATION.md`): plugin
installed from this repository via a team marketplace or the marketplace
listing, `ve` CLI on PATH, a ve-initialized project open. If the plugin was
installed during the pilot, update it so the new render is what Cursor
loads.

## 1. Component inventory

Dashboard → Plugins → `vibe-engineer` (or Customize). Expected:

- **39 skills** (was 2 in the pilot).
- **2 agents**: `chunk-executor` and `intent-auditor`.
- Still **0 commands, 0 rules, 0 hooks, 0 MCP servers**. Any hook appearing
  means the `"hooks": {}` suppression regressed.

If skills show 2, Cursor is still reading a cached install — update or
reinstall before continuing.

## 2. `chunk-create` — runtime context detection

Ask in plain language for a small, intent-bearing chunk. Expected: the
read-only probes actually run in the terminal (not read as text), the agent
uses *your request* as the chunk's subject (no `$ARGUMENTS` behavior
regressions), and it presents the GOAL.md for approval before committing.
Discard the created chunk afterwards.

## 3. `chunk-plan` — plan authoring

With an IMPLEMENTING chunk present (the one from step 2 works before you
discard it), ask the agent to plan the current chunk. Expected: it runs
`ve chunk list --current`, offers the prefix check, studies GOAL.md, and
completes PLAN.md — same behavior the Claude flavor shows.

## 4. `steward-send` — channel-naming guidance

Ask the agent to send a steward message (a swarm server need not be
reachable; the interesting part is before the send). Expected: it derives
the channel name from the **target** project per the skill's guidance, and
reports what it would send / that the server was unreachable, rather than
inventing a channel name.

## 5. `chunk-execute-all` — sub-agent orchestration

The load-bearing test, and the one most likely to diverge. With two or more
approved FUTURE chunks (small, disjoint ones), ask the agent to execute all
chunks. Expected:

1. Probes run; baseline and forbidden paths recorded; the wave plan is
   displayed and it **waits for your confirmation**.
2. For a parallel wave it launches the `chunk-executor` **agent** (the
   plugin's subagent) once per chunk, each in its own git worktree.
3. Sub-agents follow the worktree protocol from the agent definition:
   commit on their branch, never merge; the parent merges after the wave.

**What to record if it diverges:** whether Cursor can launch the plugin's
`chunk-executor` subagent at all, how it launches it (the skill's phrasing
assumes a harness with a sub-agent launch mechanism), and whether worktree
isolation happened. A divergence here is a finding, not a failure of the
render — document the exact behavior so the follow-up can encode the real
Cursor mechanism.

## 6. Known Claude-isms shipped deliberately

The orchestration/steward skills still name Claude Code harness tools where
no verified Cursor equivalent exists: `TaskStop`, `run_in_background`,
`/loop`, `CronDelete`, and "the Agent tool" in `narrative-execute` and
`audit-intent`. If you observe Cursor's real counterparts for background
tasks and sub-agent launches during step 5, note them — they are exactly
what the follow-up idiom work needs.

## 7. Report back

For each of steps 1–5: worked / diverged, with exact text for divergences.
Plus the Cursor version tested, and whether skills engaged from plain
language or had to be named.
