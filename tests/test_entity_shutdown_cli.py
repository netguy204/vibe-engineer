"""Tests for the `ve entity shutdown` CLI command."""

import json
import pathlib
from unittest.mock import patch

from click.testing import CliRunner

from entities import Entities
from ve import cli


class TestEntityShutdownCLI:
    def _setup_entity(self, tmp_path):
        """Create a legacy entity (no wiki/) for testing the legacy pipeline."""
        # Create entity directory structure without wiki/ so it routes to legacy pipeline
        entity_dir = tmp_path / ".entities" / "testbot"
        entity_dir.mkdir(parents=True)
        from models.entity import MemoryTier
        memories_dir = entity_dir / "memories"
        for tier in MemoryTier:
            (memories_dir / tier.value).mkdir(parents=True)
        (entity_dir / "identity.md").write_text("---\nname: testbot\n---\n")
        return Entities(tmp_path)

    def _make_memories_file(self, tmp_path, count=5):
        """Create a JSON file with extracted memories."""
        memories = [
            {
                "title": f"Memory {i}",
                "content": f"Content {i}",
                "category": "skill",
                "valence": "positive",
                "salience": 3,
            }
            for i in range(count)
        ]
        mem_file = tmp_path / "memories.json"
        mem_file.write_text(json.dumps(memories))
        return mem_file

    @patch("entity_shutdown.anthropic")
    def test_shutdown_with_memories_file(self, mock_anthropic, tmp_path):
        """Successful shutdown with --memories-file."""
        self._setup_entity(tmp_path)
        mem_file = self._make_memories_file(tmp_path)

        # Mock API
        mock_client = mock_anthropic.Anthropic.return_value
        mock_response = type("R", (), {
            "content": [type("C", (), {"text": json.dumps({
                "consolidated": [], "core": [], "unconsolidated": []
            })})]
        })
        mock_client.messages.create.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--memories-file", str(mem_file),
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Shutdown complete" in result.output
        assert "Journals added:" in result.output

    def test_shutdown_entity_not_found(self, tmp_path):
        """Fails when entity doesn't exist."""
        mem_file = tmp_path / "memories.json"
        mem_file.write_text('[{"title": "M", "content": "C", "category": "skill", "valence": "neutral", "salience": 3}]')

        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "shutdown", "nonexistent",
            "--memories-file", str(mem_file),
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_shutdown_empty_stdin_treated_as_empty_array(self, tmp_path):
        """Empty stdin is treated as empty array (no-op with no existing journals)."""
        self._setup_entity(tmp_path)

        runner = CliRunner()
        # CliRunner provides empty stdin (not a TTY), which gets treated as "[]"
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Shutdown complete" in result.output

    def test_shutdown_skips_consolidation_few_memories(self, tmp_path):
        """With <3 memories and no existing tiers, skips API call."""
        self._setup_entity(tmp_path)
        mem_file = self._make_memories_file(tmp_path, count=2)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--memories-file", str(mem_file),
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Journals added:  2" in result.output
        assert "Consolidated:    0" in result.output

    @patch("entity_shutdown.anthropic")
    def test_shutdown_stdin_input(self, mock_anthropic, tmp_path):
        """Reads memories from stdin when no --memories-file."""
        self._setup_entity(tmp_path)

        mock_client = mock_anthropic.Anthropic.return_value
        mock_response = type("R", (), {
            "content": [type("C", (), {"text": json.dumps({
                "consolidated": [], "core": [], "unconsolidated": []
            })})]
        })
        mock_client.messages.create.return_value = mock_response

        memories_json = json.dumps([
            {
                "title": "Stdin memory",
                "content": "From stdin",
                "category": "domain",
                "valence": "neutral",
                "salience": 2,
            }
            for _ in range(3)
        ])

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["entity", "shutdown", "testbot", "--project-dir", str(tmp_path)],
            input=memories_json,
        )

        assert result.exit_code == 0
        assert "Journals added:  3" in result.output

    # -------------------------------------------------------------------
    # Chunk: docs/chunks/entity_shutdown_silent_failure - Journal disk assertions
    # -------------------------------------------------------------------

    def test_shutdown_journals_exist_on_disk(self, tmp_path):
        """Journal files physically exist in memories/journal/ after shutdown."""
        self._setup_entity(tmp_path)
        mem_file = self._make_memories_file(tmp_path, count=2)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--memories-file", str(mem_file),
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code == 0
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        journals = list(journal_dir.glob("*.md"))
        assert len(journals) == 2, f"Expected 2 journal files, found {len(journals)}: {journals}"

    def test_shutdown_from_subdirectory_resolves_project_root(self, tmp_path, monkeypatch):
        """Shutdown from a subdirectory without --project-dir finds the project root."""
        # Create entity at the project root
        self._setup_entity(tmp_path)
        mem_file = self._make_memories_file(tmp_path, count=2)

        # Create a .git directory so resolve_project_root can find the root
        (tmp_path / ".git").mkdir()

        # Create and chdir to a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        runner = CliRunner()
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--memories-file", str(mem_file),
            # No --project-dir: should resolve up to tmp_path via .git
        ])

        assert result.exit_code == 0, f"Exit code {result.exit_code}, output: {result.output}"
        assert "Journals added:  2" in result.output

        # Journals should exist at the project root, not in the subdirectory
        journal_dir = tmp_path / ".entities" / "testbot" / "memories" / "journal"
        journals = list(journal_dir.glob("*.md"))
        assert len(journals) == 2, f"Expected 2 journal files at project root, found {len(journals)}"

        # No phantom .entities directory should exist in the subdirectory
        assert not (subdir / ".entities").exists(), "Phantom .entities created in subdirectory"

    # -------------------------------------------------------------------
    # Chunk: docs/chunks/entity_consolidate_existing
    # -------------------------------------------------------------------

    @patch("entity_shutdown.anthropic")
    def test_shutdown_empty_input_consolidates_existing(self, mock_anthropic, tmp_path):
        """Empty JSON array input triggers consolidation of existing journals."""
        from models.entity import MemoryCategory, MemoryFrontmatter, MemoryTier, MemoryValence
        from datetime import datetime, timezone

        entities = self._setup_entity(tmp_path)

        # Write pre-existing journal files
        for i in range(3):
            fm = MemoryFrontmatter(
                title=f"Existing journal {i}",
                category=MemoryCategory.SKILL,
                valence=MemoryValence.POSITIVE,
                salience=3,
                tier=MemoryTier.JOURNAL,
                last_reinforced=datetime.now(timezone.utc),
                recurrence_count=0,
                source_memories=[],
            )
            entities.write_memory("testbot", fm, f"Content {i}")

        # Mock API
        mock_client = mock_anthropic.Anthropic.return_value
        mock_response = type("R", (), {
            "content": [type("C", (), {"text": json.dumps({
                "consolidated": [{
                    "title": "Merged",
                    "content": "Combined.",
                    "valence": "positive",
                    "category": "skill",
                    "salience": 4,
                    "tier": "consolidated",
                    "source_memories": ["Existing journal 0", "Existing journal 1"],
                    "recurrence_count": 2,
                    "last_reinforced": datetime.now(timezone.utc).isoformat(),
                }],
                "core": [],
                "unconsolidated": ["Existing journal 2"],
            })})]
        })
        mock_client.messages.create.return_value = mock_response

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["entity", "shutdown", "testbot", "--project-dir", str(tmp_path)],
            input="[]",
        )

        assert result.exit_code == 0
        assert "Shutdown complete" in result.output
        assert "Journals processed:" in result.output


class TestEntityShutdownWikiCLI:
    """Tests for wiki-based entity shutdown via CLI."""

    def _setup_wiki_entity(self, tmp_path):
        """Create an entity with wiki/ directory for testing."""
        import subprocess
        entity_dir = tmp_path / ".entities" / "wikibot"
        entity_dir.mkdir(parents=True)
        wiki_dir = entity_dir / "wiki"
        wiki_dir.mkdir()
        (wiki_dir / "identity.md").write_text("# Identity\nInitial content.\n")
        # Init git repo in entity dir
        subprocess.run(["git", "init", "-b", "main"], cwd=entity_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=entity_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=entity_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=entity_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=entity_dir, check=True, capture_output=True)
        return entity_dir

    def test_wiki_shutdown_requires_no_memories_file(self, tmp_path):
        """Wiki entity shutdown succeeds without --memories-file."""
        self._setup_wiki_entity(tmp_path)

        mock_result = {"journals_added": 0, "consolidated": 0, "core": 0, "skipped": "no wiki changes"}
        with patch("entity_shutdown.run_wiki_consolidation", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(cli, [
                "entity", "shutdown", "wikibot",
                "--project-dir", str(tmp_path),
            ])

        assert result.exit_code == 0
        assert "Shutdown complete" in result.output

    def test_legacy_shutdown_without_memories_raises_error(self, tmp_path):
        """Legacy entity shutdown without memories raises a ValueError surfaced as ClickException."""
        # Create a legacy entity manually (no wiki/)
        entity_dir = tmp_path / ".entities" / "legacybot"
        entity_dir.mkdir(parents=True)
        (entity_dir / "memories").mkdir()

        # The CliRunner provides non-TTY stdin, which the CLI will read as empty string "[]".
        # To test the error path, directly test the run_shutdown function.
        from entity_shutdown import run_shutdown
        import pytest as _pytest
        with _pytest.raises(ValueError, match="legacy entity"):
            run_shutdown("legacybot", tmp_path, extracted_memories_json=None)
