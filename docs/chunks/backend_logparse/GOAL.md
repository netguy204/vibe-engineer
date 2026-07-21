---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: ["src/orchestrator/backend.py", "src/orchestrator/backends/claude.py", "src/orchestrator/agent.py", "src/orchestrator/log_parser.py", "tests/test_orchestrator_log_parser.py", "tests/test_orchestrator_backend.py"]
code_references:
  - ref: src/orchestrator/backend.py#TextEvent
    implements: "Normalized log event for agent text output"
  - ref: src/orchestrator/backend.py#ToolCallEvent
    implements: "Normalized log event for tool invocations"
  - ref: src/orchestrator/backend.py#ToolResultEvent
    implements: "Normalized log event for tool results"
  - ref: src/orchestrator/backend.py#ResultEvent
    implements: "Normalized log event for session completion"
  - ref: src/orchestrator/backends/claude.py#_emit_log_events
    implements: "Translates Claude SDK messages into normalized LogEvents"
  - ref: src/orchestrator/agent.py#create_log_callback
    implements: "Serializes LogEvents as JSON lines to disk"
  - ref: src/orchestrator/agent.py#_EVENT_TYPE_TAG
    implements: "Maps event classes to JSON type tags for serialization"
  - ref: src/orchestrator/log_parser.py#parse_log_line
    implements: "Deserializes JSON log lines into ParsedLogEntry (replaces regex parsing)"
  - ref: src/orchestrator/log_parser.py#parse_log_file
    implements: "Reads JSON-line log files into structured entries"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after:
- backend_seam
---
# Chunk Goal

## Minor Goal

`src/orchestrator/log_parser.py` produces activity summaries from the backend's
normalized log events. It consumes the `on_log` event shape defined by the
`AgentBackend` seam, so summaries render identically regardless of backend: the
Claude path emits these events from SDK messages, the Cursor path from
structured stream-json / ACP `session/update` notifications. The parser
deserializes JSON lines — not SDK message repr strings — keeping it decoupled
from any backend's native types.

## Success Criteria

- `log_parser.py` consumes normalized JSON-line log events from the seam, not
  SDK message `repr` strings.
- Claude-backed runs produce the same activity summaries as before (behavioral
  parity).
- Given equivalent normalized events from a non-Claude backend, the parser renders
  equivalent summaries.
- Log-summarize tests pass, fed normalized events rather than SDK reprs where
  needed (`tests/test_orchestrator_log_parser.py`).

## Rejected Ideas

### Maintaining a separate parser per backend

Keeping a Claude-repr parser and a distinct Cursor parser duplicates summary
logic and lets the two drift. Rejected — normalize log events at the
`AgentBackend` seam and keep a single parser.