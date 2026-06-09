---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- agents/chunk-executor.md
- agents/intent-auditor.md
- commands/narrative-execute.md
- commands/audit-intent.md
- tests/test_plugin_agents.py
code_references:
- ref: agents/chunk-executor.md
  implements: "chunk-executor plugin agent — full chunk lifecycle (plan/implement/review/complete) in a parallel session, promoted from narrative-execute's inline prompt"
- ref: agents/intent-auditor.md
  implements: "intent-auditor plugin agent — self-contained 5-chunk audit protocol (detection criteria, action rules, veto rule, symmetric verification), promoted from audit-intent's sub-agent prompt template"
- ref: commands/narrative-execute.md
  implements: "Phase 4 wave execution references the chunk-executor agent by name instead of embedding the lifecycle prompt"
- ref: commands/audit-intent.md
  implements: "Step 3 fan-out spawns intent-auditor agents; the inline sub-agent prompt template is replaced by 'The intent-auditor agent' section"
- ref: tests/test_plugin_agents.py#TestAgentInvariants
  implements: "Static-file invariants for agents/ (frontmatter name/description/tools, no Jinja2, no auto-generated header)"
- ref: tests/test_plugin_agents.py#TestChunkExecutorPromotion
  implements: "chunk-executor promotion checks: lifecycle and report contract live in the agent, not the command"
- ref: tests/test_plugin_agents.py#TestIntentAuditorPromotion
  implements: "intent-auditor promotion checks: veto rule and verification protocol live in the agent, not the command"
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_core_commands
- plugin_orch_commands
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---
# Chunk Goal

## Minor Goal

Parallelizable workflow roles that commands previously described inline are
named plugin agents in the plugin's agents/ directory. At minimum: a
chunk-executor agent (used by narrative-execute to run a chunk's plan →
implement → complete cycle in a parallel session) and an intent-auditor agent
(used by audit-intent's fan-out of five chunks per agent). Ported commands
reference these agents by name instead of embedding full agent prompts, so
each role's behavior is versioned once in the plugin.

## Context

- The promotion candidates come from a survey of the commands ported by
  plugin_core_commands and plugin_orch_commands for inline agent prompt
  blocks; the survey's full outcome (six candidates, two promoted, four
  deliberately left inline with rationale) is recorded in this chunk's
  PLAN.md under "Survey Outcome".
- Plugin agents are markdown files with frontmatter (name, description,
  tools) under agents/.
- Promotion bar: only roles that are invoked from more than one command or
  whose inline prompt is substantial earn a named agent. A one-off two-line
  prompt stays inline.

## Success Criteria

- agents/ contains at least chunk-executor and intent-auditor definitions
  with descriptions and appropriate tool access.
- The narrative-execute and audit-intent commands reference the named agents
  rather than embedding their prompts inline.
- The survey's outcome is recorded: which inline prompts were considered and
  deliberately not promoted, and why.
