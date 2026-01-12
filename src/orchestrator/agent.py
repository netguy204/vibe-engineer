# Chunk: docs/chunks/orch_scheduling - Orchestrator scheduling layer
# Chunk: docs/chunks/orch_verify_active - ACTIVE status verification
# Chunk: docs/chunks/orch_attention_queue - Answer injection on agent resume
"""Agent runner for executing chunk phases.

Uses Claude Agent SDK to run agents for each phase of chunk work.
Each phase is a fresh session - no context carryover between phases.
"""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any

from claude_agent_sdk import query
from claude_agent_sdk.types import (
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
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
            project_dir: The root project directory
        """
        self.project_dir = project_dir.resolve()

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
    ) -> AgentResult:
        """Run a single phase for a chunk.

        Args:
            chunk: Chunk name
            phase: Phase to execute
            worktree_path: Path to the worktree for this chunk
            resume_session_id: Optional session ID to resume
            answer: Optional answer to inject when resuming
            log_callback: Optional callback for logging messages

        Returns:
            AgentResult with outcome of the phase execution
        """
        prompt = self.get_phase_prompt(chunk, phase)

        # Prepend CWD reminder to help agent avoid hallucinating absolute paths
        # Background agents sometimes recall paths from training data instead of
        # using the actual working directory. This explicit reminder helps ground them.
        cwd_reminder = (
            f"**Working Directory:** `{worktree_path}`\n"
            f"Use relative paths (e.g., `docs/chunks/...`) or paths relative to this directory.\n"
            f"Do NOT guess absolute paths from memory - they will be wrong.\n\n"
        )
        prompt = cwd_reminder + prompt

        # Build options - run in bypassPermissions mode for autonomous execution
        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",  # Trust agent in orchestrator context
            max_turns=100,  # Reasonable limit per phase
            setting_sources=["project"],  # Enable project-level skills/commands
        )

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
                    # Check if the result indicates an error
                    result_text = getattr(message, "result", None)
                    is_error = getattr(message, "is_error", False)

                    if is_error:
                        error = result_text or "Agent returned error"
                    elif result_text and _is_error_result(result_text):
                        # Detect error patterns in result text
                        error = result_text
                    else:
                        completed = True

                # Track assistant messages for session_id
                if isinstance(message, AssistantMessage):
                    # Session ID might be in metadata
                    if hasattr(message, "session_id"):
                        session_id = message.session_id

        except Exception as e:
            error = str(e)

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

        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",
            max_turns=20,  # Commits should be quick
            setting_sources=["project"],  # Enable project-level skills/commands
        )

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
                    elif result_text and _is_error_result(result_text):
                        error = result_text
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

        options = ClaudeAgentOptions(
            cwd=str(worktree_path),
            permission_mode="bypassPermissions",
            max_turns=20,  # Should be quick - just editing one file
            setting_sources=["project"],  # Enable project-level skills/commands
            resume=session_id,
        )

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
                    elif result_text and _is_error_result(result_text):
                        error = result_text
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


def _is_error_result(result_text: str) -> bool:
    """Check if a result text indicates an error.

    Args:
        result_text: The result text from the agent

    Returns:
        True if the result appears to be an error
    """
    error_patterns = [
        "Unknown slash command:",
        "Error:",
        "Failed to",
        "Could not",
        "Permission denied",
        "File not found",
    ]
    return any(pattern in result_text for pattern in error_patterns)


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
