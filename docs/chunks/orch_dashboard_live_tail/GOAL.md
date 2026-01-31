---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/api.py
- src/orchestrator/log_parser.py
- src/orchestrator/templates/dashboard.html
- tests/test_orchestrator_dashboard.py
code_references:
  - ref: src/orchestrator/api.py#log_stream_websocket_endpoint
    implements: "WebSocket endpoint for streaming parsed log output to dashboard"
  - ref: src/orchestrator/api.py#_get_log_directory
    implements: "Log directory resolution for chunk log files"
  - ref: src/orchestrator/api.py#_detect_current_phase
    implements: "Phase detection from existing log files"
  - ref: src/orchestrator/api.py#_stream_log_file
    implements: "Async log file streaming with HTML formatting"
  - ref: src/orchestrator/log_parser.py#format_entry_for_html
    implements: "HTML-safe formatting of log entries for dashboard display"
  - ref: src/orchestrator/log_parser.py#format_phase_header_for_html
    implements: "HTML-safe phase header formatting"
  - ref: src/orchestrator/log_parser.py#_escape_html
    implements: "HTML escaping helper for log content"
  - ref: tests/test_orchestrator_dashboard.py#TestLogStreamWebSocket
    implements: "Tests for log streaming WebSocket endpoint"
  - ref: tests/test_orchestrator_dashboard.py#TestDashboardLogTiling
    implements: "Tests for dashboard tile expansion UI"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on:
- orch_tail_command
created_after:
- orch_plan_merge_conflict
---

# Chunk Goal

## Minor Goal

Add expandable work unit tiles to the orchestrator dashboard that show live-streamed, human-readable log output when expanded.

**Use case:** Operators viewing the dashboard at `ve orch url` can click on an active work unit tile to expand it and see a live tail of the agent's activity, using the same parsed display format as `ve orch tail -f`.

**Behavior:**
- Work unit tiles in RUNNING status show an expand/collapse control
- Expanding a tile opens a log panel below it (collapsing any previously expanded tile)
- Only one tile can be expanded at a time, allowing generous space for the log window
- Log output uses the human-readable format from `orch_tail_command`:
  - `▶` for tool calls, `✓` for results, `💬` for assistant text
  - Phase headers and timestamps
  - ResultMessage summary banners
- Collapsing the tile (or expanding another) stops the log stream

## Success Criteria

- Dashboard work unit tiles have expand/collapse functionality
- Expanded tiles show live-streamed log output
- Log display uses the parsed format from `orch_tail_command` (reuse the parsing logic)
- Stream updates in real-time as the agent works
- Only one tile expanded at a time (expanding another collapses the previous)
- Log panel has generous vertical space for comfortable reading
- Works for all phases (PLAN, IMPLEMENT, REVIEW, COMPLETE)
- Tests cover tile expansion, log streaming, accordion behavior, and format parsing
- Existing tests pass

## Dependency

This chunk depends on `orch_tail_command` which implements the log parsing and human-readable display format. This chunk reuses that parsing logic for the dashboard UI.