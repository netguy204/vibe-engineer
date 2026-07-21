---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/orchestrator/backends/cursor.py
- src/orchestrator/backends/__init__.py
- tests/test_orchestrator_cursor_backend.py
- tests/test_orchestrator_backend_factory.py
code_references:
- ref: src/orchestrator/backends/cursor.py#CursorBackend
  implements: "AgentBackend implementation that drives cursor-agent via ACP JSON-RPC"
- ref: src/orchestrator/backends/cursor.py#CursorBackend::run
  implements: "Session lifecycle: init, create/resume, event loop, result assembly"
- ref: src/orchestrator/backends/cursor.py#ACPTransport
  implements: "JSON-RPC 2.0 transport over cursor-agent acp subprocess"
- ref: src/orchestrator/backends/cursor.py#CursorAgentNotFoundError
  implements: "Actionable error when cursor-agent binary is missing"
- ref: src/orchestrator/backends/cursor.py#_write_cursor_mcp_config
  implements: "ReviewDecision MCP server scaffold written to .cursor/mcp.json"
- ref: src/orchestrator/backends/cursor.py#_remove_cursor_mcp_config
  implements: "Cleanup of .cursor/mcp.json and server script after phase"
- ref: src/orchestrator/backends/__init__.py
  implements: "CursorBackend registration in factory via lazy import"
- ref: tests/test_orchestrator_cursor_backend.py
  implements: "Transport, MCP config, and event loop tests for CursorBackend"
- ref: tests/test_orchestrator_backend_factory.py#test_create_backend_returns_cursor
  implements: "Factory integration test for cursor backend"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on:
- backend_logparse
created_after:
- backend_seam
---

# Chunk Goal

## Minor Goal

A `CursorBackend` implements the `AgentBackend` protocol by driving the
`cursor-agent` CLI over ACP (Agent Client Protocol — JSON-RPC 2.0 on stdio via
`agent acp`), so the orchestrator executes phases on Cursor's Composer model. It
maps the `SessionRequest` policy callbacks onto ACP/Cursor mechanisms:
`on_tool_use` (sandbox enforcement) to `session/request_permission` allow/deny
replies driven by worktree path checks, `on_question` (suspend/forward) to the
blocking `cursor/ask_question` method, and `on_review_decision` to a
`ReviewDecision` tool exposed via `.cursor/mcp.json` (a stdio MCP server).
Sessions are created with `session/new` and resumed via `session/load` (the
session id surfaced from the ACP `system/init` event); the model is selected as
Composer and permissions are auto-allowed under orchestrator policy for
autonomous execution. ACP `session/update` notifications are normalized into the
seam's `AgentResult` and `on_log` events.

## Success Criteria

- `CursorBackend` satisfies the `AgentBackend` protocol and returns a populated
  `AgentResult` (completed/suspended/session_id/question/error/review_decision).
- Sandbox enforcement works: a tool/shell action that would escape the worktree is
  denied via `session/request_permission` (parity with the Claude sandbox hook).
- Operator questions suspend the run and forward via `cursor/ask_question`;
  resuming with an answer continues the session via `session/load`.
- The `ReviewDecision` tool is available during REVIEW and its decision is captured
  into `AgentResult.review_decision`.
- Composer is the model used; permission prompts are auto-allowed for autonomous
  execution.
- A missing `cursor-agent` binary is reported with a clear, actionable error.

## Rejected Ideas

### Driving cursor-agent via `-p --output-format stream-json` instead of ACP

Print mode with `stream-json` gives structured output but no in-process
permission/question request-response, so sandbox enforcement and suspend/resume
would have to be reconstructed out-of-process via `.cursor/hooks.json` scripts
and stdout scraping. ACP provides `session/request_permission` and the blocking
`cursor/ask_question` in-process, mapping cleanly onto the seam's callbacks.
Rejected stream-json as the primary driver; ACP is the integration surface
(stream-json + hooks remain a fallback if specific ACP methods prove unstable).

### Capturing the review decision via a hook instead of an MCP tool

A `postToolUse` hook could observe a review decision, but the existing design
exposes `ReviewDecision` as an MCP tool the agent calls explicitly. Mirroring
that via `.cursor/mcp.json` keeps the agent-facing contract identical across
backends. Hook capture remains a fallback.