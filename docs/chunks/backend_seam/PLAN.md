# Implementation Plan

## Approach

Introduce an `AgentBackend` seam so the orchestrator executes phases through an
abstraction instead of calling the Claude Agent SDK inline. Per operator
decision (clean split + update tests), the SDK is physically relocated into its
own module:

- **`src/orchestrator/backend.py`** (new, SDK-free): the `AgentBackend` Protocol
  and the normalized contract types `SessionRequest`, `ToolUse`, `ToolDecision`.
  Reuses the existing `AgentResult` / `ReviewToolDecision` from
  `orchestrator/models.py` as the return type — no new result type (see GOAL
  Rejected Ideas). Also hosts `is_sandbox_violation` (pure path/string logic,
  no SDK), so sandbox *policy* is backend-agnostic and reusable by the future
  Cursor backend.
- **`src/orchestrator/backends/claude.py`** (new): `ClaudeBackend` plus ALL
  `claude_agent_sdk` imports, the message types (`AssistantMessage`,
  `ResultMessage`, …), the hook helpers (`create_sandbox_enforcement_hook`,
  `create_question_intercept_hook`, `create_review_decision_hook`,
  `_merge_hooks`), the MCP server (`create_orchestrator_mcp_server`,
  `review_decision_tool`), and the SDK receive-loop + message-stream parsing
  that captures questions and review decisions. This is a near-verbatim
  relocation of the SDK-touching code currently in `agent.py`.
- **`src/orchestrator/agent.py`** (modified): `AgentRunner` keeps everything
  backend-agnostic — prompt assembly (`get_phase_prompt`, feedback/re-entry
  injection, the CWD/sandbox reminder), env setup (`GIT_DIR`/`GIT_WORK_TREE`),
  and construction of the orchestrator policy callbacks. `run_phase` and
  `resume_for_active_status` build a `SessionRequest` and `await
  self.backend.run(request)`. `agent.py` no longer imports `claude_agent_sdk`
  directly.

**Critical behavior-preserving facts discovered during planning:**

1. The sandbox PreToolUse hook (Bash) is the *only* functional hook. Question
   and ReviewDecision capture do **not** use hooks — `create_question_intercept_hook`
   and `create_review_decision_hook` are dead code (their own docstrings say so);
   the real capture parses `AssistantMessage` content in the receive loop
   (`agent.py:744-818`). The relocation must preserve the message-parsing path,
   not the dead hooks. The dead hook factories are retained in `claude.py` only
   because tests import them (removing them is a separate cleanup, out of scope).
2. Tests patch `orchestrator.agent.ClaudeSDKClient` (8 files) and import the hook
   helpers + `AssistantMessage` from `orchestrator.agent`. After relocation these
   become `orchestrator.backends.claude.*`. This is mechanical (patch strings,
   import lines) with **no assertion changes** — that is the "no behavior change"
   bar in practice.

**Sandbox seam mapping.** `AgentRunner` builds `on_tool_use` from the pure
`is_sandbox_violation(command, host_repo_path, worktree_path)`; for a Bash tool
it returns `ToolDecision.DENY` on violation else `ALLOW`, non-Bash always
`ALLOW` (preserving today's behavior). `ClaudeBackend` adapts `request.on_tool_use`
into a PreToolUse Bash hook (the adapter replaces the body of
`create_sandbox_enforcement_hook`, which now delegates to the same pure
`is_sandbox_violation`). Net behavior is identical; the violation logic has one
home.

**Question/review seam mapping.** `AgentRunner` passes the orchestrator's
`question_callback` → `request.on_question` and `review_decision_callback` →
`request.on_review_decision`. `ClaudeBackend.run` invokes them from the same
message-parsing code that exists today, and populates `AgentResult`
(`suspended`/`question`/`review_decision`/`completed`/`error`). `expose_review_tool`
on the request (set by `AgentRunner` when `phase == REVIEW`) tells `ClaudeBackend`
to attach the orchestrator MCP server + allowed tool.

Per TESTING_PHILOSOPHY, the existing orchestrator suite is the regression
guard; new structural types get focused unit tests. This is a refactor, so the
bar is "suite green with only mechanical test edits."

## Subsystem Considerations

- **docs/subsystems/orchestrator** (DOCUMENTED): This chunk refactors within the
  orchestrator subsystem (`agent.py` already carries its backreference). It
  introduces the `AgentBackend` seam but does not change orchestration behavior.
  New modules (`backend.py`, `backends/claude.py`) carry
  `# Subsystem: docs/subsystems/orchestrator` and
  `# Chunk: docs/chunks/backend_seam` backreferences.

## Sequence

### Step 1: Define the backend contract (`src/orchestrator/backend.py`)

New SDK-free module containing:
- `class ToolDecision(StrEnum)`: `ALLOW = "allow"`, `DENY = "deny"`.
- `@dataclass ToolUse`: `tool_name: str`, `tool_input: dict`,
  `command: str | None`, `cwd: str | None`.
- `@dataclass SessionRequest`: `prompt: str`, `cwd: Path`, `env: dict[str,str]`,
  `max_turns: int`, `allowed_tools: list[str] = []`,
  `resume_session_id: str | None = None`, `expose_review_tool: bool = False`,
  and the policy callbacks `on_tool_use: Callable[[ToolUse], ToolDecision] | None`,
  `on_question: Callable[[dict], None] | None`,
  `on_review_decision: Callable[[ReviewToolDecision], None] | None`,
  `on_log: Callable[[Any], None] | None`.
- `class AgentBackend(Protocol)`: `async def run(self, request: SessionRequest) -> AgentResult: ...`
- `def is_sandbox_violation(command, host_repo_path, worktree_path) -> tuple[bool, str | None]`:
  moved verbatim from `agent.py:_is_sandbox_violation` (pure, no SDK).

### Step 2: Create `ClaudeBackend` (`src/orchestrator/backends/claude.py`)

New package `src/orchestrator/backends/` (`__init__.py`) and `claude.py`. Move
from `agent.py`, near-verbatim:
- all `claude_agent_sdk` imports and message types;
- `review_decision_tool`, `create_orchestrator_mcp_server`;
- `create_sandbox_enforcement_hook` (reimplemented to wire a provided
  `on_tool_use`/`ToolUse` and delegate to `backend.is_sandbox_violation`),
  `create_question_intercept_hook`, `create_review_decision_hook`, `_merge_hooks`;
- `class ClaudeBackend` implementing `AgentBackend.run`: builds
  `ClaudeAgentOptions` from `SessionRequest` (cwd, env, `permission_mode="bypassPermissions"`,
  `max_turns`, `setting_sources=["project"]`, `max_buffer_size`, `resume`),
  attaches the sandbox PreToolUse hook driven by `request.on_tool_use`, attaches
  the MCP server + `mcp__orchestrator__ReviewDecision` allowed tool when
  `expose_review_tool`, runs `ClaudeSDKClient`, and contains the receive loop +
  `AssistantMessage` parsing that fires `on_question`/`on_review_decision` and
  builds the `AgentResult` (the logic from `agent.py:707-847`).

`ClaudeBackend` is stateless aside from `host_repo_path` context it needs — note
the sandbox paths flow through `on_tool_use` (closure built in `AgentRunner`), so
`ClaudeBackend` needs no repo/worktree knowledge. Verify this holds; if the hook
adapter needs the worktree path, carry it on `SessionRequest` rather than the
backend constructor.

### Step 3: Slim `AgentRunner.run_phase` to delegate (`src/orchestrator/agent.py`)

- Remove `claude_agent_sdk` imports; import `AgentBackend`, `SessionRequest`,
  `ToolUse`, `ToolDecision`, `is_sandbox_violation` from `orchestrator.backend`
  and `ClaudeBackend` from `orchestrator.backends.claude`.
- `AgentRunner.__init__` gains `backend: AgentBackend | None = None`, defaulting
  to `ClaudeBackend()`. (The `backend_config` chunk later moves construction to a
  factory; here a default keeps callers unchanged.)
- `run_phase` keeps all prompt/env construction, then builds `on_tool_use`
  (sandbox closure over `self.host_repo_path` + `worktree_path` using
  `is_sandbox_violation`), maps `question_callback`/`review_decision_callback`
  to `on_question`/`on_review_decision`, sets `expose_review_tool = (phase ==
  REVIEW)`, assembles `SessionRequest`, and returns `await self.backend.run(req)`.
- The method signature (kwargs: `chunk`, `phase`, `worktree_path`,
  `resume_session_id`, `answer`, `reentry_context`, `log_callback`,
  `question_callback`, `review_decision_callback`) is unchanged so scheduler and
  tests that call `run_phase(...)` are untouched.

### Step 4: Route `resume_for_active_status` through the backend

Build a `SessionRequest` (fixed reminder prompt, `resume_session_id=session_id`,
`max_turns=self.config.max_turns_complete`, sandbox `on_tool_use`, no
question/review callbacks, `expose_review_tool=False`) and return
`await self.backend.run(req)`. Preserve the `new_session_id or session_id`
fallback in `AgentRunner` after the backend returns.

### Step 5: Fix `scheduler.py` import

`scheduler.py:30` imports `create_review_decision_hook` from `orchestrator.agent`
but never uses it. Drop it from the import (keep `AgentRunner`,
`create_log_callback`). No other scheduler change — `AgentRunner` construction and
`run_phase`/`resume_for_active_status` call sites are unchanged.

### Step 6: Update test imports and patch targets (mechanical)

Across the 8 affected files, change:
- `patch("orchestrator.agent.ClaudeSDKClient", ...)` →
  `patch("orchestrator.backends.claude.ClaudeSDKClient", ...)`;
- `from orchestrator.agent import (… create_*_hook, create_orchestrator_mcp_server,
  review_decision_tool, _merge_hooks, AssistantMessage …)` →
  import those from `orchestrator.backends.claude`;
- `_is_sandbox_violation` → `is_sandbox_violation` from `orchestrator.backend`
  (rename + relocate).

No assertion or test-logic changes. Files: `test_orchestrator_agent_runner.py`,
`test_orchestrator_agent_stream.py`, `test_orchestrator_agent_callbacks.py`,
`test_orchestrator_agent_review.py`, `test_orchestrator_agent_sandbox.py`,
`test_orchestrator_agent_skills.py`, `test_orchestrator_feedback_injection.py`,
`test_orchestrator_reentry.py`.

### Step 7: Add focused unit tests for the seam (`tests/test_orchestrator_backend.py`)

- `SessionRequest`/`ToolUse`/`ToolDecision` construct with expected defaults.
- A trivial fake `AgentBackend` satisfies the Protocol and `AgentRunner(backend=fake)`
  routes `run_phase` through it (proves the seam is real and injectable).
- `is_sandbox_violation` parity check (can reuse a couple of existing cases) to
  confirm the relocation preserved logic.

### Step 8: Run the full orchestrator suite and `ve validate`

`uv run pytest tests/ -k orchestrator` (plus the reviewer/reentry/feedback
files) must be green with only the mechanical edits from Step 6. Run
`uv run ve validate` to confirm no new integrity errors and that the new modules
carry correct backreference comments.

## Dependencies

None. This is the root chunk of the `pluggable_backends` narrative
(`depends_on: []`); `backend_config`, `backend_logparse`, and `backend_cursor`
build on the seam it establishes.

## Risks and Open Questions

- **Patch-target completeness.** If any test patches the SDK or imports a helper
  through a path the grep missed, it will fail loudly; fix by repointing the
  import/patch. Low risk, fast to detect.
- **Sandbox closure context.** Confirm the `on_tool_use` adapter in
  `ClaudeBackend` has everything it needs from `ToolUse` alone. If the PreToolUse
  hook needs worktree/host paths beyond what the closure captures, carry them on
  `SessionRequest` rather than reintroducing them into the backend constructor.
- **Session-id capture parity.** The receive loop reads `session_id` from `init`
  dicts, `ResultMessage`, and `AssistantMessage`. Move all three paths intact;
  the `new_session_id or session_id` fallback for resume must stay.
- **`query` deprecated import.** `agent.py` imports `query` "for backwards
  compatibility in deprecated methods" — verify nothing still uses it before
  dropping; if used, relocate alongside the SDK.
