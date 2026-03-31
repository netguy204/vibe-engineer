"""Tests for `ve entity claude --entity <name>` CLI command."""

import json
import pathlib
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from entities import Entities
from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_entity(tmp_path: pathlib.Path, name: str = "steward") -> Entities:
    """Create an entity for testing."""
    entities = Entities(tmp_path)
    entities.create_entity(name, role="Test entity")
    return entities


def _write_pid_file(claude_home: pathlib.Path, pid: int, session_id: str) -> None:
    """Write a fake Claude Code PID file."""
    sessions_dir = claude_home / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    pid_file = sessions_dir / f"{pid}.json"
    pid_file.write_text(json.dumps({"pid": pid, "sessionId": session_id, "cwd": "/tmp"}))


# ---------------------------------------------------------------------------
# Unit tests for _read_session_id_from_pid_file helper
# ---------------------------------------------------------------------------


class TestReadSessionIdFromPidFile:
    def test_reads_session_id_from_pid_file(self, tmp_path):
        """Returns sessionId from a valid PID file."""
        from cli.entity import _read_session_id_from_pid_file

        pid = 1234
        session_id = "abc-123-def"
        _write_pid_file(tmp_path, pid, session_id)

        result = _read_session_id_from_pid_file(pid, claude_home=tmp_path)
        assert result == session_id

    def test_returns_none_when_pid_file_missing(self, tmp_path):
        """Returns None when the PID file doesn't exist."""
        from cli.entity import _read_session_id_from_pid_file

        result = _read_session_id_from_pid_file(9999, claude_home=tmp_path)
        assert result is None

    def test_returns_none_on_malformed_json(self, tmp_path):
        """Returns None when the PID file contains invalid JSON."""
        from cli.entity import _read_session_id_from_pid_file

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "1234.json").write_text("not valid json{{{")

        result = _read_session_id_from_pid_file(1234, claude_home=tmp_path)
        assert result is None

    def test_returns_none_when_session_id_key_missing(self, tmp_path):
        """Returns None when JSON exists but lacks sessionId key."""
        from cli.entity import _read_session_id_from_pid_file

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "1234.json").write_text(json.dumps({"pid": 1234}))

        result = _read_session_id_from_pid_file(1234, claude_home=tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# Entity validation
# ---------------------------------------------------------------------------


class TestEntityValidation:
    def test_errors_if_entity_missing(self, tmp_path):
        """Non-zero exit with helpful message when entity doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "claude",
            "--entity", "nonexistent",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# Session ID warning
# ---------------------------------------------------------------------------


class TestSessionIdWarning:
    @patch("subprocess.Popen")
    def test_warns_when_pid_file_missing(self, mock_popen, tmp_path):
        """Exits 0 gracefully and warns when PID file is absent."""
        _setup_entity(tmp_path)

        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        runner = CliRunner()
        # Use a tmp claude_home that has no sessions dir
        claude_home = tmp_path / "claude_home"
        claude_home.mkdir()

        with patch("cli.entity._read_session_id_from_pid_file", return_value=None):
            result = runner.invoke(cli, [
                "entity", "claude",
                "--entity", "steward",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0
        # Warning should appear in output (CliRunner merges stderr into output)
        assert "session id not found" in result.output.lower() or "session" in result.output.lower()


# ---------------------------------------------------------------------------
# Happy path: resume-based shutdown
# ---------------------------------------------------------------------------


class TestHappyPathResumeShutdown:
    @patch("subprocess.Popen")
    @patch("entities.Entities.archive_transcript")
    @patch("entities.Entities.append_session")
    def test_happy_path_resume_shutdown(
        self, mock_append, mock_archive, mock_popen, tmp_path
    ):
        """Full lifecycle succeeds with resume-based shutdown."""
        _setup_entity(tmp_path)

        session_id = "abc-123-uuid"
        pid = 1234

        # First Popen: the main claude session
        main_proc = MagicMock()
        main_proc.pid = pid
        main_proc.wait.return_value = 0

        # Second Popen: the resume shutdown
        resume_proc = MagicMock()
        resume_proc.wait.return_value = 0

        mock_popen.side_effect = [main_proc, resume_proc]
        mock_archive.return_value = True

        with patch("cli.entity._read_session_id_from_pid_file", return_value=session_id):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "entity", "claude",
                "--entity", "steward",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0, f"exit={result.exit_code}\noutput={result.output}\nexc={result.exception}"
        assert session_id in result.output
        assert "Shutdown method:     resume" in result.output
        assert "Transcript archived:" in result.output
        mock_append.assert_called_once()

    @patch("subprocess.Popen")
    @patch("entities.Entities.archive_transcript")
    @patch("entities.Entities.append_session")
    def test_summary_shows_skipped_when_no_transcript(
        self, mock_append, mock_archive, mock_popen, tmp_path
    ):
        """When archive_transcript returns False, summary says '(skipped)'."""
        _setup_entity(tmp_path)

        session_id = "abc-456-uuid"
        pid = 1234

        main_proc = MagicMock()
        main_proc.pid = pid
        main_proc.wait.return_value = 0

        resume_proc = MagicMock()
        resume_proc.wait.return_value = 0

        mock_popen.side_effect = [main_proc, resume_proc]
        mock_archive.return_value = False  # transcript not found

        with patch("cli.entity._read_session_id_from_pid_file", return_value=session_id):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "entity", "claude",
                "--entity", "steward",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0
        assert "Transcript archived: (skipped)" in result.output


# ---------------------------------------------------------------------------
# Transcript fallback when resume fails
# ---------------------------------------------------------------------------


class TestTranscriptFallback:
    @patch("subprocess.Popen")
    @patch("entities.Entities.archive_transcript")
    @patch("entities.Entities.append_session")
    @patch("entity_shutdown.shutdown_from_transcript")
    @patch("entity_transcript.resolve_session_jsonl_path")
    @patch("entity_transcript.parse_session_jsonl")
    def test_falls_back_to_transcript_extraction_on_resume_failure(
        self,
        mock_parse,
        mock_resolve,
        mock_shutdown_from_transcript,
        mock_append,
        mock_archive,
        mock_popen,
        tmp_path,
    ):
        """When resume returns non-zero, falls back to transcript extraction."""
        _setup_entity(tmp_path)

        session_id = "def-456-uuid"
        pid = 5678

        main_proc = MagicMock()
        main_proc.pid = pid
        main_proc.wait.return_value = 0

        resume_proc = MagicMock()
        resume_proc.wait.return_value = 1  # Non-zero exit

        mock_popen.side_effect = [main_proc, resume_proc]
        mock_archive.return_value = True

        fake_jsonl_path = tmp_path / "fake.jsonl"
        fake_jsonl_path.touch()
        mock_resolve.return_value = fake_jsonl_path
        mock_parse.return_value = MagicMock()
        mock_shutdown_from_transcript.return_value = {
            "journals_added": 3,
            "journals_consolidated": 3,
            "consolidated": 1,
            "core": 0,
        }

        with patch("cli.entity._read_session_id_from_pid_file", return_value=session_id):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "entity", "claude",
                "--entity", "steward",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0, f"exit={result.exit_code}\noutput={result.output}\nexc={result.exception}"
        assert "Shutdown method:     transcript fallback" in result.output
        mock_shutdown_from_transcript.assert_called_once()

    @patch("subprocess.Popen")
    @patch("entities.Entities.archive_transcript")
    @patch("entities.Entities.append_session")
    @patch("entity_shutdown.shutdown_from_transcript")
    @patch("entity_transcript.resolve_session_jsonl_path")
    @patch("entity_transcript.parse_session_jsonl")
    def test_resume_timeout_triggers_fallback(
        self,
        mock_parse,
        mock_resolve,
        mock_shutdown_from_transcript,
        mock_append,
        mock_archive,
        mock_popen,
        tmp_path,
    ):
        """When resume times out, kills process and falls back to transcript extraction."""
        _setup_entity(tmp_path)

        session_id = "ghi-789-uuid"
        pid = 8888

        main_proc = MagicMock()
        main_proc.pid = pid
        main_proc.wait.return_value = 0

        resume_proc = MagicMock()
        # First call (with timeout) raises TimeoutExpired; second call (bare wait after kill) returns None
        resume_proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="claude", timeout=300),
            None,
        ]

        mock_popen.side_effect = [main_proc, resume_proc]
        mock_archive.return_value = True

        fake_jsonl_path = tmp_path / "fake.jsonl"
        fake_jsonl_path.touch()
        mock_resolve.return_value = fake_jsonl_path
        mock_parse.return_value = MagicMock()
        mock_shutdown_from_transcript.return_value = {
            "journals_added": 2,
            "journals_consolidated": 2,
            "consolidated": 1,
            "core": 0,
        }

        with patch("cli.entity._read_session_id_from_pid_file", return_value=session_id):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "entity", "claude",
                "--entity", "steward",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0, f"exit={result.exit_code}\noutput={result.output}\nexc={result.exception}"
        # Resume process was killed
        resume_proc.kill.assert_called_once()
        # Fallback used
        assert "Shutdown method:     transcript fallback" in result.output
        mock_shutdown_from_transcript.assert_called_once()
