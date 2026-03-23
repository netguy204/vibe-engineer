---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/orchestrator-monitor.md.jinja2
code_references:
- ref: src/templates/commands/orchestrator-monitor.md.jinja2
  implements: "Guardrails DO NOT section, updated DONE handler, CWD verification reminders, and loop prompt guardrails"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_watch_stale_reconnect
---

# Chunk Goal

## Minor Goal

Add guardrails to the `/orchestrator-monitor` skill template to prevent four anti-patterns observed during real orchestrator monitoring sessions.

Anti-patterns reported by palette/creator entity:

1. **Unnecessary intervention on DONE chunks**: Agents manually merge or run `ve chunk complete` on DONE branches that the orchestrator handles automatically. The skill should clarify: only intervene on NEEDS_ATTENTION — DONE chunks are finalized by the orchestrator.

2. **Starting a second orchestrator**: When `ve orch ps` returns "not running" (transient or CWD issue), agents run `ve orch start`, creating a nested Claude Code situation. The skill should explicitly warn: NEVER run `ve orch start` or `ve orch stop` — the orchestrator is managed externally by the operator.

3. **Working in worktree directories**: After inspecting a worktree at `.ve/chunks/<name>/worktree`, agents run git commands from that directory instead of the project root. The skill should remind agents to verify `pwd` is the project root before any git operations.

4. **Dirty working tree blocking merges**: Manual merge attempts leave uncommitted changes on main, blocking the orchestrator's automatic merge. The skill should warn: never leave uncommitted changes on main.

## Success Criteria

- `/orchestrator-monitor` template includes a "DO NOT" section with all four guardrails
- DONE status handler says "no action needed — orchestrator handles merge automatically"
- Template warns against `ve orch start/stop` from monitoring context
- Template includes CWD verification reminder after any worktree inspection
- Template includes clean working tree check before any git operations

