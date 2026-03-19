# Chunk: docs/chunks/orch_daemon_root_resolution - CLI integration tests for orch root resolution
"""Tests that orch CLI commands resolve the project root from subdirectories.

Verifies that `ve orch` commands find the daemon at the project root
when invoked from a subdirectory, using the same resolution chain as
board commands: .ve-task.yaml → .git → CWD fallback.
"""

import pathlib
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.orch import orch, resolve_orch_project_dir


# ---------------------------------------------------------------------------
# resolve_orch_project_dir unit tests
# ---------------------------------------------------------------------------


def test_resolve_orch_project_dir_explicit(tmp_path):
    """Explicit --project-dir is used as-is."""
    explicit = tmp_path / "my-project"
    explicit.mkdir()
    assert resolve_orch_project_dir(explicit) == explicit


def test_resolve_orch_project_dir_none_resolves(tmp_path, monkeypatch):
    """When None, resolves using the project root resolution chain."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    result = resolve_orch_project_dir(None)
    assert result == tmp_path


def test_resolve_orch_project_dir_task_over_git(tmp_path, monkeypatch):
    """Task directory takes priority over git root."""
    task_root = tmp_path / "task"
    task_root.mkdir()
    (task_root / ".ve-task.yaml").write_text("projects: []\n")
    (tmp_path / ".git").mkdir()

    subdir = task_root / "sub"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    result = resolve_orch_project_dir(None)
    assert result == task_root


# ---------------------------------------------------------------------------
# CLI integration tests — representative commands
# ---------------------------------------------------------------------------


def test_orch_status_from_subdirectory(tmp_path, monkeypatch):
    """ve orch status resolves the project root from a subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "workers" / "leader-board"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    mock_status = MagicMock()
    mock_status.running = False

    with patch("orchestrator.daemon.get_daemon_status", return_value=mock_status) as mock_get:
        runner = CliRunner()
        result = runner.invoke(orch, ["status"])

        assert result.exit_code == 0
        # Verify it was called with the git root, not the subdirectory
        mock_get.assert_called_once_with(tmp_path)


def test_orch_ps_from_subdirectory(tmp_path, monkeypatch):
    """ve orch ps resolves the project root from a subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "src" / "lib"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    mock_client = MagicMock()
    mock_client.list_work_units.return_value = {"work_units": []}

    with patch("orchestrator.client.create_client", return_value=mock_client) as mock_create:
        runner = CliRunner()
        result = runner.invoke(orch, ["ps"])

        assert result.exit_code == 0
        # Verify create_client was called with the git root
        mock_create.assert_called_once_with(tmp_path)


def test_orch_start_from_subdirectory(tmp_path, monkeypatch):
    """ve orch start resolves the project root from a subdirectory."""
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "deploy"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    with patch("orchestrator.daemon.start_daemon", return_value=(12345, 8080)) as mock_start:
        runner = CliRunner()
        result = runner.invoke(orch, ["start"])

        assert result.exit_code == 0
        # Verify start_daemon was called with the git root
        mock_start.assert_called_once_with(tmp_path, port=0, host="127.0.0.1")


def test_orch_status_with_explicit_project_dir(tmp_path, monkeypatch):
    """Explicit --project-dir overrides resolution."""
    # Set up a git root that would be found by resolution
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    explicit = tmp_path / "other-project"
    explicit.mkdir()

    mock_status = MagicMock()
    mock_status.running = False

    with patch("orchestrator.daemon.get_daemon_status", return_value=mock_status) as mock_get:
        runner = CliRunner()
        result = runner.invoke(orch, ["status", "--project-dir", str(explicit)])

        assert result.exit_code == 0
        # Verify it used the explicit path, not the git root
        mock_get.assert_called_once_with(explicit)


def test_orch_status_task_dir_priority(tmp_path, monkeypatch):
    """Task directory takes priority over git root for orch commands."""
    task_root = tmp_path / "task"
    task_root.mkdir()
    (task_root / ".ve-task.yaml").write_text("projects: []\n")
    (tmp_path / ".git").mkdir()

    subdir = task_root / "deep" / "sub"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)

    mock_status = MagicMock()
    mock_status.running = False

    with patch("orchestrator.daemon.get_daemon_status", return_value=mock_status) as mock_get:
        runner = CliRunner()
        result = runner.invoke(orch, ["status"])

        assert result.exit_code == 0
        mock_get.assert_called_once_with(task_root)
