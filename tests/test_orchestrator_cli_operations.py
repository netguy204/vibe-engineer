# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for orchestrator CLI operation commands.

Tests for work-unit delete, inject, queue, prioritize, and config commands.
These tests mock the daemon to test the CLI behavior without starting actual daemon processes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from ve import cli
from orchestrator.models import OrchestratorState, WorkUnit, WorkUnitPhase, WorkUnitStatus
from orchestrator.daemon import DaemonError
from orchestrator.client import OrchestratorClientError, DaemonNotRunningError


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


class TestWorkUnitDelete:
    """Tests for ve orch work-unit delete command."""

    def test_delete_success(self, runner, tmp_path):
        """Deletes work unit."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.delete_work_unit.return_value = {"deleted": True, "chunk": "test"}
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "delete", "test", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Deleted" in result.output

    def test_delete_not_found(self, runner, tmp_path):
        """Shows error for non-existent work unit."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.delete_work_unit.side_effect = OrchestratorClientError("not found")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "delete", "missing", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1




class TestOrchInject:
    """Tests for ve orch inject command."""

    def test_inject_success(self, runner, tmp_path):
        """Successfully injects chunk."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "chunk": "test_chunk",
                "phase": "PLAN",
                "priority": 5,
                "status": "READY",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "test_chunk", "--priority", "5", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Injected" in result.output
            assert "test_chunk" in result.output
            assert "priority=5" in result.output

    def test_inject_with_phase(self, runner, tmp_path):
        """Inject with explicit phase."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "chunk": "test_chunk",
                "phase": "IMPLEMENT",
                "priority": 0,
                "status": "READY",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "test_chunk", "--phase", "IMPLEMENT", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "POST", "/work-units/inject",
                json={"chunk": "test_chunk", "priority": 0, "phase": "IMPLEMENT"},
            )

    def test_inject_not_found(self, runner, tmp_path):
        """Shows error when chunk not found."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.side_effect = OrchestratorClientError("Chunk not found")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "missing_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_inject_daemon_not_running(self, runner, tmp_path):
        """Shows error when daemon not running."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.side_effect = DaemonNotRunningError("not running")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "test_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not running" in result.output.lower()


class TestOrchQueue:
    """Tests for ve orch queue command."""

    def test_queue_empty(self, runner, tmp_path):
        """Shows message when queue is empty."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {"work_units": [], "count": 0}
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "queue", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "empty" in result.output.lower()

    def test_queue_with_units(self, runner, tmp_path):
        """Shows queue with work units."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "work_units": [
                    {"chunk": "high_priority", "phase": "PLAN", "priority": 10},
                    {"chunk": "low_priority", "phase": "GOAL", "priority": 0},
                ],
                "count": 2,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "queue", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "high_priority" in result.output
            assert "low_priority" in result.output
            # High priority should be first
            assert result.output.index("high_priority") < result.output.index("low_priority")

    def test_queue_json(self, runner, tmp_path):
        """Queue outputs JSON format."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "work_units": [{"chunk": "test", "phase": "PLAN", "priority": 0}],
                "count": 1,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "queue", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["count"] == 1


class TestOrchPrioritize:
    """Tests for ve orch prioritize command."""

    def test_prioritize_success(self, runner, tmp_path):
        """Successfully sets priority."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "chunk": "test_chunk",
                "priority": 10,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "prioritize", "test_chunk", "10", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "priority" in result.output.lower()
            assert "10" in result.output

    def test_prioritize_not_found(self, runner, tmp_path):
        """Shows error when work unit not found."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.side_effect = OrchestratorClientError("not found")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "prioritize", "missing", "5", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not found" in result.output


class TestOrchConfig:
    """Tests for ve orch config command."""

    def test_config_get(self, runner, tmp_path):
        """Gets current configuration."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "max_agents: 2" in result.output
            assert "dispatch_interval_seconds: 1.0" in result.output

    def test_config_set_max_agents(self, runner, tmp_path):
        """Sets max_agents."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 4,
                "dispatch_interval_seconds": 1.0,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--max-agents", "4", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "PATCH", "/config", json={"max_agents": 4}
            )

    def test_config_set_dispatch_interval(self, runner, tmp_path):
        """Sets dispatch interval."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 0.5,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--dispatch-interval", "0.5", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "PATCH", "/config", json={"dispatch_interval_seconds": 0.5}
            )

    def test_config_json(self, runner, tmp_path):
        """Config outputs JSON format."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["max_agents"] == 2

    # Chunk: docs/chunks/orch_worktree_retain - Test worktree threshold config
    def test_config_set_worktree_threshold(self, runner, tmp_path):
        """Sets worktree_warning_threshold."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
                "worktree_warning_threshold": 20,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--worktree-threshold", "20", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "PATCH", "/config", json={"worktree_warning_threshold": 20}
            )
            assert "worktree_warning_threshold: 20" in result.output

    def test_config_shows_worktree_threshold(self, runner, tmp_path):
        """Config output includes worktree_warning_threshold."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
                "worktree_warning_threshold": 15,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "worktree_warning_threshold: 15" in result.output

    # Chunk: docs/chunks/orch_max_turns_config - Test per-phase turn budget config
    def test_config_set_max_turns_implement(self, runner, tmp_path):
        """Sets max_turns_implement."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
                "worktree_warning_threshold": 10,
                "max_turns_implement": 200,
                "max_turns_complete": 20,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--max-turns-implement", "200", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "PATCH", "/config", json={"max_turns_implement": 200}
            )
            assert "max_turns_implement: 200" in result.output

    def test_config_set_max_turns_complete(self, runner, tmp_path):
        """Sets max_turns_complete."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
                "worktree_warning_threshold": 10,
                "max_turns_implement": 100,
                "max_turns_complete": 40,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--max-turns-complete", "40", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            mock_client._request.assert_called_with(
                "PATCH", "/config", json={"max_turns_complete": 40}
            )
            assert "max_turns_complete: 40" in result.output

    def test_config_shows_max_turns(self, runner, tmp_path):
        """Config output includes max_turns_implement and max_turns_complete."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "max_agents": 2,
                "dispatch_interval_seconds": 1.0,
                "worktree_warning_threshold": 10,
                "max_turns_implement": 150,
                "max_turns_complete": 30,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "config", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "max_turns_implement: 150" in result.output
            assert "max_turns_complete: 30" in result.output
