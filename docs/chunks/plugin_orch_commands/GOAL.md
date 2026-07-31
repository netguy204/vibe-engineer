---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- skills/orchestrator-inject/SKILL.md
- skills/orchestrator-monitor/SKILL.md
- skills/orchestrator-investigate/SKILL.md
- skills/orchestrator-submit-future/SKILL.md
- skills/steward-setup/SKILL.md
- skills/steward-watch/SKILL.md
- skills/steward-send/SKILL.md
- skills/steward-changelog/SKILL.md
- skills/swarm-monitor/SKILL.md
- skills/swarm-request-response/SKILL.md
- skills/entity-startup/SKILL.md
- skills/entity-shutdown/SKILL.md
- skills/entity-episodic/SKILL.md
- skills/audit-intent/SKILL.md
- skills/migrate-managed-claude-md/SKILL.md
code_references:
- ref: skills/orchestrator-inject/SKILL.md
  implements: 'Static plugin command: commit pre-flight + ve orch inject with monitoring
    offer'
- ref: skills/orchestrator-monitor/SKILL.md
  implements: 'Static plugin command: recurring orchestrator polling with status handlers
    and guardrails'
- ref: skills/orchestrator-investigate/SKILL.md
  implements: 'Static plugin command: stuck work-unit diagnosis scenarios A-G and
    resolutions'
- ref: skills/orchestrator-submit-future/SKILL.md
  implements: 'Static plugin command: batch FUTURE-chunk submission with eligibility
    guards'
- ref: skills/steward-setup/SKILL.md
  implements: 'Static plugin command: steward SOP interview producing docs/trunk/STEWARD.md'
- ref: skills/steward-watch/SKILL.md
  implements: 'Static plugin command: watch-respond-rewatch steward loop with cursor
    safety'
- ref: skills/steward-send/SKILL.md
  implements: 'Static plugin command: send to a steward channel; carries the target-project
    channel-naming guidance and common-mistake warning'
- ref: skills/steward-changelog/SKILL.md
  implements: 'Static plugin command: watch a project''s changelog channel with project-local
    cursor'
- ref: skills/swarm-monitor/SKILL.md
  implements: 'Static plugin command: multi-channel changelog monitoring; carries
    cross-project channel-naming guidance'
- ref: skills/swarm-request-response/SKILL.md
  implements: 'Static plugin command: request-response over channel pairs; carries
    the target-project channel-naming guidance'
- ref: skills/entity-startup/SKILL.md
  implements: 'Static plugin command: entity wake sequence (identity, memories, wiki,
    SOP)'
- ref: skills/entity-shutdown/SKILL.md
  implements: 'Static plugin command: entity sleep cycle for wiki and legacy entities'
- ref: skills/entity-episodic/SKILL.md
  implements: 'Static plugin command: episodic transcript search workflow'
- ref: skills/audit-intent/SKILL.md
  implements: 'Static plugin command: parallel chunk-corpus intent audit with inline
    sub-agent prompt template'
- ref: skills/migrate-managed-claude-md/SKILL.md
  implements: 'Static plugin command: CLAUDE.md magic-marker migration phases'
narrative: claude_plugin_port
investigation: null
subsystems: []
friction_entries: []
depends_on:
- plugin_runtime_context
created_after:
- orch_max_turns_config
- watch_handshake_timeout_retry
---

# Chunk Goal

## Minor Goal

The orchestrator, steward, swarm, entity, and migration commands ship as
static plugin commands and skills: orchestrator-inject, orchestrator-monitor,
orchestrator-investigate, orchestrator-submit-future, steward-setup,
steward-watch, steward-send, steward-changelog, swarm-monitor,
swarm-request-response, entity-startup, entity-shutdown, entity-episodic,
audit-intent, and migrate-managed-claude-md. Each exists as a slash command
and carries a skill description for proactive invocation; all follow the
runtime context-detection convention established by plugin_runtime_context.

## Context

- Sources: src/templates/commands/<name>.md.jinja2, same porting rules as
  plugin_core_commands (strip Jinja2, drop the auto-generated header, apply
  the runtime context-detection convention).
- These commands shell out to `ve orch`, `ve board`, and entity tooling — the
  ve CLI dependency is expected and checked by the plugin_session_hooks chunk.
- The cross-project messaging guidance (derive the channel name from the
  TARGET project: `<target-project>-steward`, not the local steward's channel)
  travels inside the steward-send and swarm command bodies. It therefore
  survives plugin_init_slimdown, which shrinks the AGENTS.md managed block
  where the guidance also appears.
- Source templates remain in place during this chunk — deletion belongs to
  plugin_init_slimdown.

## Success Criteria

- All 15 commands exist in the plugin with no Jinja2 syntax remaining.
- Each command has a description suitable for proactive/skill invocation.
- The steward-send and swarm command bodies carry the target-project channel
  naming guidance.
- Spot-check from a plugin install: steward-send and orchestrator-monitor run
  correctly in a ve project.
