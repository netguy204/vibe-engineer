---
status: DOCUMENTED
chunks:
  - chunk_id: orch_review_phase
    relationship: implements
  - chunk_id: orch_task_agent_env
    relationship: implements
  - chunk_id: explicit_deps_workunit_flag
    relationship: implements
  - chunk_id: orch_url_command
    relationship: implements
  - chunk_id: orch_merge_safety
    relationship: implements
  - chunk_id: orch_state_transactions
    relationship: implements
  - chunk_id: orch_worktree_cleanup
    relationship: implements
  - chunk_id: orch_merge_before_delete
    relationship: implements
  - chunk_id: orch_prune_consolidate
    relationship: implements
  - chunk_id: orchestrator_api_decompose
    relationship: implements
  - chunk_id: orch_session_auto_resume
    relationship: implements
  - chunk_id: optimistic_locking
    relationship: implements
  - chunk_id: phase_aware_recovery
    relationship: implements
  - chunk_id: finalization_recovery
    relationship: implements
  - chunk_id: merge_strategy_simplify
    relationship: implements
  - chunk_id: finalize_double_commit
    relationship: implements
code_references:
- ref: src/orchestrator/__init__.py
  implements: Package exports for orchestrator module
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#WorkUnitPhase
  implements: Enum for chunk lifecycle phases (GOAL/PLAN/IMPLEMENT/COMPLETE)
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#WorkUnitStatus
  implements: Enum for work unit scheduling states
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#WorkUnit
  implements: Core work unit model tracking chunk through lifecycle
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#OrchestratorState
  implements: Daemon status information model
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#OrchestratorConfig
  implements: Configuration model with max_agents and dispatch_interval
  compliance: COMPLIANT
- ref: src/orchestrator/models.py#AgentResult
  implements: Result model for agent phase execution
  compliance: COMPLIANT
- ref: src/orchestrator/state.py#StateStore
  implements: SQLite state persistence with migrations and work unit CRUD
  compliance: COMPLIANT
- ref: src/orchestrator/daemon.py#DaemonError
  implements: Daemon-specific exception type
  compliance: COMPLIANT
- ref: src/orchestrator/daemon.py#start_daemon
  implements: Daemon startup with double-fork daemonization
  compliance: COMPLIANT
- ref: src/orchestrator/daemon.py#stop_daemon
  implements: Graceful daemon shutdown
  compliance: COMPLIANT
- ref: src/orchestrator/daemon.py#is_daemon_running
  implements: Daemon running status check via PID file
  compliance: COMPLIANT
- ref: src/orchestrator/api/app.py#create_app
  implements: Starlette app factory with REST endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/streaming.py#dashboard_endpoint
  implements: Dashboard HTML rendering
  compliance: COMPLIANT
- ref: src/orchestrator/api/streaming.py#websocket_endpoint
  implements: WebSocket for real-time updates
  compliance: COMPLIANT
- ref: src/orchestrator/api/work_units.py
  implements: Work unit CRUD endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/scheduling.py
  implements: Inject, queue, prioritize, and config endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/attention.py
  implements: Attention queue and answer endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/conflicts.py
  implements: Conflict analysis and resolution endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/worktrees.py
  implements: Worktree management endpoints
  compliance: COMPLIANT
- ref: src/orchestrator/api/common.py
  implements: Shared utilities and state access helpers
  compliance: COMPLIANT
- ref: src/orchestrator/client.py#OrchestratorClient
  implements: HTTP client for CLI-to-daemon communication
  compliance: COMPLIANT
- ref: src/orchestrator/scheduler.py#Scheduler
  implements: Dispatch loop for scheduling work units to agents
  compliance: COMPLIANT
- ref: src/orchestrator/agent.py#AgentRunner
  implements: Agent execution using Claude Agent SDK
  compliance: COMPLIANT
- ref: src/orchestrator/worktree.py#WorktreeManager
  implements: Git worktree lifecycle management
  compliance: COMPLIANT
- ref: src/orchestrator/oracle.py#ConflictOracle
  implements: Conflict detection between concurrent work units
  compliance: COMPLIANT
- ref: src/orchestrator/websocket.py#ConnectionManager
  implements: WebSocket connection management for dashboard
  compliance: COMPLIANT
- ref: src/ve.py#orch
  implements: CLI command group for orchestrator commands
  compliance: COMPLIANT
created_after:
- workflow_artifacts
---

# orchestrator

## Intent

Enable parallel execution of chunk work across multiple AI agents by
providing an "operating system" for agent scheduling. Without this subsystem, operators
can only run one agent at a time, creating a throughput bottleneck for complex
multi-chunk work.

The orchestrator manages work units (chunks) through their lifecycle phases, spawns
agents in isolated git worktrees, routes operator attention to blocking issues, and
provides a dashboard for monitoring parallel execution.

## Scope

### In Scope

- **Daemon lifecycle**: Start/stop/status of the orchestrator daemon process
- **Work unit management**: Create, queue, prioritize, and track work units
- **Agent scheduling**: Dispatch ready work to available agent slots
- **Worktree isolation**: Git worktrees as execution environments
- **Attention queue**: Capture and route questions/conflicts needing operator input
- **Conflict detection**: Oracle for detecting potential conflicts between parallel work
- **Dashboard**: Web UI for monitoring and intervention
- **Phase execution**: GOAL → PLAN → IMPLEMENT → COMPLETE lifecycle

### Out of Scope

- **Workflow artifact schemas**: Defined in workflow_artifacts subsystem
- **External reference handling**: Defined in cross_repo_operations subsystem
- **Template rendering**: Uses template_system but doesn't extend it
- **Semantic merge resolution**: Beyond current scope

## Invariants

### Hard Invariants

1. **Only one daemon instance allowed per project** - Enforced via PID file. Multiple
   daemons would corrupt shared state.

2. **Work unit transitions are logged for debugging** - Status changes recorded in
   SQLite for audit trail.

3. **Each phase is a fresh agent context** - No context carryover between phases.
   The workdir contains all needed context.

4. **Worktrees are isolated execution environments** - Each chunk gets its own branch
   and worktree. Agents cannot interfere with each other.

5. **Configurable max agent slots** - Controls throughput and cost. Default: 2.

6. **Questions must be captured with session_id for resume** - Attention queue pattern
   enables pause/resume of agent execution.

7. **Conflicts must be detected before parallel execution** - Oracle checks prevent
   parallel work on conflicting files.

8. **Phase completion detected when async generator exhausts** - Clean completion
   semantics for agent execution.

9. **Daemon must broadcast state changes to dashboard** - WebSocket updates keep
   dashboard current.

### Soft Conventions

1. **CLI commands are thin wrappers around HTTP calls** - Business logic lives in
   daemon, CLI just formats output.

2. **Phase execution via skills** - GOAL/PLAN/IMPLEMENT/COMPLETE map to slash commands.

## Implementation Locations

**Canonical location**: `src/orchestrator/` module

The module provides:
- `models.py` - Data models (WorkUnit, WorkUnitPhase, WorkUnitStatus, etc.)
- `state.py` - SQLite persistence (StateStore)
- `daemon.py` - Daemon lifecycle (start, stop, status)
- `api/` - REST API package (Starlette)
  - `app.py` - Application factory (create_app)
  - `common.py` - Shared utilities and state access helpers
  - `work_units.py` - Work unit CRUD endpoints
  - `scheduling.py` - Inject, queue, prioritize, and config endpoints
  - `attention.py` - Attention queue and answer endpoints
  - `conflicts.py` - Conflict analysis and resolution endpoints
  - `worktrees.py` - Worktree management endpoints
  - `streaming.py` - WebSocket log streaming and dashboard
- `scheduler.py` - Dispatch loop (Scheduler)
- `agent.py` - Agent execution (AgentRunner)
- `worktree.py` - Git worktree management (WorktreeManager)
- `oracle.py` - Conflict detection (ConflictOracle)
- `websocket.py` - Real-time updates (ConnectionManager)
- `client.py` - CLI-to-daemon communication (OrchestratorClient)

CLI commands: `ve orch start|stop|status|ps|inject|queue|prioritize|config|attention|answer|resolve`

## Known Deviations

*None identified during migration synthesis.*

## Chunk Relationships

### Implements

All 21 orch_* chunks implement this subsystem. See frontmatter for complete list.

Key chunks by phase:
- **Phase 1 (Foundation)**: orch_foundation - daemon skeleton, SQLite, work unit model
- **Phase 2 (Scheduling)**: orch_scheduling - worktrees, agent spawning, dispatch loop
- **Phase 3 (Attention)**: orch_attention_queue, orch_attention_reason - question/decision capture
- **Phase 4 (Conflicts)**: orch_conflict_oracle - parallel conflict detection
- **Phase 5 (Dashboard)**: orch_dashboard - web UI, WebSocket updates

## Investigation Reference

This subsystem originated from the `parallel_agent_orchestration` investigation
which established the core design principles (stateless agents, stateful orchestrator,
OS analogy with worktrees as processes).
