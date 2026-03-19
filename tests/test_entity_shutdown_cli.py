"""Tests for the `ve entity shutdown` CLI command."""

import json
import pathlib
from unittest.mock import patch

from click.testing import CliRunner

from entities import Entities
from ve import cli


class TestEntityShutdownCLI:
    def _setup_entity(self, tmp_path):
        """Create an entity for testing."""
        entities = Entities(tmp_path)
        entities.create_entity("testbot", role="Test bot")
        return entities

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

    def test_shutdown_no_input(self, tmp_path):
        """Fails with appropriate error when no memories provided."""
        self._setup_entity(tmp_path)

        runner = CliRunner()
        # Simulate a TTY (no stdin pipe) by using default input
        result = runner.invoke(cli, [
            "entity", "shutdown", "testbot",
            "--project-dir", str(tmp_path),
        ])

        assert result.exit_code != 0
        # CliRunner provides empty stdin (not a TTY), so we get "Empty memories input"
        assert "memories" in result.output.lower()

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
