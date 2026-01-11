# Chunk: docs/chunks/orch_foundation - Orchestrator daemon foundation
"""Orchestrator package for parallel agent work management."""

from orchestrator.models import (
    WorkUnitPhase,
    WorkUnitStatus,
    WorkUnit,
    OrchestratorState,
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

__all__ = [
    # Models
    "WorkUnitPhase",
    "WorkUnitStatus",
    "WorkUnit",
    "OrchestratorState",
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
]
