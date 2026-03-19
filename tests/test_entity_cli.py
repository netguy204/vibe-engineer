"""Tests for entity CLI commands.

Tests `ve entity create` and `ve entity list` commands.
"""

import pathlib

import pytest
from click.testing import CliRunner

from ve import cli


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
