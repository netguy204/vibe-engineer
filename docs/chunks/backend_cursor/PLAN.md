

<!--
This document captures HOW you'll achieve the chunk's GOAL.
It should be specific enough that each step is a reasonable unit of work
to hand to an agent.
-->

# Implementation Plan

## Approach

`CursorBackend` implements the `AgentBackend` protocol (single method:
`async run(request: SessionRequest) -> AgentResult`) by spawning
`cursor-agent acp` as a subprocess and speaking JSON-RPC 2.0 over its
stdin/stdout. The implementation mirrors `ClaudeBackend`'s responsibilities —
sandbox enforcement, question forwarding, review-decision capture, session
resume, log-event normalization — but maps each onto ACP methods and Cursor
configuration files instead of Claude Agent SDK primitives.

Key design choices:

- **Subprocess, not SDK import.** `cursor-agent` is an external binary; the
  backend spawns it with `asyncio.create_subprocess_exec` and communicates via
  JSON-RPC. No Cursor-specific Python library is imported.
- **Sandbox enforcement via `session/request_permission`.** ACP surfaces
  tool-permission requests; the backend evaluates them against
  `is_sandbox_violation` (shared with ClaudeBackend) and replies allow/deny.
- **Question forwarding via `cursor/ask_question`.** This is a blocking
  JSON-RPC method from the agent side. The backend receives it, invokes
  `on_question`, and returns a response that causes the session to suspend
  (the orchestrator will resume later via `session/load`).
- **ReviewDecision via `.cursor/mcp.json`.** A stdio MCP server definition
  is written into the worktree's `.cursor/mcp.json` before the session starts.
  The backend watches `session/update` events for a ReviewDecision tool call
  and captures it into `AgentResult.review_decision`.
- **Log normalization.** `session/update` notifications carry structured
  content (text, tool calls, tool results). The backend translates these into
  `TextEvent`, `ToolCallEvent`, `ToolResultEvent`, and `ResultEvent` and
  invokes `on_log` — same event types `ClaudeBackend` emits.
- **Registration.** `CursorBackend` is added to `BACKEND_REGISTRY` in
  `src/orchestrator/backends/__init__.py` so `create_backend("cursor")` works
  with the existing factory (backend_config chunk).

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk IMPLEMENTS a new
  backend within the orchestrator subsystem, following the same seam pattern
  established by `ClaudeBackend`.

## Sequence

### Step 1: ACP JSON-RPC transport layer

Create `src/orchestrator/backends/cursor.py`. Implement a low-level ACP
transport class (`ACPTransport`) that:

- Spawns `cursor-agent acp` as a subprocess (`asyncio.create_subprocess_exec`).
- Sends JSON-RPC 2.0 requests (with auto-incrementing `id`) via stdin.
- Reads newline-delimited JSON-RPC responses/notifications from stdout.
- Provides `async send_request(method, params) -> result` for request/response
  pairs (correlating by `id`).
- Provides `async send_notification(method, params)` for one-way messages
  (JSON-RPC notifications have no `id`).
- Buffers incoming notifications (those without a correlated request `id`)
  into an `asyncio.Queue` for the event loop to consume.
- Handles subprocess lifecycle: start, graceful shutdown, error on unexpected
  exit.
- Raises a clear error (`FileNotFoundError`-derived or `RuntimeError`) when
  `cursor-agent` is not found on `$PATH`, satisfying the "missing binary"
  success criterion.

Location: `src/orchestrator/backends/cursor.py`

Write tests for the transport layer:
- Test that a missing binary raises a clear, actionable error message.
- Test JSON-RPC request/response correlation using a mock subprocess.
- Test notification buffering.

Location: `tests/test_orchestrator_cursor_backend.py`

### Step 2: ReviewDecision MCP server scaffold

Implement a helper that writes a `.cursor/mcp.json` file into the worktree's
`.cursor/` directory. This file declares a stdio MCP server that exposes the
`ReviewDecision` tool with the same schema as the Claude MCP tool
(`review_decision_tool` in `backends/claude.py`).

The MCP server itself is a small Python script (or inline command) that:
- Reads JSON-RPC from stdin, writes to stdout.
- Handles `tools/list` (returns the ReviewDecision tool definition).
- Handles `tools/call` for `ReviewDecision` (returns a confirmation).
- The backend will capture the decision by observing the tool call in the
  ACP event stream, not from the MCP server's response.

Provide a helper function `_write_cursor_mcp_config(worktree: Path)` that
writes the config and a `_remove_cursor_mcp_config(worktree: Path)` that
cleans up. The cleanup ensures the worktree isn't polluted after the phase.

Location: `src/orchestrator/backends/cursor.py`

Tests:
- `_write_cursor_mcp_config` creates `.cursor/mcp.json` with correct schema.
- `_remove_cursor_mcp_config` removes it.
- The MCP server script, if a file, is valid Python that can be imported
  without error.

Location: `tests/test_orchestrator_cursor_backend.py`

### Step 3: CursorBackend.run — session creation and model selection

Implement the `CursorBackend` class with `async def run(self, request:
SessionRequest) -> AgentResult`.

The initial skeleton:

1. Validate `cursor-agent` is on PATH; raise clear error if not.
2. If `request.expose_review_tool`, call `_write_cursor_mcp_config`.
3. Start the ACP transport (`cursor-agent acp`).
4. Send `system/init` — receive the session init event; capture `session_id`.
5. Create or resume session:
   - If `request.resume_session_id` is set: send `session/load` with the
     existing session id + prompt (operator answer is already prepended by
     `AgentRunner`).
   - Otherwise: send `session/new` with `model: "composer"`,
     `permissions: "auto-allow"`, `cwd: str(request.cwd)`, and the prompt.
6. Enter the event loop (Step 4).
7. After the event loop exits, clean up MCP config if written, shut down
   transport.
8. Return a populated `AgentResult`.

Location: `src/orchestrator/backends/cursor.py`

Tests:
- `CursorBackend` satisfies the `AgentBackend` protocol (static assertion at
  module bottom, same pattern as `claude.py`).
- A mock ACP transport that replays a simple session (init → new → update →
  result) produces a correct `AgentResult(completed=True, session_id=...)`.

Location: `tests/test_orchestrator_cursor_backend.py`

### Step 4: ACP event loop — sandbox, questions, review, and log events

Implement the main event-processing loop that runs after session creation.
The loop reads `session/update` notifications from the transport's queue and
handles each event type:

**Sandbox enforcement (`session/request_permission`):**
- Extract the tool name, input, command, and cwd from the permission request.
- Build a `ToolUse` and call `is_sandbox_violation(command,
  request.host_repo_path, request.cwd)`.
- Reply with allow or deny. On deny, include the violation reason so the
  agent sees it.

**Question forwarding (`cursor/ask_question`):**
- This is a blocking JSON-RPC request from the agent to us.
- Extract question text/options into the same dict shape `ClaudeBackend` uses
  (`question`, `options`, `header`, `multiSelect`, `all_questions`).
- Invoke `request.on_question(question_data)`.
- The session is suspended; set `captured_question` and break the event loop.
  (The orchestrator will later call `session/load` to resume.)

**ReviewDecision capture:**
- Watch for tool-call events where `name` matches `ReviewDecision` (or the
  MCP-namespaced variant).
- Parse the input into a `ReviewToolDecision` and invoke
  `request.on_review_decision`.
- Set `captured_review_decision`.

**Log-event normalization:**
- `session/update` notifications carry content blocks (text, tool_use,
  tool_result). Translate each into `TextEvent`, `ToolCallEvent`,
  `ToolResultEvent` and call `request.on_log`.
- On session completion (result notification), emit `ResultEvent` and break
  the loop.

**Error handling:**
- If the subprocess exits unexpectedly, capture the error.
- If a JSON-RPC error response arrives, capture it.

Location: `src/orchestrator/backends/cursor.py`

Tests:
- Permission request for a safe command → allow reply.
- Permission request for a sandbox-violating command → deny reply with reason.
- `cursor/ask_question` event → `on_question` called, result is
  `AgentResult(suspended=True, question=...)`.
- ReviewDecision tool call in event stream → `on_review_decision` called,
  `AgentResult.review_decision` populated.
- Text/tool events in the stream → `on_log` called with correct `LogEvent`
  types.
- Session error → `AgentResult(completed=False, error=...)`.

Location: `tests/test_orchestrator_cursor_backend.py`

### Step 5: Register in backend factory

Add `CursorBackend` to `BACKEND_REGISTRY` in
`src/orchestrator/backends/__init__.py`:

```python
from orchestrator.backends.cursor import CursorBackend

BACKEND_REGISTRY: dict[str, type] = {
    "claude": ClaudeBackend,
    "cursor": CursorBackend,
}
```

Use a lazy import (or conditional import) so that the module loads cleanly
even if `cursor-agent` isn't installed — the binary check happens at
`run()` time, not import time.

Location: `src/orchestrator/backends/__init__.py`

Tests:
- `create_backend("cursor")` returns a `CursorBackend` instance.
- `create_backend("cursor")` result satisfies `AgentBackend` protocol.

Location: `tests/test_orchestrator_backend_factory.py` (extend existing)

### Step 6: Update GOAL.md code_paths and final protocol assertion

Update the chunk GOAL.md frontmatter `code_paths` with the files touched:
- `src/orchestrator/backends/cursor.py`
- `src/orchestrator/backends/__init__.py`
- `tests/test_orchestrator_cursor_backend.py`
- `tests/test_orchestrator_backend_factory.py`

Add a module-level protocol assertion at the bottom of `cursor.py`:
```python
_: AgentBackend = CursorBackend()
```

Run full test suite to verify nothing is broken.

---

**BACKREFERENCE COMMENTS**

All new code should carry:
```python
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_cursor - CursorBackend: ACP-based Cursor/Composer backend
```

## Dependencies

- **backend_seam** (ACTIVE): Provides `AgentBackend`, `SessionRequest`,
  `ToolUse`, `ToolDecision`, `is_sandbox_violation`, and the `LogEvent` types.
- **backend_logparse** (ACTIVE): Provides the normalized `LogEvent` contract
  that the Cursor backend must emit into.
- **backend_config** (ACTIVE): Provides `BACKEND_REGISTRY` and
  `create_backend` factory where `CursorBackend` registers.
- **External**: `cursor-agent` binary (Cursor CLI 1.7+). Not a Python
  dependency — the backend shells out. Missing binary produces a clear error
  at runtime, not import time.

## Risks and Open Questions

- **ACP protocol stability.** The `cursor-agent acp` surface is new (Cursor
  1.7+). Method names and parameter shapes may shift between releases. The
  implementation should be defensive about unexpected fields and log warnings
  rather than crash on unknown event types.
- **`session/request_permission` coverage.** It's unclear whether ACP
  surfaces permission requests for *all* tool types or only a subset. If
  some tools bypass the permission flow, sandbox enforcement may have gaps.
  The parity-test chunk (backend_parity) will validate this end-to-end.
- **Question suspension semantics.** `cursor/ask_question` is described as
  blocking from the agent's perspective. Need to confirm that not replying
  (or replying with a sentinel) actually suspends the session in a way that
  `session/load` can resume later. If it doesn't, we may need to kill the
  subprocess and rely on session persistence.
- **ReviewDecision tool naming in ACP.** The MCP tool may appear in the event
  stream under an MCP-namespaced name (e.g., `mcp__orchestrator__ReviewDecision`)
  or a plain name. The matching logic should handle both forms.
- **Subprocess cleanup.** If the orchestrator process is killed, the
  `cursor-agent` subprocess may linger. The transport should register cleanup
  via `atexit` or `try/finally` patterns.

## Deviations

<!--
POPULATE DURING IMPLEMENTATION, not at planning time.

When reality diverges from the plan, document it here:
- What changed?
- Why?
- What was the impact?

Minor deviations (renamed a function, used a different helper) don't need
documentation. Significant deviations (changed the approach, skipped a step,
added steps) do.

Example:
- Step 4: Originally planned to use std::fs::rename for atomic swap.
  Testing revealed this isn't atomic across filesystems. Changed to
  write-fsync-rename-fsync sequence per platform best practices.
-->