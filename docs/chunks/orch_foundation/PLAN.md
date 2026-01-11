<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

This chunk establishes the foundation for the parallel agent orchestrator - a daemon process that manages concurrent chunk work. The implementation follows patterns from the investigation's design document while integrating with the existing `ve` CLI architecture.

**Strategy:**

1. **Daemon Architecture**: A background daemon process that communicates via HTTP on a Unix domain socket (fallback to TCP port). The daemon maintains all state in SQLite; CLI commands are stateless wrappers around HTTP calls.

2. **State Persistence**: SQLite database stored in `.ve/orchestrator.db` with a simple migrations infrastructure for future schema evolution. Schema captures work units with their chunk, phase, status, and timing information.

3. **HTTP API**: Minimal FastAPI/Starlette-based HTTP server for the daemon. JSON request/response format enables future dashboard and scripting integration.

4. **CLI Integration**: New `ve orch` command group following existing patterns from `ve chunk`, `ve narrative`, etc. Commands delegate to HTTP calls to the daemon.

5. **Process Management**: PID file at `.ve/orchestrator.pid` ensures single instance. Daemon properly detaches from terminal using standard Unix daemonization.

**Key Design Decisions:**

- Per DEC-001 (uvx-based CLI), the orchestrator must be accessible via the `ve` command with no additional dependencies beyond what's in pyproject.toml
- Per DEC-002 (git not assumed), the orchestrator state lives in `.ve/` (not `.git/`) and does not require git
- The HTTP API uses a Unix domain socket by default (`.ve/orchestrator.sock`) for security, with TCP port as a fallback for environments where sockets are problematic

**Testing Strategy:**

Following docs/trunk/TESTING_PHILOSOPHY.md:
- Unit tests for SQLite state layer (migrations, CRUD operations)
- Unit tests for WorkUnit model and state transitions
- CLI integration tests using Click's test runner
- Daemon lifecycle tests (start/stop/status) using subprocess management in fixtures

## Subsystem Considerations

This chunk creates new functionality that doesn't directly touch existing subsystems. However:

- **docs/subsystems/workflow_artifacts**: This chunk USES the workflow_artifacts subsystem concepts (chunks have phases/statuses) but does not modify its implementation. The WorkUnit model tracks chunk phase progression.

No subsystem deviations discovered during exploration.

## Sequence

### Step 1: Add HTTP dependencies to pyproject.toml

Add minimal HTTP server dependencies. We'll use `uvicorn` (ASGI server) and `starlette` (lightweight HTTP framework) rather than the heavier FastAPI, keeping dependencies minimal per DEC-001.

Location: pyproject.toml

Dependencies to add:
- `starlette` - Lightweight HTTP framework
- `uvicorn` - ASGI server for production use
- `httpx` - HTTP client for CLI-to-daemon communication

### Step 2: Define orchestrator models

Create Pydantic models for the orchestrator domain:
- `WorkUnitPhase` enum: GOAL, PLAN, IMPLEMENT, COMPLETE
- `WorkUnitStatus` enum: READY, RUNNING, BLOCKED, NEEDS_ATTENTION, DONE
- `WorkUnit` model: chunk, phase, status, blocked_by, worktree, timestamps
- `OrchestratorState` model: For daemon status responses

These models define the data contract between CLI, daemon, and SQLite.

Location: src/orchestrator/models.py

### Step 3: Implement SQLite state store

Create the persistence layer with:
- Database initialization in `.ve/orchestrator.db`
- Schema creation with `work_units` table
- Simple migrations infrastructure (version table + migration functions)
- CRUD operations: create_work_unit, get_work_unit, update_work_unit, list_work_units
- Status transition logging for debugging

Schema:
```sql
CREATE TABLE work_units (
    chunk TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    status TEXT NOT NULL,
    blocked_by TEXT,  -- JSON array of chunk names
    worktree TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE status_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

Location: src/orchestrator/state.py

### Step 4: Write tests for state store

Test the SQLite layer before building on it:
- Database creation in temp directory
- Work unit CRUD operations
- Status transitions logged correctly
- Migration version tracking
- Concurrent access handling (SQLite thread safety)

Location: tests/test_orchestrator_state.py

### Step 5: Implement daemon process management

Create the daemon lifecycle manager:
- `start_daemon()`: Fork and daemonize, write PID file
- `stop_daemon()`: Read PID, send SIGTERM, wait for exit, cleanup PID file
- `is_daemon_running()`: Check PID file and validate process exists
- `get_daemon_status()`: Return uptime, PID, and state summary

PID file location: `.ve/orchestrator.pid`
Unix socket location: `.ve/orchestrator.sock`

The daemon should:
- Properly double-fork to detach from terminal
- Redirect stdout/stderr to a log file (`.ve/orchestrator.log`)
- Handle SIGTERM gracefully
- Acquire a lock on the PID file to prevent duplicate instances

Location: src/orchestrator/daemon.py

### Step 6: Implement HTTP API endpoints

Create the Starlette application with routes:
- `GET /status` - Daemon status (uptime, PID, work unit counts)
- `GET /work-units` - List all work units
- `GET /work-units/{chunk}` - Get specific work unit
- `POST /work-units` - Create work unit
- `PATCH /work-units/{chunk}` - Update work unit status/phase
- `DELETE /work-units/{chunk}` - Remove work unit

All endpoints return JSON. Error responses include structured error information.

Location: src/orchestrator/api.py

### Step 7: Write tests for HTTP API

Test the API layer:
- Status endpoint returns correct structure
- Work unit CRUD via HTTP
- Error responses for invalid requests
- JSON serialization of WorkUnit models

Use Starlette's TestClient for synchronous testing.

Location: tests/test_orchestrator_api.py

### Step 8: Implement HTTP client for CLI

Create a client wrapper that handles:
- Unix domain socket connection (primary)
- TCP fallback connection
- Request/response serialization
- Connection error handling with helpful messages
- Timeout handling

Location: src/orchestrator/client.py

### Step 9: Implement `ve orch` CLI command group

Add the orchestrator command group to the CLI with subcommands:

```
ve orch start     # Start daemon
ve orch stop      # Stop daemon
ve orch status    # Show daemon status
ve orch ps        # List work units
```

Each command follows existing CLI patterns (project-dir option, error handling, output formatting).

Location: src/ve.py (add command group and commands)

### Step 10: Write CLI integration tests

Test the full CLI surface:
- `ve orch start` creates PID file and socket
- `ve orch stop` removes PID file
- `ve orch status` shows running/stopped state
- `ve orch ps` lists work units (empty list initially)
- Error handling when daemon not running

Location: tests/test_orchestrator_cli.py

### Step 11: Implement `ve orch work-unit` subcommands

Add work unit management commands:

```
ve orch work-unit create <chunk> [--phase GOAL]    # Create work unit
ve orch work-unit status <chunk> [new_status]      # Show/update status
ve orch work-unit list                             # Same as `ve orch ps`
```

These commands follow the existing pattern from `ve chunk status` for consistency.

Location: src/ve.py (extend orch command group)

### Step 12: Add JSON output mode

Add `--json` flag to all `ve orch` commands for scripting:
- `ve orch status --json` returns machine-readable status
- `ve orch ps --json` returns work units array
- Consistent with future dashboard/automation use cases

Location: src/ve.py (update orch commands)

### Step 13: Write end-to-end daemon tests

Integration tests for the complete daemon lifecycle:
- Start daemon, verify running, stop daemon
- Create work units while daemon running
- State persists across daemon restart
- Only one daemon instance allowed

These tests require careful cleanup to avoid leaving orphan processes.

Location: tests/test_orchestrator_integration.py

---

**BACKREFERENCE COMMENTS**

All new files in src/orchestrator/ should include:
```python
# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
```

The ve.py additions should include:
```python
# Chunk: docs/chunks/orch_foundation - Orchestrator CLI commands
```

## Dependencies

**External Libraries (new to pyproject.toml):**
- `starlette>=0.36.0` - HTTP framework for the daemon API
- `uvicorn>=0.27.0` - ASGI server for running the daemon
- `httpx>=0.27.0` - HTTP client for CLI-to-daemon communication

**No chunk dependencies** - This is the foundation chunk; all subsequent orchestrator work depends on this.

## Risks and Open Questions

1. **Unix socket vs TCP port**: The design prefers Unix domain sockets for security (no network exposure), but Windows doesn't support them well. For now, focusing on macOS/Linux is acceptable since this is the primary developer platform, but may need TCP fallback for cross-platform support in the future.

2. **Daemon testing complexity**: Testing daemon processes is inherently tricky - need robust cleanup in test fixtures to avoid orphan processes. Will use pytest fixtures with `addFinalizer` for cleanup.

3. **SQLite concurrent access**: SQLite handles concurrent reads well but writes serialize. For this foundation phase with low throughput requirements, this is acceptable. May need WAL mode enabled if future phases require higher concurrency.

4. **Process daemonization on different platforms**: Double-fork daemonization is Unix-specific. Will document macOS/Linux as supported platforms for now.

5. **Graceful shutdown during active work**: In this foundation phase, there's no active work to interrupt. Future phases will need to consider what happens to RUNNING work units when the daemon stops.

## Deviations

<!-- POPULATE DURING IMPLEMENTATION, not at planning time. -->