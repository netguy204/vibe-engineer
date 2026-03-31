---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/narrative-execute.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
- .claude/commands/narrative-execute.md
- CLAUDE.md
code_references:
- ref: src/templates/commands/narrative-execute.md.jinja2
  implements: "Slash command template with full narrative execution workflow: DAG parsing, wave computation, parallel Agent dispatch, failure handling, and finalization"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Registration of /narrative-execute in Available Commands section"
narrative: null
investigation: null
subsystems:
- subsystem_id: template_system
  relationship: uses
friction_entries: []
bug_type: null
depends_on: []
created_after:
- landing_page_analytics_domain
---

# Chunk Goal

## Minor Goal

Create a `/narrative-execute` slash command skill that executes a narrative's
proposed chunks in dependency order, maximizing parallelism via background
subagents. This codifies a pattern proven in the gsr-model-migration task.

### Input

Narrative short name (e.g., `gsr_coverage_integration`).

### Behavior

1. **Parse the narrative** — Read OVERVIEW.md, extract `proposed_chunks` array
   from frontmatter. Each entry has a `chunk_directory` and `depends_on` field
   (list of array indices referencing other proposed_chunks).

2. **Build the dependency DAG** — Map `depends_on` indices to
   `chunk_directory` names. Identify roots (chunks with empty `depends_on`).

3. **Create missing chunks** — For proposed chunks that don't yet exist on
   disk, create them via `ve chunk create`. Populate GOAL.md from the
   narrative's proposed chunk description.

4. **Execute in topological order:**
   - Activate each chunk before executing (`ve chunk activate` or set status
     to IMPLEMENTING)
   - Launch independent chunks in parallel via background Agent tool calls
     (multiple Agent invocations in a single message)
   - Each subagent runs the full lifecycle: `/chunk-plan` → `/chunk-implement`
     → `/chunk-review` (loop until approved) → `/chunk-complete`
   - The parent agent stays lightweight — just tracks completion and launches
     the next wave of unblocked chunks
   - When a chunk completes, check which blocked chunks now have all
     dependencies satisfied and launch them

5. **Handle failures** — If a chunk fails, report to operator and pause
   execution (don't cascade failures to dependents). The operator can fix
   and resume.

6. **Finalize** — When all chunks complete, set narrative status to COMPLETED.

### Origin

This pattern was developed manually during the `gsr_coverage_integration`
narrative execution in the gsr-model-migration task. The execution graph was:

```
[0] gsr_coverage_key_encoding (root)
 ├── [1] gsr_coverage_query (depends_on: [0])
 ├── [2] gsr_recommender_coverage (depends_on: [0])
 │
 └──► [3] gsr_opportunities_coverage (depends_on: [1, 2])
          └──► [4] gsr_offering_id_parsing (depends_on: [0, 3])
```

Chunks 1 and 2 ran in parallel after 0 completed. Chunk 3 waited for both.
This skill automates that orchestration pattern.

### Distinction from orchestrator

The orchestrator (`ve orch inject`) delegates to background worktree agents
managed by a server daemon. `/narrative-execute` runs chunks inline using
Claude Code's native Agent tool for parallelism — no orchestrator daemon
needed. This is better for task contexts where agents need the full
multi-project environment, and for narratives where the executing agent
benefits from accumulated session context.

## Success Criteria

- `/narrative-execute <name>` executes all proposed chunks in dependency order
- Independent chunks launch in parallel (multiple Agent calls in one message)
- Dependent chunks wait for all dependencies before launching
- Each chunk goes through plan → implement → review → complete lifecycle
- Failed chunks pause execution and report to operator
- Narrative status set to COMPLETED when all chunks finish
- The skill is listed in CLAUDE.md under Available Commands
- The skill description triggers on "execute the narrative", "run the
  narrative", "implement the narrative"