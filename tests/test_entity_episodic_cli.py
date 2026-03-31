"""Tests for `ve entity episodic` CLI command."""

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


class TestEpisodicSearchCLI:
    def test_episodic_search_prints_ranked_results(self, tmp_path):
        runner = CliRunner()
        # Set up entity directory
        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Write a session with searchable content
        _make_session_jsonl(
            sessions_dir / "abc123.jsonl",
            turns=[
                {
                    "type": "user",
                    "text": "How does websocket reconnect work in this system?",
                },
                {
                    "type": "assistant",
                    "text": "The websocket reconnect logic handles dropped connections automatically.",
                },
            ] * 5,  # Repeat to have enough turns
        )

        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--query", "websocket",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert "score=" in result.output
        assert "session=" in result.output
        assert "expand:" in result.output

    def test_episodic_search_no_results_prints_no_results_message(self, tmp_path):
        runner = CliRunner()
        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        _make_session_jsonl(
            sessions_dir / "abc123.jsonl",
            turns=[
                {"type": "user", "text": "This is a test message about bananas and fruit."},
                {"type": "assistant", "text": "Yes bananas are a type of fruit indeed."},
            ] * 5,
        )

        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--query", "xyzzy_never_matches_anything",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_episodic_search_missing_entity_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        # No entity directory created
        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "nonexistent",
            "--query", "websocket",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code != 0

    def test_episodic_expand_prints_context_with_markers(self, tmp_path):
        runner = CliRunner()
        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Need enough turns to have chunk_id=0 available
        _make_session_jsonl(
            sessions_dir / "abc123.jsonl",
            turns=[
                {"type": "user", "text": f"This is user message number {i} with enough content to index."}
                if i % 2 == 0
                else {"type": "assistant", "text": f"This is assistant message {i} with enough content to index."}
                for i in range(10)
            ],
        )

        # First build the index
        runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--query", "message",
            "--project-dir", str(tmp_path),
        ])

        # Now expand
        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--expand", "abc123",
            "--chunk", "0",
            "--radius", "2",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code == 0, result.output
        assert ">>>" in result.output

    def test_episodic_expand_missing_session_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        entity_dir = tmp_path / ".entities" / "steward"
        sessions_dir = entity_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Build a minimal index with one real session
        _make_session_jsonl(
            sessions_dir / "realses.jsonl",
            turns=[
                {"type": "user", "text": "Real session content here with enough words."},
                {"type": "assistant", "text": "Real assistant response with enough content."},
            ] * 5,
        )
        runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--query", "real",
            "--project-dir", str(tmp_path),
        ])

        # Try expanding a session that doesn't exist
        result = runner.invoke(cli, [
            "entity", "episodic",
            "--entity", "steward",
            "--expand", "nonexistent_session",
            "--chunk", "0",
            "--project-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
