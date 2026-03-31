---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/orchestrator-inject.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
  - ref: src/templates/commands/orchestrator-inject.md.jinja2
    implements: "Slash command template with pre-flight commit check and orchestrator injection workflow"
  - ref: src/templates/claude/CLAUDE.md.jinja2
    implements: "Added /orchestrator-inject to orchestrator commands listing"
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

Create a `/orchestrator-inject` slash command skill that wraps
`ve orch inject <chunk>` with proper pre-flight checks. The skill description
must trigger when the user says "inject the chunk", "inject it", "send it to
the orchestrator", etc.

The skill should:
1. Accept a chunk name argument (or default to the current IMPLEMENTING/FUTURE chunk)
2. **Pre-flight: ensure the chunk is committed** — Run `git status` and check
   if the chunk's GOAL.md and PLAN.md are tracked and committed. If not,
   commit both files automatically before injecting. This prevents the common
   error of injecting a chunk whose files only exist in the working tree.
3. Run `ve orch inject <chunk>` and report the result
4. Optionally set up `/orchestrator-monitor` for the injected chunk

Add the command to CLAUDE.md's available commands list.

### Context

Currently, injecting chunks requires the agent to remember to commit first.
Agents frequently forget this step, causing the orchestrator worktree to not
have the chunk files. This skill automates the commit-then-inject pattern.

## Success Criteria

- `/orchestrator-inject <chunk>` commits and injects the chunk
- `/orchestrator-inject` without arguments picks up the current chunk
- The skill triggers on "inject the chunk", "inject it", "send to orchestrator"
- Uncommitted chunk files are auto-committed before injection
- The skill is listed in CLAUDE.md under Available Commands
- Already-committed chunks skip the commit step cleanly