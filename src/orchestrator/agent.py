# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_question_forward - AskUserQuestion forwarding to attention queue
# Chunk: docs/chunks/orch_sandbox_enforcement - Sandbox enforcement via hooks
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

from claude_agent_sdk import query
from claude_agent_sdk.types import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    PreToolUseHookInput,
    SyncHookJSONOutput,
    HookMatcher,
    HookContext,
)

from orchestrator.models import AgentResult, WorkUnitPhase


class AgentRunnerError(Exception):
    """Exception raised for agent execution errors."""

    pass


# Mapping from phase to skill file name
PHASE_SKILL_FILES = {
    WorkUnitPhase.GOAL: "chunk-create.md",
    WorkUnitPhase.PLAN: "chunk-plan.md",
    WorkUnitPhase.IMPLEMENT: "chunk-implement.md",
    WorkUnitPhase.COMPLETE: "chunk-complete.md",
}


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

    async def run_phase(
        self,
        chunk: str,
        phase: WorkUnitPhase,
        worktree_path: Path,
        resume_session_id: Optional[str] = None,
        answer: Optional[str] = None,
        log_callback: Optional[callable] = None,
        question_callback: Optional[Callable[[dict], None]] = None,
    ) -> AgentResult:
        """Run a single phase for a chunk.

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

        if question_callback:
            # Create hook that intercepts AskUserQuestion and captures data
            def on_question(question_data: dict) -> None:
                nonlocal captured_question
                captured_question = question_data
                question_callback(question_data)

            question_hooks = create_question_intercept_hook(on_question)
            # Merge sandbox and question hooks
            options.hooks = _merge_hooks(sandbox_hooks, question_hooks)
        else:
            options.hooks = sandbox_hooks

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

        try:
            async for message in query(prompt=prompt, options=options):
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

                # Track assistant messages for session_id
                if isinstance(message, AssistantMessage):
                    # Session ID might be in metadata
                    if hasattr(message, "session_id"):
                        session_id = message.session_id

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
            )
        else:
            return AgentResult(
                completed=completed,
                suspended=False,
                session_id=session_id,
            )

    async def run_commit(
        self,
        chunk: str,
        worktree_path: Path,
        log_callback: Optional[callable] = None,
    ) -> AgentResult:
        """Run the /chunk-commit skill to commit changes with proper conventional commit message.

        .. deprecated::
            The orchestrator scheduler now uses WorktreeManager.commit_changes() for
            mechanical commits instead of this agent-based approach. This method is
            kept for potential manual use cases or debugging, but may be removed in
            a future version.

        Args:
            chunk: Chunk name (for logging)
            worktree_path: Path to the worktree
            log_callback: Optional callback for logging messages

        Returns:
            AgentResult with outcome of the commit
        """
        # Load the chunk-commit skill content (more task-specific than generic commit)
        commit_skill_path = self.project_dir / ".claude" / "commands" / "chunk-commit.md"
        if not commit_skill_path.exists():
            # Fall back to a simple commit instruction if skill doesn't exist
            prompt = f"Please commit all changes for chunk {chunk} with a proper conventional commit message describing what was done."
        else:
            prompt = _load_skill_content(commit_skill_path)

        env = os.environ.copy()
        env["GIT_DIR"] = str(worktree_path / ".git")
        env["GIT_WORK_TREE"] = str(worktree_path)

        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",
            max_turns=20,  # Commits should be quick
            setting_sources=["project"],  # Enable project-level skills/commands
            env=env,  # Restrict git operations to worktree
        )

        sandbox_hooks = create_sandbox_enforcement_hook(
            host_repo_path=self.host_repo_path,
            worktree_path=worktree_path,
        )
        options.hooks = sandbox_hooks

        session_id: Optional[str] = None
        error: Optional[str] = None
        completed = False

        try:
            async for message in query(prompt=prompt, options=options):
                if log_callback:
                    log_callback(message)

                if isinstance(message, dict):
                    if message.get("type") == "init":
                        session_id = message.get("session_id")

                if isinstance(message, ResultMessage):
                    result_text = getattr(message, "result", None)
                    is_error = getattr(message, "is_error", False)

                    if is_error:
                        error = result_text or "Commit returned error"
                    else:
                        completed = True

                if isinstance(message, AssistantMessage):
                    if hasattr(message, "session_id"):
                        session_id = message.session_id

        except Exception as e:
            error = str(e)

        if error:
            return AgentResult(
                completed=False,
                suspended=False,
                session_id=session_id,
                error=error,
            )
        else:
            return AgentResult(
                completed=completed,
                suspended=False,
                session_id=session_id,
            )

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

        try:
            async for message in query(prompt=prompt, options=options):
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

                if isinstance(message, AssistantMessage):
                    if hasattr(message, "session_id"):
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
