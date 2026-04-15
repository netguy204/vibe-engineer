"""Tests for the updated `ve entity create` CLI command (git-repo-based).

# Chunk: docs/chunks/entity_repo_structure - CLI tests for standalone entity repo creation

The updated `ve entity create` creates a standalone git repo in the working
directory (or --output-dir) instead of a subdirectory of .entities/.
"""

import pathlib

import pytest
from click.testing import CliRunner

from entity_repo import is_entity_repo, read_entity_metadata
from ve import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestEntityCreateCommand:
    """Tests for updated `ve entity create` command."""

    def test_create_command_produces_git_repo_in_cwd(self, runner, tmp_path):
        """Invoking `ve entity create my_agent --output-dir <dir>` creates a git repo."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (tmp_path / "my_agent").is_dir()

    def test_create_command_with_output_dir(self, runner, tmp_path):
        """--output-dir creates the repo in the specified directory."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"Output: {result.output}"
        repo_path = tmp_path / "my_agent"
        assert repo_path.is_dir()
        assert is_entity_repo(repo_path)

    def test_create_command_output_shows_path(self, runner, tmp_path):
        """CLI stdout contains the repo path."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "my_agent" in result.output

    def test_create_command_rejects_invalid_name(self, runner, tmp_path):
        """CLI exits non-zero with a helpful error message for invalid names."""
        result = runner.invoke(
            cli,
            ["entity", "create", "123invalid", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code != 0
        assert "Invalid entity name" in result.output

    def test_create_command_with_role(self, runner, tmp_path):
        """--role causes role to appear in ENTITY.md."""
        result = runner.invoke(
            cli,
            [
                "entity", "create", "my_agent",
                "--role", "Infrastructure expert",
                "--output-dir", str(tmp_path),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        metadata = read_entity_metadata(tmp_path / "my_agent")
        assert metadata.role == "Infrastructure expert"

    def test_create_command_produces_valid_git_repo(self, runner, tmp_path):
        """Created directory is a valid entity git repo."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        repo_path = tmp_path / "my_agent"
        assert is_entity_repo(repo_path)

    def test_create_command_kebab_case_name(self, runner, tmp_path):
        """Kebab-case entity names are accepted by the CLI."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my-specialist", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (tmp_path / "my-specialist").is_dir()

    def test_create_command_duplicate_fails(self, runner, tmp_path):
        """Second creation of the same entity name exits non-zero."""
        runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
        )
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_create_command_no_project_dir_required(self, runner, tmp_path):
        """The new create command does not require --project-dir."""
        result = runner.invoke(
            cli,
            ["entity", "create", "my_agent", "--output-dir", str(tmp_path)],
            catch_exceptions=False,
        )
        # Should succeed without any --project-dir
        assert result.exit_code == 0
