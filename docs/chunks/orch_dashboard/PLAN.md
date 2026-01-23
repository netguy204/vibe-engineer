# Implementation Plan

## Approach

Add a web dashboard to the orchestrator daemon using **Starlette + Jinja2 templates** for server-rendered HTML with **WebSocket** for real-time updates. This builds on the existing `src/orchestrator/api.py` which already uses Starlette.

**Key design decisions:**

1. **Server-Rendered HTML** (not SPA): Use Jinja2 templates for the dashboard. This keeps dependencies minimal and consistent with the Python codebase. The dashboard is lightweight and doesn't need a full JavaScript framework.

2. **WebSocket for Live Updates**: A single WebSocket endpoint streams attention queue changes and work unit status transitions. The frontend JavaScript reconnects automatically on disconnect.

3. **Extend Existing API**: Add new routes to the existing Starlette app rather than creating a separate server. The dashboard is served from the same socket as the REST API.

4. **Action Buttons for Common Operations**: Provide UI affordances to answer questions and resolve conflicts, which map directly to the existing `/work-units/{chunk}/answer` and `/work-units/{chunk}/resolve` REST endpoints.

**Testing Strategy (per docs/trunk/TESTING_PHILOSOPHY.md):**
- Integration tests using Starlette's TestClient for HTTP endpoints
- WebSocket tests using `TestClient` with `websocket_connect()` context manager
- Tests verify semantic behavior (dashboard renders, WebSocket receives updates) not implementation details

## Subsystem Considerations

No existing subsystems directly apply to this chunk. The dashboard is a new component that integrates with the existing orchestrator API.

## Sequence

### Step 1: Add WebSocket endpoint for state streaming

Create a WebSocket endpoint at `/ws` that streams orchestrator state updates in real-time. The endpoint will:
- Send initial state snapshot on connection
- Broadcast status transitions when work units change
- Broadcast attention queue updates when items are added/resolved

**Implementation:**
- Add `WebSocketRoute` to the existing Starlette routes
- Create a `ConnectionManager` class to track active WebSocket connections
- Add hooks to state transitions to broadcast changes

Location: `src/orchestrator/api.py`, `src/orchestrator/websocket.py` (new file)

### Step 2: Create dashboard HTML template

Create a Jinja2 template for the dashboard that displays:
- Attention queue with expandable items
- Process grid showing RUNNING/READY/BLOCKED work units
- Action buttons for answering questions and resolving conflicts

The template uses minimal JavaScript for:
- WebSocket connection management with auto-reconnect
- DOM updates when state changes
- Form submission for answers/resolutions

Location: `src/orchestrator/templates/dashboard.html` (new file)

### Step 3: Add dashboard endpoint to serve HTML

Add a GET `/` endpoint that renders the dashboard template with current state. The endpoint will:
- Query current attention queue and work unit status from the state store
- Render the template with this data
- Include WebSocket URL for real-time updates

Location: `src/orchestrator/api.py`

### Step 4: Add form submission endpoints for UI actions

The existing `/work-units/{chunk}/answer` and `/work-units/{chunk}/resolve` endpoints accept JSON. Add HTML form handling for browser submissions:
- Parse `application/x-www-form-urlencoded` content type
- Redirect back to dashboard after successful action

This allows the UI to work without JavaScript for basic operations.

Location: `src/orchestrator/api.py`

### Step 5: Wire WebSocket broadcasts into state store operations

Modify the API endpoints to broadcast changes via WebSocket when:
- Work unit status changes (READY → RUNNING, etc.)
- Attention items are added or resolved
- Answers/resolutions are submitted

The broadcast system needs to be integrated with the existing async API handlers.

Location: `src/orchestrator/api.py`, `src/orchestrator/websocket.py`

### Step 6: Write integration tests for dashboard

Create tests that verify:
- Dashboard HTML renders at GET `/`
- WebSocket connects and receives initial state
- Status changes broadcast via WebSocket
- Answer/resolve actions work from the UI

Location: `tests/test_orchestrator_dashboard.py` (new file)

### Step 7: Update pyproject.toml if needed

Verify all dependencies are present. Starlette, Uvicorn, and Jinja2 are already in `pyproject.toml`, so this may be a no-op. Add `websockets` if needed for client-side testing.

Location: `pyproject.toml`

## Dependencies

**Required chunks (already complete):**
- `orch_foundation` - Daemon skeleton and state store
- `orch_attention_queue` - Attention queue model and endpoints

**External libraries (already in pyproject.toml):**
- `starlette>=0.36.0` - Web framework with WebSocket support
- `uvicorn>=0.27.0` - ASGI server
- `jinja2` - Template engine

No new dependencies required - Starlette includes WebSocket support natively.

## Risks and Open Questions

1. **WebSocket Connection Stability**: Long-running WebSocket connections may drop due to network issues. The frontend must handle reconnection gracefully. Plan: Include auto-reconnect logic with exponential backoff in the dashboard JavaScript.

2. **Concurrent Updates**: Multiple browser tabs may be connected simultaneously. Need to ensure broadcasts don't cause race conditions. Plan: The ConnectionManager will use asyncio-safe sets for connection tracking.

3. **Template Hot Reload in Development**: During development, template changes require daemon restart. This is acceptable since the daemon is typically restarted during development anyway.

4. **Port Configuration**: The daemon uses a Unix socket by default. For dashboard access via browser, operators will need to configure HTTP on a TCP port, or use a reverse proxy. This is documented in the investigation design but may need CLI support in a future chunk.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.
-->