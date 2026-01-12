---
status: ACTIVE
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
code_references:
  - ref: src/orchestrator/worktree.py#WorktreeManager
    implements: "Git worktree lifecycle management for isolated chunk execution"
  - ref: src/orchestrator/worktree.py#WorktreeManager::create_worktree
    implements: "Creates git worktree for chunk at .ve/chunks/<chunk>/worktree/"
  - ref: src/orchestrator/worktree.py#WorktreeManager::remove_worktree
    implements: "Removes worktree and optionally its branch"
  - ref: src/orchestrator/worktree.py#WorktreeManager::merge_to_base
    implements: "Merges chunk branch back to base branch on completion"
  - ref: src/orchestrator/agent.py#AgentRunner
    implements: "Agent execution using Claude Agent SDK"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Single phase execution with session-per-phase semantics"
  - ref: src/orchestrator/agent.py#create_log_callback
    implements: "Transcript capture to .ve/chunks/<chunk>/log/<phase>.txt"
  - ref: src/orchestrator/scheduler.py#Scheduler
    implements: "Dispatch loop for scheduling work units to agents"
  - ref: src/orchestrator/scheduler.py#Scheduler::start
    implements: "Main scheduler loop that checks for READY work and spawns agents"
  - ref: src/orchestrator/scheduler.py#Scheduler::_dispatch_tick
    implements: "One dispatch cycle - spawns agents up to max_agents slots"
  - ref: src/orchestrator/scheduler.py#Scheduler::_advance_phase
    implements: "Phase progression and merge-on-complete logic"
  - ref: src/orchestrator/scheduler.py#create_scheduler
    implements: "Factory function to create configured scheduler"
  - ref: src/orchestrator/models.py#OrchestratorConfig
    implements: "Configuration model with max_agents and dispatch_interval_seconds"
  - ref: src/orchestrator/models.py#AgentResult
    implements: "Result model for agent phase execution"
  - ref: src/orchestrator/state.py#StateStore::_migrate_v2
    implements: "Schema migration adding priority, session_id, and config table"
  - ref: src/orchestrator/state.py#StateStore::get_ready_queue
    implements: "Ready queue ordered by priority DESC, created_at ASC"
  - ref: src/orchestrator/state.py#StateStore::get_config
    implements: "Config key-value retrieval"
  - ref: src/orchestrator/state.py#StateStore::set_config
    implements: "Config key-value storage"
  - ref: src/orchestrator/api.py#inject_endpoint
    implements: "POST /work-units/inject - adds chunk to work pool"
  - ref: src/orchestrator/api.py#queue_endpoint
    implements: "GET /work-units/queue - shows ready queue by priority"
  - ref: src/orchestrator/api.py#prioritize_endpoint
    implements: "PATCH /work-units/{chunk}/priority - updates priority"
  - ref: src/orchestrator/api.py#get_config_endpoint
    implements: "GET /config - retrieves daemon configuration"
  - ref: src/orchestrator/api.py#update_config_endpoint
    implements: "PATCH /config - updates daemon configuration"
  - ref: src/orchestrator/api.py#_detect_initial_phase
    implements: "Phase detection logic for inject command"
  - ref: src/orchestrator/daemon.py#_run_daemon_async
    implements: "Async daemon runner with scheduler integration"
  - ref: src/ve.py#orch_inject
    implements: "ve orch inject CLI command"
  - ref: src/ve.py#orch_queue
    implements: "ve orch queue CLI command"
  - ref: src/ve.py#orch_prioritize
    implements: "ve orch prioritize CLI command"
  - ref: src/ve.py#orch_config
    implements: "ve orch config CLI command"
  - ref: src/orchestrator/__init__.py
    implements: "Package exports for scheduling layer components"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after: ["orch_foundation"]
---

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