"""Tests for the 've entity from-transcript' CLI command.

# Chunk: docs/chunks/entity_from_transcript - CLI tests
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli.entity import entity
from entity_from_transcript import FromTranscriptResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stub_result(
    entity_name: str = "my-specialist",
    entity_path: Path | None = None,
    transcripts_processed: int = 1,
    wiki_pages_written: int = 8,
    sessions_archived: int = 1,
) -> FromTranscriptResult:
    """Build a fixed FromTranscriptResult for CLI test assertions."""
    return FromTranscriptResult(
        entity_name=entity_name,
        entity_path=entity_path or Path(f"/tmp/{entity_name}"),
        transcripts_processed=transcripts_processed,
        wiki_pages_written=wiki_pages_written,
        sessions_archived=sessions_archived,
    )


def _make_jsonl(tmp_path: Path, name: str = "session.jsonl") -> Path:
    """Write a minimal JSONL file so the path exists."""
    path = tmp_path / name
    path.write_text(
        json.dumps({
            "type": "user",
            "uuid": "u1",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {"content": "Hello"},
        }) + "\n"
    )
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromTranscriptCLI:
    """Tests for 've entity from-transcript' command using CliRunner."""

    def test_success_exit_code_zero(self, tmp_path: Path) -> None:
        """Valid invocation exits with code 0."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = _make_stub_result(entity_path=tmp_path / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ):
            result = runner.invoke(
                entity,
                ["from-transcript", "my-specialist", str(jsonl)],
            )

        assert result.exit_code == 0, result.output

    def test_success_output_contains_entity_name(self, tmp_path: Path) -> None:
        """Output mentions entity name and 'Transcripts processed'."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = _make_stub_result(entity_path=tmp_path / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ):
            result = runner.invoke(
                entity,
                ["from-transcript", "my-specialist", str(jsonl)],
            )

        assert "my-specialist" in result.output
        assert "Transcripts processed: 1" in result.output

    def test_missing_jsonl_exits_nonzero(self, tmp_path: Path) -> None:
        """Nonexistent JSONL path causes non-zero exit with error message."""
        runner = CliRunner()
        missing = tmp_path / "does_not_exist.jsonl"

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            side_effect=FileNotFoundError(f"Transcript file not found: {missing}"),
        ):
            result = runner.invoke(
                entity,
                ["from-transcript", "my-specialist", str(missing)],
            )

        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()

    def test_invalid_name_exits_nonzero(self, tmp_path: Path) -> None:
        """Entity name with invalid chars causes non-zero exit."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            side_effect=ValueError("Invalid entity name 'INVALID!'"),
        ):
            result = runner.invoke(
                entity,
                ["from-transcript", "INVALID!", str(jsonl)],
            )

        assert result.exit_code != 0

    def test_role_passed_to_function(self, tmp_path: Path) -> None:
        """--role option is passed as role= to create_entity_from_transcript."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = _make_stub_result(entity_path=tmp_path / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ) as mock_fn:
            runner.invoke(
                entity,
                [
                    "from-transcript",
                    "my-specialist",
                    str(jsonl),
                    "--role",
                    "my role",
                ],
            )

        mock_fn.assert_called_once()
        call_kwargs = mock_fn.call_args.kwargs
        assert call_kwargs.get("role") == "my role"

    def test_multiple_paths_passed_as_list(self, tmp_path: Path) -> None:
        """Multiple JSONL paths result in jsonl_paths list of length 3."""
        runner = CliRunner()
        jsonls = [_make_jsonl(tmp_path, f"s{i}.jsonl") for i in range(1, 4)]
        stub = _make_stub_result(
            transcripts_processed=3,
            sessions_archived=3,
            entity_path=tmp_path / "my-specialist",
        )

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ) as mock_fn:
            runner.invoke(
                entity,
                [
                    "from-transcript",
                    "my-specialist",
                    str(jsonls[0]),
                    str(jsonls[1]),
                    str(jsonls[2]),
                ],
            )

        mock_fn.assert_called_once()
        call_kwargs = mock_fn.call_args.kwargs
        assert len(call_kwargs.get("jsonl_paths", [])) == 3

    def test_output_dir_passed_to_function(self, tmp_path: Path) -> None:
        """--output-dir is forwarded as output_dir= to create_entity_from_transcript."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        out_dir = tmp_path / "custom_output"
        out_dir.mkdir()
        stub = _make_stub_result(entity_path=out_dir / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ) as mock_fn:
            runner.invoke(
                entity,
                [
                    "from-transcript",
                    "my-specialist",
                    str(jsonl),
                    "--output-dir",
                    str(out_dir),
                ],
            )

        mock_fn.assert_called_once()
        call_kwargs = mock_fn.call_args.kwargs
        assert call_kwargs.get("output_dir") == out_dir

    def test_project_context_passed_to_function(self, tmp_path: Path) -> None:
        """--project-context option is forwarded correctly."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = _make_stub_result(entity_path=tmp_path / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ) as mock_fn:
            runner.invoke(
                entity,
                [
                    "from-transcript",
                    "my-specialist",
                    str(jsonl),
                    "--project-context",
                    "vibe-engineer infrastructure",
                ],
            )

        mock_fn.assert_called_once()
        call_kwargs = mock_fn.call_args.kwargs
        assert call_kwargs.get("project_context") == "vibe-engineer infrastructure"

    def test_ready_for_attach_message(self, tmp_path: Path) -> None:
        """Output contains 'ready for attach/push' line."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = _make_stub_result(entity_path=tmp_path / "my-specialist")

        with patch(
            "entity_from_transcript.create_entity_from_transcript",
            return_value=stub,
        ):
            result = runner.invoke(
                entity,
                ["from-transcript", "my-specialist", str(jsonl)],
            )

        assert "ready for attach" in result.output.lower()
