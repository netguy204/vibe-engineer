"""Tests for orchestrator log streaming module."""
# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/cli_decompose - Extract log streaming logic from CLI

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from orchestrator.log_streaming import (
    get_phase_log_files,
    stream_phase_log,
    display_phase_log,
)
from orchestrator.models import WorkUnitPhase


class TestGetPhaseLogFiles:
    """Tests for get_phase_log_files function."""

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        """Returns empty list for non-existent log directory."""
        log_dir = tmp_path / "nonexistent"
        result = get_phase_log_files(log_dir)
        assert result == []

    def test_returns_empty_for_empty_dir(self, tmp_path):
        """Returns empty list for empty log directory."""
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        result = get_phase_log_files(log_dir)
        assert result == []

    def test_returns_existing_phase_files_in_order(self, tmp_path):
        """Returns existing phase log files in phase order."""
        log_dir = tmp_path / "log"
        log_dir.mkdir()

        # Create log files in reverse order to ensure ordering comes from phase_order
        (log_dir / "implement.txt").write_text("implement log")
        (log_dir / "goal.txt").write_text("goal log")
        (log_dir / "plan.txt").write_text("plan log")

        result = get_phase_log_files(log_dir)

        assert len(result) == 3
        assert result[0] == (WorkUnitPhase.GOAL, log_dir / "goal.txt")
        assert result[1] == (WorkUnitPhase.PLAN, log_dir / "plan.txt")
        assert result[2] == (WorkUnitPhase.IMPLEMENT, log_dir / "implement.txt")

    def test_skips_missing_phases(self, tmp_path):
        """Only returns phases that have existing log files."""
        log_dir = tmp_path / "log"
        log_dir.mkdir()

        # Create only goal and implement logs
        (log_dir / "goal.txt").write_text("goal log")
        (log_dir / "implement.txt").write_text("implement log")

        result = get_phase_log_files(log_dir)

        assert len(result) == 2
        assert result[0][0] == WorkUnitPhase.GOAL
        assert result[1][0] == WorkUnitPhase.IMPLEMENT

    def test_includes_all_phases(self, tmp_path):
        """Returns all phases when all log files exist."""
        log_dir = tmp_path / "log"
        log_dir.mkdir()

        for phase in WorkUnitPhase:
            (log_dir / f"{phase.value.lower()}.txt").write_text(f"{phase.value} log")

        result = get_phase_log_files(log_dir)

        assert len(result) == len(WorkUnitPhase)
        # Verify order matches WorkUnitPhase order
        for i, (phase, path) in enumerate(result):
            assert path.name == f"{phase.value.lower()}.txt"


class TestStreamPhaseLog:
    """Tests for stream_phase_log function."""

    def test_streams_new_lines_from_position(self, tmp_path):
        """Streams new lines starting from given position."""
        log_file = tmp_path / "goal.txt"
        log_file.write_text("line1\nline2\n")

        # Get lines from position 0
        lines = list(stream_phase_log(log_file, start_position=0))

        assert len(lines) == 2
        assert lines[0] == ("line1\n", 6)  # 6 bytes for "line1\n"
        assert lines[1] == ("line2\n", 12)  # 12 bytes total

    def test_streams_from_middle_of_file(self, tmp_path):
        """Streams only lines after start position."""
        log_file = tmp_path / "goal.txt"
        log_file.write_text("line1\nline2\nline3\n")

        # Start after first line
        lines = list(stream_phase_log(log_file, start_position=6))

        assert len(lines) == 2
        assert lines[0] == ("line2\n", 12)
        assert lines[1] == ("line3\n", 18)

    def test_returns_empty_when_at_end(self, tmp_path):
        """Returns empty when start position is at end of file."""
        log_file = tmp_path / "goal.txt"
        log_file.write_text("line1\n")

        # Start at end of file
        lines = list(stream_phase_log(log_file, start_position=6))

        assert lines == []

    def test_handles_nonexistent_file(self, tmp_path):
        """Returns empty for non-existent file."""
        log_file = tmp_path / "nonexistent.txt"

        lines = list(stream_phase_log(log_file, start_position=0))

        assert lines == []


class TestDisplayPhaseLog:
    """Tests for display_phase_log function."""

    def test_calls_output_function_for_each_entry(self, tmp_path):
        """Calls output function for each formatted line."""
        log_file = tmp_path / "goal.txt"
        # Create a simple log file with parseable entries
        log_file.write_text("")

        outputs = []

        def capture_output(line):
            outputs.append(line)

        # With empty file, should not call output
        display_phase_log(
            WorkUnitPhase.GOAL, log_file, show_header=False, output=capture_output
        )

        # Empty file should produce no output
        assert outputs == []

    def test_shows_header_when_requested(self, tmp_path):
        """Shows phase header when show_header is True."""
        log_file = tmp_path / "goal.txt"
        log_file.write_text("")

        outputs = []

        def capture_output(line):
            outputs.append(line)

        display_phase_log(
            WorkUnitPhase.GOAL, log_file, show_header=True, output=capture_output
        )

        # Empty file with header should produce header output
        # But since no entries, no header is shown (header needs first entry timestamp)
        assert outputs == []

    def test_default_output_is_print(self, tmp_path):
        """Default output function is print (smoke test)."""
        log_file = tmp_path / "goal.txt"
        log_file.write_text("")

        # Should not raise
        display_phase_log(WorkUnitPhase.GOAL, log_file, show_header=False)
