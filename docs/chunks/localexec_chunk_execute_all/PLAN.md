

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

Encode the wave/worktree/merge execution pattern proven on the
claude_plugin_port narrative as a static plugin command, reusing the existing
chunk-executor agent (extended with a worktree mode) rather than introducing a
new agent. Record the billing-driven preference for session-local execution as
an ADR so the contemplated orchestrator deprecation has a documented anchor.

## Subsystem Considerations

No subsystem implicated: the command is static plugin content (DEC-010
world); no template-system or src/ changes.

## Sequence

### Step 1: Write commands/chunk-execute-all.md

Canonical preamble per PORTING_GUIDE.md; phases: target selection → pre-flight
(committed chunks, test baseline, forbidden paths) → DAG/waves from depends_on
→ operator confirmation → wave execution (solo: main tree; parallel: worktree
isolation via chunk-executor) → per-wave merge-back/cleanup/verify → handoff
propagation → failure handling → finalize.

### Step 2: Extend agents/chunk-executor.md with worktree mode

Self-activation when FUTURE, fast-forward to main tip, commit on branch, never
merge, extended report (branch, worktree path, commits, handoffs). Preserve
lifecycle text, "3 times maximum" cap, SUCCESS/FAILURE contract.

### Step 3: DEC-012 ADR + README command-table row

### Step 4: Run plugin test suites; complete the chunk

## Dependencies

All eight claude_plugin_port chunks are ACTIVE; builds directly on
plugin_subagents (chunk-executor agent) and the porting convention.

## Risks and Open Questions

- The Agent-tool worktree mechanics (isolation parameter, branch naming) are
  host-environment features; the command describes them behaviorally ("an
  isolated git worktree on a dedicated branch") so it degrades gracefully on
  hosts with different agent tooling.

## Deviations

(populated during implementation)
