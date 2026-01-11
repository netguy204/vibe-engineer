# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
# Chunk: docs/chunks/orch_scheduling - Scheduling layer exports
"""Orchestrator package for parallel agent work management."""

from orchestrator.models import (
    AgentResult,
    OrchestratorConfig,
    OrchestratorState,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore, get_default_db_path
from orchestrator.daemon import (
    DaemonError,
    start_daemon,
    stop_daemon,
    is_daemon_running,
    get_daemon_status,
    get_pid_path,
    get_socket_path,
    get_log_path,
)
from orchestrator.client import (
    OrchestratorClient,
    OrchestratorClientError,
    DaemonNotRunningError,
    create_client,
)
from orchestrator.api import create_app
from orchestrator.worktree import (
    WorktreeError,
    WorktreeManager,
)
from orchestrator.agent import (
    AgentRunner,
    AgentRunnerError,
    PHASE_SKILL_FILES,
)
from orchestrator.scheduler import (
    Scheduler,
    SchedulerError,
    create_scheduler,
)

__all__ = [
    # Models
    "AgentResult",
    "OrchestratorConfig",
    "OrchestratorState",
    "WorkUnit",
    "WorkUnitPhase",
    "WorkUnitStatus",
    # State
    "StateStore",
    "get_default_db_path",
    # Daemon
    "DaemonError",
    "start_daemon",
    "stop_daemon",
    "is_daemon_running",
    "get_daemon_status",
    "get_pid_path",
    "get_socket_path",
    "get_log_path",
    # Client
    "OrchestratorClient",
    "OrchestratorClientError",
    "DaemonNotRunningError",
    "create_client",
    # API
    "create_app",
    # Worktree
    "WorktreeError",
    "WorktreeManager",
    # Agent
    "AgentRunner",
    "AgentRunnerError",
    "PHASE_SKILL_FILES",
    # Scheduler
    "Scheduler",
    "SchedulerError",
    "create_scheduler",
]
