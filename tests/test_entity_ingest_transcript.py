"""Tests for entity_from_transcript.ingest_transcripts_into_entity and CLI.

# Chunk: docs/chunks/entity_ingest_transcript - Unit and CLI tests
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.entity import entity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jsonl(tmp_path: Path, name: str = "session.jsonl") -> Path:
    """Write a minimal JSONL session file so the path exists."""
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


def _make_project_with_entity(
    tmp_path: Path,
    entity_name: str = "test-entity",
    with_wiki: bool = True,
) -> tuple[Path, Path]:
    """Create a minimal project + attached entity for testing.

    Returns (project_dir, entity_dir).
    """
    from entity_repo import create_entity_repo

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    entities_dir = project_dir / ".entities"
    entities_dir.mkdir()

    entity_dir = entities_dir / entity_name

    if with_wiki:
        # Full wiki-based entity repo
        create_entity_repo(entities_dir, entity_name)
        # Set git identity so commits work in isolated test environments
        subprocess.run(
            ["git", "-C", str(entity_dir), "config", "user.email", "test@ve.local"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(entity_dir), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
    else:
        # Legacy entity: just a directory with identity.md but no wiki/
        entity_dir.mkdir()
        (entity_dir / "identity.md").write_text("# Identity\nlegacy entity\n")

    return project_dir, entity_dir


# ---------------------------------------------------------------------------
# Unit tests: ingest_transcripts_into_entity
# ---------------------------------------------------------------------------


class TestIngestTranscriptsIntoEntity:
    """Unit tests for ingest_transcripts_into_entity(), mocking the Agent SDK."""

    @pytest.fixture()
    def mock_wiki_agent(self):
        """Patch _run_wiki_agent to return success immediately."""
        success = {"success": True, "summary": "Updated 3 pages.", "error": None}
        with patch(
            "entity_from_transcript._run_wiki_agent",
            new_callable=AsyncMock,
            return_value=success,
        ) as m:
            yield m

    @pytest.fixture()
    def mock_consolidation_agent(self):
        """Patch _run_consolidation_agent to return success immediately."""
        with patch(
            "entity_from_transcript._run_consolidation_agent",
            new_callable=AsyncMock,
            return_value={"success": True, "session_id": None, "error": None},
        ) as m:
            yield m

    def test_single_transcript_calls_wiki_update_agent(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """ingest_transcripts_into_entity calls _run_wiki_agent once for a single JSONL."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path)
        jsonl = _make_jsonl(tmp_path, "session1.jsonl")

        ingest_transcripts_into_entity(
            name="test-entity",
            jsonl_paths=[jsonl],
            project_dir=project_dir,
        )

        assert mock_wiki_agent.call_count == 1

    def test_multiple_transcripts_processed_in_order(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """Three transcripts are processed in submission order with sequential session numbers."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path)
        jsonls = [_make_jsonl(tmp_path, f"s{i}.jsonl") for i in range(1, 4)]

        ingest_transcripts_into_entity(
            name="test-entity",
            jsonl_paths=jsonls,
            project_dir=project_dir,
        )

        # wiki agent called once per transcript
        assert mock_wiki_agent.call_count == 3

        # Verify processing order by checking prompt session numbers
        call_prompts = [call.args[1] for call in mock_wiki_agent.call_args_list]
        assert "session 1" in call_prompts[0].lower()
        assert "session 2" in call_prompts[1].lower()
        assert "session 3" in call_prompts[2].lower()

    def test_legacy_entity_raises_value_error(self, tmp_path: Path) -> None:
        """Entity without wiki/ raises ValueError suggesting ve entity migrate."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path, with_wiki=False)
        jsonl = _make_jsonl(tmp_path)

        with pytest.raises(ValueError, match="migrate"):
            ingest_transcripts_into_entity(
                name="test-entity",
                jsonl_paths=[jsonl],
                project_dir=project_dir,
            )

    def test_nonexistent_entity_raises_value_error(self, tmp_path: Path) -> None:
        """Nonexistent entity raises ValueError."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".entities").mkdir()

        jsonl = _make_jsonl(tmp_path)

        with pytest.raises(ValueError, match="not found"):
            ingest_transcripts_into_entity(
                name="ghost-entity",
                jsonl_paths=[jsonl],
                project_dir=project_dir,
            )

    def test_transcripts_archived_in_episodic(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """After ingest, each JSONL appears under episodic/ in the entity repo."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, entity_dir = _make_project_with_entity(tmp_path)
        jsonl1 = _make_jsonl(tmp_path, "alpha.jsonl")
        jsonl2 = _make_jsonl(tmp_path, "beta.jsonl")

        ingest_transcripts_into_entity(
            name="test-entity",
            jsonl_paths=[jsonl1, jsonl2],
            project_dir=project_dir,
        )

        assert (entity_dir / "episodic" / "alpha.jsonl").exists()
        assert (entity_dir / "episodic" / "beta.jsonl").exists()

    def test_skip_consolidation_flag(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """With skip_consolidation=True, consolidation agent is NOT called."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path)
        jsonl = _make_jsonl(tmp_path)

        # Need a non-empty wiki diff to trigger consolidation if not skipped
        fake_diff = "diff --git a/wiki/identity.md b/wiki/identity.md\n+new knowledge\n"
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
            ingest_transcripts_into_entity(
                name="test-entity",
                jsonl_paths=[jsonl],
                project_dir=project_dir,
                skip_consolidation=True,
            )

        mock_consolidation_agent.assert_not_called()

    def test_session_numbering_continues_from_existing_episodic(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """If entity already has 2 files in episodic/, first ingest uses session_n=3."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, entity_dir = _make_project_with_entity(tmp_path)

        # Pre-populate episodic/ with 2 existing files
        episodic_dir = entity_dir / "episodic"
        episodic_dir.mkdir(parents=True, exist_ok=True)
        (episodic_dir / "existing1.jsonl").write_text("{}\n")
        (episodic_dir / "existing2.jsonl").write_text("{}\n")

        jsonl = _make_jsonl(tmp_path, "new.jsonl")

        ingest_transcripts_into_entity(
            name="test-entity",
            jsonl_paths=[jsonl],
            project_dir=project_dir,
        )

        # The prompt passed to the wiki agent should mention session 3
        call_prompt = mock_wiki_agent.call_args.args[1]
        assert "session 3" in call_prompt.lower()

    def test_missing_jsonl_raises_file_not_found(self, tmp_path: Path) -> None:
        """Nonexistent JSONL path raises FileNotFoundError before touching the entity."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path)
        missing = tmp_path / "does_not_exist.jsonl"

        with pytest.raises(FileNotFoundError, match="does_not_exist.jsonl"):
            ingest_transcripts_into_entity(
                name="test-entity",
                jsonl_paths=[missing],
                project_dir=project_dir,
            )

    def test_no_sdk_raises_runtime_error(self, tmp_path: Path) -> None:
        """When ClaudeSDKClient is None, raises RuntimeError with install hint."""
        from entity_from_transcript import ingest_transcripts_into_entity

        project_dir, _ = _make_project_with_entity(tmp_path)
        jsonl = _make_jsonl(tmp_path)

        with patch("entity_from_transcript.ClaudeSDKClient", None):
            with pytest.raises(RuntimeError, match="claude_agent_sdk"):
                ingest_transcripts_into_entity(
                    name="test-entity",
                    jsonl_paths=[jsonl],
                    project_dir=project_dir,
                )

    def test_result_fields(
        self, tmp_path: Path, mock_wiki_agent, mock_consolidation_agent
    ) -> None:
        """Result contains expected fields with correct values."""
        from entity_from_transcript import IngestTranscriptResult, ingest_transcripts_into_entity

        project_dir, entity_dir = _make_project_with_entity(tmp_path)
        jsonls = [_make_jsonl(tmp_path, f"s{i}.jsonl") for i in range(1, 3)]

        result = ingest_transcripts_into_entity(
            name="test-entity",
            jsonl_paths=jsonls,
            project_dir=project_dir,
        )

        assert isinstance(result, IngestTranscriptResult)
        assert result.entity_name == "test-entity"
        assert result.entity_path == entity_dir
        assert result.transcripts_processed == 2
        assert result.sessions_archived == 2
        assert result.wiki_pages_total >= 0


# ---------------------------------------------------------------------------
# CLI integration tests: ve entity ingest-transcript
# ---------------------------------------------------------------------------


class TestIngestTranscriptCLI:
    """CLI tests for 've entity ingest-transcript' using CliRunner."""

    def _make_stub_result(
        self,
        entity_path: Path | None = None,
        transcripts_processed: int = 1,
        sessions_archived: int = 1,
        wiki_pages_total: int = 5,
    ):
        from entity_from_transcript import IngestTranscriptResult

        return IngestTranscriptResult(
            entity_name="student",
            entity_path=entity_path or Path("/tmp/student"),
            transcripts_processed=transcripts_processed,
            sessions_archived=sessions_archived,
            wiki_pages_total=wiki_pages_total,
        )

    def test_cli_single_transcript_exits_zero(self, tmp_path: Path) -> None:
        """Happy path: single transcript, exits 0, output contains entity name."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = self._make_stub_result()

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            return_value=stub,
        ):
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(jsonl)],
            )

        assert result.exit_code == 0, result.output
        assert "student" in result.output

    def test_cli_legacy_entity_exits_nonzero(self, tmp_path: Path) -> None:
        """Legacy entity (no wiki/) causes non-zero exit mentioning 'migrate'."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            side_effect=ValueError("Entity 'student' has no wiki/. Run ve entity migrate first."),
        ):
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(jsonl)],
            )

        assert result.exit_code != 0
        assert "migrate" in result.output.lower()

    def test_cli_skip_consolidation_flag(self, tmp_path: Path) -> None:
        """--skip-consolidation flag is forwarded to ingest_transcripts_into_entity."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = self._make_stub_result()

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            return_value=stub,
        ) as mock_fn:
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(jsonl), "--skip-consolidation"],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_fn.call_args.kwargs
        assert call_kwargs.get("skip_consolidation") is True

    def test_cli_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        """Nonexistent JSONL path causes non-zero exit."""
        runner = CliRunner()
        missing = tmp_path / "does_not_exist.jsonl"

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            side_effect=FileNotFoundError(f"Transcript file not found: {missing}"),
        ):
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(missing)],
            )

        assert result.exit_code != 0

    def test_cli_skip_consolidation_note_in_output(self, tmp_path: Path) -> None:
        """When skip_consolidation is set, output includes note about ve entity shutdown."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = self._make_stub_result()

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            return_value=stub,
        ):
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(jsonl), "--skip-consolidation"],
            )

        assert result.exit_code == 0, result.output
        assert "shutdown" in result.output.lower()

    def test_cli_multiple_transcripts(self, tmp_path: Path) -> None:
        """Multiple JSONL paths are forwarded as a list."""
        runner = CliRunner()
        jsonls = [_make_jsonl(tmp_path, f"s{i}.jsonl") for i in range(1, 3)]
        stub = self._make_stub_result(transcripts_processed=2, sessions_archived=2)

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            return_value=stub,
        ) as mock_fn:
            result = runner.invoke(
                entity,
                ["ingest-transcript", "student", str(jsonls[0]), str(jsonls[1])],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_fn.call_args.kwargs
        assert len(call_kwargs.get("jsonl_paths", [])) == 2

    def test_cli_project_context_forwarded(self, tmp_path: Path) -> None:
        """--project-context option is forwarded correctly."""
        runner = CliRunner()
        jsonl = _make_jsonl(tmp_path)
        stub = self._make_stub_result()

        with patch(
            "entity_from_transcript.ingest_transcripts_into_entity",
            return_value=stub,
        ) as mock_fn:
            result = runner.invoke(
                entity,
                [
                    "ingest-transcript", "student", str(jsonl),
                    "--project-context", "vibe-engineer codebase",
                ],
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_fn.call_args.kwargs
        assert call_kwargs.get("project_context") == "vibe-engineer codebase"
