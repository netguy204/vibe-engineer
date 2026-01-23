---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
  - src/templates/commands/chunk-create.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-create.md.jinja2
    implements: "User intent detection for FUTURE vs IMPLEMENTING chunk creation, including priority order, conflict handling, and safe pause protocol"
narrative: null
subsystems: []
created_after: ["investigation_chunk_refs"]
---

# Chunk Goal

## Minor Goal

The `/chunk-create` slash command currently has rigid logic for determining whether to create a FUTURE or IMPLEMENTING chunk: it only uses `--future` when an implementing chunk already exists. This ignores explicit user intent when they say things like "create this for the future" or "queue this up for later."

This chunk improves the slash command to analyze the user's input for explicit signals about timing preference, giving those signals priority over the default heuristics. This respects user autonomy and makes the workflow more flexible.

## Success Criteria

1. **User intent detection**: The `/chunk-create` slash command instructions explicitly tell the agent to scan for user signals indicating FUTURE preference (e.g., "future", "later", "queue", "backlog", "upcoming", "not now", "after current work")
2. **Priority order documented**: Instructions clearly state: (1) explicit user signals take priority, (2) then check for existing implementing chunk, (3) then use default behavior
3. **IMPLEMENTING intent detection**: Also detect explicit "now", "immediately", "start working on", "next up" signals that indicate the user wants IMPLEMENTING status even when a chunk already exists
4. **Conflict handling**: If user intent conflicts with current state (e.g., "work on this now" but implementing chunk exists), the agent offers to pause the current implementing chunk so the new chunk can become IMPLEMENTING
5. **Safe pause protocol**: Before pausing an implementing chunk, the agent must:
   - Run tests and confirm they pass (gate the transition on healthy codebase)
   - Add a "Paused State" section to the chunk's PLAN.md documenting: what's been completed, what remains, any work-in-progress context the resuming agent needs
   - Only then change the chunk status from IMPLEMENTING to FUTURE

