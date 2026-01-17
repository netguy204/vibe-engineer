---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/claude/CLAUDE.md.jinja2
- src/templates/chunk/GOAL.md.jinja2
code_references:
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Background keyword documentation section in CLAUDE.md"
- ref: src/templates/chunk/GOAL.md.jinja2
  implements: "Background workflow note in chunk GOAL.md template"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
created_after:
- orch_broadcast_invariant
- selective_artifact_friction
---

# Chunk Goal

## Minor Goal

Document the "background" keyword semantic for agent-orchestrator interaction in `CLAUDE.md`.

When an operator says **"do this in the background"** (or similar phrasing like "handle this in the background", "run this in the background"), this is an explicit signal that the agent should:

1. Create a FUTURE chunk for the work
2. Refine the GOAL.md as normal
3. **Present the goal to the operator for review** before proceeding
4. Once approved, commit the chunk
5. Inject it into the orchestrator

This is distinct from the existing orchestrator guidance, which describes *how* to interact with the orchestrator but doesn't define *when* agents should proactively use it. The "background" keyword provides that trigger.

### Why This Matters

The previous CLAUDE.md guidance suggested agents might proactively inject work into the orchestrator. However, this was too implicit—agents shouldn't assume every piece of work should be backgrounded. The "background" keyword makes this explicit:

- **Without "background"**: Create chunk normally, work on it in the current session
- **With "background"**: Create FUTURE chunk, commit, inject into orchestrator, continue with other work

### Scope

This chunk updates documentation in two places:
1. **CLAUDE.md** - Agent-facing guidance on when to use background workflow
2. **GOAL.md template** - Ensures agents implementing chunks see guidance about the review step

It does not:
- Modify any CLI commands
- Change orchestrator behavior
- Add code-level detection of the keyword

## Success Criteria

1. **CLAUDE.md updated**: The "Working with the Orchestrator" section includes a subsection explaining the "background" keyword semantic

2. **Clear trigger words documented**: The documentation lists phrases that trigger background workflow:
   - "do this in the background"
   - "handle this in the background"
   - "run this in the background"
   - "in the background"

3. **Workflow documented**: The expected agent behavior is clearly documented:
   - Create FUTURE chunk (not IMPLEMENTING)
   - Refine goal with operator
   - **Present goal for operator review and wait for approval**
   - Commit the chunk
   - Inject into orchestrator
   - Continue with other work or confirm completion

4. **Contrast with default behavior**: Documentation clarifies that without the "background" keyword, chunks are created as IMPLEMENTING and worked on immediately

5. **GOAL.md template updated**: The chunk GOAL.md template (`src/templates/chunks/GOAL.md.jinja2`) includes guidance in its comment block reminding agents that background work requires operator review before commit/inject