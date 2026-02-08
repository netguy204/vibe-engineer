# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/test_file_split - CLI tail command tests
"""Tests for the orchestrator CLI tail command.

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
