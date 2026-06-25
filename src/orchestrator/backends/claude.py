# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - ClaudeBackend: Claude Agent SDK behind the AgentBackend seam
"""Claude Agent SDK backend.

Implements :class:`~orchestrator.backend.AgentBackend` on top of the Claude
Agent SDK. This module is the ONLY place in the orchestrator that imports
``claude_agent_sdk``; everything above the seam (``AgentRunner``, the scheduler)
talks to the backend through :class:`~orchestrator.backend.SessionRequest` and
:class:`~orchestrator.models.AgentResult`.
"""

import re
from pathlib import Path
from typing import Callable, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    tool,
    create_sdk_mcp_server,
)
from claude_agent_sdk.types import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    PreToolUseHookInput,
    SyncHookJSONOutput,
    HookMatcher,
    HookContext,
    McpSdkServerConfig,
)

from orchestrator.backend import (
    AgentBackend,
    LogEvent,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolDecision,
    ToolResultEvent,
    ToolUse,
    is_sandbox_violation,
)
from orchestrator.models import AgentResult, ReviewToolDecision


# Chunk: docs/chunks/orch_reviewer_decision_mcp - ReviewDecision MCP tool
# Define ReviewDecision tool using the @tool decorator
@tool(
    "ReviewDecision",
    "Submit the final review decision for the implementation",
    {
        "type": "object",
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["APPROVE", "FEEDBACK", "ESCALATE"],
                "description": "The review decision",
            },
            "summary": {
                "type": "string",
                "description": "Brief summary of the review findings",
            },
            "criteria_assessment": {
                "type": "array",
                "description": "Optional structured assessment of success criteria",
                "items": {"type": "object"},
            },
            "issues": {
                "type": "array",
                "description": "List of issues for FEEDBACK decisions",
                "items": {"type": "object"},
            },
            "reason": {
                "type": "string",
                "description": "Reason for ESCALATE decisions",
            },
        },
        "required": ["decision", "summary"],
    },
)
async def review_decision_tool(args: dict) -> dict:
    """Handle ReviewDecision tool calls from the reviewer agent.

    The actual decision capture happens by parsing the AssistantMessage tool
    call (PreToolUse hooks do not fire for MCP tools). This handler just returns
    a confirmation message so the agent knows its tool call succeeded.
    """
    decision = args.get("decision", "UNKNOWN")
    return {
        "content": [
            {
                "type": "text",
                "text": f"Review decision '{decision}' recorded successfully.",
            }
        ]
    }


def create_orchestrator_mcp_server() -> McpSdkServerConfig:
    """Create MCP server with orchestrator tools.

    Returns:
        MCP server configuration suitable for ClaudeAgentOptions.mcp_servers
    """
    return create_sdk_mcp_server(
        name="orchestrator",
        version="1.0.0",
        tools=[review_decision_tool],
    )


# Chunk: docs/chunks/orch_sandbox_enforcement - Hook configuration merging
def _merge_hooks(
    *hook_configs: dict[str, list[HookMatcher]],
) -> dict[str, list[HookMatcher]]:
    """Merge multiple hook configurations.

    Combines multiple hook configs into a single config, merging
    matchers for the same event type.

    Args:
        *hook_configs: Variable number of hook configuration dicts

    Returns:
        Merged hook configuration dict
    """
    merged: dict[str, list[HookMatcher]] = {}
    for config in hook_configs:
        for event_type, matchers in config.items():
            if event_type not in merged:
                merged[event_type] = []
            merged[event_type].extend(matchers)
    return merged


# Chunk: docs/chunks/orch_sandbox_enforcement - PreToolUse hook for sandbox isolation
def create_sandbox_enforcement_hook(
    host_repo_path: Path,
    worktree_path: Path,
) -> dict[str, list[HookMatcher]]:
    """Create a PreToolUse hook that enforces sandbox isolation.

    Intercepts Bash commands and blocks those that would escape the
    worktree sandbox. The decision is expressed in the backend-agnostic
    ToolUse/ToolDecision vocabulary and delegated to the shared
    :func:`~orchestrator.backend.is_sandbox_violation` so the Cursor backend can
    enforce the same policy through its own permission mechanism.

    Args:
        host_repo_path: Absolute path to the host repository
        worktree_path: Absolute path to the worktree (agent's sandbox)

    Returns:
        Hook configuration dict suitable for ClaudeAgentOptions.hooks
    """

    async def hook_handler(
        hook_input: PreToolUseHookInput,
        transcript: str | None,
        context: HookContext,
    ) -> SyncHookJSONOutput:
        """Handle PreToolUse events for Bash commands."""
        tool_input = hook_input.get("tool_input", {})
        tool_use = ToolUse(
            tool_name=hook_input.get("tool_name", "Bash"),
            tool_input=tool_input,
            command=tool_input.get("command", ""),
            cwd=hook_input.get("cwd"),
        )

        is_violation, reason = is_sandbox_violation(
            tool_use.command or "", host_repo_path, worktree_path
        )
        decision = ToolDecision.DENY if is_violation else ToolDecision.ALLOW

        if decision is ToolDecision.DENY:
            return SyncHookJSONOutput(
                decision="block",
                reason=reason,
                hookSpecificOutput={
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                },
            )

        # Allow the command to proceed
        return SyncHookJSONOutput(decision="allow")

    # Build the hook matcher for Bash
    hook_matcher: HookMatcher = {
        "matcher": "Bash",
        "hooks": [hook_handler],
        "timeout": None,
    }

    return {"PreToolUse": [hook_matcher]}


# Chunk: docs/chunks/orch_question_forward - PreToolUse hook for intercepting AskUserQuestion calls
def create_question_intercept_hook(
    on_question: Callable[[dict], None],
) -> dict[str, list[HookMatcher]]:
    """Create a PreToolUse hook that intercepts AskUserQuestion calls.

    IMPORTANT: This hook is defined but non-functional. PreToolUse hooks in the
    Claude Agent SDK do not fire for built-in tools like AskUserQuestion. The
    actual capture happens via message parsing in ClaudeBackend.run, which
    extracts AskUserQuestion calls from AssistantMessage content. This hook is
    retained for potential future SDK compatibility and so options.hooks carries
    a matcher for the question flow.

    Args:
        on_question: Callback receiving the extracted question data dict.
            The dict contains: question, options, header, multiSelect.

    Returns:
        Hook configuration dict suitable for ClaudeAgentOptions.hooks
    """

    async def hook_handler(
        hook_input: PreToolUseHookInput,
        transcript: str | None,
        context: HookContext,
    ) -> SyncHookJSONOutput:
        """Handle PreToolUse events for AskUserQuestion."""
        tool_input = hook_input.get("tool_input", {})

        # Extract question data from tool_input
        # AskUserQuestion has a 'questions' array with 1-4 questions
        questions = tool_input.get("questions", [])

        # Build question data - take the first question for primary display,
        # but include all questions in the data
        if questions:
            first_q = questions[0]
            question_data = {
                "question": first_q.get("question", ""),
                "options": first_q.get("options", []),
                "header": first_q.get("header", ""),
                "multiSelect": first_q.get("multiSelect", False),
                "all_questions": questions,  # Include all questions
            }
        else:
            # Fallback if questions array is empty or malformed
            question_data = {
                "question": "Agent asked a question (no details available)",
                "options": [],
                "header": "",
                "multiSelect": False,
                "all_questions": [],
            }

        # Call the callback with extracted data
        on_question(question_data)

        # Return hook output that blocks the tool and stops the agent
        return SyncHookJSONOutput(
            decision="block",
            stopReason="question_queued",
            reason="Question forwarded to attention queue for operator response",
            hookSpecificOutput={
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Question queued for operator",
            },
        )

    # Build the hook matcher for AskUserQuestion
    hook_matcher: HookMatcher = {
        "matcher": "AskUserQuestion",  # Match tool name
        "hooks": [hook_handler],
        "timeout": None,
    }

    return {"PreToolUse": [hook_matcher]}


# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
def create_review_decision_hook(
    on_decision: Callable[[ReviewToolDecision], None],
) -> dict[str, list[HookMatcher]]:
    """Create a PreToolUse hook that intercepts ReviewDecision tool calls.

    IMPORTANT: This hook is defined but non-functional. PreToolUse hooks in the
    Claude Agent SDK do not fire for MCP tools like mcp__orchestrator__ReviewDecision.
    The actual capture happens via message parsing in ClaudeBackend.run, which
    extracts ReviewDecision calls from AssistantMessage content. This hook is
    retained for potential future SDK compatibility.

    Args:
        on_decision: Callback receiving the captured ReviewToolDecision.

    Returns:
        Hook configuration dict suitable for ClaudeAgentOptions.hooks
    """

    async def hook_handler(
        hook_input: PreToolUseHookInput,
        transcript: str | None,
        context: HookContext,
    ) -> SyncHookJSONOutput:
        """Handle PreToolUse events for ReviewDecision."""
        tool_input = hook_input.get("tool_input", {})

        # Extract decision data from tool_input
        decision_str = tool_input.get("decision", "").upper()
        summary = tool_input.get("summary", "No summary provided")
        criteria_assessment = tool_input.get("criteria_assessment")
        issues = tool_input.get("issues")
        reason = tool_input.get("reason")

        # Create the structured decision object
        decision_data = ReviewToolDecision(
            decision=decision_str,
            summary=summary,
            criteria_assessment=criteria_assessment,
            issues=issues,
            reason=reason,
        )

        # Call the callback with the captured decision
        on_decision(decision_data)

        # Return hook output that allows the tool to succeed
        # This tells the agent its tool call was accepted
        return SyncHookJSONOutput(
            decision="allow",
            hookSpecificOutput={
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Review decision captured",
            },
        )

    # Build the hook matcher for ReviewDecision MCP tool
    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Match MCP tool naming convention
    # MCP tools are named mcp__<server>__<tool>, so the full name is
    # mcp__orchestrator__ReviewDecision. We match case-insensitively.
    hook_matcher: HookMatcher = {
        "matcher": re.compile(r"^mcp__orchestrator__ReviewDecision$", re.IGNORECASE),
        "hooks": [hook_handler],
        "timeout": None,
    }

    return {"PreToolUse": [hook_matcher]}


# Chunk: docs/chunks/backend_logparse - Translate SDK messages to normalized LogEvents
def _emit_log_events(message: object, on_log: Callable[[LogEvent], None]) -> None:
    """Translate a Claude SDK message into normalized LogEvent(s) and emit them.

    Each SDK message may produce zero or more LogEvents. Messages that don't
    map to a known event type (dicts, init messages) are silently skipped.
    """
    if isinstance(message, ResultMessage):
        on_log(
            ResultEvent(
                subtype=getattr(message, "subtype", "success"),
                duration_ms=getattr(message, "duration_ms", 0),
                total_cost_usd=getattr(message, "total_cost_usd", 0.0),
                num_turns=getattr(message, "num_turns", 0),
                is_error=getattr(message, "is_error", False),
                session_id=getattr(message, "session_id", None),
                result_text=getattr(message, "result", None),
            )
        )
        return

    if isinstance(message, AssistantMessage):
        if not hasattr(message, "content") or not message.content:
            return
        for block in message.content:
            if hasattr(block, "text") and not hasattr(block, "name"):
                # TextBlock
                on_log(TextEvent(text=block.text))
            elif hasattr(block, "name") and hasattr(block, "id"):
                # ToolUseBlock
                tool_input = getattr(block, "input", {})
                description = tool_input.get("description") if isinstance(tool_input, dict) else None
                on_log(
                    ToolCallEvent(
                        tool_id=block.id,
                        name=block.name,
                        input=tool_input if isinstance(tool_input, dict) else {},
                        description=description,
                    )
                )
        return

    # UserMessage with ToolResultBlocks
    if hasattr(message, "content") and not isinstance(message, dict):
        content = message.content if hasattr(message, "content") else []
        if isinstance(content, list):
            for block in content:
                if hasattr(block, "tool_use_id"):
                    block_content = getattr(block, "content", "")
                    if not isinstance(block_content, str):
                        block_content = str(block_content)
                    on_log(
                        ToolResultEvent(
                            tool_use_id=block.tool_use_id,
                            content=block_content,
                            is_error=getattr(block, "is_error", False),
                        )
                    )


# Chunk: docs/chunks/backend_seam - Claude Agent SDK implementation of AgentBackend
class ClaudeBackend:
    """Runs an agent phase via the Claude Agent SDK (ClaudeSDKClient).

    Translates a :class:`~orchestrator.backend.SessionRequest` into
    ``ClaudeAgentOptions`` (sandbox hook, optional question/review hooks, MCP
    server for the REVIEW phase), runs the SDK client, and normalizes the
    message stream into an :class:`~orchestrator.models.AgentResult`. Question
    and ReviewDecision capture happen by parsing ``AssistantMessage`` content,
    since PreToolUse hooks do not fire for built-in/MCP tools.
    """

    async def run(self, request: SessionRequest) -> AgentResult:
        options = ClaudeAgentOptions(
            cwd=str(request.cwd),
            permission_mode="bypassPermissions",  # Trust agent in orchestrator context
            max_turns=request.max_turns,
            setting_sources=["project"],  # Enable project-level skills/commands
            env=request.env,  # Restrict git operations to worktree
            max_buffer_size=10 * 1024 * 1024,  # 10MB - default 1MB too small for COMPLETE phase
        )
        if request.allowed_tools:
            options.allowed_tools = list(request.allowed_tools)
        if request.resume_session_id:
            options.resume = request.resume_session_id

        # Captured outcomes. The question/review hooks are non-functional in real
        # SDK runs (PreToolUse hooks don't fire for built-in/MCP tools), so the
        # message parsing below is the live capture path. The hook wrappers set
        # these too so the structurally-present hooks still capture if they fire.
        captured_question: Optional[dict] = None
        captured_review_decision: Optional[ReviewToolDecision] = None
        session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False

        def handle_question(question_data: dict) -> None:
            nonlocal captured_question
            captured_question = question_data
            if request.on_question:
                request.on_question(question_data)

        def handle_review_decision(decision: ReviewToolDecision) -> None:
            nonlocal captured_review_decision
            captured_review_decision = decision
            if request.on_review_decision:
                request.on_review_decision(decision)

        # Always enforce the sandbox; merge in question/review hooks when wired.
        all_hooks = create_sandbox_enforcement_hook(
            host_repo_path=request.host_repo_path,
            worktree_path=request.cwd,
        )
        if request.on_question:
            all_hooks = _merge_hooks(
                all_hooks, create_question_intercept_hook(handle_question)
            )
        if request.on_review_decision:
            all_hooks = _merge_hooks(
                all_hooks, create_review_decision_hook(handle_review_decision)
            )
        options.hooks = all_hooks

        # The ReviewDecision MCP tool is only needed during the REVIEW phase.
        if request.expose_review_tool:
            options.mcp_servers = {"orchestrator": create_orchestrator_mcp_server()}
            options.allowed_tools.append("mcp__orchestrator__ReviewDecision")

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(request.prompt)
                async for message in client.receive_response():
                    if request.on_log:
                        _emit_log_events(message, request.on_log)

                    # Capture session_id from init messages
                    if isinstance(message, dict):
                        if message.get("type") == "init":
                            session_id = message.get("session_id")

                    if isinstance(message, ResultMessage):
                        # The is_error flag is authoritative - we do not parse result text
                        result_text = getattr(message, "result", None)
                        is_error = getattr(message, "is_error", False)

                        if is_error:
                            error = result_text or "Agent returned error"
                        else:
                            completed = True

                        if hasattr(message, "session_id") and message.session_id:
                            session_id = message.session_id

                    if isinstance(message, AssistantMessage):
                        if hasattr(message, "session_id") and message.session_id:
                            session_id = message.session_id

                        # Capture ReviewDecision tool calls from message content.
                        # PreToolUse hooks don't fire for MCP tools, so we capture
                        # the tool call directly from the AssistantMessage instead.
                        if (
                            captured_review_decision is None
                            and request.expose_review_tool
                            and hasattr(message, "content")
                            and message.content
                        ):
                            for block in message.content:
                                if (
                                    hasattr(block, "name")
                                    and block.name == "mcp__orchestrator__ReviewDecision"
                                ):
                                    tool_input = getattr(block, "input", {})
                                    if tool_input:
                                        captured_review_decision = ReviewToolDecision(
                                            decision=tool_input.get("decision", "").upper(),
                                            summary=tool_input.get("summary", ""),
                                            criteria_assessment=tool_input.get(
                                                "criteria_assessment"
                                            ),
                                            issues=tool_input.get("issues"),
                                            reason=tool_input.get("reason"),
                                        )
                                        if request.on_review_decision:
                                            request.on_review_decision(captured_review_decision)
                                        break  # Only capture first call

                        # Capture AskUserQuestion from AssistantMessage content.
                        # PreToolUse hooks don't fire for built-in tools either.
                        if (
                            captured_question is None
                            and hasattr(message, "content")
                            and message.content
                        ):
                            for block in message.content:
                                if hasattr(block, "name") and block.name == "AskUserQuestion":
                                    tool_input = getattr(block, "input", {})
                                    if tool_input:
                                        questions = tool_input.get("questions", [])
                                        if questions:
                                            first_q = questions[0]
                                            captured_question = {
                                                "question": first_q.get("question", ""),
                                                "options": first_q.get("options", []),
                                                "header": first_q.get("header", ""),
                                                "multiSelect": first_q.get("multiSelect", False),
                                                "all_questions": questions,
                                            }
                                        else:
                                            captured_question = {
                                                "question": "Agent asked a question (no details available)",
                                                "options": [],
                                                "header": "",
                                                "multiSelect": False,
                                                "all_questions": [],
                                            }
                                    else:
                                        captured_question = {
                                            "question": "Agent asked a question (no details available)",
                                            "options": [],
                                            "header": "",
                                            "multiSelect": False,
                                            "all_questions": [],
                                        }
                                    if request.on_question:
                                        request.on_question(captured_question)
                                    break  # Only capture first call

        except Exception as e:
            error = str(e)

        # If a question was captured, the agent was suspended waiting for an answer
        if captured_question:
            return AgentResult(
                completed=False,
                suspended=True,
                session_id=session_id,
                question=captured_question,
            )

        if error:
            return AgentResult(
                completed=False,
                suspended=False,
                session_id=session_id,
                error=error,
                review_decision=captured_review_decision,
            )

        return AgentResult(
            completed=completed,
            suspended=False,
            session_id=session_id,
            review_decision=captured_review_decision,
        )


# Assert ClaudeBackend satisfies the AgentBackend protocol at import time.
_: AgentBackend = ClaudeBackend()
