"""Tests for entity CLI commands.

Tests `ve entity create`, `ve entity list`, `ve entity startup`,
`ve entity recall`, and `ve entity touch` commands.
"""

import json
import pathlib
from datetime import datetime, timezone

import pytest
from click.testing import CliRunner

from entities import Entities
from models.entity import MemoryCategory, MemoryFrontmatter, MemoryTier, MemoryValence
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
    """Tests for `ve entity create` (git-repo-based).

    These tests verify the updated create command which produces a standalone
    git repo. See test_entity_create_cli.py for comprehensive coverage.
    """

    def test_creates_entity_git_repo(self, runner, tmp_path):
        """Creates a standalone git repo with ENTITY.md."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "mysteward" in result.output

        repo_dir = tmp_path / "mysteward"
        assert repo_dir.is_dir()
        assert (repo_dir / "ENTITY.md").is_file()
        assert (repo_dir / "wiki").is_dir()
        assert (repo_dir / "memories").is_dir()

    def test_creates_entity_with_role(self, runner, tmp_path):
        """Creates entity with role description in ENTITY.md."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--role", "Project steward for code reviews",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code == 0

        content = (tmp_path / "mysteward" / "ENTITY.md").read_text()
        assert "Project steward for code reviews" in content

    def test_duplicate_entity_fails(self, runner, tmp_path):
        """Second creation of same entity fails with error."""
        runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--output-dir", str(tmp_path),
        ])
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_invalid_name_fails(self, runner, tmp_path):
        """Invalid entity name fails with validation error."""
        result = runner.invoke(cli, [
            "entity", "create", "bad name",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code != 0
        assert "Invalid entity name" in result.output

    def test_invalid_name_uppercase_fails(self, runner, tmp_path):
        """Uppercase entity name fails."""
        result = runner.invoke(cli, [
            "entity", "create", "BadName",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code != 0

    def test_output_includes_path(self, runner, tmp_path):
        """Output includes the entity name/path."""
        result = runner.invoke(cli, [
            "entity", "create", "mysteward",
            "--output-dir", str(tmp_path),
        ])
        assert result.exit_code == 0
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
        entities = Entities(temp_project)
        entities.create_entity("alpha")
        entities.create_entity("beta")

        result = runner.invoke(cli, [
            "entity", "list",
            "--project-dir", str(temp_project),
        ])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_lists_with_roles(self, runner, temp_project):
        """Lists entities with their roles."""
        entities = Entities(temp_project)
        entities.create_entity("mysteward", role="Code reviewer")

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
        Entities(temp_project).create_entity("mysteward", role="Project steward")
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
        Entities(temp_project).create_entity("agent")
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
