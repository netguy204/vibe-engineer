# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator CLI commands.

Tests the CLI layer using Click's test runner. These tests mock the daemon
to test the CLI behavior without starting actual daemon processes.
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


class TestOrchStart:
    """Tests for ve orch start command."""

    def test_start_success(self, runner, tmp_path):
        """Successfully starts daemon."""
        with patch("orchestrator.daemon.start_daemon") as mock_start:
            mock_start.return_value = (12345, 8080)

            result = runner.invoke(cli, ["orch", "start", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "started" in result.output.lower()
            assert "12345" in result.output
            assert "http://127.0.0.1:8080/" in result.output

    def test_start_with_custom_port(self, runner, tmp_path):
        """Starts daemon with custom port."""
        with patch("orchestrator.daemon.start_daemon") as mock_start:
            mock_start.return_value = (12345, 9090)

            result = runner.invoke(cli, ["orch", "start", "--port", "9090", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            mock_start.assert_called_once()
            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["port"] == 9090

    def test_start_with_custom_host(self, runner, tmp_path):
        """Starts daemon with custom host."""
        with patch("orchestrator.daemon.start_daemon") as mock_start:
            mock_start.return_value = (12345, 8080)

            result = runner.invoke(cli, ["orch", "start", "--host", "0.0.0.0", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            mock_start.assert_called_once()
            call_kwargs = mock_start.call_args[1]
            assert call_kwargs["host"] == "0.0.0.0"
            assert "http://0.0.0.0:8080/" in result.output

    def test_start_already_running(self, runner, tmp_path):
        """Shows error when daemon already running."""
        with patch("orchestrator.daemon.start_daemon") as mock_start:
            mock_start.side_effect = DaemonError("Daemon already running with PID 12345")

            result = runner.invoke(cli, ["orch", "start", "--project-dir", str(tmp_path)])

            assert result.exit_code == 1
            assert "already running" in result.output.lower()


class TestOrchStop:
    """Tests for ve orch stop command."""

    def test_stop_success(self, runner, tmp_path):
        """Successfully stops daemon."""
        with patch("orchestrator.daemon.stop_daemon") as mock_stop:
            mock_stop.return_value = True

            result = runner.invoke(cli, ["orch", "stop", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "stopped" in result.output.lower()

    def test_stop_not_running(self, runner, tmp_path):
        """Reports when daemon not running."""
        with patch("orchestrator.daemon.stop_daemon") as mock_stop:
            mock_stop.return_value = False

            result = runner.invoke(cli, ["orch", "stop", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "not running" in result.output.lower()


class TestOrchStatus:
    """Tests for ve orch status command."""

    def test_status_running(self, runner, tmp_path):
        """Shows status when daemon running."""
        with patch("orchestrator.daemon.get_daemon_status") as mock_status:
            mock_status.return_value = OrchestratorState(
                running=True,
                pid=12345,
                uptime_seconds=120,
                work_unit_counts={"READY": 2, "RUNNING": 1},
            )

            result = runner.invoke(cli, ["orch", "status", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "Running" in result.output
            assert "12345" in result.output
            assert "READY: 2" in result.output

    def test_status_stopped(self, runner, tmp_path):
        """Shows status when daemon stopped."""
        with patch("orchestrator.daemon.get_daemon_status") as mock_status:
            mock_status.return_value = OrchestratorState(running=False)

            result = runner.invoke(cli, ["orch", "status", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "Stopped" in result.output

    def test_status_json(self, runner, tmp_path):
        """Shows status in JSON format."""
        with patch("orchestrator.daemon.get_daemon_status") as mock_status:
            mock_status.return_value = OrchestratorState(
                running=True,
                pid=12345,
            )

            result = runner.invoke(cli, ["orch", "status", "--json", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["running"] is True
            assert data["pid"] == 12345


class TestOrchPs:
    """Tests for ve orch ps command."""

    def test_ps_empty(self, runner, tmp_path):
        """Shows message when no work units."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.return_value = {"work_units": [], "count": 0}
            mock_create.return_value = mock_client

            result = runner.invoke(cli, ["orch", "ps", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "No work units" in result.output

    def test_ps_with_units(self, runner, tmp_path):
        """Lists work units."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.return_value = {
                "work_units": [
                    {
                        "chunk": "test_chunk",
                        "phase": "GOAL",
                        "status": "READY",
                        "blocked_by": [],
                    },
                ],
                "count": 1,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(cli, ["orch", "ps", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            assert "test_chunk" in result.output
            assert "GOAL" in result.output
            assert "READY" in result.output

    def test_ps_daemon_not_running(self, runner, tmp_path):
        """Shows error when daemon not running."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.side_effect = DaemonNotRunningError("not running")
            mock_create.return_value = mock_client

            result = runner.invoke(cli, ["orch", "ps", "--project-dir", str(tmp_path)])

            assert result.exit_code == 1
            assert "not running" in result.output.lower()

    def test_ps_json(self, runner, tmp_path):
        """Shows work units in JSON format."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.return_value = {
                "work_units": [{"chunk": "test"}],
                "count": 1,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(cli, ["orch", "ps", "--json", "--project-dir", str(tmp_path)])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["count"] == 1


class TestWorkUnitCreate:
    """Tests for ve orch work-unit create command."""

    def test_create_default(self, runner, tmp_path):
        """Creates work unit with defaults."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.create_work_unit.return_value = {
                "chunk": "new_chunk",
                "phase": "GOAL",
                "status": "READY",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "create", "new_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Created" in result.output
            assert "new_chunk" in result.output

    def test_create_with_options(self, runner, tmp_path):
        """Creates work unit with custom options."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.create_work_unit.return_value = {
                "chunk": "test",
                "phase": "PLAN",
                "status": "BLOCKED",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                [
                    "orch", "work-unit", "create", "test",
                    "--phase", "PLAN",
                    "--status", "BLOCKED",
                    "--blocked-by", "dep1",
                    "--blocked-by", "dep2",
                    "--project-dir", str(tmp_path),
                ],
            )

            assert result.exit_code == 0
            mock_client.create_work_unit.assert_called_once_with(
                chunk="test",
                phase="PLAN",
                status="BLOCKED",
                blocked_by=["dep1", "dep2"],
            )

    def test_create_duplicate_error(self, runner, tmp_path):
        """Shows error for duplicate chunk."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.create_work_unit.side_effect = OrchestratorClientError("already exists")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "create", "dup", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "already exists" in result.output


class TestWorkUnitStatus:
    """Tests for ve orch work-unit status command."""

    def test_show_status(self, runner, tmp_path):
        """Shows work unit status."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.return_value = {
                "chunk": "test",
                "phase": "IMPLEMENT",
                "status": "RUNNING",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "status", "test", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "test" in result.output
            assert "IMPLEMENT" in result.output
            assert "RUNNING" in result.output

    def test_update_status(self, runner, tmp_path):
        """Updates work unit status."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.return_value = {
                "chunk": "test",
                "phase": "GOAL",
                "status": "READY",
            }
            mock_client.update_work_unit.return_value = {
                "chunk": "test",
                "phase": "GOAL",
                "status": "RUNNING",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "status", "test", "RUNNING", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "READY" in result.output
            assert "RUNNING" in result.output
            assert "->" in result.output

    def test_status_not_found(self, runner, tmp_path):
        """Shows error for non-existent work unit."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.side_effect = OrchestratorClientError("not found")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "status", "missing", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not found" in result.output


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




class TestWorkUnitShow:
    """Tests for ve orch work-unit show command."""

    def test_show_work_unit_basic(self, runner, tmp_path):
        """Shows basic work unit information."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.return_value = {
                "chunk": "test_chunk",
                "phase": "PLAN",
                "status": "READY",
                "priority": 5,
                "blocked_by": [],
                "worktree": None,
                "session_id": None,
                "attention_reason": None,
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "show", "test_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "test_chunk" in result.output
            assert "PLAN" in result.output
            assert "READY" in result.output
            assert "Priority:" in result.output
            assert "5" in result.output

    def test_show_with_attention_reason(self, runner, tmp_path):
        """Shows attention_reason when present."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.return_value = {
                "chunk": "test_chunk",
                "phase": "PLAN",
                "status": "NEEDS_ATTENTION",
                "priority": 0,
                "blocked_by": [],
                "worktree": None,
                "session_id": "session123",
                "attention_reason": "Question: Which database should I use?",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "show", "test_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Attention Reason:" in result.output
            assert "Question: Which database should I use?" in result.output
            assert "session123" in result.output

    def test_show_json_output(self, runner, tmp_path):
        """Shows work unit in JSON format."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.return_value = {
                "chunk": "test_chunk",
                "phase": "PLAN",
                "status": "NEEDS_ATTENTION",
                "priority": 0,
                "blocked_by": [],
                "worktree": None,
                "session_id": None,
                "attention_reason": "Connection timeout",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "show", "test_chunk", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["chunk"] == "test_chunk"
            assert data["attention_reason"] == "Connection timeout"

    def test_show_not_found(self, runner, tmp_path):
        """Shows error when work unit not found."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.side_effect = OrchestratorClientError("Work unit not found")
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "work-unit", "show", "missing_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not found" in result.output.lower()




# Chunk: docs/chunks/orch_url_command - URL command for orchestrator
class TestOrchUrl:
    """Tests for ve orch url command."""

    def test_url_prints_url_when_running(self, runner, tmp_path):
        """When daemon is running, prints the URL."""
        # Create port file to simulate running daemon
        ve_dir = tmp_path / ".ve"
        ve_dir.mkdir()
        port_file = ve_dir / "orchestrator.port"
        port_file.write_text("8080\n")

        with patch("orchestrator.daemon.is_daemon_running") as mock_running:
            mock_running.return_value = True

            result = runner.invoke(
                cli,
                ["orch", "url", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "http://127.0.0.1:8080" in result.output

    def test_url_error_when_not_running(self, runner, tmp_path):
        """When daemon is not running, exits with error and helpful message."""
        with patch("orchestrator.daemon.is_daemon_running") as mock_running:
            mock_running.return_value = False

            result = runner.invoke(
                cli,
                ["orch", "url", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "not running" in result.output.lower()
            assert "ve orch start" in result.output

    def test_url_json_output(self, runner, tmp_path):
        """When --json flag provided, outputs JSON with url key."""
        # Create port file to simulate running daemon
        ve_dir = tmp_path / ".ve"
        ve_dir.mkdir()
        port_file = ve_dir / "orchestrator.port"
        port_file.write_text("9090\n")

        with patch("orchestrator.daemon.is_daemon_running") as mock_running:
            mock_running.return_value = True

            result = runner.invoke(
                cli,
                ["orch", "url", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["url"] == "http://127.0.0.1:9090"

    def test_url_port_file_missing_when_running(self, runner, tmp_path):
        """Edge case: daemon appears running but port file is missing."""
        # Don't create port file - simulates corruption
        ve_dir = tmp_path / ".ve"
        ve_dir.mkdir()

        with patch("orchestrator.daemon.is_daemon_running") as mock_running:
            mock_running.return_value = True

            result = runner.invoke(
                cli,
                ["orch", "url", "--project-dir", str(tmp_path)],
            )

            # Should fail gracefully
            assert result.exit_code == 1
            assert "port" in result.output.lower() or "not found" in result.output.lower()


class TestOrchPsAttentionReason:
    """Tests for ve orch ps command with attention_reason display."""

    def test_ps_shows_attention_reason_column(self, runner, tmp_path):
        """Shows REASON column when NEEDS_ATTENTION units have reasons."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.return_value = {
                "work_units": [
                    {
                        "chunk": "chunk_with_reason",
                        "phase": "PLAN",
                        "status": "NEEDS_ATTENTION",
                        "blocked_by": [],
                        "attention_reason": "Question: Which framework?",
                    },
                    {
                        "chunk": "ready_chunk",
                        "phase": "GOAL",
                        "status": "READY",
                        "blocked_by": [],
                        "attention_reason": None,
                    },
                ],
                "count": 2,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "ps", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "REASON" in result.output
            assert "Question: Which framework?" in result.output

    def test_ps_truncates_long_reason(self, runner, tmp_path):
        """Truncates long attention_reason to 30 characters."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            long_reason = "This is a very long attention reason that should be truncated"
            mock_client.list_work_units.return_value = {
                "work_units": [
                    {
                        "chunk": "test_chunk",
                        "phase": "PLAN",
                        "status": "NEEDS_ATTENTION",
                        "blocked_by": [],
                        "attention_reason": long_reason,
                    },
                ],
                "count": 1,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "ps", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # Reason should be truncated to 27 chars + "..."
            assert "This is a very long attenti..." in result.output
            # Full reason should not appear
            assert long_reason not in result.output

    def test_ps_no_reason_column_when_no_attention_reasons(self, runner, tmp_path):
        """Omits REASON column when no NEEDS_ATTENTION units have reasons."""
        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.return_value = {
                "work_units": [
                    {
                        "chunk": "ready_chunk",
                        "phase": "GOAL",
                        "status": "READY",
                        "blocked_by": [],
                        "attention_reason": None,
                    },
                    {
                        "chunk": "running_chunk",
                        "phase": "PLAN",
                        "status": "RUNNING",
                        "blocked_by": [],
                        "attention_reason": None,
                    },
                ],
                "count": 2,
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "ps", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # REASON column should not appear when no attention reasons
            assert "REASON" not in result.output


# Chunk: docs/chunks/explicit_deps_batch_inject - Batch injection with dependency ordering
class TestOrchInjectBatch:
    """Tests for ve orch inject command with multiple chunks."""

    def test_inject_multiple_chunks_no_dependencies(self, runner, tmp_path):
        """Inject multiple chunks without dependencies."""
        # Create chunk directories with GOAL.md files
        chunks_dir = tmp_path / "docs" / "chunks"
        for name in ["chunk_a", "chunk_b", "chunk_c"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: []
---

# {name}
"""
            )

        injected_chunks = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    injected_chunks.append(json["chunk"])
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": json.get("priority", 0),
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    # List work units - return empty initially
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "chunk_c", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(injected_chunks) == 3
            assert "chunk_a" in injected_chunks
            assert "chunk_b" in injected_chunks
            assert "chunk_c" in injected_chunks

    def test_inject_single_chunk_backward_compatible(self, runner, tmp_path):
        """Single-chunk usage remains backward compatible."""
        # Create a chunk directory
        chunks_dir = tmp_path / "docs" / "chunks"
        chunk_dir = chunks_dir / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# my_chunk
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client._request.return_value = {
                "chunk": "my_chunk",
                "phase": "PLAN",
                "priority": 0,
                "status": "READY",
            }
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "my_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert "Injected" in result.output
            assert "my_chunk" in result.output

    def test_inject_topological_ordering(self, runner, tmp_path):
        """Chunks with depends_on are injected after their dependencies."""
        # Create chunk directories with dependencies
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has no dependencies
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        # chunk_c depends on chunk_b (transitive dep on chunk_a)
        chunk_c_dir = chunks_dir / "chunk_c"
        chunk_c_dir.mkdir(parents=True)
        (chunk_c_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_b
---

# chunk_c
"""
        )

        injection_order = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    injection_order.append(json["chunk"])
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": json.get("priority", 0),
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            # Inject in reverse order to verify topological sort works
            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_c", "chunk_b", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # chunk_a must be before chunk_b, chunk_b must be before chunk_c
            assert injection_order.index("chunk_a") < injection_order.index("chunk_b")
            assert injection_order.index("chunk_b") < injection_order.index("chunk_c")

    def test_inject_cycle_detection(self, runner, tmp_path):
        """Error when chunks form a dependency cycle."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a depends on chunk_b
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_b
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a (cycle!)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "cycle" in result.output.lower()

    def test_inject_external_dependency_validation(self, runner, tmp_path):
        """Error when depends_on references a chunk not in batch and not an existing work unit."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a depends on missing_chunk (not in batch)
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - missing_chunk
---

# chunk_a
"""
        )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units":
                    # No existing work units
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 1
            assert "missing_chunk" in result.output
            # Should mention it's not in batch and not existing work unit
            assert "not" in result.output.lower()

    def test_inject_blocked_by_populated(self, runner, tmp_path):
        """Work units have blocked_by populated from depends_on."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has no dependencies
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # Find the chunk_b injection call
            chunk_b_call = next(c for c in inject_calls if c["chunk"] == "chunk_b")
            assert "chunk_a" in chunk_b_call["blocked_by"]

    def test_inject_explicit_deps_flag_set(self, runner, tmp_path):
        """Work units with explicit depends_on declaration have explicit_deps=True.

        Both empty list [] and populated list have explicit_deps=True (agent knows deps).
        Only null/omitted has explicit_deps=False (agent doesn't know deps).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_a has explicit empty depends_on (explicitly no deps)
        chunk_a_dir = chunks_dir / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# chunk_a
"""
        )

        # chunk_b depends on chunk_a (explicit deps)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - chunk_a
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # chunk_a has depends_on: [] (explicit empty list), so explicit_deps should be True
            chunk_a_call = next(c for c in inject_calls if c["chunk"] == "chunk_a")
            assert chunk_a_call.get("explicit_deps") is True

            # chunk_b has depends_on with items, so explicit_deps should be True
            chunk_b_call = next(c for c in inject_calls if c["chunk"] == "chunk_b")
            assert chunk_b_call.get("explicit_deps") is True

    def test_inject_external_dependency_exists_as_work_unit(self, runner, tmp_path):
        """Dependencies outside the batch are allowed if they exist as work units."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # chunk_b depends on external_chunk (not in batch but exists as work unit)
        chunk_b_dir = chunks_dir / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on:
  - external_chunk
---

# chunk_b
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                elif path == "/work-units":
                    # external_chunk exists as a work unit
                    return {
                        "work_units": [
                            {"chunk": "external_chunk", "status": "RUNNING"}
                        ],
                        "count": 1,
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_b", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1
            assert inject_calls[0]["chunk"] == "chunk_b"
            assert "external_chunk" in inject_calls[0]["blocked_by"]

    def test_inject_batch_output_format(self, runner, tmp_path):
        """Batch injection shows progress for each chunk."""
        chunks_dir = tmp_path / "docs" / "chunks"

        for name in ["chunk_a", "chunk_b"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            deps = "[]" if name == "chunk_a" else "[chunk_a]"
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: {deps}
---

# {name}
"""
            )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_b", "chunk_a", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            # Should mention both chunks were injected
            assert "chunk_a" in result.output
            assert "chunk_b" in result.output
            # Should show blocked_by info for chunk_b
            assert "blocked_by" in result.output.lower() or "Injected 2" in result.output

    def test_inject_batch_json_output(self, runner, tmp_path):
        """Batch injection with --json outputs array of results."""
        chunks_dir = tmp_path / "docs" / "chunks"

        for name in ["chunk_a", "chunk_b"]:
            chunk_dir = chunks_dir / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(
                f"""---
status: FUTURE
depends_on: []
---

# {name}
"""
            )

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                    }
                elif path == "/work-units":
                    return {"work_units": [], "count": 0}
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "chunk_a", "chunk_b", "--json", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "results" in data
            assert len(data["results"]) == 2

    def test_inject_empty_depends_on_sets_explicit_deps_true(self, runner, tmp_path):
        """A chunk with depends_on: [] should have explicit_deps=True when injected.

        The empty list means the agent explicitly declares no dependencies,
        which is different from null/omitted (unknown dependencies).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with explicit empty depends_on
        chunk_dir = chunks_dir / "independent_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: []
---

# independent_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "independent_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # Empty depends_on means explicit declaration of no deps
            # So explicit_deps should be True
            call = inject_calls[0]
            assert call.get("explicit_deps") is True, (
                f"Expected explicit_deps=True for depends_on: [], got {call}"
            )

    def test_inject_null_depends_on_sets_explicit_deps_false(self, runner, tmp_path):
        """A chunk with depends_on: null should have explicit_deps=False.

        Null means the agent doesn't know dependencies, so oracle should be consulted.
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with null depends_on
        chunk_dir = chunks_dir / "unknown_deps_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
depends_on: null
---

# unknown_deps_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "unknown_deps_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # null depends_on means unknown deps - consult oracle
            # So explicit_deps should be False
            call = inject_calls[0]
            assert call.get("explicit_deps", False) is False, (
                f"Expected explicit_deps=False for depends_on: null, got {call}"
            )

    def test_inject_omitted_depends_on_sets_explicit_deps_false(self, runner, tmp_path):
        """A chunk with no depends_on field should have explicit_deps=False.

        Omitted field means the agent doesn't know dependencies (same as null).
        """
        chunks_dir = tmp_path / "docs" / "chunks"

        # Create chunk with omitted depends_on
        chunk_dir = chunks_dir / "no_depends_field_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
---

# no_depends_field_chunk
"""
        )

        inject_calls = []

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()

            def mock_request(method, path, json=None):
                if path == "/work-units/inject":
                    inject_calls.append(json)
                    return {
                        "chunk": json["chunk"],
                        "phase": "PLAN",
                        "priority": 0,
                        "status": "READY",
                        "blocked_by": json.get("blocked_by", []),
                        "explicit_deps": json.get("explicit_deps", False),
                    }
                return {}

            mock_client._request = mock_request
            mock_create.return_value = mock_client

            result = runner.invoke(
                cli,
                ["orch", "inject", "no_depends_field_chunk", "--project-dir", str(tmp_path)],
            )

            assert result.exit_code == 0
            assert len(inject_calls) == 1

            # omitted depends_on means unknown deps - consult oracle
            # So explicit_deps should be False
            call = inject_calls[0]
            assert call.get("explicit_deps", False) is False, (
                f"Expected explicit_deps=False for omitted depends_on, got {call}"
            )


class TestOrchTail:
    """Tests for ve orch tail command."""

    def test_tail_chunk_not_found(self, runner, tmp_path):
        """Shows error when chunk doesn't exist."""
        result = runner.invoke(
            cli,
            ["orch", "tail", "nonexistent_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_tail_no_logs_yet(self, runner, tmp_path):
        """Shows message when no logs exist."""
        # Create chunk directory but no log directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        result = runner.invoke(
            cli,
            ["orch", "tail", "my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 1
        assert "no logs" in result.output.lower()

    def test_tail_displays_log_output(self, runner, tmp_path):
        """Displays parsed log output."""
        # Create chunk directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        # Create log directory and file
        log_dir = tmp_path / ".ve" / "chunks" / "my_chunk" / "log"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "implement.txt"
        log_file.write_text(
            "[2026-01-31T14:30:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
            "[2026-01-31T14:30:01.000000+00:00] AssistantMessage(content=[ToolUseBlock(id='t1', name='Bash', input={'command': 'ls', 'description': 'List files'})])\n"
            "[2026-01-31T14:30:02.000000+00:00] UserMessage(content=[ToolResultBlock(tool_use_id='t1', content='file1.txt', is_error=False)])\n"
        )

        result = runner.invoke(
            cli,
            ["orch", "tail", "my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert "IMPLEMENT" in result.output  # Phase header
        assert "▶" in result.output  # Tool call symbol
        assert "Bash" in result.output
        assert "✓" in result.output  # Success symbol

    def test_tail_shows_phase_header(self, runner, tmp_path):
        """Shows phase header with start time."""
        # Create chunk directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        # Create log directory and file
        log_dir = tmp_path / ".ve" / "chunks" / "my_chunk" / "log"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "plan.txt"
        log_file.write_text(
            "[2026-01-31T14:30:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
        )

        result = runner.invoke(
            cli,
            ["orch", "tail", "my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert "=== PLAN phase ===" in result.output
        assert "14:30:00" in result.output

    def test_tail_result_message_shows_banner(self, runner, tmp_path):
        """Shows result banner for completed phase."""
        # Create chunk directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        # Create log directory and file
        log_dir = tmp_path / ".ve" / "chunks" / "my_chunk" / "log"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "implement.txt"
        log_file.write_text(
            "[2026-01-31T14:30:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
            "[2026-01-31T14:36:00.000000+00:00] ResultMessage(subtype='success', duration_ms=360000, duration_api_ms=300000, is_error=False, num_turns=20, session_id='abc', total_cost_usd=1.50, usage={}, result='Done')\n"
        )

        result = runner.invoke(
            cli,
            ["orch", "tail", "my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert "SUCCESS" in result.output
        assert "$1.50" in result.output
        assert "20 turns" in result.output

    def test_tail_multiple_phases(self, runner, tmp_path):
        """Displays multiple phase logs in order."""
        # Create chunk directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        # Create log directory and files for multiple phases
        log_dir = tmp_path / ".ve" / "chunks" / "my_chunk" / "log"
        log_dir.mkdir(parents=True)

        # Plan phase
        (log_dir / "plan.txt").write_text(
            "[2026-01-31T14:00:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
            "[2026-01-31T14:05:00.000000+00:00] ResultMessage(subtype='success', duration_ms=300000, duration_api_ms=250000, is_error=False, num_turns=10, session_id='abc', total_cost_usd=0.50, usage={}, result='Plan done')\n"
        )

        # Implement phase
        (log_dir / "implement.txt").write_text(
            "[2026-01-31T14:10:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
            "[2026-01-31T14:30:00.000000+00:00] ResultMessage(subtype='success', duration_ms=1200000, duration_api_ms=1000000, is_error=False, num_turns=30, session_id='def', total_cost_usd=2.00, usage={}, result='Implement done')\n"
        )

        result = runner.invoke(
            cli,
            ["orch", "tail", "my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 0
        # Both phases should appear
        assert "=== PLAN phase ===" in result.output
        assert "=== IMPLEMENT phase ===" in result.output
        # Plan should come before implement
        plan_pos = result.output.index("PLAN")
        impl_pos = result.output.index("IMPLEMENT")
        assert plan_pos < impl_pos

    def test_tail_help(self, runner):
        """Shows help text."""
        result = runner.invoke(cli, ["orch", "tail", "--help"])

        assert result.exit_code == 0
        assert "Stream log output" in result.output
        assert "--follow" in result.output or "-f" in result.output

    def test_tail_normalizes_chunk_path(self, runner, tmp_path):
        """Handles full chunk path prefix."""
        # Create chunk directory
        chunk_dir = tmp_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("# Goal")

        # Create log directory and file
        log_dir = tmp_path / ".ve" / "chunks" / "my_chunk" / "log"
        log_dir.mkdir(parents=True)
        (log_dir / "implement.txt").write_text(
            "[2026-01-31T14:30:00.000000+00:00] SystemMessage(subtype='init', data={})\n"
        )

        # Use full path prefix
        result = runner.invoke(
            cli,
            ["orch", "tail", "docs/chunks/my_chunk", "--project-dir", str(tmp_path)],
        )

        assert result.exit_code == 0
        assert "IMPLEMENT" in result.output
