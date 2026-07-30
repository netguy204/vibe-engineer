---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- docs/trunk/ORCHESTRATOR.md
- src/orchestrator/backends/cursor.py
- src/orchestrator/agent.py
- src/orchestrator/models.py
- tests/test_orchestrator_cursor_backend.py
code_references:
  - ref: src/orchestrator/backends/cursor.py#CursorBackend::run
    implements: "End-to-end ACP event loop driving cursor-agent through phase lifecycle"
  - ref: src/orchestrator/backends/cursor.py#ACPTransport
    implements: "JSON-RPC 2.0 transport over cursor-agent stdin/stdout"
  - ref: src/orchestrator/backends/cursor.py#_write_cursor_mcp_config
    implements: "ReviewDecision MCP server setup for REVIEW phase"
  - ref: src/orchestrator/backends/cursor.py#_remove_cursor_mcp_config
    implements: "MCP config cleanup after phase completion"
  - ref: src/orchestrator/backends/cursor.py#CursorAgentNotFoundError
    implements: "Actionable error when cursor-agent binary is missing"
  - ref: src/orchestrator/agent.py#create_log_callback
    implements: "JSON-line log serialization for normalized LogEvent types"
  - ref: src/orchestrator/agent.py#create_log_callback::callback
    implements: "JSON-line event serializer with type tags for each LogEvent subclass"
  - ref: docs/trunk/ORCHESTRATOR.md
    implements: "Cursor backend documentation: setup, ACP integration, divergences, troubleshooting"
  - ref: tests/test_orchestrator_cursor_backend.py#TestCursorBackendParityEdgeCases
    implements: "Edge-case tests discovered during parity analysis (MCP cleanup, permission without id, early exit)"
  - ref: tests/test_orchestrator_cursor_backend.py#TestCursorBackendEventLoop
    implements: "Event loop tests: sandbox enforcement, question forwarding, review decisions"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on:
- backend_cursor
- backend_config
created_after:
- backend_seam
---
# Chunk Goal

## Minor Goal

The orchestrator is validated to run real chunks end-to-end on Cursor's Composer
at parity with Claude, and the Cursor backend is documented. Phase prompts and
per-phase turn budgets are tuned where Composer diverges from Claude — the
orchestrator skill prompts and `OrchestratorConfig.max_turns_*`.
`docs/trunk/ORCHESTRATOR.md` documents the Cursor backend end-to-end: installing
`cursor-agent`, the ACP integration, the required `.cursor/` configuration
(`mcp.json`, any `hooks.json`), and selecting the backend via config.

## Success Criteria

- A handful of representative chunks complete the full lifecycle
  (PLAN → IMPLEMENT → REVIEW → COMPLETE) on the Cursor backend through the
  orchestrator.
- Sandbox isolation, operator question forwarding, and review decisions are
  confirmed working on Composer in a real run, not just unit tests.
- Divergences from Claude (prompt wording, turn budgets) are identified and tuned;
  any per-backend differences are recorded.
- `docs/trunk/ORCHESTRATOR.md` documents Cursor setup and backend selection
  end-to-end.

## Rejected Ideas

### Standing up an automated Composer-vs-Claude CI gate in this chunk

An automated parity comparison in CI is valuable but out of scope here; this
chunk establishes manual parity and documentation first. Rejected for now to
keep scope focused.