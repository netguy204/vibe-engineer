---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- pyproject.toml
- src/orchestrator/__init__.py
- src/orchestrator/models.py
- src/orchestrator/state.py
- src/orchestrator/daemon.py
- src/orchestrator/api.py
- src/orchestrator/client.py
- src/ve.py
- tests/test_orchestrator_state.py
- tests/test_orchestrator_api.py
- tests/test_orchestrator_cli.py
code_references:
  - ref: src/orchestrator/__init__.py
    implements: "Package exports for orchestrator module"
  - ref: src/orchestrator/models.py#WorkUnitPhase
    implements: "Enum for chunk lifecycle phases (GOAL/PLAN/IMPLEMENT/COMPLETE)"
  - ref: src/orchestrator/models.py#WorkUnitStatus
    implements: "Enum for work unit scheduling states (READY/RUNNING/BLOCKED/NEEDS_ATTENTION/DONE)"
  - ref: src/orchestrator/models.py#WorkUnit
    implements: "Core work unit model tracking chunk through lifecycle"
  - ref: src/orchestrator/models.py#OrchestratorState
    implements: "Daemon status information model"
  - ref: src/orchestrator/state.py#StateStore
    implements: "SQLite state persistence with migrations, work unit CRUD, and status logging"
  - ref: src/orchestrator/state.py#get_default_db_path
    implements: "Database path resolution in .ve directory"
  - ref: src/orchestrator/daemon.py#DaemonError
    implements: "Daemon-specific exception type"
  - ref: src/orchestrator/daemon.py#start_daemon
    implements: "Daemon startup with double-fork daemonization"
  - ref: src/orchestrator/daemon.py#stop_daemon
    implements: "Graceful daemon shutdown with SIGTERM/SIGKILL"
  - ref: src/orchestrator/daemon.py#is_daemon_running
    implements: "Daemon running status check via PID file"
  - ref: src/orchestrator/daemon.py#get_daemon_status
    implements: "Comprehensive daemon status including uptime and work unit counts"
  - ref: src/orchestrator/api.py#create_app
    implements: "Starlette app factory with REST endpoints for work unit CRUD"
  - ref: src/orchestrator/client.py#OrchestratorClient
    implements: "HTTP client for CLI-to-daemon communication via Unix socket"
  - ref: src/orchestrator/client.py#DaemonNotRunningError
    implements: "Client exception for daemon not running"
  - ref: src/ve.py#orch
    implements: "CLI command group for orchestrator commands"
  - ref: src/ve.py#start
    implements: "ve orch start command"
  - ref: src/ve.py#stop
    implements: "ve orch stop command"
  - ref: src/ve.py#orch_status
    implements: "ve orch status command with JSON output support"
  - ref: src/ve.py#orch_ps
    implements: "ve orch ps command to list work units"
  - ref: src/ve.py#work_unit
    implements: "Work unit subcommand group"
  - ref: src/ve.py#work_unit_create
    implements: "ve orch work-unit create command"
  - ref: src/ve.py#work_unit_status
    implements: "ve orch work-unit status command"
  - ref: src/ve.py#work_unit_delete
    implements: "ve orch work-unit delete command"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
created_after:
- jinja_backrefs
---

# Chunk Goal

## Minor Goal

Establish the foundation of the parallel agent orchestrator - a daemon process that manages concurrent chunk work across multiple agents. This chunk implements the core architectural skeleton: daemon lifecycle, SQLite state persistence, and basic work unit tracking.

This is the first step in the orchestration vision from the parallel_agent_orchestration investigation. The orchestrator functions as an "operating system scheduler" where worktrees are processes, agents are CPUs, and the orchestrator routes operator attention to where it creates the most throughput.

Everything else depends on this foundation:
- Scheduling (Phase 2) needs the daemon and work unit model
- Attention queue (Phase 3) needs state persistence
- Conflict oracle (Phase 4) builds on work unit tracking
- Dashboard (Phase 5) connects to the daemon's API

## Success Criteria

1. **Daemon lifecycle works reliably**
   - `ve orch start` spawns a background daemon process
   - `ve orch stop` gracefully shuts down the daemon
   - `ve orch status` reports daemon state (running/stopped, uptime, PID)
   - Daemon survives terminal close (properly daemonized)
   - Only one daemon instance allowed per project

2. **SQLite state persists across daemon restarts**
   - Database stored in `.ve/orchestrator.db`
   - Schema includes work_units table with: chunk, phase, status, blocked_by, worktree, timestamps
   - State survives daemon stop/start cycles
   - Basic migrations infrastructure for future schema changes

3. **Work unit model supports chunk lifecycle**
   - WorkUnit tracks: chunk directory, phase (GOAL/PLAN/IMPLEMENT/COMPLETE), status (READY/RUNNING/BLOCKED/NEEDS_ATTENTION/DONE)
   - `ve orch ps` lists all work units with their current state
   - Work units can be created, updated, and queried via CLI
   - Status transitions are logged for debugging

4. **HTTP API exposes core functionality**
   - Daemon listens on localhost port (configurable, default: ~/.ve/orchestrator.sock or localhost:7845)
   - Endpoints for: status, work unit CRUD, process listing
   - CLI commands are thin wrappers around HTTP calls
   - JSON response format for scripting

## Design Context

This chunk implements Phase 1 from the design document at `docs/investigations/parallel_agent_orchestration/design.md`. Key architectural decisions from that document:

- **Stateless agents, stateful orchestrator**: Agents are ephemeral workers; the daemon maintains all durable state
- **OS analogy**: WorkUnit is like a process (worktree + chunk), daemon is the scheduler
- **HTTP API**: Enables future dashboard and scripting integration
- **SQLite**: Simple, reliable, no external dependencies

## Out of Scope

- Agent spawning and execution (Phase 2: Scheduling)
- Question/decision capture (Phase 3: Attention Queue)
- Conflict detection (Phase 4: Conflict Oracle)
- Web dashboard (Phase 5: Dashboard)
- Worktree management (Phase 2)

This chunk is purely the daemon skeleton - it knows work units exist but doesn't yet do anything with them beyond basic CRUD.