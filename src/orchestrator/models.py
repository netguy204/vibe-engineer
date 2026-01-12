# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_question_forward - AgentResult question field
"""Pydantic models for the orchestrator daemon.

These models define the data contract between CLI, daemon, and SQLite.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, field_validator


class WorkUnitPhase(StrEnum):
    """Phase of a work unit in the chunk lifecycle.

    Represents the phase of work an agent would perform on a chunk.
    """

    GOAL = "GOAL"  # Drafting or refining the chunk goal
    PLAN = "PLAN"  # Creating the technical implementation plan
    IMPLEMENT = "IMPLEMENT"  # Writing the code
    COMPLETE = "COMPLETE"  # Finalizing and completing the chunk


class WorkUnitStatus(StrEnum):
    """Status of a work unit.

    Represents the current scheduling state of a work unit.
    """

    READY = "READY"  # Ready to be assigned to an agent
    RUNNING = "RUNNING"  # Currently being worked on by an agent
    BLOCKED = "BLOCKED"  # Blocked by dependencies on other chunks
    NEEDS_ATTENTION = "NEEDS_ATTENTION"  # Requires operator intervention
    DONE = "DONE"  # Work unit completed


# Chunk: docs/chunks/orch_attention_reason - Attention reason tracking for work units
# Chunk: docs/chunks/orch_activate_on_inject - Displaced chunk tracking
# Chunk: docs/chunks/orch_attention_queue - Pending answer storage for resume
class WorkUnit(BaseModel):
    """A work unit representing a chunk in a specific phase.

    The work unit is the fundamental scheduling entity - like a process
    in an operating system. It tracks a chunk through its lifecycle phases.
    """

    chunk: str  # Chunk directory name (the "PID")
    phase: WorkUnitPhase
    status: WorkUnitStatus
    blocked_by: list[str] = []  # Chunk names that must complete first
    worktree: Optional[str] = None  # Git worktree path, if assigned
    priority: int = 0  # Scheduling priority (higher = more urgent)
    session_id: Optional[str] = None  # Agent session ID for suspended sessions
    completion_retries: int = 0  # Retry count for ACTIVE status verification
    attention_reason: Optional[str] = None  # Why work unit needs operator attention
    displaced_chunk: Optional[str] = None  # Chunk that was IMPLEMENTING when worktree created
    pending_answer: Optional[str] = None  # Operator answer to be injected on resume
    created_at: datetime
    updated_at: datetime

    @field_validator("chunk")
    @classmethod
    def validate_chunk(cls, v: str) -> str:
        """Validate chunk is not empty."""
        if not v or not v.strip():
            raise ValueError("chunk cannot be empty")
        return v

    def model_dump_json_serializable(self) -> dict:
        """Return a JSON-serializable dict representation.

        Converts datetime objects to ISO format strings.
        """
        return {
            "chunk": self.chunk,
            "phase": self.phase.value,
            "status": self.status.value,
            "blocked_by": self.blocked_by,
            "worktree": self.worktree,
            "priority": self.priority,
            "session_id": self.session_id,
            "completion_retries": self.completion_retries,
            "attention_reason": self.attention_reason,
            "displaced_chunk": self.displaced_chunk,
            "pending_answer": self.pending_answer,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class OrchestratorState(BaseModel):
    """Status information about the orchestrator daemon.

    Returned by the status endpoint to provide daemon health information.
    """

    running: bool
    pid: Optional[int] = None
    uptime_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    work_unit_counts: dict[str, int] = {}  # Status -> count mapping
    version: str = "0.1.0"

    def model_dump_json_serializable(self) -> dict:
        """Return a JSON-serializable dict representation.

        Converts datetime objects to ISO format strings.
        """
        return {
            "running": self.running,
            "pid": self.pid,
            "uptime_seconds": self.uptime_seconds,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "work_unit_counts": self.work_unit_counts,
            "version": self.version,
        }


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator daemon.

    Controls agent scheduling behavior.
    """

    max_agents: int = 2  # Maximum concurrent agents
    dispatch_interval_seconds: float = 1.0  # How often to check for READY work units
    max_completion_retries: int = 2  # Max retries for ACTIVE status verification

    def model_dump_json_serializable(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return {
            "max_agents": self.max_agents,
            "dispatch_interval_seconds": self.dispatch_interval_seconds,
            "max_completion_retries": self.max_completion_retries,
        }


class AgentResult(BaseModel):
    """Result from running an agent phase.

    Captures the outcome of a single phase execution.
    """

    completed: bool  # Phase finished successfully
    suspended: bool = False  # Agent called AskUserQuestion
    session_id: Optional[str] = None  # Session ID for resuming
    question: Optional[dict] = None  # Question data if suspended
    error: Optional[str] = None  # Error message if failed
