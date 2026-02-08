# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/test_file_split - Split test_orchestrator_cli.py into smaller files
"""Tests for the orchestrator CLI display commands.

Tests the CLI layer for work unit display and URL commands using Click's test runner.
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


# Chunk: docs/chunks/orch_attention_reason - CLI tests for work-unit show command
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
