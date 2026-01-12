---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api.py
- src/orchestrator/websocket.py
- src/orchestrator/templates/dashboard.html
- tests/test_orchestrator_dashboard.py
code_references:
  - ref: src/orchestrator/api.py#dashboard_endpoint
    implements: "GET / endpoint rendering dashboard HTML with attention queue and work unit grid"
  - ref: src/orchestrator/api.py#websocket_endpoint
    implements: "WebSocket endpoint for real-time dashboard updates with initial state snapshot"
  - ref: src/orchestrator/api.py#answer_endpoint
    implements: "POST answer endpoint with form submission support for dashboard UI"
  - ref: src/orchestrator/api.py#resolve_conflict_endpoint
    implements: "POST conflict resolution endpoint with form submission support"
  - ref: src/orchestrator/api.py#_get_jinja_env
    implements: "Jinja2 environment setup for template rendering"
  - ref: src/orchestrator/websocket.py#ConnectionManager
    implements: "WebSocket connection manager for tracking active connections and broadcasting"
  - ref: src/orchestrator/websocket.py#ConnectionManager::connect
    implements: "WebSocket connection acceptance and registration"
  - ref: src/orchestrator/websocket.py#ConnectionManager::disconnect
    implements: "WebSocket disconnection handling"
  - ref: src/orchestrator/websocket.py#ConnectionManager::broadcast
    implements: "Message broadcasting to all connected WebSocket clients"
  - ref: src/orchestrator/websocket.py#get_manager
    implements: "Global connection manager singleton access"
  - ref: src/orchestrator/websocket.py#broadcast_state_update
    implements: "Helper for broadcasting state updates to dashboard clients"
  - ref: src/orchestrator/websocket.py#broadcast_work_unit_update
    implements: "Work unit status change broadcasting"
  - ref: src/orchestrator/websocket.py#broadcast_attention_update
    implements: "Attention queue change broadcasting"
  - ref: src/orchestrator/templates/dashboard.html
    implements: "Dashboard HTML template with attention queue, process grid, and WebSocket client"
  - ref: tests/test_orchestrator_dashboard.py#TestDashboardEndpoint
    implements: "Dashboard HTML rendering tests"
  - ref: tests/test_orchestrator_dashboard.py#TestWebSocketEndpoint
    implements: "WebSocket connection and initial state tests"
  - ref: tests/test_orchestrator_dashboard.py#TestFormSubmissions
    implements: "Form submission handling tests for answer and resolve endpoints"
  - ref: tests/test_orchestrator_dashboard.py#TestDashboardWithData
    implements: "Dashboard rendering tests with various data scenarios"
narrative: null
investigation: parallel_agent_orchestration
subsystems: []
friction_entries: []
created_after:
- artifact_copy_backref
- friction_chunk_linking
- friction_claude_docs
- remove_external_ref
- selective_project_linking
---

# Chunk Goal

## Minor Goal

Add a web dashboard to the orchestrator that provides an "at a glance" interface for rapid re-orientation after interruptions. The dashboard enables operators to monitor parallel agent workflows, see what needs attention, and respond to questions without switching to the CLI.

This is Phase 5 of the orchestrator implementation (per `docs/investigations/parallel_agent_orchestration/design.md`). It depends on the attention queue infrastructure from `orch_attention_queue`.

**Technology choices:**
- **FastAPI + Jinja2** for server-rendered HTML (lightweight, consistent with Python codebase)
- **WebSocket** for real-time updates (attention queue changes + work unit status transitions)
- **Basic actions** in UI (answer questions, resolve conflicts) with CLI for advanced operations

## Success Criteria

1. **Dashboard serves at `/` when daemon is running**
   - `ve orch start` spawns the daemon which serves HTTP on a configurable port
   - Root URL shows the orchestrator dashboard
   - Dashboard accessible at `http://localhost:<port>/` (port from config or default)

2. **Real-time attention queue view**
   - WebSocket connection streams attention queue updates
   - New attention items appear without page refresh
   - Resolved items disappear without page refresh
   - Each item shows: type, chunk, downstream impact (blocks:N), time waiting, question/context

3. **Process grid showing work unit status**
   - RUNNING work units with current phase and elapsed time
   - READY work units queued for execution
   - BLOCKED work units with blocking reason visible
   - Status changes stream via WebSocket

4. **Answer questions from the UI**
   - Click on attention item to expand context
   - Text input for free-form answers
   - Option buttons for multiple-choice questions
   - Submit answer triggers `ve orch answer` equivalent

5. **Resolve conflicts from the UI**
   - Conflict items show the two chunks and confidence level
   - Buttons for "Parallelize anyway" vs "Serialize"
   - Submit triggers `ve orch resolve` equivalent

6. **Tests pass**
   - Integration tests for WebSocket connection and message streaming
   - Tests for answer/resolve endpoints
   - Dashboard renders correctly with various queue states