"""Tests for CLI dotenv loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.dotenv_loader import load_dotenv_from_project_root


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
