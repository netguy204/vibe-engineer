# Chunk: docs/chunks/episodic_ingest_external - External transcript ingest tests
"""Tests for `ve entity ingest` CLI command."""

import json
import pathlib

import pytest
from click.testing import CliRunner

from ve import cli


def _make_session_jsonl(path: pathlib.Path, turns: list[dict] | None = None) -> pathlib.Path:
    """Write a minimal valid Claude Code JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if turns is None:
        turns = [
            {
                "type": "user",
                "text": "This is a substantive user message with enough content to be indexed by BM25.",
            },
            {
                "type": "assistant",
                "text": "This is the assistant response with websocket reconnect logic details.",
            },
        ]
    with open(path, "w") as f:
        for i, turn in enumerate(turns):
            entry = {
                "type": turn.get("type", "user"),
                "uuid": turn.get("uuid", f"uuid-{i}"),
                "timestamp": turn.get("timestamp", "2026-01-01T00:00:00.000Z"),
                "requestId": turn.get("requestId", f"req-{i}"),
                "message": {
                    "content": turn.get("text", "Default content that is long enough."),
                },
            }
            f.write(json.dumps(entry) + "\n")
    return path


class TestEntityIngestCLI:
    def test_single_file_ingest(self, tmp_path):
        """Single file ingest copies file with ingested_ prefix."""
        runner = CliRunner()

        # Set up entity
        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create an external session file
        external = tmp_path / "external" / "old_session.jsonl"
        _make_session_jsonl(external)

        result = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(external),
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Ingested 1" in result.output

        # Verify the file was copied with ingested_ prefix
        dest = sessions_dir / "ingested_old_session.jsonl"
        assert dest.exists()
        assert dest.read_text() == external.read_text()

    def test_glob_ingest(self, tmp_path):
        """Glob pattern ingests multiple files."""
        runner = CliRunner()

        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create multiple external session files
        ext_dir = tmp_path / "external"
        _make_session_jsonl(ext_dir / "session_a.jsonl")
        _make_session_jsonl(ext_dir / "session_b.jsonl")

        result = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(ext_dir / "*.jsonl"),
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "Ingested 2" in result.output

        assert (sessions_dir / "ingested_session_a.jsonl").exists()
        assert (sessions_dir / "ingested_session_b.jsonl").exists()

    def test_invalid_file_rejected(self, tmp_path):
        """Invalid JSONL files are skipped with a warning."""
        runner = CliRunner()

        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create an invalid file (not valid JSONL)
        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text("this is not json at all\n")

        result = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(bad_file),
            "--project-dir", str(tmp_path),
        ])
        # Partial success: exit 0 but with skip
        assert result.exit_code == 0, result.output
        assert "skipped 1" in result.output.lower() or "Skipped" in result.output

        # The file should NOT have been copied
        assert not (sessions_dir / "ingested_bad.jsonl").exists()

    def test_duplicate_ingest_skipped(self, tmp_path):
        """Ingesting the same file twice skips with a message."""
        runner = CliRunner()

        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        external = tmp_path / "external" / "dup_session.jsonl"
        _make_session_jsonl(external)

        # First ingest
        result1 = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(external),
            "--project-dir", str(tmp_path),
        ])
        assert result1.exit_code == 0
        assert "Ingested 1" in result1.output

        # Second ingest — should skip
        result2 = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(external),
            "--project-dir", str(tmp_path),
        ])
        assert result2.exit_code == 0
        assert "skipped 1" in result2.output.lower() or "Skipped" in result2.output

    def test_nonexistent_entity(self, tmp_path):
        """Nonexistent entity returns an error."""
        runner = CliRunner()

        external = tmp_path / "session.jsonl"
        _make_session_jsonl(external)

        result = runner.invoke(cli, [
            "entity", "ingest", "nonexistent",
            str(external),
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_nonexistent_file(self, tmp_path):
        """Nonexistent file path produces a warning."""
        runner = CliRunner()

        entity_dir = tmp_path / ".entities" / "steward"
        entity_dir.mkdir(parents=True)

        result = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(tmp_path / "does_not_exist.jsonl"),
            "--project-dir", str(tmp_path),
        ])
        # Should handle gracefully — no files matched
        assert result.exit_code == 0
        assert "no files" in result.output.lower() or "Ingested 0" in result.output

    def test_episodic_search_picks_up_ingested_files(self, tmp_path):
        """After ingesting, episodic search returns hits from ingested content."""
        runner = CliRunner()

        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create an external session with distinctive searchable content
        external = tmp_path / "external" / "kubernetes_session.jsonl"
        _make_session_jsonl(external, turns=[
            {
                "type": "user",
                "text": "How do we configure kubernetes deployment manifests for production?",
            },
            {
                "type": "assistant",
                "text": "The kubernetes deployment manifests need resource limits and health checks configured.",
            },
        ] * 5)

        # Ingest
        result = runner.invoke(cli, [
            "entity", "ingest", "steward",
            str(external),
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0

        # Search — should find the ingested content
        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--query", "kubernetes deployment",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "kubernetes" in result.output.lower()
        assert "score=" in result.output
