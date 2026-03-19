"""Tests for entity CLI commands.

Tests `ve entity create`, `ve entity list`, `ve entity startup`,
and `ve entity recall` commands.
"""

import pathlib
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from entities import Entities
from models.entity import MemoryFrontmatter
from ve import cli


def _make_memory(**overrides) -> MemoryFrontmatter:
    """Create a valid MemoryFrontmatter with optional overrides."""
    defaults = {
        "title": "Test memory",
        "category": "correction",
        "valence": "negative",
        "salience": 3,
        "tier": "journal",
        "last_reinforced": datetime.now(timezone.utc),
        "recurrence_count": 1,
    }
    defaults.update(overrides)
    return MemoryFrontmatter(**defaults)


@pytest.fixture
def runner():
    return CliRunner()


class TestEntityCreate:
    """Tests for `ve entity create`."""

    def test_creates_entity(self, runner, temp_project):
        """Creates entity with correct directory structure."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "mysteward" in result.output

        entity_dir = temp_project / ".entities" / "mysteward"
        assert entity_dir.is_dir()
        assert (entity_dir / "identity.md").is_file()
        assert (entity_dir / "memories" / "journal").is_dir()
        assert (entity_dir / "memories" / "consolidated").is_dir()
        assert (entity_dir / "memories" / "core").is_dir()

    def test_creates_entity_with_role(self, runner, temp_project):
        """Creates entity with role description."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--role", "Project steward for code reviews",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0

        content = (temp_project / ".entities" / "mysteward" / "identity.md").read_text()
        assert "Project steward for code reviews" in content

    def test_duplicate_entity_fails(self, runner, temp_project):
        """Second creation of same entity fails with error."""
        runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--project-dir", str(temp_project),
        ])
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_invalid_name_fails(self, runner, temp_project):
        """Invalid entity name fails with validation error."""
        result = runner.invoke(cli, [
            "entity", "create", "bad name",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "Invalid entity name" in result.output

    def test_invalid_name_uppercase_fails(self, runner, temp_project):
        """Uppercase entity name fails."""
        result = runner.invoke(cli, [
            "entity", "create", "BadName",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0

    def test_output_includes_path(self, runner, temp_project):
        """Output includes the entity path."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert ".entities" in result.output
        assert "mysteward" in result.output


class TestEntityList:
    """Tests for `ve entity list`."""

    def test_no_entities(self, runner, temp_project):
        """Shows message when no entities exist."""
        result = runner.invoke(cli, [
            "entity", "list",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "No entities found" in result.output

    def test_lists_created_entities(self, runner, temp_project):
        """Lists entities after creation."""
        runner.invoke(cli, [
            "entity", "create", "alpha",
            "--project-dir", str(temp_project),
        ])
        runner.invoke(cli, [
            "entity", "create", "beta",
            "--project-dir", str(temp_project),
        ])

        result = runner.invoke(cli, [
            "entity", "list",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_lists_with_roles(self, runner, temp_project):
        """Lists entities with their roles."""
        runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--role", "Code reviewer",
            "--project-dir", str(temp_project),
        ])

        result = runner.invoke(cli, [
            "entity", "list",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "mysteward" in result.output
        assert "Code reviewer" in result.output


class TestEntityStartup:
    """Tests for `ve entity startup`."""

    def test_startup_outputs_payload(self, runner, temp_project):
        """Exit code 0, output contains entity name and Core Memories section."""
        runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--role", "Project steward",
            "--project-dir", str(temp_project),
        ])
        result = runner.invoke(cli, [
            "entity", "startup", "mysteward",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "mysteward" in result.output
        assert "Core Memories" in result.output

    def test_startup_nonexistent_entity_fails(self, runner, temp_project):
        """Exit code != 0, error message mentions entity name."""
        result = runner.invoke(cli, [
            "entity", "startup", "ghost",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "ghost" in result.output

    def test_startup_with_memories(self, runner, temp_project):
        """Create entity with core + consolidated memories, verify output contains memory titles."""
        runner.invoke(cli, [
            "entity", "create", "agent",
            "--project-dir", str(temp_project),
        ])
        entities = Entities(temp_project)
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Always verify first", salience=5),
            "Check before acting.",
        )
        entities.write_memory(
            "agent",
            _make_memory(tier="consolidated", title="Pattern recognition skill"),
            "Recognize patterns across sessions.",
        )
        result = runner.invoke(cli, [
            "entity", "startup", "agent",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "Always verify first" in result.output
        assert "Pattern recognition skill" in result.output


class TestEntityRecall:
    """Tests for `ve entity recall`."""

    def test_recall_outputs_matching_memory(self, runner, temp_project):
        """Creates memory, recalls by title, output contains content."""
        runner.invoke(cli, [
            "entity", "create", "agent",
            "--project-dir", str(temp_project),
        ])
        entities = Entities(temp_project)
        entities.write_memory(
            "agent",
            _make_memory(tier="core", title="Template editing workflow"),
            "Always edit source templates.",
        )
        result = runner.invoke(cli, [
            "entity", "recall", "agent", "Template",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "Template editing workflow" in result.output
        assert "Always edit source templates." in result.output

    def test_recall_no_match(self, runner, temp_project):
        """Outputs 'No memories matching' message."""
        runner.invoke(cli, [
            "entity", "create", "agent",
            "--project-dir", str(temp_project),
        ])
        result = runner.invoke(cli, [
            "entity", "recall", "agent", "nonexistent",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "No memories matching" in result.output

    def test_recall_nonexistent_entity_fails(self, runner, temp_project):
        """Error when entity doesn't exist."""
        result = runner.invoke(cli, [
            "entity", "recall", "ghost", "anything",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "ghost" in result.output
