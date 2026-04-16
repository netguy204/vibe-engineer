"""Tests for entity_from_transcript.py.

# Chunk: docs/chunks/entity_from_transcript - Unit tests
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from entity_from_transcript import (
    FromTranscriptResult,
    _wiki_creation_prompt,
    _wiki_update_prompt,
    create_entity_from_transcript,
    format_transcript_text,
)
from entity_transcript import SessionTranscript, Turn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transcript(
    session_id: str = "test-session",
    turns: list[Turn] | None = None,
) -> SessionTranscript:
    """Build a minimal SessionTranscript for testing."""
    if turns is None:
        turns = [
            Turn(
                role="user",
                text="How do I implement async iterators in Python?",
                timestamp="2026-01-01T00:00:00Z",
                uuid="uuid-1",
            ),
            Turn(
                role="assistant",
                text="Async iterators implement __aiter__ and __anext__ methods. Here is a complete example with error handling.",
                timestamp="2026-01-01T00:00:01Z",
                uuid="uuid-2",
            ),
        ]
    return SessionTranscript(session_id=session_id, turns=turns)


def _make_jsonl_file(tmp_path: Path, name: str = "session.jsonl") -> Path:
    """Write a minimal JSONL session file."""
    import json

    path = tmp_path / name
    lines = [
        json.dumps({
            "type": "user",
            "uuid": "uuid-1",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {"content": "How do I implement async iterators in Python?"},
        }),
        json.dumps({
            "type": "assistant",
            "uuid": "uuid-2",
            "requestId": "req-1",
            "timestamp": "2026-01-01T00:00:01Z",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Async iterators implement __aiter__ and __anext__ methods. "
                            "Here is a complete example with error handling."
                        ),
                    }
                ]
            },
        }),
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def _make_entity_repo(tmp_path: Path, name: str = "test-entity") -> Path:
    """Create a real entity git repo for testing (uses create_entity_repo)."""
    from entity_repo import create_entity_repo

    repo = create_entity_repo(tmp_path, name)
    # Set git identity so commits work in isolated test environments
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@ve.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    return repo


# ---------------------------------------------------------------------------
# format_transcript_text tests
# ---------------------------------------------------------------------------


class TestFormatTranscriptText:
    def test_labels_turns(self) -> None:
        """Output contains 'User' and 'Assistant' labels."""
        transcript = _make_transcript()
        text = format_transcript_text(transcript)
        assert "[User]" in text
        assert "[Assistant]" in text

    def test_skips_short_turns(self) -> None:
        """Turns with fewer than 20 characters are omitted."""
        turns = [
            Turn(role="user", text="Hi", timestamp="", uuid="u1"),  # < 20 chars
            Turn(
                role="assistant",
                text="Hello! This is a substantive response that definitely exceeds twenty characters.",
                timestamp="",
                uuid="u2",
            ),
        ]
        transcript = _make_transcript(turns=turns)
        text = format_transcript_text(transcript)
        assert "Hi" not in text
        assert "Hello!" in text

    def test_header_contains_session_id(self) -> None:
        """Output starts with the session_id from the transcript."""
        transcript = _make_transcript(session_id="my-session-abc")
        text = format_transcript_text(transcript)
        assert text.startswith("Session: my-session-abc")

    def test_turn_count_in_header(self) -> None:
        """Header includes count of substantive turns."""
        transcript = _make_transcript()
        text = format_transcript_text(transcript)
        # Both turns are substantive (>= 20 chars)
        assert "Turns: 2" in text

    def test_empty_transcript_produces_header(self) -> None:
        """Empty transcript still produces a header with zero turns."""
        transcript = _make_transcript(turns=[])
        text = format_transcript_text(transcript)
        assert "Session:" in text
        assert "Turns: 0" in text


# ---------------------------------------------------------------------------
# create_entity_from_transcript — validation tests (no SDK needed)
# ---------------------------------------------------------------------------


class TestCreateEntityFromTranscriptValidation:
    def test_invalid_name_raises_value_error(self, tmp_path: Path) -> None:
        """Name with uppercase/special chars raises ValueError."""
        jsonl = _make_jsonl_file(tmp_path)
        with pytest.raises(ValueError, match="Invalid entity name"):
            create_entity_from_transcript(
                name="INVALID!",
                jsonl_paths=[jsonl],
                output_dir=tmp_path,
            )

    def test_name_with_spaces_raises_value_error(self, tmp_path: Path) -> None:
        """Name with spaces raises ValueError."""
        jsonl = _make_jsonl_file(tmp_path)
        with pytest.raises(ValueError, match="Invalid entity name"):
            create_entity_from_transcript(
                name="my entity",
                jsonl_paths=[jsonl],
                output_dir=tmp_path,
            )

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent JSONL path raises FileNotFoundError."""
        missing = tmp_path / "does_not_exist.jsonl"
        with pytest.raises(FileNotFoundError, match="does_not_exist.jsonl"):
            create_entity_from_transcript(
                name="my-entity",
                jsonl_paths=[missing],
                output_dir=tmp_path,
            )

    def test_no_sdk_raises_runtime_error(self, tmp_path: Path) -> None:
        """When ClaudeSDKClient is None, raises RuntimeError."""
        jsonl = _make_jsonl_file(tmp_path)
        with patch("entity_from_transcript.ClaudeSDKClient", None):
            with pytest.raises(RuntimeError, match="claude_agent_sdk"):
                create_entity_from_transcript(
                    name="my-entity",
                    jsonl_paths=[jsonl],
                    output_dir=tmp_path,
                )


# ---------------------------------------------------------------------------
# create_entity_from_transcript — single transcript (mocked agent)
# ---------------------------------------------------------------------------


class TestCreateEntitySingleTranscript:
    """Tests for single-transcript flow with mocked Agent SDK."""

    @pytest.fixture()
    def mock_wiki_agent(self):
        """Patch _run_wiki_agent to return a success dict immediately."""
        success = {"success": True, "summary": "Built 5 wiki pages.", "error": None}
        with patch(
            "entity_from_transcript._run_wiki_agent",
            new_callable=AsyncMock,
            return_value=success,
        ) as m:
            yield m

    def test_archives_jsonl_in_episodic(
        self, tmp_path: Path, mock_wiki_agent
    ) -> None:
        """After single-transcript run, JSONL is copied to episodic/."""
        jsonl = _make_jsonl_file(tmp_path, "mysession.jsonl")
        result = create_entity_from_transcript(
            name="test-entity",
            jsonl_paths=[jsonl],
            output_dir=tmp_path / "out",
        )
        episodic_copy = result.entity_path / "episodic" / "mysession.jsonl"
        assert episodic_copy.exists(), "JSONL should be archived in episodic/"

    def test_creates_session1_commit(
        self, tmp_path: Path, mock_wiki_agent
    ) -> None:
        """After single-transcript run, git log shows 'Session 1: initial wiki from transcript'."""
        jsonl = _make_jsonl_file(tmp_path)
        result = create_entity_from_transcript(
            name="test-entity",
            jsonl_paths=[jsonl],
            output_dir=tmp_path / "out",
        )
        log = subprocess.run(
            ["git", "-C", str(result.entity_path), "log", "--oneline"],
            capture_output=True,
            text=True,
        )
        assert "Session 1: initial wiki from transcript" in log.stdout

    def test_result_fields(self, tmp_path: Path, mock_wiki_agent) -> None:
        """Result has correct entity_name, entity_path, and transcripts_processed."""
        jsonl = _make_jsonl_file(tmp_path)
        result = create_entity_from_transcript(
            name="my-specialist",
            jsonl_paths=[jsonl],
            output_dir=tmp_path / "out",
        )
        assert result.entity_name == "my-specialist"
        assert result.entity_path.name == "my-specialist"
        assert result.transcripts_processed == 1
        assert result.sessions_archived == 1
        assert result.entity_path.exists()

    def test_temp_file_removed_after_agent(
        self, tmp_path: Path, mock_wiki_agent
    ) -> None:
        """_transcript_incoming.txt is cleaned up after the agent runs."""
        jsonl = _make_jsonl_file(tmp_path)
        result = create_entity_from_transcript(
            name="test-entity",
            jsonl_paths=[jsonl],
            output_dir=tmp_path / "out",
        )
        assert not (result.entity_path / "_transcript_incoming.txt").exists()


# ---------------------------------------------------------------------------
# create_entity_from_transcript — multi-transcript (mocked agents)
# ---------------------------------------------------------------------------


class TestCreateEntityMultiTranscript:
    """Tests for multi-transcript flow with mocked Agent SDK sessions."""

    @pytest.fixture()
    def mock_wiki_agent(self):
        success = {"success": True, "summary": "Updated 3 pages.", "error": None}
        with patch(
            "entity_from_transcript._run_wiki_agent",
            new_callable=AsyncMock,
            return_value=success,
        ) as m:
            yield m

    @pytest.fixture()
    def mock_consolidation_agent(self):
        with patch(
            "entity_from_transcript._run_consolidation_agent",
            new_callable=AsyncMock,
            return_value={"success": True, "session_id": None, "error": None},
        ) as m:
            yield m

    def test_multi_makes_consolidation_call(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """With 2 transcripts, _run_consolidation_agent is called once (session 2).

        consolidation is only called when wiki_diff is non-empty.  We intercept
        the git-diff subprocess call to return a fake non-empty diff, while
        passing all other subprocess calls through to the real implementation.
        """
        jsonl1 = _make_jsonl_file(tmp_path, "s1.jsonl")
        jsonl2 = _make_jsonl_file(tmp_path, "s2.jsonl")

        fake_diff = "diff --git a/wiki/identity.md b/wiki/identity.md\n+new knowledge\n"

        # Capture the real subprocess.run before patching to avoid recursion
        real_run = subprocess.run

        def selective_run(cmd, **kwargs):
            if (
                isinstance(cmd, list)
                and "diff" in cmd
                and "--cached" in cmd
                and "wiki/" in cmd
            ):
                result = MagicMock()
                result.stdout = fake_diff
                result.returncode = 0
                return result
            return real_run(cmd, **kwargs)

        with patch("subprocess.run", side_effect=selective_run):
            create_entity_from_transcript(
                name="test-entity",
                jsonl_paths=[jsonl1, jsonl2],
                output_dir=tmp_path / "out",
            )

        # consolidation called once for session 2
        assert mock_consolidation_agent.call_count == 1

    def test_multi_result_transcripts_processed(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """Result shows correct transcripts_processed for 3 inputs."""
        jsonls = [_make_jsonl_file(tmp_path, f"s{i}.jsonl") for i in range(1, 4)]
        result = create_entity_from_transcript(
            name="test-entity",
            jsonl_paths=jsonls,
            output_dir=tmp_path / "out",
        )
        assert result.transcripts_processed == 3
        assert result.sessions_archived == 3

    def test_multi_all_sessions_archived(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """All JSONL files are archived in episodic/ for multi-transcript run."""
        jsonl1 = _make_jsonl_file(tmp_path, "s1.jsonl")
        jsonl2 = _make_jsonl_file(tmp_path, "s2.jsonl")
        result = create_entity_from_transcript(
            name="test-entity",
            jsonl_paths=[jsonl1, jsonl2],
            output_dir=tmp_path / "out",
        )
        assert (result.entity_path / "episodic" / "s1.jsonl").exists()
        assert (result.entity_path / "episodic" / "s2.jsonl").exists()


# ---------------------------------------------------------------------------
# Wiki prompt content tests
# ---------------------------------------------------------------------------


class TestWikiPromptContent:
    """Tests that wiki construction prompts include required framing.

    These functions are pure string-returning functions — no mocking needed.
    Tests call them with simple args and assert on the returned string content.
    """

    def test_creation_prompt_includes_compounding_framing(self) -> None:
        """Creation prompt should include compounding-artifact framing."""
        result = _wiki_creation_prompt("test-entity", None, None)
        assert "compound" in result.lower()

    def test_creation_prompt_includes_lint_step(self) -> None:
        """Creation prompt should include an explicit lint operation."""
        result = _wiki_creation_prompt("test-entity", None, None)
        assert any(
            kw in result.lower()
            for kw in ("cross-reference", "orphan", "lint")
        )

    def test_creation_prompt_emphasizes_adversity(self) -> None:
        """Creation prompt should frame adversity as the richest source material."""
        result = _wiki_creation_prompt("test-entity", None, None)
        assert any(
            kw in result.lower()
            for kw in ("adversity", "failure", "failures")
        )

    def test_update_prompt_includes_cross_reference_guidance(self) -> None:
        """Update prompt should require connecting new knowledge to existing pages."""
        result = _wiki_update_prompt("test-entity", 2, None)
        assert "cross-reference" in result.lower()

    def test_update_prompt_includes_lint_step(self) -> None:
        """Update prompt should include an explicit lint operation."""
        result = _wiki_update_prompt("test-entity", 2, None)
        assert any(
            kw in result.lower()
            for kw in ("lint", "missing", "cross-reference")
        )

    def test_update_prompt_includes_identity_evolution(self) -> None:
        """Update prompt should reference identity evolution across sessions."""
        result = _wiki_update_prompt("test-entity", 2, None)
        assert "identity.md" in result
        assert any(
            kw in result.lower()
            for kw in ("evolved", "shifted", "update", "evolution")
        )
