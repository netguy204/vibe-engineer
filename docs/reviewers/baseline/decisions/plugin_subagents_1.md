---
decision: APPROVE
summary: "Both promoted agents exist with descriptions and explicit tool access, the rewired commands reference them by name with no inline prompt bodies remaining, and the survey outcome (2 promoted, 4 deliberately not promoted with rationale) is recorded in the chunk's PLAN.md — all enforced by 150 passing plugin tests."
operator_review: null  # DO NOT SET - reserved for operator curation good | bad | feedback: "<message>"
---

## Criteria Assessment

### Criterion 1: agents/ contains at least chunk-executor and intent-auditor definitions with descriptions and appropriate tool access

- **Status**: satisfied
- **Evidence**: `agents/chunk-executor.md` (tools: Bash, Read, Edit, Write, Grep, Glob, SlashCommand — it runs the chunk lifecycle slash commands) and `agents/intent-auditor.md` (tools: Bash, Read, Edit, Write, Grep, Glob — edits GOAL.md files and writes inconsistency entries, body forbids commits) both carry name/description/tools frontmatter. The audit protocol's load-bearing rules (veto rule, symmetric verification, return format, working-tree-only constraint) and the executor's retry cap and SUCCESS/FAILURE contract survived the promotion — asserted by tests/test_plugin_agents.py (TestChunkExecutorPromotion::test_agent_carries_lifecycle, TestIntentAuditorPromotion::test_agent_carries_load_bearing_rules).

### Criterion 2: The narrative-execute and audit-intent commands reference the named agents rather than embedding their prompts inline

- **Status**: satisfied
- **Evidence**: commands/narrative-execute.md Phase 4 now launches "the chunk-executor plugin agent" with a one-line task message; the "You are executing chunk" inline prompt is gone. commands/audit-intent.md Step 3 spawns subagent type `intent-auditor` and the 80-line "## Sub-agent prompt template" section is replaced by "## The intent-auditor agent" describing only the per-invocation task message. Wave mechanics, failure handling, and "Notes for the orchestrating agent" remain with the commands. Enforced by tests (test_command_no_longer_embeds_prompt, test_command_no_longer_embeds_protocol, test_command_keeps_wave_mechanics, test_command_keeps_orchestration). All 150 plugin tests pass; full suite shows only the 32 pre-existing failures.

### Criterion 3: The survey's outcome is recorded: which inline prompts were considered and deliberately not promoted, and why

- **Status**: satisfied
- **Evidence**: docs/chunks/plugin_subagents/PLAN.md "## Survey Outcome" records the two promotions and four deliberate non-promotions with rationale: chunks-resolve-references step 2 and chunk-complete step 6 (one-line delegations to already-versioned commands — below the bar), orchestrator-monitor Step 2 (cron loop payload with per-session runtime values, not a subagent role), steward-setup autonomous-mode template (project-owned STEWARD.md content, not a subagent prompt).
