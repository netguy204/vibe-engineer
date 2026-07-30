# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - Agent spawning and phase execution
# Chunk: docs/chunks/orch_verify_active - Resume agent session for ACTIVE status marking
# Chunk: docs/chunks/backend_seam - Runs phases through a pluggable AgentBackend
"""Agent runner for executing chunk phases.

Runs each chunk phase through a pluggable ``AgentBackend`` (default:
``ClaudeBackend``). The runner owns the backend-agnostic concerns — prompt
assembly, worktree env setup, and orchestrator policy callbacks — and delegates
agent execution, sandbox enforcement, question/ReviewDecision capture, and
session resume to the backend. Each phase is a fresh session: no context
carryover between phases.
"""

import json
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from orchestrator.backend import (
    AgentBackend,
    LogEvent,
    ResultEvent,
    SessionRequest,
    TextEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from orchestrator.backends.claude import ClaudeBackend
from orchestrator.models import AgentResult, OrchestratorConfig, ReviewToolDecision, WorkUnitPhase


class AgentRunnerError(Exception):
    """Exception raised for agent execution errors."""

    pass


# Chunk: docs/chunks/orch_review_phase - Added chunk-review.md as skill for REVIEW phase
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE skill for pre-review trunk integration
# Mapping from phase to skill file name
PHASE_SKILL_FILES = {
    WorkUnitPhase.GOAL: "chunk-create",
    WorkUnitPhase.PLAN: "chunk-plan",
    WorkUnitPhase.IMPLEMENT: "chunk-implement",
    WorkUnitPhase.REBASE: "chunk-rebase",
    WorkUnitPhase.REVIEW: "chunk-review",
    WorkUnitPhase.COMPLETE: "chunk-complete",
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

    # Chunk: docs/chunks/orch_sandbox_enforcement - Store host_repo_path for sandbox enforcement
    # Chunk: docs/chunks/orch_max_turns_config - Accept config for per-phase turn budgets
    # Chunk: docs/chunks/backend_seam - Accept a pluggable AgentBackend (default: ClaudeBackend)
    def __init__(
        self,
        project_dir: Path,
        config: Optional[OrchestratorConfig] = None,
        backend: Optional[AgentBackend] = None,
    ):
        """Initialize the agent runner.

        Args:
            project_dir: The root project directory (host repo path)
            config: Orchestrator config used for per-phase turn budgets.
                Defaults to a fresh OrchestratorConfig (today's literal values).
            backend: Agent backend used to execute phases. Defaults to
                ClaudeBackend (Claude Agent SDK).
        """
        self.project_dir = project_dir.resolve()
        self.host_repo_path = self.project_dir
        self.config = config if config is not None else OrchestratorConfig()
        self.backend: AgentBackend = backend if backend is not None else ClaudeBackend()

    # Chunk: docs/chunks/plugin_legacy_migration - Phase prompts ship with the
    # vibe-engineer package (plugin command sources), not with the target project
    def get_skill_path(self, phase: WorkUnitPhase) -> Path:
        """Get the path to the phase-prompt source file for a phase.

        Phase prompts are the plugin command sources (DEC-010). They ship
        with the vibe-engineer package: an installed wheel carries them as
        package data at orchestrator/skills/<name>.md (hatch force-include
        of the repo-root commands/ directory). In a development checkout
        (editable install), the force-include is not materialized, so we
        fall back to the repo-root commands/ directory.

        The target project's layout is irrelevant: since plugin-based
        distribution, projects no longer carry .agents/skills/ content.

        Args:
            phase: The work unit phase

        Returns:
            Path to the phase-prompt markdown file
        """
        skill_name = PHASE_SKILL_FILES[phase]

        # Installed package: commands/ force-included as orchestrator/skills/
        packaged = Path(__file__).resolve().parent / "skills" / f"{skill_name}.md"
        if packaged.is_file():
            return packaged

        # Development checkout: src/orchestrator/agent.py -> repo root
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "commands" / f"{skill_name}.md"

    def get_phase_prompt(self, chunk: str, phase: WorkUnitPhase) -> str:
        """Build the prompt for a phase execution.

        Loads the phase-prompt content shipped with the vibe-engineer
        package and injects any necessary arguments.

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

    # Chunk: docs/chunks/orch_question_forward - Accepts question_callback to capture questions
    # Chunk: docs/chunks/orch_attention_queue - Accept and inject answer parameter when resuming sessions
    # Chunk: docs/chunks/orch_implement_reentry_prompt - Accept reentry_context for IMPLEMENT re-entry prompt injection
    # Chunk: docs/chunks/backend_seam - Build a SessionRequest and delegate to the AgentBackend
    async def run_phase(
        self,
        chunk: str,
        phase: WorkUnitPhase,
        worktree_path: Path,
        resume_session_id: Optional[str] = None,
        answer: Optional[str] = None,
        reentry_context: Optional[str] = None,
        log_callback: Optional[callable] = None,
        question_callback: Optional[Callable[[dict], None]] = None,
        review_decision_callback: Optional[Callable[[ReviewToolDecision], None]] = None,
    ) -> AgentResult:
        """Run a single phase for a chunk.

        Builds the phase prompt and a SessionRequest, then delegates execution to
        the configured AgentBackend. The backend owns agent invocation, sandbox
        enforcement, question/ReviewDecision capture, and session resume.

        Args:
            chunk: Chunk name
            phase: Phase to execute
            worktree_path: Path to the worktree for this chunk
            resume_session_id: Optional session ID to resume
            answer: Optional answer to inject when resuming
            reentry_context: Optional context string explaining why the IMPLEMENT
                phase is being re-entered. Injected into the prompt so the implementer
                understands what needs to be addressed.
            log_callback: Optional callback for logging messages
            question_callback: Optional callback for capturing AskUserQuestion calls.
                When provided, the backend forwards questions and suspends the agent.
                The callback receives the question data dict.
            review_decision_callback: Optional callback for capturing ReviewDecision
                tool calls during the REVIEW phase. The callback receives the
                ReviewToolDecision data.

        Returns:
            AgentResult with outcome of the phase execution
        """
        prompt = self.get_phase_prompt(chunk, phase)

        # Chunk: docs/chunks/orch_review_feedback_fidelity - Inject review feedback into implementer prompt
        # If re-implementing after FEEDBACK, inject the review feedback content
        # so it's the FIRST thing in the prompt, maximizing visibility
        if phase == WorkUnitPhase.IMPLEMENT:
            feedback_path = worktree_path / "docs" / "chunks" / chunk / "REVIEW_FEEDBACK.md"
            if feedback_path.exists():
                feedback_content = feedback_path.read_text()
                feedback_header = (
                    "## Prior Review Feedback (MUST ADDRESS)\n\n"
                    "The following feedback was provided by the reviewer. "
                    "You MUST address EVERY issue listed below. For each issue, either:\n"
                    "- Fix it in the code\n"
                    "- Defer it with a clear reason why it cannot be addressed now\n"
                    "- Dispute it with evidence for why the current approach is correct\n\n"
                    "Do NOT skip any items. Non-functional feedback (documentation, style, "
                    "naming) is equally important as functional feedback.\n\n"
                )
                prompt = feedback_header + feedback_content + "\n\n---\n\n" + prompt

        # Chunk: docs/chunks/orch_implement_reentry_prompt - Inject re-entry context for IMPLEMENT phase
        # This provides the implementer with context about WHY it's being re-entered,
        # covering paths like unaddressed feedback reroute and other non-review re-entries.
        if phase == WorkUnitPhase.IMPLEMENT and reentry_context:
            reentry_header = (
                "## Re-entry Context\n\n"
                "You are re-entering the IMPLEMENT phase. Here is why:\n\n"
                f"{reentry_context}\n\n"
                "Address the above before doing any other work.\n\n"
                "---\n\n"
            )
            prompt = reentry_header + prompt

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

        # Inject operator answer into prompt. This applies both when resuming a
        # suspended session (question flow) and when starting a fresh session
        # after ESCALATE (where session_id is None but the operator answered via
        # the attention queue).
        if answer:
            prompt = f"Operator feedback: {answer}\n\n{prompt}"

        request = SessionRequest(
            prompt=prompt,
            cwd=worktree_path,
            host_repo_path=self.host_repo_path,
            env=env,
            max_turns=self.config.max_turns_implement,
            resume_session_id=resume_session_id,
            expose_review_tool=(phase == WorkUnitPhase.REVIEW),
            on_question=question_callback,
            on_review_decision=review_decision_callback,
            on_log=log_callback,
        )

        return await self.backend.run(request)

    # Chunk: docs/chunks/orch_reviewer_decision_mcp - Removed deprecated run_commit() method
    # The orchestrator scheduler now uses WorktreeManager.commit_changes() for
    # mechanical commits instead of the agent-based approach.

    # Chunk: docs/chunks/backend_seam - Delegate resume to the AgentBackend
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

        Builds a resume SessionRequest and delegates to the configured
        AgentBackend, which enforces the sandbox during the fixup.

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

        request = SessionRequest(
            prompt=prompt,
            cwd=worktree_path,
            host_repo_path=self.host_repo_path,
            env=env,
            max_turns=self.config.max_turns_complete,
            resume_session_id=session_id,
            on_log=log_callback,
        )

        result = await self.backend.run(request)

        # Preserve the original session_id when the backend captured none.
        if not result.session_id:
            return result.model_copy(update={"session_id": session_id})
        return result


# Chunk: docs/chunks/backend_logparse - JSON-line log serialization

# Map event classes to their JSON type tag
_EVENT_TYPE_TAG: dict[type, str] = {
    TextEvent: "text",
    ToolCallEvent: "tool_call",
    ToolResultEvent: "tool_result",
    ResultEvent: "result",
}


def create_log_callback(chunk: str, phase: WorkUnitPhase, log_dir: Path):
    """Create a logging callback for agent execution.

    Serializes each :class:`LogEvent` as a single JSON line containing a
    ``timestamp``, ``type`` tag, and the event's own fields.

    Args:
        chunk: Chunk name
        phase: Current phase
        log_dir: Directory for log files

    Returns:
        Callback function for logging LogEvent messages
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{phase.value.lower()}.txt"

    def callback(event: LogEvent) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        type_tag = _EVENT_TYPE_TAG.get(type(event), type(event).__name__)
        record = {"timestamp": timestamp, "type": type_tag, **asdict(event)}
        with open(log_file, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    return callback
