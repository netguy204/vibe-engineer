# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator CLI attention-related commands.

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


# Chunk: docs/chunks/orch_attention_reason - CLI tests for ps command attention_reason display
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
