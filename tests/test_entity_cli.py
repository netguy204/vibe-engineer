"""Tests for entity CLI commands.

Tests `ve entity create`, `ve entity list`, and `ve entity touch` commands.
"""

import json
import pathlib
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from entities import Entities
from models.entity import MemoryCategory, MemoryFrontmatter, MemoryTier, MemoryValence
from ve import cli


@pytest.fixture
def runner():
    return CliRunner()


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


class TestEntityTouch:
    """Tests for `ve entity touch`."""

    def _setup_entity_with_core_memory(self, temp_project):
        """Helper: create an entity with a core memory, return (entities, memory_path)."""
        entities = Entities(temp_project)
        entities.create_entity("mysteward")
        memory = _make_memory(tier="core", title="Verify state before acting")
        path = entities.write_memory("mysteward", memory, "Always check state first.")
        return entities, path

    def test_touches_core_memory(self, runner, temp_project):
        """Touches a core memory and echoes confirmation."""
        _, path = self._setup_entity_with_core_memory(temp_project)

        result = runner.invoke(cli, [
            "entity", "touch", "mysteward", path.stem,
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "Touched" in result.output
        assert "Verify state before acting" in result.output
        assert "last_reinforced updated" in result.output

    def test_touch_with_reason(self, runner, temp_project):
        """Touches a memory with a reason argument."""
        _, path = self._setup_entity_with_core_memory(temp_project)

        result = runner.invoke(cli, [
            "entity", "touch", "mysteward", path.stem,
            "applying lifecycle rule",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "Touched" in result.output

        # Verify reason was recorded in log
        log_path = temp_project / ".entities" / "mysteward" / "touch_log.jsonl"
        event_data = json.loads(log_path.read_text().strip())
        assert event_data["reason"] == "applying lifecycle rule"

    def test_missing_entity_fails(self, runner, temp_project):
        """Missing entity exits non-zero with error."""
        result = runner.invoke(cli, [
            "entity", "touch", "nonexistent", "some_memory",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_missing_memory_fails(self, runner, temp_project):
        """Missing memory exits non-zero with error."""
        entities = Entities(temp_project)
        entities.create_entity("mysteward")

        result = runner.invoke(cli, [
            "entity", "touch", "mysteward", "nonexistent_memory",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_touch_creates_log_file(self, runner, temp_project):
        """Touch creates touch_log.jsonl with correct content."""
        _, path = self._setup_entity_with_core_memory(temp_project)

        runner.invoke(cli, [
            "entity", "touch", "mysteward", path.stem,
            "--project-dir", str(temp_project),
        ])

        log_path = temp_project / ".entities" / "mysteward" / "touch_log.jsonl"
        assert log_path.exists()
        event_data = json.loads(log_path.read_text().strip())
        assert event_data["memory_id"] == path.stem
        assert event_data["memory_title"] == "Verify state before acting"
        assert "timestamp" in event_data
