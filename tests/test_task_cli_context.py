"""Tests for CLI context warnings when running artifact commands from within task projects.

These tests verify that the CLI emits a warning when artifact creation commands
are run from inside a project directory that is part of a task, suggesting the
user run from the task directory instead.
"""
# Chunk: docs/chunks/taskdir_cli_guidance - CLI context warnings for task projects

import os

import pytest
from click.testing import CliRunner

from ve import cli
from conftest import setup_task_directory


class TestChunkCreateContextWarning:
    """Tests for context warnings when creating chunks from within task projects."""

    def test_warns_when_running_from_project_in_task(self, tmp_path):
        """Warning appears when ve chunk create runs from a project that's part of a task."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "create", "my_chunk", "--project-dir", str(project_path)],
        )

        # Command should still succeed (warning is non-blocking)
        assert result.exit_code == 0
        # But should emit a warning
        assert "Warning:" in result.output
        assert "part of task" in result.output.lower() or "task directory" in result.output.lower()

    def test_no_warning_when_running_from_task_root(self, tmp_path):
        """No warning when ve chunk create runs from task directory."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "create", "my_chunk", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output

    def test_no_warning_for_standalone_project(self, tmp_path):
        """No warning when running from a standalone project (no task context)."""
        from conftest import make_ve_initialized_git_repo

        # Create a standalone project with no task above it
        standalone_project = tmp_path / "standalone"
        make_ve_initialized_git_repo(standalone_project)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "create", "my_chunk", "--project-dir", str(standalone_project)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output

    def test_warning_is_non_blocking(self, tmp_path):
        """The warning does not prevent chunk creation from proceeding."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "create", "my_chunk", "--project-dir", str(project_path)],
        )

        # Command should succeed
        assert result.exit_code == 0
        # Chunk should have been created
        chunk_dir = project_path / "docs" / "chunks" / "my_chunk"
        assert chunk_dir.exists()
        assert (chunk_dir / "GOAL.md").exists()

    def test_warning_includes_task_directory_suggestion(self, tmp_path):
        """Warning suggests running from the task directory."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["chunk", "create", "my_chunk", "--project-dir", str(project_path)],
        )

        assert result.exit_code == 0
        # Warning should suggest running from task directory
        assert "task directory" in result.output.lower()


class TestNarrativeCreateContextWarning:
    """Tests for context warnings when creating narratives from within task projects."""

    def test_warns_when_running_from_project_in_task(self, tmp_path):
        """Warning appears when ve narrative create runs from a project that's part of a task."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(project_path)],
        )

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "part of task" in result.output.lower() or "task directory" in result.output.lower()

    def test_no_warning_when_running_from_task_root(self, tmp_path):
        """No warning when ve narrative create runs from task directory."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output

    def test_no_warning_for_standalone_project(self, tmp_path):
        """No warning when running from a standalone project (no task context)."""
        from conftest import make_ve_initialized_git_repo

        standalone_project = tmp_path / "standalone"
        make_ve_initialized_git_repo(standalone_project)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["narrative", "create", "my_narrative", "--project-dir", str(standalone_project)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output


class TestInvestigationCreateContextWarning:
    """Tests for context warnings when creating investigations from within task projects."""

    def test_warns_when_running_from_project_in_task(self, tmp_path):
        """Warning appears when ve investigation create runs from a project that's part of a task."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["investigation", "create", "my_investigation", "--project-dir", str(project_path)],
        )

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "part of task" in result.output.lower() or "task directory" in result.output.lower()

    def test_no_warning_when_running_from_task_root(self, tmp_path):
        """No warning when ve investigation create runs from task directory."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["investigation", "create", "my_investigation", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output

    def test_no_warning_for_standalone_project(self, tmp_path):
        """No warning when running from a standalone project (no task context)."""
        from conftest import make_ve_initialized_git_repo

        standalone_project = tmp_path / "standalone"
        make_ve_initialized_git_repo(standalone_project)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["investigation", "create", "my_investigation", "--project-dir", str(standalone_project)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output


class TestSubsystemDiscoverContextWarning:
    """Tests for context warnings when discovering subsystems from within task projects."""

    def test_warns_when_running_from_project_in_task(self, tmp_path):
        """Warning appears when ve subsystem discover runs from a project that's part of a task."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "my_subsystem", "--project-dir", str(project_path)],
        )

        assert result.exit_code == 0
        assert "Warning:" in result.output
        assert "part of task" in result.output.lower() or "task directory" in result.output.lower()

    def test_no_warning_when_running_from_task_root(self, tmp_path):
        """No warning when ve subsystem discover runs from task directory."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "my_subsystem", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output

    def test_no_warning_for_standalone_project(self, tmp_path):
        """No warning when running from a standalone project (no task context)."""
        from conftest import make_ve_initialized_git_repo

        standalone_project = tmp_path / "standalone"
        make_ve_initialized_git_repo(standalone_project)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "my_subsystem", "--project-dir", str(standalone_project)],
        )

        assert result.exit_code == 0
        assert "Warning:" not in result.output
