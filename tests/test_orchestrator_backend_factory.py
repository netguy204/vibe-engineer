# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/backend_config - Backend factory and config-driven backend selection
# Chunk: docs/chunks/backend_cursor - CursorBackend registration in factory
"""Tests for the backend factory and config-driven backend wiring.

Covers:
- Factory returns ClaudeBackend for the default "claude" value
- Factory raises ValueError with a clear message for unknown backends
- create_scheduler passes the factory-resolved backend into AgentRunner
"""

from pathlib import Path

import pytest

from orchestrator.backend import AgentBackend
from orchestrator.backends import create_backend, BACKEND_REGISTRY
from orchestrator.backends.claude import ClaudeBackend
from orchestrator.backends.cursor import CursorBackend
from orchestrator.models import OrchestratorConfig


def test_create_backend_returns_claude_for_default():
    """Factory called with 'claude' returns a ClaudeBackend instance."""
    backend = create_backend("claude")
    assert isinstance(backend, ClaudeBackend)


def test_create_backend_raises_on_unknown():
    """Factory called with an unknown name raises ValueError listing available backends."""
    with pytest.raises(ValueError, match="nonexistent") as exc_info:
        create_backend("nonexistent")
    # The error message should list available backends
    assert "claude" in str(exc_info.value)


def test_create_scheduler_uses_config_backend(tmp_path):
    """create_scheduler with backend='claude' produces a scheduler whose
    agent_runner.backend is a ClaudeBackend."""
    from orchestrator.scheduler import create_scheduler
    from orchestrator.state import StateStore

    db_path = tmp_path / "test.db"
    store = StateStore(db_path)
    store.initialize()

    config = OrchestratorConfig(backend="claude")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    scheduler = create_scheduler(store, project_dir, config, base_branch="main")
    assert isinstance(scheduler.agent_runner.backend, ClaudeBackend)

    store.close()


def test_create_backend_returns_cursor():
    """Factory called with 'cursor' returns a CursorBackend instance."""
    backend = create_backend("cursor")
    assert isinstance(backend, CursorBackend)


def test_cursor_backend_satisfies_protocol():
    """CursorBackend from the factory satisfies AgentBackend protocol."""
    backend = create_backend("cursor")
    _: AgentBackend = backend
    assert hasattr(backend, "run")
