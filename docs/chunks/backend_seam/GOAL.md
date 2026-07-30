---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: ["src/orchestrator/backend.py", "src/orchestrator/backends/__init__.py", "src/orchestrator/backends/claude.py", "src/orchestrator/agent.py", "src/orchestrator/scheduler.py", "tests/test_orchestrator_backend.py", "tests/test_orchestrator_agent_runner.py", "tests/test_orchestrator_agent_stream.py", "tests/test_orchestrator_agent_callbacks.py", "tests/test_orchestrator_agent_review.py", "tests/test_orchestrator_agent_sandbox.py", "tests/test_orchestrator_agent_skills.py", "tests/test_orchestrator_feedback_injection.py", "tests/test_orchestrator_reentry.py"]
code_references:
  - ref: src/orchestrator/backend.py#AgentBackend
    implements: "Backend-agnostic protocol the orchestrator runs phases through"
  - ref: src/orchestrator/backend.py#SessionRequest
    implements: "Normalized per-phase request (prompt, env, sandbox context, policy callbacks)"
  - ref: src/orchestrator/backend.py#ToolUse
    implements: "Normalized tool-invocation type for permission/sandbox gating"
  - ref: src/orchestrator/backend.py#ToolDecision
    implements: "ALLOW/DENY vocabulary for tool-use policy"
  - ref: src/orchestrator/backend.py#is_sandbox_violation
    implements: "Shared, backend-agnostic worktree sandbox policy"
  - ref: src/orchestrator/backends/claude.py#ClaudeBackend
    implements: "Claude Agent SDK confined behind the AgentBackend seam"
  - ref: src/orchestrator/agent.py#AgentRunner::__init__
    implements: "Pluggable backend injection (default ClaudeBackend)"
  - ref: src/orchestrator/agent.py#AgentRunner::run_phase
    implements: "Builds a SessionRequest and delegates phase execution to the backend"
  - ref: src/orchestrator/agent.py#AgentRunner::resume_for_active_status
    implements: "Resume delegated to the backend with session-id fallback"
narrative: pluggable_backends
investigation: null
subsystems: []
friction_entries: []
depends_on: []
created_after: ["watch_handshake_5xx_retry"]
---

# Chunk Goal

## Minor Goal

The orchestrator executes agent phases through an `AgentBackend` abstraction
rather than calling the Claude Agent SDK directly. `AgentRunner.run_phase` and
`AgentRunner.resume_for_active_status` (in `src/orchestrator/agent.py`) delegate
to a backend implementing a single protocol; all Claude-specific machinery —
`ClaudeSDKClient`, `ClaudeAgentOptions`, the SDK hook helpers
(`create_sandbox_enforcement_hook`, `create_question_intercept_hook`,
`create_review_decision_hook`, `_merge_hooks`), the in-process MCP server
(`create_orchestrator_mcp_server`), and session resume (`options.resume`) —
lives entirely behind a `ClaudeBackend` implementation.

The contract is expressed in backend-agnostic, normalized types: a
`SessionRequest` (prompt, cwd, env, max_turns, allowed_tools,
resume_session_id, sandbox context, and `expose_review_tool`), `ToolUse` and
`ToolDecision` for tool/permission gating, and the existing
`AgentResult` (`src/orchestrator/models.py`, reused unchanged). Orchestrator
policy is split two ways: worktree sandbox enforcement is shared logic
(`is_sandbox_violation`) applied over the request's sandbox context and
expressed in `ToolUse`/`ToolDecision` terms, while operator question/suspend
forwarding and review-decision capture are observation callbacks on the request
(`on_question`, `on_review_decision`, plus `on_log`) that `ClaudeBackend` maps
onto the SDK hooks and message stream. The abstraction owns the seam at which a
second backend (e.g. Cursor/Composer) plugs in without touching the scheduler,
work-unit state machine, or worktree management.

## Success Criteria

- An `AgentBackend` Protocol (or ABC) exists with a single entry point —
  `async run(request: SessionRequest) -> AgentResult` — covering both fresh
  runs and resume (resume folded in via `resume_session_id` on the request; the
  operator answer is injected into the prompt by `AgentRunner`).
- Normalized types `SessionRequest`, `ToolUse`, `ToolDecision` are defined;
  `AgentResult` is reused with no field changes
  (`completed`, `suspended`, `session_id`, `question`, `error`,
  `review_decision`).
- All `claude_agent_sdk` imports and SDK-specific config/hook/MCP code are
  confined to the `ClaudeBackend` module. `run_phase` / `resume_for_active_status`
  no longer reference `ClaudeSDKClient`, `ClaudeAgentOptions`, the hook helpers,
  or `create_sdk_mcp_server` directly.
- The three policy callbacks are invoked by `ClaudeBackend` through the existing
  SDK hooks, preserving current behavior: sandbox enforcement still blocks
  worktree escapes, `AskUserQuestion` still suspends and forwards, the
  `ReviewDecision` MCP tool still records decisions during the REVIEW phase.
- **No behavior change.** The existing orchestrator test suite
  (`tests/test_orchestrator_*.py`) passes unchanged. This is the acceptance bar:
  the refactor is behavior-preserving.
- The scheduler, work-unit state machine, worktree management, and `AgentResult`
  shape are untouched.

## Rejected Ideas

### Defining a new result type instead of reusing AgentResult

`AgentResult` already captures everything a backend needs to communicate
(`completed`, `suspended`, `session_id`, `question`, `error`,
`review_decision`). Introducing a parallel result type would force a translation
layer for no gain. Rejected — reuse `AgentResult` as the backend return type.

### Folding the structured log-event reader into this chunk

Normalizing log parsing (replacing the regex over Claude SDK message
string-reprs in `log_parser.py`) is its own chunk (`backend_logparse`). This
chunk defines the normalized log-event shape via the `on_log` callback but does
not rewrite the summarizer. Keeping them separate preserves the "pure refactor,
no behavior change" acceptance bar for this chunk.