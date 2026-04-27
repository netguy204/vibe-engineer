---
discovered_by: audit batch 8b
discovered_at: 2026-04-26T02:12:10Z
severity: medium
status: open
artifacts:
  - docs/chunks/orch_reviewer_decision_mcp/GOAL.md
  - src/orchestrator/agent.py
---

## Claim

The chunk's GOAL.md (lines 46-50, 73-74, and the success criteria at lines 80-87) frames the migration as fixing two broken hook-based interceptions:

> 1. **AskUserQuestion interception never works**: The hook to capture agent questions and route them to the attention queue never fires. Questions have never reached the operator.
> 2. **ReviewDecision tool can't be called**: The custom tool doesn't exist (hooks can't create tools), and even if it did, the hook to intercept it wouldn't fire.

And later:

> With `ClaudeSDKClient`:
> - Hooks work → AskUserQuestion interception functions
> - Custom tools via MCP → ReviewDecision is callable

Success criteria assert:

> - `AskUserQuestion` hook fires and questions reach the attention queue
> - `ReviewDecision` custom tool is defined via `@tool` decorator and MCP server
> - Reviewer agent can call `ReviewDecision` and decision is captured/routed correctly

## Reality

The migration to `ClaudeSDKClient` did happen (verified at `src/orchestrator/agent.py:692`), and a `create_orchestrator_mcp_server()` plus `@tool`-decorated `review_decision_tool` are in place (lines 57-118). But the load-bearing capture mechanism for *both* tools is **not** the hook — it's message-content parsing inside the `AssistantMessage` loop:

- `src/orchestrator/agent.py:288-298` — the docstring on `create_question_intercept_hook` states explicitly:

  > IMPORTANT: This hook is defined but non-functional. PreToolUse hooks in the Claude Agent SDK do not fire for built-in tools like AskUserQuestion. The actual capture happens via message parsing in run_orchestrator_agent(), which extracts AskUserQuestion calls from AssistantMessage content. This hook is retained for potential future SDK compatibility.

- `src/orchestrator/agent.py:755-768` — the AskUserQuestion capture path:

  > # Note: PreToolUse hooks don't fire for built-in tools like AskUserQuestion,
  > # so we capture the tool call directly from the AssistantMessage content.

- `src/orchestrator/agent.py:726-753` — the ReviewDecision capture path mirrors this pattern:

  > # Note: PreToolUse hooks don't fire for MCP tools, so we capture
  > # the tool call directly from the AssistantMessage instead.

So the chunk's central claim — that migrating to `ClaudeSDKClient` makes the hooks fire — is contradicted by the very file the chunk owns. The hooks are still defined (and `create_review_decision_hook` is wired in at line 661), but the reason ReviewDecision and AskUserQuestion now work is message-content parsing, not hook firing. The hooks are dormant fallbacks.

This is undeclared over-claim: `code_references` are honest (each entry maps to a real symbol) but the prose mis-attributes the mechanism. A reader following the chunk to understand *why* the system works would conclude hooks fire — and would be wrong.

## Workaround

None needed for runtime — the system works correctly via the message-parsing path. The inconsistency is documentary: the chunk's stated mechanism does not match the implemented mechanism.

## Fix paths

1. **Rewrite the GOAL.md prose to describe the actual mechanism.** Frame the chunk as: "Migrate to `ClaudeSDKClient` to enable the MCP server (which makes `ReviewDecision` callable) and to keep hooks available; capture both `AskUserQuestion` and `ReviewDecision` via `AssistantMessage` content parsing because PreToolUse hooks do not fire for built-in or MCP tools." Update success criteria to drop "hook fires" claims and instead assert "AssistantMessage parsing captures the tool call."

2. **Make the hooks actually fire** (i.e., bring reality up to the chunk's claim). This depends on SDK behavior the project does not control — the docstrings explicitly note this is an SDK limitation. Lower preference.

The audit's veto rule applies: do not rewrite this chunk for tense in the same pass that identifies the over-claim. A follow-up chunk should rewrite both the prose and the success criteria together, after confirming the fix-path-1 description matches the implementation.
