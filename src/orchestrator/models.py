# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
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
