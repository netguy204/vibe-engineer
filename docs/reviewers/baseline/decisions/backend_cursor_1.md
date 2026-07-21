---
decision: APPROVE
summary: All six success criteria satisfied — CursorBackend implements AgentBackend via ACP JSON-RPC with sandbox enforcement, question forwarding, ReviewDecision capture, Composer model selection, and clear missing-binary errors; 29 tests pass.
operator_review: null
---

## Criteria Assessment

### Criterion 1: `CursorBackend` satisfies the `AgentBackend` protocol and returns a populated `AgentResult`

- **Status**: satisfied
- **Evidence**: Module-level assertion `_: AgentBackend = CursorBackend()` at cursor.py:686. `run()` returns `AgentResult` with completed/suspended/session_id/question/error/review_decision populated across all code paths (lines 660-682). Factory test confirms `create_backend("cursor")` returns a protocol-satisfying instance.

### Criterion 2: Sandbox enforcement works: a tool/shell action that would escape the worktree is denied via `session/request_permission`

- **Status**: satisfied
- **Evidence**: `session/request_permission` handler at cursor.py:532-572 builds a `ToolUse`, calls shared `is_sandbox_violation()`, and replies allow/deny with reason via JSON-RPC. Tests `test_sandbox_allow_safe_command` and `test_sandbox_deny_violation` cover both paths.

### Criterion 3: Operator questions suspend the run and forward via `cursor/ask_question`; resuming with an answer continues the session via `session/load`

- **Status**: satisfied
- **Evidence**: `cursor/ask_question` handler at cursor.py:575-593 captures question data in the same dict shape as ClaudeBackend, calls `on_question`, breaks the loop. Result is `AgentResult(suspended=True, question=...)`. Resume path at cursor.py:480-485 sends `session/load` with the existing session ID. Tests `test_question_forwarding` and `test_session_resume` validate both directions.

### Criterion 4: The `ReviewDecision` tool is available during REVIEW and its decision is captured into `AgentResult.review_decision`

- **Status**: satisfied
- **Evidence**: `_write_cursor_mcp_config` writes `.cursor/mcp.json` with an inline MCP server script exposing ReviewDecision (cursor.py:211-235). The event loop captures ReviewDecision tool calls from `session/update` at cursor.py:619-633, matching both plain and MCP-namespaced names via `_REVIEW_DECISION_NAMES` frozenset. Cleanup via `_remove_cursor_mcp_config` in the finally block. Tests cover both name variants.

### Criterion 5: Composer is the model used; permission prompts are auto-allowed for autonomous execution

- **Status**: satisfied
- **Evidence**: `session/new` request at cursor.py:487-492 sends `"model": "composer"` and `"permissions": "auto-allow"`.

### Criterion 6: A missing `cursor-agent` binary is reported with a clear, actionable error

- **Status**: satisfied
- **Evidence**: `CursorAgentNotFoundError` (cursor.py:260-268) with message including the binary name, version requirement, and docs URL. Checked both at transport start and at `CursorBackend.run` entry (double-check pattern). Tests `test_start_raises_when_binary_missing`, `test_error_message_is_actionable`, and `test_raises_when_binary_missing` validate.

## Notes

- The permission reply (cursor.py:567-571) writes directly to `transport._process.stdin` rather than through an `ACPTransport` method, because `send_request` auto-increments IDs while replies need the incoming message's ID. A `send_reply(id, result)` method would be cleaner encapsulation, but this is a minor style observation, not a functional issue.
- `_FakeTransportBackend` (test line 281) is defined but unused — `_run_with_fake_events` is used instead. Dead code, but trivial.
- The pre-existing `test_subsystem_list.py` failure is unrelated to this chunk.
