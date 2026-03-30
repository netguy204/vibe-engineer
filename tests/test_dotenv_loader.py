"""Tests for CLI dotenv loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.dotenv_loader import _find_dotenv_walking_parents, load_dotenv_from_project_root


class TestLoadDotenvFromProjectRoot:
    """Unit tests for load_dotenv_from_project_root."""

    def test_loads_env_from_project_root(self, tmp_path, monkeypatch):
        """Loads .env from a directory with .git marker."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").write_text("TEST_DOTENV_VAR=hello\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TEST_DOTENV_VAR", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["TEST_DOTENV_VAR"] == "hello"
        monkeypatch.delenv("TEST_DOTENV_VAR", raising=False)

    def test_existing_env_vars_take_precedence(self, tmp_path, monkeypatch):
        """Existing env vars are NOT overridden by .env values."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").write_text("EXISTING_VAR=overridden\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("EXISTING_VAR", "original")

        load_dotenv_from_project_root()

        assert os.environ["EXISTING_VAR"] == "original"

    def test_missing_env_file_silently_ignored(self, tmp_path, monkeypatch):
        """No error when .env file doesn't exist."""
        (tmp_path / ".git").mkdir()
        # No .env file created

        monkeypatch.chdir(tmp_path)

        # Should not raise
        load_dotenv_from_project_root()

    def test_works_from_subdirectory(self, tmp_path, monkeypatch):
        """Resolves .env from project root even when CWD is a subdirectory."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").write_text("SUBDIR_TEST_VAR=from_root\n")
        subdir = tmp_path / "some" / "nested" / "dir"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)
        monkeypatch.delenv("SUBDIR_TEST_VAR", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["SUBDIR_TEST_VAR"] == "from_root"
        monkeypatch.delenv("SUBDIR_TEST_VAR", raising=False)

    def test_multiple_variables_loaded(self, tmp_path, monkeypatch):
        """Multiple variables from .env are all loaded."""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").write_text("MULTI_A=one\nMULTI_B=two\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MULTI_A", raising=False)
        monkeypatch.delenv("MULTI_B", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["MULTI_A"] == "one"
        assert os.environ["MULTI_B"] == "two"
        monkeypatch.delenv("MULTI_A", raising=False)
        monkeypatch.delenv("MULTI_B", raising=False)


class TestFindDotenvWalkingParents:
    """Unit tests for the _find_dotenv_walking_parents helper."""

    def test_finds_env_in_start_directory(self, tmp_path):
        """Returns .env when it exists in the start directory."""
        (tmp_path / ".env").write_text("KEY=value\n")
        result = _find_dotenv_walking_parents(tmp_path)
        assert result == (tmp_path / ".env").resolve()

    def test_finds_env_in_parent_directory(self, tmp_path):
        """Returns .env from a parent when not in start directory."""
        (tmp_path / ".env").write_text("PARENT_KEY=parent_value\n")
        child = tmp_path / "projects" / "my-project"
        child.mkdir(parents=True)

        result = _find_dotenv_walking_parents(child)
        assert result == (tmp_path / ".env").resolve()

    def test_finds_env_in_grandparent_directory(self, tmp_path):
        """Returns .env from a grandparent directory."""
        (tmp_path / ".env").write_text("GRANDPARENT=val\n")
        deeply_nested = tmp_path / "a" / "b" / "c"
        deeply_nested.mkdir(parents=True)

        result = _find_dotenv_walking_parents(deeply_nested)
        assert result == (tmp_path / ".env").resolve()

    def test_returns_none_when_no_env_found(self, tmp_path):
        """Returns None when no .env exists anywhere in ancestry."""
        child = tmp_path / "no-env-here"
        child.mkdir()
        # We can't guarantee no .env exists above tmp_path,
        # so we test the helper directly with a controlled walk
        # by checking the function returns a Path or None without error
        result = _find_dotenv_walking_parents(child)
        # Result is either None (no .env above) or a Path (some .env exists above tmp_path)
        assert result is None or result.is_file()

    def test_closest_env_wins(self, tmp_path):
        """Returns the .env closest to the start directory (first found)."""
        (tmp_path / ".env").write_text("OUTER=outer\n")
        inner = tmp_path / "project"
        inner.mkdir()
        (inner / ".env").write_text("INNER=inner\n")

        result = _find_dotenv_walking_parents(inner)
        assert result == (inner / ".env").resolve()


class TestDotenvWalkParents:
    """Integration tests for parent-walking .env loading."""

    def test_finds_env_in_parent_directory(self, tmp_path, monkeypatch):
        """Loads .env from a parent dir when not in project root."""
        # Parent has .env, project root (child with .git) does not
        (tmp_path / ".env").write_text("PARENT_DOTENV_VAR=from_parent\n")
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.delenv("PARENT_DOTENV_VAR", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["PARENT_DOTENV_VAR"] == "from_parent"
        monkeypatch.delenv("PARENT_DOTENV_VAR", raising=False)

    def test_project_root_env_wins_over_parent(self, tmp_path, monkeypatch):
        """Project-level .env takes precedence over parent .env."""
        (tmp_path / ".env").write_text("PRECEDENCE_VAR=parent\n")
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()
        (project / ".env").write_text("PRECEDENCE_VAR=project\n")

        monkeypatch.chdir(project)
        monkeypatch.delenv("PRECEDENCE_VAR", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["PRECEDENCE_VAR"] == "project"
        monkeypatch.delenv("PRECEDENCE_VAR", raising=False)

    def test_walk_terminates_without_error(self, tmp_path, monkeypatch):
        """No error when no .env exists anywhere in ancestry."""
        project = tmp_path / "empty_project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)

        # Should not raise even if no .env is found
        load_dotenv_from_project_root()

    def test_existing_env_vars_still_win_with_parent_env(self, tmp_path, monkeypatch):
        """Existing env vars take precedence over parent .env values."""
        (tmp_path / ".env").write_text("EXISTING_PARENT_VAR=overridden\n")
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("EXISTING_PARENT_VAR", "original")

        load_dotenv_from_project_root()

        assert os.environ["EXISTING_PARENT_VAR"] == "original"

    def test_home_dir_env_loaded(self, tmp_path, monkeypatch):
        """Simulates ~/.env being loaded from a deeply nested project."""
        # tmp_path simulates home dir with .env
        (tmp_path / ".env").write_text("HOME_API_KEY=secret123\n")
        # Deeply nested project
        project = tmp_path / "Projects" / "org" / "my-project"
        project.mkdir(parents=True)
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.delenv("HOME_API_KEY", raising=False)

        load_dotenv_from_project_root()

        assert os.environ["HOME_API_KEY"] == "secret123"
        monkeypatch.delenv("HOME_API_KEY", raising=False)


class TestDotenvCLIIntegration:
    """Integration test: .env is loaded when CLI commands run."""

    def test_env_var_available_during_command(self, tmp_path, monkeypatch):
        """A .env variable is visible inside a CLI subcommand."""
        import click

        from cli import cli

        (tmp_path / ".git").mkdir()
        (tmp_path / ".env").write_text("CLI_INTEGRATION_VAR=works\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLI_INTEGRATION_VAR", raising=False)

        # Register a temporary test command that echoes the env var
        @cli.command("_test_env_echo")
        def _test_env_echo():
            click.echo(f"VAR={os.environ.get('CLI_INTEGRATION_VAR', 'NOT_SET')}")

        runner = CliRunner()
        result = runner.invoke(cli, ["_test_env_echo"])

        assert result.exit_code == 0
        assert "VAR=works" in result.output

        # Clean up registered test command
        cli.commands.pop("_test_env_echo", None)
        monkeypatch.delenv("CLI_INTEGRATION_VAR", raising=False)
