# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_seam - AgentBackend seam and normalized contract types
"""Backend-agnostic contract for executing agent phases.

The orchestrator runs each chunk phase through an :class:`AgentBackend` rather
than calling any specific agent SDK directly. This module defines the seam:
the normalized request/decision types and the protocol every backend
implements. Concrete backends (e.g. ``orchestrator.backends.claude.ClaudeBackend``)
translate a :class:`SessionRequest` onto their native mechanism and return the
shared :class:`~orchestrator.models.AgentResult`.

This module imports no agent SDK and must stay that way: it is the contract both
the Claude and future (Cursor/Composer) backends depend on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Optional, Protocol, Union

from orchestrator.models import AgentResult, ReviewToolDecision


# ---------------------------------------------------------------------------
# Normalized log event types
# ---------------------------------------------------------------------------
# Chunk: docs/chunks/backend_logparse - Backend-agnostic log events
#
# Every backend translates its native message stream into these event types
# before calling ``on_log``. Downstream consumers (log_parser, log_streaming)
# never touch vendor-specific shapes.


@dataclass
class TextEvent:
    """Agent emitted a text block."""

    text: str


@dataclass
class ToolCallEvent:
    """Agent invoked a tool."""

    tool_id: str
    name: str
    input: dict
    description: Optional[str] = None


@dataclass
class ToolResultEvent:
    """A tool returned a result."""

    tool_use_id: str
    content: str
    is_error: bool


@dataclass
class ResultEvent:
    """Session completed (success or error)."""

    subtype: str  # "success" | "error"
    duration_ms: int
    total_cost_usd: float
    num_turns: int
    is_error: bool
    session_id: Optional[str] = None
    result_text: Optional[str] = None


LogEvent = Union[TextEvent, ToolCallEvent, ToolResultEvent, ResultEvent]


class ToolDecision(StrEnum):
    """Decision a tool-use policy returns before a tool executes."""

    ALLOW = "allow"
    DENY = "deny"


@dataclass
class ToolUse:
    """A tool invocation an agent is about to make, surfaced to policy.

    ``command`` and ``cwd`` are conveniences populated for shell/Bash tools so
    sandbox policy can inspect them without re-parsing ``tool_input``.
    """

    tool_name: str
    tool_input: dict
    command: Optional[str] = None
    cwd: Optional[str] = None


@dataclass
class SessionRequest:
    """Everything a backend needs to run (or resume) one agent phase.

    The orchestrator owns policy and passes it to the backend two ways:

    - **Sandbox context** (``host_repo_path`` + ``cwd``, the worktree): every
      backend gates tool use through the shared :func:`is_sandbox_violation`,
      expressed in :class:`ToolUse`/:class:`ToolDecision` terms, to keep agents
      inside their worktree. Carried as data (not a callback) so the deny reason
      survives to the agent.
    - **Observation callbacks** the backend invokes against its native event
      stream: ``on_question`` (agent asked the operator something — suspend and
      forward), ``on_review_decision`` (reviewer submitted its ReviewDecision),
      and ``on_log`` (per-message activity logging).

    Resume is folded into ``resume_session_id``; ``expose_review_tool`` asks the
    backend to make the orchestrator ReviewDecision tool available (REVIEW phase).
    """

    prompt: str
    cwd: Path
    host_repo_path: Path
    env: dict[str, str]
    max_turns: int
    allowed_tools: list[str] = field(default_factory=list)
    resume_session_id: Optional[str] = None
    expose_review_tool: bool = False
    on_question: Optional[Callable[[dict], None]] = None
    on_review_decision: Optional[Callable[[ReviewToolDecision], None]] = None
    on_log: Optional[Callable[["LogEvent"], None]] = None


class AgentBackend(Protocol):
    """Executes a single agent phase described by a :class:`SessionRequest`.

    Implementations own all vendor-specific machinery (process/SDK management,
    tool interception, session resume) and must return a populated
    :class:`~orchestrator.models.AgentResult`. Resume is folded into
    :attr:`SessionRequest.resume_session_id`; there is no separate entry point.
    """

    async def run(self, request: SessionRequest) -> AgentResult: ...


# Chunk: docs/chunks/orch_sandbox_enforcement - Sandbox violation detection logic
def is_sandbox_violation(
    command: str,
    host_repo_path: Path,
    worktree_path: Path,
) -> tuple[bool, Optional[str]]:
    """Check if a command violates sandbox rules.

    Detects commands that would escape the worktree sandbox and access
    the host repository or other forbidden locations. Pure path/string logic
    with no SDK dependency, so any backend's tool-use policy can reuse it.

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
