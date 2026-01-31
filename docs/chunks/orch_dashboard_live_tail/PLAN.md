# Implementation Plan

## Approach

Extend the orchestrator dashboard with expandable work unit tiles that show live-streamed, human-readable log output. The key insight is to **reuse the existing log parsing and formatting logic** from `orch_tail_command` (`src/orchestrator/log_parser.py`) to maintain consistency between CLI and dashboard display.

**Architecture:**
1. Add a new WebSocket-based log streaming endpoint that streams parsed log entries
2. Modify the dashboard template to add expand/collapse controls on RUNNING tiles
3. Implement JavaScript client-side logic for accordion behavior and WebSocket log streaming
4. The server streams formatted log lines using the same `format_entry()` function used by `ve orch tail`

**Key design decisions:**
- **Server-side formatting**: Parse and format logs on the server using existing `log_parser.py` functions, send pre-formatted HTML/text to the client. This ensures consistent display with `ve orch tail -f` and avoids duplicating parsing logic in JavaScript.
- **Accordion pattern**: Only one tile expanded at a time gives generous vertical space for log viewing
- **WebSocket for streaming**: Reuse the existing WebSocket infrastructure in `websocket.py` rather than adding a new connection mechanism

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS additional dashboard functionality, extending the existing dashboard pattern. Will follow established patterns for:
  - WebSocket broadcasting via `ConnectionManager`
  - Dashboard templates in `src/orchestrator/templates/`
  - API endpoints in `src/orchestrator/api.py`

## Sequence

### Step 1: Add log streaming WebSocket endpoint

Create a new WebSocket endpoint `/ws/log/{chunk}` that streams parsed log output for a specific chunk. The endpoint will:
1. Accept a WebSocket connection with chunk parameter
2. Locate the log directory for the chunk (`.ve/chunks/{chunk}/log/`)
3. Determine the current phase from existing log files
4. Stream existing log entries (using `parse_log_file()` and `format_entry()`)
5. Enter follow mode: watch for new log lines and stream them
6. Detect phase transitions and switch to new phase log file
7. Send formatted output as JSON messages: `{"type": "log_line", "content": "..."}`

**Implementation:**
```python
async def log_stream_websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming parsed log output."""
```

Location: `src/orchestrator/api.py`

### Step 2: Add log formatting helper for HTML display

Create a helper function that wraps `format_entry()` output for HTML display:
- Escape HTML special characters
- Convert ANSI-style formatting (if any) to HTML spans
- Preserve the visual symbols (▶, ✓, ✗, 💬, ══)

```python
def format_entry_for_html(entry: ParsedLogEntry, terminal_width: int = 100) -> list[str]:
    """Format a log entry as HTML-safe strings for dashboard display."""
```

Location: `src/orchestrator/log_parser.py` (add to existing module)

### Step 3: Update dashboard template with expandable tiles

Modify `src/orchestrator/templates/dashboard.html` to:
1. Add expand/collapse button to RUNNING work unit tiles
2. Add a log panel container that appears below expanded tiles
3. Style the log panel with monospace font, dark background, scrollable area
4. Ensure only one tile can be expanded at a time (accordion behavior)

CSS additions:
```css
.process-card.expandable { /* cursor, hover states */ }
.log-panel { /* monospace, pre-formatted, scrollable */ }
.log-panel.visible { /* shown state */ }
.expand-button { /* toggle button styling */ }
```

Location: `src/orchestrator/templates/dashboard.html`

### Step 4: Implement JavaScript log streaming client

Add JavaScript to the dashboard template that:
1. Handles expand/collapse click events on RUNNING tiles
2. When expanding: opens a WebSocket connection to `/ws/log/{chunk}`
3. Receives log messages and appends them to the log panel
4. Auto-scrolls to bottom as new content arrives
5. When collapsing (or expanding another): closes the WebSocket connection
6. Implements accordion behavior - collapsing previously expanded tile

```javascript
function expandLogPanel(chunk) {
    // Close any existing log stream
    // Open WebSocket to /ws/log/{chunk}
    // Show log panel below the tile
}

function collapseLogPanel() {
    // Close WebSocket connection
    // Hide log panel
}
```

Location: `src/orchestrator/templates/dashboard.html` (in `<script>` section)

### Step 5: Add phase header display in log stream

Enhance the log stream to include phase headers when starting a new phase:
- Send phase header at stream start: `=== IMPLEMENT phase === (started HH:MM:SS)`
- Send phase header when transitioning to a new phase during follow
- Use `format_phase_header()` from `log_parser.py`

Location: `src/orchestrator/api.py` (in log streaming endpoint)

### Step 6: Handle stream lifecycle edge cases

Implement proper handling for:
- **Chunk not found**: Send error message and close WebSocket
- **No logs yet**: Send informative message, wait for log file to appear
- **Chunk completed**: Stream all logs, send completion message, close WebSocket
- **Client disconnect**: Clean up resources gracefully
- **Work unit no longer RUNNING**: Send status change notification

Location: `src/orchestrator/api.py`

### Step 7: Write tests for log streaming endpoint

Create tests in `tests/test_orchestrator_dashboard.py`:

```python
class TestLogStreamWebSocket:
    def test_log_stream_connects(self, client): ...
    def test_log_stream_sends_existing_logs(self, client, tmp_path): ...
    def test_log_stream_chunk_not_found(self, client): ...
    def test_log_stream_no_logs_yet(self, client): ...
```

Location: `tests/test_orchestrator_dashboard.py`

### Step 8: Write tests for tile expansion UI

Create tests for the dashboard UI behavior:

```python
class TestDashboardLogTiling:
    def test_running_tiles_have_expand_button(self, client): ...
    def test_non_running_tiles_no_expand_button(self, client): ...
    def test_log_panel_present_in_html(self, client): ...
```

Location: `tests/test_orchestrator_dashboard.py`

### Step 9: Integration testing

Verify end-to-end behavior:
1. Create a work unit in RUNNING status
2. Create a mock log file with sample log entries
3. Open the dashboard and verify tile expansion works
4. Verify log content is displayed correctly with formatting

## Dependencies

- **orch_tail_command** (ACTIVE): Provides `src/orchestrator/log_parser.py` with all parsing and formatting functions. This chunk reuses:
  - `parse_log_file()`, `parse_log_line()` - Parse raw log format
  - `format_entry()`, `format_phase_header()`, `format_result_banner()` - Display formatting
  - Dataclasses: `ParsedLogEntry`, `ToolCall`, `ToolResult`, `TextContent`, `ResultInfo`

## Risks and Open Questions

- **Log file size**: For long-running agents, log files could be large. Consider adding a "max lines" parameter or only streaming recent entries initially.
- **WebSocket connection limits**: If many operators open dashboards simultaneously, each expanding tiles creates WebSocket connections. The existing `ConnectionManager` handles cleanup, but should verify behavior under load.
- **File watching approach**: Using polling (like `ve orch tail -f`) is simple but less efficient than inotify/kqueue. For dashboard use, polling at 500ms intervals should be acceptable.
- **Browser compatibility**: WebSocket and modern CSS should work in all recent browsers; no exotic features planned.

## Deviations

*To be populated during implementation.*