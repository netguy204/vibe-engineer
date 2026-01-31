# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/explicit_deps_workunit_flag - WorkUnit explicit_deps field
# Chunk: docs/chunks/orch_verify_active - completion_retries and max_completion_retries fields
"""Pydantic models for the orchestrator daemon.

These models define the data contract between CLI, daemon, and SQLite.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, field_validator


class ConflictVerdict(StrEnum):
    """Verdict from conflict analysis between two chunks.

    Determines whether chunks can be safely parallelized or require serialization.
    """

    INDEPENDENT = "INDEPENDENT"  # Safe to parallelize (high confidence no overlap)
    SERIALIZE = "SERIALIZE"  # Must sequence (high confidence overlap)
    ASK_OPERATOR = "ASK_OPERATOR"  # Uncertain, needs human judgment


class ConflictAnalysis(BaseModel):
    """Result of analyzing potential conflict between two chunks.

    Stores the verdict, reasoning, and any detected overlaps.
    """

    chunk_a: str
    chunk_b: str
    verdict: ConflictVerdict
    confidence: float  # 0.0 to 1.0
    reason: str
    analysis_stage: str  # PROPOSED, GOAL, PLAN, COMPLETED
    overlapping_files: list[str] = []  # Files detected as overlapping
    overlapping_symbols: list[str] = []  # Symbols detected as overlapping (when available)
    created_at: datetime

    def model_dump_json_serializable(self) -> dict:
        """Return a JSON-serializable dict representation."""
        return {
            "chunk_a": self.chunk_a,
            "chunk_b": self.chunk_b,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "analysis_stage": self.analysis_stage,
            "overlapping_files": self.overlapping_files,
            "overlapping_symbols": self.overlapping_symbols,
            "created_at": self.created_at.isoformat(),
        }


class WorkUnitPhase(StrEnum):
    """Phase of a work unit in the chunk lifecycle.

    Represents the phase of work an agent would perform on a chunk.
    """

    GOAL = "GOAL"  # Drafting or refining the chunk goal
    PLAN = "PLAN"  # Creating the technical implementation plan
    IMPLEMENT = "IMPLEMENT"  # Writing the code
    REVIEW = "REVIEW"  # Reviewing implementation for alignment with documented intent
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
    priority: int = 0  # Scheduling priority (higher = more urgent)
    session_id: Optional[str] = None  # Agent session ID for suspended sessions
    completion_retries: int = 0  # Retry count for ACTIVE status verification
    attention_reason: Optional[str] = None  # Why work unit needs operator attention
    displaced_chunk: Optional[str] = None  # Chunk that was IMPLEMENTING when worktree created
    pending_answer: Optional[str] = None  # Operator answer to be injected on resume
    conflict_verdicts: dict[str, str] = {}  # Maps other chunk names to ConflictVerdict values
    conflict_override: Optional[str] = None  # Operator override for ASK_OPERATOR cases
    # When True, this work unit uses explicitly declared dependencies from the chunk's
    # depends_on frontmatter. The blocked_by list was populated at injection time from
    # these declared dependencies. The scheduler should skip oracle conflict analysis
    # for this work unit, treating the dependencies as authoritative rather than
    # heuristically detected.
    explicit_deps: bool = False
    # Track how many IMPLEMENT → REVIEW cycles have occurred for loop detection
    review_iterations: int = 0
    # Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
    # Track how many times the reviewer was nudged to call the ReviewDecision tool
    review_nudge_count: int = 0
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
            "conflict_verdicts": self.conflict_verdicts,
            "conflict_override": self.conflict_override,
            "explicit_deps": self.explicit_deps,
            "review_iterations": self.review_iterations,
            "review_nudge_count": self.review_nudge_count,
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


# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
class ReviewToolDecision(BaseModel):
    """Structured data from the ReviewDecision tool call.

    Captures the reviewer's explicit decision submitted via the tool,
    making the decision unambiguous and machine-readable.
    """

    decision: str  # APPROVE, FEEDBACK, or ESCALATE
    summary: str  # Brief summary of the review
    criteria_assessment: Optional[list[dict]] = None  # Optional structured feedback
    issues: Optional[list[dict]] = None  # Issues for FEEDBACK decisions
    reason: Optional[str] = None  # Reason for ESCALATE decisions


class AgentResult(BaseModel):
    """Result from running an agent phase.

    Captures the outcome of a single phase execution.
    """

    completed: bool  # Phase finished successfully
    suspended: bool = False  # Agent called AskUserQuestion
    session_id: Optional[str] = None  # Session ID for resuming
    question: Optional[dict] = None  # Question data if suspended
    error: Optional[str] = None  # Error message if failed
    # Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
    review_decision: Optional[ReviewToolDecision] = None  # Captured from ReviewDecision tool call


class ReviewDecision(StrEnum):
    """Decision outcome from the /chunk-review skill.

    Determines how the scheduler routes the work unit after review.
    """

    APPROVE = "APPROVE"  # Implementation meets documented intent, proceed to COMPLETE
    FEEDBACK = "FEEDBACK"  # Issues found, return to IMPLEMENT with context
    ESCALATE = "ESCALATE"  # Cannot decide, requires operator intervention


class ReviewIssue(BaseModel):
    """A single issue identified during review.

    Structured representation of a concern with location and suggested fix.
    """

    location: str  # File path or symbol reference
    concern: str  # Description of the issue
    suggestion: Optional[str] = None  # Suggested fix or approach


class ReviewResult(BaseModel):
    """Structured output from the /chunk-review skill.

    Parsed from the YAML decision block in the agent's response.
    """

    decision: ReviewDecision
    summary: str  # Brief summary of the review
    issues: list[ReviewIssue] = []  # Issues found (for FEEDBACK decisions)
    reason: Optional[str] = None  # Escalation reason (for ESCALATE decisions)
    iteration: int = 1  # Current review iteration number


from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskContextInfo:
    """Information about task context for orchestrator operation.

    In task context mode, the orchestrator runs from a task directory
    (containing .ve-task.yaml) with multiple project repositories.
    Chunks are read from an external artifacts repo and work affects
    multiple project repos based on the chunk's dependents field.

    In single-repo mode (no .ve-task.yaml), the orchestrator behaves
    as before, with chunks located in the project's docs/chunks/.
    """

    is_task_context: bool
    # The root directory for .ve/ placement (task_dir if task context, project_dir otherwise)
    root_dir: Path
    # External artifacts repo reference (org/repo format) - only set in task context
    external_repo: Optional[str] = None
    # Resolved filesystem path to external artifacts repo - only set in task context
    external_repo_path: Optional[Path] = None
    # List of project references (org/repo format) - only set in task context
    projects: list[str] = field(default_factory=list)
    # Resolved filesystem paths to project repos - only set in task context
    project_paths: list[Path] = field(default_factory=list)


def detect_task_context(directory: Path) -> TaskContextInfo:
    """Detect whether the orchestrator is running in task context.

    Checks for .ve-task.yaml in the given directory to determine if this is
    a task directory (multi-repo mode) or a single project repo.

    In task context:
    - .ve/ is placed at the task directory level
    - Chunks are read from the external artifacts repo
    - Work unit scheduling reads dependents to determine affected repos

    In single-repo mode:
    - .ve/ is placed at the project directory level
    - Chunks are read from the project's docs/chunks/

    Args:
        directory: Directory to check (typically cwd or project_dir)

    Returns:
        TaskContextInfo with detected context information
    """
    from task_utils import is_task_directory, load_task_config, resolve_repo_directory

    directory = directory.resolve()

    if not is_task_directory(directory):
        # Single-repo mode
        return TaskContextInfo(
            is_task_context=False,
            root_dir=directory,
        )

    # Task context mode - load config and resolve paths
    try:
        config = load_task_config(directory)
    except FileNotFoundError:
        # Shouldn't happen if is_task_directory returned True, but handle gracefully
        return TaskContextInfo(
            is_task_context=False,
            root_dir=directory,
        )

    # Resolve external repo path
    external_repo_path = None
    try:
        external_repo_path = resolve_repo_directory(directory, config.external_artifact_repo)
    except FileNotFoundError:
        pass  # External repo not accessible - will be handled by caller

    # Resolve project paths
    project_paths = []
    for project_ref in config.projects:
        try:
            project_path = resolve_repo_directory(directory, project_ref)
            project_paths.append(project_path)
        except FileNotFoundError:
            pass  # Project not accessible

    return TaskContextInfo(
        is_task_context=True,
        root_dir=directory,
        external_repo=config.external_artifact_repo,
        external_repo_path=external_repo_path,
        projects=config.projects,
        project_paths=project_paths,
    )


def get_chunk_location(task_info: TaskContextInfo, chunk: str) -> Path:
    """Get the filesystem path to a chunk's directory.

    In task context mode, chunks are located in the external artifacts repo.
    In single-repo mode, chunks are in the project's docs/chunks/.

    Args:
        task_info: Task context information
        chunk: Chunk directory name

    Returns:
        Path to the chunk directory
    """
    if task_info.is_task_context and task_info.external_repo_path:
        return task_info.external_repo_path / "docs" / "chunks" / chunk
    else:
        return task_info.root_dir / "docs" / "chunks" / chunk


def get_chunk_dependents(chunk_path: Path) -> list[dict]:
    """Get the dependents list from a chunk's GOAL.md frontmatter.

    The dependents field lists artifacts in other repos that are affected
    by this chunk, with format: {artifact_type, artifact_id, repo}.

    Args:
        chunk_path: Path to the chunk directory

    Returns:
        List of dependent dicts, or empty list if no dependents
    """
    import yaml

    goal_path = chunk_path / "GOAL.md"
    if not goal_path.exists():
        return []

    content = goal_path.read_text()

    # Parse frontmatter
    import re
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return []

    frontmatter = yaml.safe_load(match.group(1)) or {}
    dependents = frontmatter.get("dependents", [])

    if dependents is None:
        return []
    if isinstance(dependents, list):
        return dependents

    return []


def resolve_affected_repos(task_info: TaskContextInfo, chunk: str) -> list[Path]:
    """Resolve the project repo paths affected by a chunk.

    Reads the chunk's dependents field and maps repo references to
    filesystem paths. Only returns repos that are accessible.

    Args:
        task_info: Task context information
        chunk: Chunk directory name

    Returns:
        List of resolved project repo paths
    """
    from task_utils import resolve_repo_directory

    if not task_info.is_task_context:
        # Single-repo mode - only the current repo is affected
        return [task_info.root_dir]

    chunk_path = get_chunk_location(task_info, chunk)
    dependents = get_chunk_dependents(chunk_path)

    if not dependents:
        # No dependents specified - use all project repos
        return task_info.project_paths

    # Collect unique repos from dependents
    affected_repos: list[Path] = []
    seen_repos: set[str] = set()

    for dep in dependents:
        repo_ref = dep.get("repo")
        if not repo_ref or repo_ref in seen_repos:
            continue
        seen_repos.add(repo_ref)

        try:
            repo_path = resolve_repo_directory(task_info.root_dir, repo_ref)
            affected_repos.append(repo_path)
        except FileNotFoundError:
            pass  # Repo not accessible

    return affected_repos if affected_repos else task_info.project_paths
