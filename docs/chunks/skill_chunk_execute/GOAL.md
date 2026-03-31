---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/chunk-execute.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/commands/chunk-execute.md.jinja2
    implements: "Chunk-execute slash command template — orchestrates plan → implement → complete lifecycle inline"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Lists /chunk-execute in Available Commands section of CLAUDE.md"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_analytics_domain
---

# Chunk Goal

## Minor Goal

Create a `/chunk-execute` slash command skill that is the official way to run
a chunk's plan → implement → complete cycle within the current session. This is
distinct from orchestrator injection — `/chunk-execute` runs the work inline
(same agent, same session), while `ve orch inject` delegates to a background
worktree agent.

**Key behavior:** In a task context, `/chunk-execute` should be the preferred
execution method (not orchestrator injection), because task contexts often need
the implementing agent to have access to the full multi-project environment.

The skill should:
- Accept a chunk name argument (or default to the current IMPLEMENTING chunk)
- Run `/chunk-plan` if the chunk doesn't have a plan yet
- Run `/chunk-implement` to execute the plan
- Run `/chunk-complete` to finalize
- Handle errors at each stage gracefully (report and stop)

Add the command to CLAUDE.md's available commands list.

The skill description must clearly indicate when to use it vs orchestrator
injection: "Use /chunk-execute to run a chunk in the current session. Use
ve orch inject to delegate to a background agent."

## Success Criteria

- `/chunk-execute <chunk>` runs the full plan → implement → complete cycle
- `/chunk-execute` without arguments picks up the current IMPLEMENTING chunk
- The skill is listed in CLAUDE.md under Available Commands
- The skill description triggers correctly when user says "execute the chunk"
  or "implement the chunk in this session"
- In task context, this is preferred over orchestrator injection