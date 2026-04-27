---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/orchestrator-monitor.md.jinja2
- src/templates/commands/steward-watch.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/commands/orchestrator-monitor.md.jinja2
  implements: "Orchestrator monitor slash command skill template with status handler logic, loop setup, and lifecycle management"
- ref: src/templates/commands/steward-watch.md.jinja2
  implements: "Updated Step 6 to delegate monitoring to /orchestrator-monitor instead of inline loop construction"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Registered /orchestrator-monitor in the orchestrator commands list"
narrative: null
investigation: null
subsystems:
- subsystem_id: orchestrator
  relationship: uses
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_cursor_root_resolution
---

# Chunk Goal

## Minor Goal

The `/orchestrator-monitor` slash command skill standardizes how stewards (and other agents) monitor injected chunks through the orchestrator lifecycle to completion.

Without this skill, steward-watch would manually construct `/loop` prompts with inline orchestrator polling logic each time a chunk is injected — error-prone because agents forget to handle NEEDS_ATTENTION, don't know the right `ve orch` subcommands for diagnosis, or fail to cancel loops after completion.

The skill:
1. Accepts chunk name(s) as arguments
2. Sets up a `/loop 3m` to poll `ve orch ps` for those chunks
3. Runs the first check immediately (doesn't wait for first cron fire)
4. Handles each status: RUNNING (no action), NEEDS_ATTENTION (diagnose via `ve orch work-unit show`, resolve or escalate), DONE (push, deploy if needed, post changelog, cancel loop), FAILED (post failure summary)
5. For NEEDS_ATTENTION: checks `attention_reason`, inspects branch commits/diffs, merges manually if sufficient or resets to READY for retry
6. Accepts a `--changelog-channel` and `--swarm` to know where to post outcomes

This pairs with `/steward-watch` — the steward monitors chunks concurrently with watching the inbound channel.

## Success Criteria

- `/orchestrator-monitor <chunk1> [chunk2...]` skill exists in the commands directory
- Skill sets up recurring poll via `/loop` and runs first check immediately
- Handles all orchestrator statuses: RUNNING, NEEDS_ATTENTION, DONE, FAILED
- NEEDS_ATTENTION handling includes diagnosis steps (`ve orch work-unit show`, branch inspection, manual merge or reset)
- DONE handling includes git push, conditional worker deploy, and changelog posting
- Skill is registered in CLAUDE.md command list
- `/steward-watch` is updated to reference `/orchestrator-monitor` instead of inline loop construction

