---
status: IMPLEMENTING
ticket: null
parent_chunk: null
code_paths:
- pyproject.toml
- src/orchestrator/__init__.py
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/orchestrator/worktree.py
- src/orchestrator/agent.py
- src/orchestrator/scheduler.py
- src/orchestrator/daemon.py
- src/orchestrator/api.py
- src/ve.py
- tests/test_orchestrator_worktree.py
- tests/test_orchestrator_agent.py
- tests/test_orchestrator_scheduler.py
- tests/test_orchestrator_cli.py
- tests/test_orchestrator_integration.py
code_references: []
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_foundation"]
---

<!--
╔══════════════════════════════════════════════════════════════════════════════╗
║  DO NOT DELETE THIS COMMENT BLOCK until the chunk complete command is run.   ║
║                                                                              ║
║  AGENT INSTRUCTIONS: When editing this file, preserve this entire comment    ║
║  block. Only modify the frontmatter YAML and the content sections below      ║
║  (Minor Goal, Success Criteria, Relationship to Parent). Use targeted edits  ║
║  that replace specific sections rather than rewriting the entire file.       ║
╚══════════════════════════════════════════════════════════════════════════════╝

This comment describes schema information that needs to be adhered
to throughout the process.

STATUS VALUES:
- FUTURE: This chunk is queued for future work and not yet being implemented
- IMPLEMENTING: This chunk is in the process of being implemented.
- ACTIVE: This chunk accurately describes current or recently-merged work
- SUPERSEDED: Another chunk has modified the code this chunk governed
- HISTORICAL: Significant drift; kept for archaeology only

PARENT_CHUNK:
- null for new work
- chunk directory name (e.g., "006-segment-compaction") for corrections or modifications

CODE_PATHS:
- Populated at planning time
- List files you expect to create or modify
- Example: ["src/segment/writer.rs", "src/segment/format.rs"]

CODE_REFERENCES:
- Populated after implementation, before PR
- Uses symbolic references to identify code locations

- Format: {file_path}#{symbol_path} where symbol_path uses :: as nesting separator
- Example:
  code_references:
    - ref: src/segment/writer.rs#SegmentWriter
      implements: "Core write loop and buffer management"
    - ref: src/segment/writer.rs#SegmentWriter::fsync
      implements: "Durability guarantees"
    - ref: src/utils.py#validate_input
      implements: "Input validation logic"


NARRATIVE:
- If this chunk was derived from a narrative document, reference the narrative directory name.
- When setting this field during /chunk-create, also update the narrative's OVERVIEW.md
  frontmatter to add this chunk to its `chunks` array with the prompt and chunk_directory.
- If this is the final chunk of a narrative, the narrative status should be set to completed
  when this chunk is completed.

INVESTIGATION:
- If this chunk was derived from an investigation's proposed_chunks, reference the investigation
  directory name (e.g., "memory_leak" for docs/investigations/memory_leak/).
- This provides traceability from implementation work back to exploratory findings.
- When implementing, read the referenced investigation's OVERVIEW.md for context on findings,
  hypotheses tested, and decisions made during exploration.
- Validated by `ve chunk validate` to ensure referenced investigations exist.

SUBSYSTEMS:
- Optional list of subsystem references that this chunk relates to
- Format: subsystem_id is {NNNN}-{short_name}, relationship is "implements" or "uses"
- "implements": This chunk directly implements part of the subsystem's functionality
- "uses": This chunk depends on or uses the subsystem's functionality
- Example:
  subsystems:
    - subsystem_id: "0001-validation"
      relationship: implements
    - subsystem_id: "0002-frontmatter"
      relationship: uses
- Validated by `ve chunk validate` to ensure referenced subsystems exist
- When a chunk that implements a subsystem is completed, a reference should be added to
  that chunk in the subsystems OVERVIEW.md file front matter and relevant section.

CHUNK ARTIFACTS:
- Single-use scripts, migration tools, or one-time utilities created for this chunk
  should be stored in the chunk directory (e.g., docs/chunks/0042-foo/migrate.py)
- These artifacts help future archaeologists understand what the chunk did
- Unlike code in src/, chunk artifacts are not expected to be maintained long-term
- Examples: data migration scripts, one-time fixups, analysis tools used during implementation
-->

# Chunk Goal

## Minor Goal

Implement the scheduling layer of the parallel agent orchestrator - the ability to manage git worktrees as isolated execution environments and spawn agents to execute single phases of chunk work.

This is Phase 2 from the `docs/investigations/parallel_agent_orchestration/design.md`. Building on the daemon foundation (orch_foundation), this chunk brings the "OS analogy" to life: worktrees are processes with their own address space, agents are stateless CPUs that execute a single phase then return the worktree to the ready queue.

This chunk enables:
- Parallel chunk execution across multiple worktrees
- Automatic dispatching of ready work units to available agent slots
- The `ve orch inject` command to add chunks to the work pool
- A ready queue that the daemon pulls from when agent slots are available

## Success Criteria

1. **Worktree manager creates and destroys isolated workspaces**
   - `git worktree add` creates worktree when work unit starts
   - Each chunk gets its own branch (e.g., `orch/chunk_name`)
   - Worktrees stored at `.ve/chunks/<chunk_name>/worktree/`
   - Worktree is removed when work unit completes or is killed
   - Handles concurrent worktree operations safely

2. **Agent spawning executes single-phase work**
   - Uses Claude Agent SDK (`claude-agent-sdk` Python package) to run agents
   - Each phase is a fresh `query()` call - no context carryover between phases
   - Agent receives: phase-specific prompt with chunk directory as working directory
   - Agent runs in the worktree (isolated from main tree)
   - Phase completion detected when async generator exhausts
   - Transcript captured to `.ve/chunks/<chunk_name>/log/<phase>.txt`

3. **Dispatch loop automatically schedules ready work**
   - Configurable max agent slots (default: 2)
   - When slots available, daemon picks READY work unit and spawns agent
   - Work unit transitions: READY → RUNNING → (DONE | NEEDS_ATTENTION | BLOCKED)
   - `ve orch config --max-agents=N` controls throughput

4. **`ve orch inject` command adds chunks to work pool**
   - `ve orch inject <chunk>` adds single chunk
   - `ve orch inject --all-proposed` imports all proposed chunks from investigations/narratives
   - Validates chunk exists and has GOAL.md
   - Sets initial phase based on chunk state (e.g., has PLAN.md → IMPLEMENT phase)

5. **Ready queue surfaces pending work**
   - `ve orch queue` shows work units in READY state
   - Queue ordered by priority (blocked_count, then age)
   - `ve orch prioritize <chunk>` bumps priority

## Design Context

From the design document:

- **Stateless agents**: Each phase is a fresh agent context. Agent completes phase, worktree returns to ready queue.
- **Agent slots**: Control throughput/cost, not context. 2 slots = at most 2 concurrent agents.
- **Phase execution via skills**: The orchestrator invokes existing slash commands:
  - GOAL: `/chunk-create` (with chunk context)
  - PLAN: `/chunk-plan`
  - IMPLEMENT: `/chunk-implement`
  - COMPLETE: `/chunk-complete`

## Agent Interface: Claude Agent SDK

**Decision**: Use the Claude Agent SDK (Python: `claude-agent-sdk`) with session-per-phase semantics.

**Session lifecycle per phase:**
1. Fresh `query()` call starts a new session for each phase (GOAL/PLAN/IMPLEMENT/COMPLETE)
2. Capture `session_id` from the `init` message
3. Iterate async generator, processing tool calls and messages
4. If agent calls `AskUserQuestion`: suspend iteration, queue to attention queue, save session_id
5. When operator answers: resume with `options.resume=session_id`, injecting the answer
6. When phase completes: session ends, next phase starts fresh (empty agent context)

**Why session-per-phase (not session-per-chunk):**
- Agent context shouldn't accumulate across phases - each phase is a focused task
- The workdir contains all needed context (GOAL.md, PLAN.md, code files)
- Fresh context prevents confusion from stale assumptions
- Matches the OS analogy: phase = instruction, not long-running process

**Handling AskUserQuestion:**
- Use `PreToolUse` hook to intercept `AskUserQuestion` calls
- Extract question and options from tool input
- Queue to attention queue with session_id for later resume
- Return hook result that suspends the agent loop
- When operator answers, resume session with answer in prompt

## Out of Scope

- Question/decision capture from agents (Phase 3: Attention Queue) — though agent interface choice affects this
- Conflict detection between work units (Phase 4: Conflict Oracle)
- Web dashboard (Phase 5: Dashboard)
- Semantic merge resolution
- Review gates (auto-advance vs require-review decisions)