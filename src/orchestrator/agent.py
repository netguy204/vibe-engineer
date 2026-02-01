# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - Agent spawning and phase execution
# Chunk: docs/chunks/orch_verify_active - Resume agent session for ACTIVE status marking
"""Agent runner for executing chunk phases.

Uses Claude Agent SDK to run agents for each phase of chunk work.
Each phase is a fresh session - no context carryover between phases.
"""

import asyncio
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Callable

from claude_agent_sdk import (
    query,  # Keep for backwards compatibility in deprecated methods
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

from orchestrator.models import AgentResult, ReviewToolDecision, WorkUnitPhase


class AgentRunnerError(Exception):
    """Exception raised for agent execution errors."""

    pass


# Mapping from phase to skill file name
PHASE_SKILL_FILES = {
    WorkUnitPhase.GOAL: "chunk-create.md",
    WorkUnitPhase.PLAN: "chunk-plan.md",
    WorkUnitPhase.IMPLEMENT: "chunk-implement.md",
    WorkUnitPhase.REVIEW: "chunk-review.md",
    WorkUnitPhase.COMPLETE: "chunk-complete.md",
}


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

    The actual decision capture happens via the PreToolUse hook which fires
    before this handler. This handler just returns a confirmation message
    so the agent knows its tool call succeeded.
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


# Chunk: docs/chunks/orch_sandbox_enforcement - Sandbox violation detection logic
def _is_sandbox_violation(
    command: str,
    host_repo_path: Path,
    worktree_path: Path,
) -> tuple[bool, str | None]:
    """Check if a command violates sandbox rules.

    Detects commands that would escape the worktree sandbox and access
    the host repository or other forbidden locations.

    Args:
        command: The bash command string to check
        host_repo_path: Absolute path to the host repository (where orchestrator runs)
        worktree_path: Absolute path to the worktree (agent's sandbox)

    Returns:
        Tuple of (is_violation, reason) where reason explains the violation.
    """
    host_str = str(host_repo_path)
    worktree_str = str(worktree_path)

    # Normalize paths for consistent comparison
    host_str = host_str.rstrip("/")
    worktree_str = worktree_str.rstrip("/")

    # Pattern 1: Direct cd to host repo (with or without quotes)
    # Matches: cd /path/to/host, cd '/path/to/host', cd "/path/to/host"
    # Must be exact match (with optional trailing slash), not a prefix of worktree path
    cd_patterns = [
        f"cd {host_str}",
        f"cd '{host_str}'",
        f'cd "{host_str}"',
        f"cd {host_str}/",
        f"cd '{host_str}/'",
        f'cd "{host_str}/"',
    ]
    for pattern in cd_patterns:
        if pattern in command:
            # Make sure this isn't actually a path within the worktree
            # (e.g., cd /host/path/.ve/chunks/test/worktree should be allowed)
            cd_target_match = re.search(r"cd\s+['\"]?([^'\"\s]+)['\"]?", command)
            if cd_target_match:
                cd_target = cd_target_match.group(1).rstrip("/")
                # If the target is within the worktree, it's safe
                if cd_target.startswith(worktree_str):
                    continue
            return (True, f"Blocked: cd to host repository path ({host_str})")

    # Pattern 2: Git commands with -C flag pointing to host repo
    # Matches: git -C /path/to/host ..., git -C '/path/to/host' ...
    git_c_patterns = [
        f"git -C {host_str}",
        f"git -C '{host_str}'",
        f'git -C "{host_str}"',
    ]
    for pattern in git_c_patterns:
        if pattern in command:
            return (True, f"Blocked: git -C targeting host repository ({host_str})")

    # Pattern 3: Any git command containing host repo path as argument
    # This catches things like: git --git-dir=/host/path/.git
    # But allow paths within the worktree (which may contain the host path as prefix)
    if "git " in command and host_str in command:
        # Check if the reference is to a path within the worktree
        # If the command references the worktree path, it's allowed
        if worktree_str not in command:
            return (True, f"Blocked: git command references host repository path ({host_str})")

    # Pattern 4: cd to absolute path outside worktree
    # Match cd followed by absolute path
    cd_abs_pattern = re.compile(r"cd\s+['\"]?(/[^'\"\s]+)['\"]?")
    for match in cd_abs_pattern.finditer(command):
        target_path = match.group(1).rstrip("/")
        # Allow paths within worktree
        if target_path.startswith(worktree_str):
            continue
        # Allow common system paths that agents might need
        safe_prefixes = ["/tmp", "/var/tmp", "/dev"]
        if any(target_path.startswith(p) for p in safe_prefixes):
            continue
        # Block cd to other absolute paths
        return (True, f"Blocked: cd to absolute path outside worktree ({target_path})")

    return (False, None)


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
    worktree sandbox (e.g., cd to host repo, git commands on host repo).

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
        command = tool_input.get("command", "")

        is_violation, reason = _is_sandbox_violation(
            command, host_repo_path, worktree_path
        )

        if is_violation:
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

    When AskUserQuestion is called, extracts the question data and calls
    on_question callback, then returns a result that blocks the tool and
    stops the agent loop.

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

    When the reviewer agent calls the ReviewDecision tool, this hook captures
    the decision data and allows the tool to succeed from the agent's perspective.
    The captured decision is then available for the scheduler to route the work unit.

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


def _load_skill_content(skill_path: Path) -> str:
    """Load skill content from a file, stripping YAML frontmatter.

    Args:
        skill_path: Path to the skill file

    Returns:
        Skill content without YAML frontmatter

    Raises:
        FileNotFoundError: If skill file doesn't exist
    """
    content = skill_path.read_text()

    # Strip YAML frontmatter (content between --- markers at start)
    frontmatter_pattern = r"^---\n.*?\n---\n"
    content = re.sub(frontmatter_pattern, "", content, flags=re.DOTALL)

    return content.strip()


class AgentRunner:
    """Runs agents for chunk phase execution.

    Each phase invocation creates a fresh agent session.
    The agent runs in the chunk's worktree directory.
    """

    # Chunk: docs/chunks/orch_sandbox_enforcement - Store host_repo_path for sandbox enforcement
    def __init__(self, project_dir: Path):
        """Initialize the agent runner.

        Args:
            project_dir: The root project directory (host repo path)
        """
        self.project_dir = project_dir.resolve()
        self.host_repo_path = self.project_dir

    def get_skill_path(self, phase: WorkUnitPhase) -> Path:
        """Get the path to the skill file for a phase.

        Args:
            phase: The work unit phase

        Returns:
            Path to the skill file
        """
        skill_file = PHASE_SKILL_FILES[phase]
        return self.project_dir / ".claude" / "commands" / skill_file

    def get_phase_prompt(self, chunk: str, phase: WorkUnitPhase) -> str:
        """Build the prompt for a phase execution.

        Loads the skill content from the .claude/commands/ directory and
        injects any necessary arguments.

        Args:
            chunk: Chunk name
            phase: The work unit phase

        Returns:
            Prompt string for the agent

        Raises:
            FileNotFoundError: If the skill file doesn't exist
        """
        skill_path = self.get_skill_path(phase)
        skill_content = _load_skill_content(skill_path)

        if phase == WorkUnitPhase.GOAL:
            # For GOAL phase, replace $ARGUMENTS with chunk context
            # Since we're refining an existing FUTURE chunk, provide context
            arguments = f"Refine the GOAL.md for existing chunk: {chunk}"
            skill_content = skill_content.replace("$ARGUMENTS", arguments)

        return skill_content

    # Chunk: docs/chunks/orch_question_forward - Accepts question_callback and configures hook to capture questions
    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Migrate to ClaudeSDKClient for hooks and MCP tools
    async def run_phase(
        self,
        chunk: str,
        phase: WorkUnitPhase,
        worktree_path: Path,
        resume_session_id: Optional[str] = None,
        answer: Optional[str] = None,
        log_callback: Optional[callable] = None,
        question_callback: Optional[Callable[[dict], None]] = None,
        review_decision_callback: Optional[Callable[[ReviewToolDecision], None]] = None,
    ) -> AgentResult:
        """Run a single phase for a chunk.

        Uses ClaudeSDKClient for agent execution, which enables:
        - Hooks for intercepting tool calls (AskUserQuestion, ReviewDecision)
        - Custom MCP tools (ReviewDecision for REVIEW phase)
        - Session continuity for resume

        Args:
            chunk: Chunk name
            phase: Phase to execute
            worktree_path: Path to the worktree for this chunk
            resume_session_id: Optional session ID to resume
            answer: Optional answer to inject when resuming
            log_callback: Optional callback for logging messages
            question_callback: Optional callback for capturing AskUserQuestion calls.
                When provided, configures a hook to intercept questions and suspend
                the agent. The callback receives the question data dict.
            review_decision_callback: Optional callback for capturing ReviewDecision tool calls.
                When provided, configures a hook to intercept review decisions during
                the REVIEW phase. The callback receives the ReviewToolDecision data.

        Returns:
            AgentResult with outcome of the phase execution
        """
        prompt = self.get_phase_prompt(chunk, phase)

        # Prepend CWD reminder with sandbox rules to help agent stay isolated
        cwd_reminder = (
            f"**Working Directory:** `{worktree_path}`\n"
            f"Use relative paths (e.g., `docs/chunks/...`) or paths relative to this directory.\n"
            f"Do NOT guess absolute paths from memory - they will be wrong.\n\n"
            f"## SANDBOX RULES (CRITICAL)\n\n"
            f"You are operating in an isolated git worktree. You MUST:\n"
            f"- NEVER use `cd` with absolute paths outside this directory\n"
            f"- NEVER run git commands targeting the host repository\n"
            f"- ALWAYS use relative paths from the current worktree\n"
            f"- ONLY commit to the current branch in this worktree\n\n"
            f"Violations will be blocked and logged.\n\n"
        )
        prompt = cwd_reminder + prompt

        # Set GIT_DIR and GIT_WORK_TREE to restrict git operations to the worktree
        env = os.environ.copy()
        env["GIT_DIR"] = str(worktree_path / ".git")
        env["GIT_WORK_TREE"] = str(worktree_path)

        # Build options - run in bypassPermissions mode for autonomous execution
        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",  # Trust agent in orchestrator context
            max_turns=100,  # Reasonable limit per phase
            setting_sources=["project"],  # Enable project-level skills/commands
            env=env,  # Restrict git operations to worktree
        )

        # Always add sandbox hook to prevent agents from escaping worktree
        sandbox_hooks = create_sandbox_enforcement_hook(
            host_repo_path=self.host_repo_path,
            worktree_path=worktree_path,
        )

        # Track captured question data for building result
        captured_question: dict | None = None
        # Track captured review decision from ReviewDecision MCP tool call
        captured_review_decision: ReviewToolDecision | None = None

        # Start with sandbox hooks
        all_hooks = sandbox_hooks

        if question_callback:
            # Create hook that intercepts AskUserQuestion and captures data
            def on_question(question_data: dict) -> None:
                nonlocal captured_question
                captured_question = question_data
                question_callback(question_data)

            question_hooks = create_question_intercept_hook(on_question)
            all_hooks = _merge_hooks(all_hooks, question_hooks)

        # Chunk: docs/chunks/orch_reviewer_decision_mcp - Hook for ReviewDecision MCP tool
        if review_decision_callback:
            # Create hook that intercepts ReviewDecision MCP tool calls
            def on_review_decision(decision_data: ReviewToolDecision) -> None:
                nonlocal captured_review_decision
                captured_review_decision = decision_data
                review_decision_callback(decision_data)

            review_hooks = create_review_decision_hook(on_review_decision)
            all_hooks = _merge_hooks(all_hooks, review_hooks)

        options.hooks = all_hooks

        # Chunk: docs/chunks/orch_reviewer_decision_mcp - Add MCP server for REVIEW phase
        # The ReviewDecision tool is only needed during REVIEW phase
        if phase == WorkUnitPhase.REVIEW:
            mcp_server = create_orchestrator_mcp_server()
            options.mcp_servers = {"orchestrator": mcp_server}
            # Allow the ReviewDecision MCP tool
            options.allowed_tools.append("mcp__orchestrator__ReviewDecision")

        # Handle resume with answer
        if resume_session_id:
            options.resume = resume_session_id
            if answer:
                # Prepend answer to prompt when resuming
                prompt = f"User answer: {answer}\n\n{prompt}"

        session_id: Optional[str] = None
        error: Optional[str] = None
        result_text: Optional[str] = None
        completed = False

        # Chunk: docs/chunks/orch_reviewer_decision_mcp - Use ClaudeSDKClient instead of query()
        # ClaudeSDKClient supports hooks and custom MCP tools, unlike query()
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    # Log message if callback provided
                    if log_callback:
                        log_callback(message)

                    # Capture session_id from init messages
                    if isinstance(message, dict):
                        if message.get("type") == "init":
                            session_id = message.get("session_id")

                    # Check for result message (completion)
                    if isinstance(message, ResultMessage):
                        # Check if the result indicates an error using SDK's is_error flag
                        # The is_error flag is authoritative - we do not parse result text
                        result_text = getattr(message, "result", None)
                        is_error = getattr(message, "is_error", False)

                        if is_error:
                            error = result_text or "Agent returned error"
                        else:
                            completed = True

                        # ResultMessage may contain session_id
                        if hasattr(message, "session_id") and message.session_id:
                            session_id = message.session_id

                    # Track assistant messages for session_id and ReviewDecision tool calls
                    if isinstance(message, AssistantMessage):
                        # Session ID might be in metadata
                        if hasattr(message, "session_id") and message.session_id:
                            session_id = message.session_id

                        # Capture ReviewDecision tool calls from message content
                        # Note: PreToolUse hooks don't fire for MCP tools, so we capture
                        # the tool call directly from the AssistantMessage instead.
                        if (
                            captured_review_decision is None
                            and phase == WorkUnitPhase.REVIEW
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
                                        if review_decision_callback:
                                            review_decision_callback(captured_review_decision)
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

        # Build result
        if error:
            return AgentResult(
                completed=False,
                suspended=False,
                session_id=session_id,
                error=error,
                review_decision=captured_review_decision,
            )
        else:
            return AgentResult(
                completed=completed,
                suspended=False,
                session_id=session_id,
                review_decision=captured_review_decision,
            )

    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Removed deprecated run_commit() method
    # The orchestrator scheduler now uses WorktreeManager.commit_changes() for
    # mechanical commits instead of the agent-based approach.

    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Migrate to ClaudeSDKClient
    async def resume_for_active_status(
        self,
        chunk: str,
        worktree_path: Path,
        session_id: str,
        log_callback: Optional[callable] = None,
    ) -> AgentResult:
        """Resume an agent session to complete ACTIVE status marking.

        Called when /chunk-complete finished but the GOAL.md status was not
        updated to ACTIVE. This resumes the session with a targeted reminder.

        Uses ClaudeSDKClient for agent execution, which enables hooks (e.g.,
        sandbox enforcement) to work properly.

        Args:
            chunk: Chunk name
            worktree_path: Path to the worktree
            session_id: Session ID from the original COMPLETE phase run
            log_callback: Optional callback for logging messages

        Returns:
            AgentResult with outcome of the resume
        """
        prompt = (
            "The /chunk-complete command finished but the chunk's GOAL.md status was "
            "not updated to ACTIVE. Please complete the final step:\n\n"
            "1. Open the chunk's GOAL.md file\n"
            "2. Change the frontmatter `status: IMPLEMENTING` to `status: ACTIVE`\n"
            "3. Remove the large comment block that starts with "
            "'DO NOT DELETE THIS COMMENT BLOCK'\n\n"
            "This is the final step to complete the chunk."
        )

        env = os.environ.copy()
        env["GIT_DIR"] = str(worktree_path / ".git")
        env["GIT_WORK_TREE"] = str(worktree_path)

        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",
            max_turns=20,  # Should be quick - just editing one file
            setting_sources=["project"],  # Enable project-level skills/commands
            resume=session_id,
            env=env,  # Restrict git operations to worktree
        )

        sandbox_hooks = create_sandbox_enforcement_hook(
            host_repo_path=self.host_repo_path,
            worktree_path=worktree_path,
        )
        options.hooks = sandbox_hooks

        new_session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False

        # Use ClaudeSDKClient for session management and hooks support
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    if log_callback:
                        log_callback(message)

                    if isinstance(message, dict):
                        if message.get("type") == "init":
                            new_session_id = message.get("session_id")

                    if isinstance(message, ResultMessage):
                        result_text = getattr(message, "result", None)
                        is_error = getattr(message, "is_error", False)

                        if is_error:
                            error = result_text or "Resume returned error"
                        else:
                            completed = True

                        # ResultMessage may contain session_id
                        if hasattr(message, "session_id") and message.session_id:
                            new_session_id = message.session_id

                    if isinstance(message, AssistantMessage):
                        if hasattr(message, "session_id") and message.session_id:
                            new_session_id = message.session_id

        except Exception as e:
            error = str(e)

        if error:
            return AgentResult(
                completed=False,
                suspended=False,
                session_id=new_session_id or session_id,
                error=error,
            )
        else:
            return AgentResult(
                completed=completed,
                suspended=False,
                session_id=new_session_id or session_id,
            )


def create_log_callback(chunk: str, phase: WorkUnitPhase, log_dir: Path):
    """Create a logging callback for agent execution.

    Args:
        chunk: Chunk name
        phase: Current phase
        log_dir: Directory for log files

    Returns:
        Callback function for logging messages
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{phase.value.lower()}.txt"

    def callback(message: Any) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        message_str = str(message)

        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {message_str}\n")

    return callback
