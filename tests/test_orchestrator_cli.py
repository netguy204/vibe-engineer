# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_foundation - Orchestrator CLI tests
# Chunk: docs/chunks/orch_tcp_port - TCP port CLI tests
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
