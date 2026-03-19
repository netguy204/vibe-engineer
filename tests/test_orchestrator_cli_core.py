# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator CLI core commands.

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


# Chunk: docs/chunks/orch_client_context - Tests for orch_client context manager
class TestOrchClientContextManager:
    """Tests for the orch_client context manager."""

    def test_successful_client_usage(self, tmp_path):
        """Context manager yields client and closes on exit."""
        from cli.orch import orch_client

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            with orch_client(tmp_path) as client:
                assert client is mock_client
                client.list_work_units()

            mock_client.close.assert_called_once()

    def test_daemon_not_running_error(self, tmp_path, capsys):
        """Context manager handles DaemonNotRunningError."""
        from cli.orch import orch_client

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.list_work_units.side_effect = DaemonNotRunningError("Daemon not running")
            mock_create.return_value = mock_client

            with pytest.raises(SystemExit) as exc_info:
                with orch_client(tmp_path) as client:
                    client.list_work_units()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "Daemon not running" in captured.err
            mock_client.close.assert_called_once()

    def test_orchestrator_client_error(self, tmp_path, capsys):
        """Context manager handles OrchestratorClientError."""
        from cli.orch import orch_client

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_client.get_work_unit.side_effect = OrchestratorClientError("Work unit not found")
            mock_create.return_value = mock_client

            with pytest.raises(SystemExit) as exc_info:
                with orch_client(tmp_path) as client:
                    client.get_work_unit("missing")

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "Work unit not found" in captured.err
            mock_client.close.assert_called_once()

    def test_client_close_called_on_exception(self, tmp_path):
        """Context manager calls client.close() even on exception."""
        from cli.orch import orch_client

        with patch("orchestrator.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            with pytest.raises(ValueError):
                with orch_client(tmp_path) as client:
                    raise ValueError("Some unexpected error")

            mock_client.close.assert_called_once()


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

    # Chunk: docs/chunks/orch_empty_repo_handling - Empty repo detection
    def test_start_in_empty_repo_shows_actionable_error(self, runner, tmp_path):
        """Shows actionable error when starting in a repo with no commits."""
        with patch("orchestrator.daemon.start_daemon") as mock_start:
            mock_start.side_effect = DaemonError(
                "Cannot start orchestrator: repository has no commits. "
                "Make an initial commit first (e.g., `git commit --allow-empty -m 'Initial commit'`)."
            )

            result = runner.invoke(cli, ["orch", "start", "--project-dir", str(tmp_path)])

            assert result.exit_code == 1
            # Verify user-friendly message
            assert "no commits" in result.output.lower()
            assert "initial commit" in result.output.lower()
            # Verify no stack trace or git internals
            assert "Traceback" not in result.output
            assert "fatal:" not in result.output


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
