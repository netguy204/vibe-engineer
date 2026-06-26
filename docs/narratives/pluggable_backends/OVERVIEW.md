---
status: COMPLETED
advances_trunk_goal: "Required Properties: The workflow must not be locked to a single agent vendor; the orchestrator must support pluggable agent backends."
proposed_chunks:
  - prompt: >-
      Extract an AgentBackend protocol (with normalized, backend-agnostic types:
      ToolUse, ToolDecision, SessionRequest, and the existing AgentResult) at the
      AgentRunner.run_phase / resume_for_active_status seam, and move the current
      Claude-Agent-SDK logic behind a ClaudeBackend implementation. Pure refactor:
      no behavior change, existing orchestrator tests stay green. This makes the
      Claude coupling explicit and is the precondition for any second backend.
    depends_on: []
    chunk_directory: backend_seam
  - prompt: >-
      Implement a CursorBackend that drives cursor-agent over ACP (JSON-RPC 2.0
      on stdio via `agent acp`). Map the three orchestrator policy callbacks to
      ACP: sandbox enforcement -> session/request_permission, question/suspend ->
      cursor/ask_question, and the ReviewDecision tool -> a .cursor/mcp.json stdio
      MCP server (or postToolUse capture). Resume via session/load; model selects
      Composer. Implements the AgentBackend protocol from the seam chunk.
    depends_on: [0, 3]
    chunk_directory: backend_cursor
  - prompt: >-
      Add backend selection to OrchestratorConfig (a `backend` field, default
      claude) plus a factory that constructs the configured AgentBackend, and
      surface it through `ve settings` / orchestrator config. Defaults to Claude
      so behavior is unchanged until an operator opts into Cursor.
    depends_on: [0]
    chunk_directory: backend_config
  - prompt: >-
      Replace the regex parser over Claude SDK message string-reprs in
      log_parser.py with a structured reader driven by the seam's normalized log
      events, so activity summaries work across backends (Cursor emits structured
      stream-json / ACP session/update rather than Claude SDK reprs). Removes the
      fragile str(message) regex coupling.
    depends_on: [0]
    chunk_directory: backend_logparse
  - prompt: >-
      Parity-test Composer against Claude on a handful of real chunks end-to-end
      through the orchestrator (plan/implement/review/complete), tune phase prompts
      and per-phase max_turns budgets for Composer where they diverge, and document
      the Cursor setup (cursor-agent install, ACP, .cursor/ config) in
      ORCHESTRATOR.md.
    depends_on: [1, 2]
    chunk_directory: backend_parity
created_after: ["intent_ownership"]
---

## Advances Trunk Goal

**Required Properties** — "The workflow must not be locked to a single agent
vendor. The tooling that executes agentic work — most significantly the
orchestrator — must support pluggable agent backends so an operator can run the
workflow on the agent of their choice (e.g. Claude Code, Cursor's Composer)."

This narrative delivers that property for the orchestrator, the component most
deeply coupled to Claude today.

## Driving Ambition

VE's orchestrator runs every phase through the Claude Agent SDK
(`ClaudeSDKClient` in `src/orchestrator/agent.py`), leaning on SDK-specific
primitives: in-process `PreToolUse` hooks for sandbox enforcement, an in-process
MCP server for the ReviewDecision tool, session resume, and a log parser that
regex-scrapes the string representation of SDK message objects. There is no
backend abstraction — Claude is assumed throughout.

Operators have asked to run their workflows on Cursor's Composer. Cursor's CLI
(1.7+) now exposes equivalents for every primitive VE relies on: `agent acp`
(JSON-RPC over stdio) as a programmatic driver, `session/request_permission`
and `.cursor/hooks.json` for tool interception/sandboxing, a blocking
`cursor/ask_question` method for the suspend/resume flow, `.cursor/mcp.json`
MCP servers, `session/load` for resume, structured `stream-json` output, and
`--model` to select Composer. So this is an adapter project, not a redesign of
the orchestrator's safety model.

Success means an operator can set one config value and have the orchestrator
execute chunk phases on Composer, with sandbox isolation, operator question
forwarding, and review decisions all working as they do on Claude — and the
Claude path is unchanged.

Scope note: this narrative covers the **orchestrator** backend only. The entity/
memory subsystem (`src/cli/entity.py`, which shells the `claude` binary and reads
`~/.claude/` paths) and the interactive editor command surface (Claude Code
plugin vs Cursor rules) are separate initiatives, deliberately out of scope here.

## Chunks

The seam comes first; then the Cursor backend, config/factory, and log-parser
work proceed in parallel; parity testing closes it out.

1. **AgentBackend seam + ClaudeBackend** *(no deps)* — Extract the protocol and
   normalized types at the `run_phase` seam; move existing logic behind
   `ClaudeBackend`. Pure refactor, tests stay green. Foundation for everything
   else and worth doing on its own merits.
2. **CursorBackend (ACP client)** *(needs 1, 4)* — Drive `cursor-agent` over ACP;
   map sandbox/question/review callbacks to `session/request_permission`,
   `cursor/ask_question`, and an MCP server.
3. **Backend selection in config + factory** *(needs 1)* — `backend` field on
   `OrchestratorConfig`, factory, `ve settings` surface; defaults to Claude.
4. **Structured log parsing** *(needs 1)* — Replace the SDK-repr regex parser
   with a normalized-event reader so summaries are backend-agnostic.
5. **Composer parity test + tuning + docs** *(needs 2, 3)* — Run Composer
   through real chunks, tune prompts and `max_turns`, document Cursor setup.

## Completion Criteria

When complete, an operator can configure the orchestrator to run on Cursor's
Composer instead of Claude with a single setting, and:

- chunk phases execute end-to-end on Composer (plan → implement → review → complete);
- worktree sandbox isolation, operator question forwarding, and review decisions
  all function on the Cursor backend at parity with Claude;
- the default (Claude) path is behaviorally unchanged and its tests stay green;
- adding a *third* backend later means implementing one `AgentBackend`, not
  touching the scheduler, state machine, or worktree management.
