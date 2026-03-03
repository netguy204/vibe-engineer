"""Shared pytest fixtures for vibe-engineer tests."""

import os
import pathlib
import subprocess
import tempfile

import pytest
from click.testing import CliRunner

from ve import cli
from chunks import Chunks
from project import Project, InitResult


@pytest.fixture(autouse=True)
def clean_git_environment(monkeypatch):
    """Remove GIT_DIR and GIT_WORK_TREE env vars during tests.

    These environment variables can leak from worktree context and cause
    git commands to target the wrong repository during tests. This fixture
    runs automatically for all tests.
    """
    for var in list(os.environ.keys()):
        if var.startswith("GIT_"):
            monkeypatch.delenv(var, raising=False)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


def make_ve_initialized_git_repo(path, remote_url=None):
    """Helper to create a VE-initialized git repository with a commit.

    Creates a git repo with docs/{chunks,narratives,investigations,subsystems}
    directories and an initial commit so HEAD exists.

    Note: Relies on clean_git_environment fixture to remove GIT_DIR/GIT_WORK_TREE
    environment variables that could interfere with git commands.

    Args:
        path: Path where the repository will be created
        remote_url: Optional remote URL to configure as 'origin'
    """
    path.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    # Create all workflow artifact directories
    (path / "docs" / "chunks").mkdir(parents=True)
    (path / "docs" / "narratives").mkdir(parents=True)
    (path / "docs" / "investigations").mkdir(parents=True)
    (path / "docs" / "subsystems").mkdir(parents=True)
    # Create initial commit so HEAD exists
    (path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    # Optionally configure remote origin
    if remote_url is not None:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=path,
            check=True,
            capture_output=True,
        )


def setup_task_directory(tmp_path, external_name="ext", project_names=None):
    """Create a complete task directory setup for testing.

    Args:
        tmp_path: Base temporary directory
        external_name: Name for the external repo directory
        project_names: List of project directory names (default: ["proj"])

    Returns:
        tuple: (task_dir, external_path, project_paths)
    """
    if project_names is None:
        project_names = ["proj"]

    task_dir = tmp_path

    # Create external repo
    external_path = task_dir / external_name
    make_ve_initialized_git_repo(external_path)

    # Create project repos
    project_paths = []
    for name in project_names:
        project_path = task_dir / name
        make_ve_initialized_git_repo(project_path)
        project_paths.append(project_path)

    # Create .ve-task.yaml
    projects_yaml = "\n".join(f"  - acme/{name}" for name in project_names)
    config_content = f"""external_artifact_repo: acme/{external_name}
projects:
{projects_yaml}
"""
    (task_dir / ".ve-task.yaml").write_text(config_content)

    return task_dir, external_path, project_paths


# =============================================================================
# Orchestrator Scheduler Fixtures
# =============================================================================
# These fixtures are used by the orchestrator scheduler test files.
# Extracted from test_orchestrator_scheduler.py for reuse across split files.


@pytest.fixture
def state_store(tmp_path):
    """Create a state store for testing."""
    from orchestrator.state import StateStore

    db_path = tmp_path / "test.db"
    store = StateStore(db_path)
    store.initialize()
    return store


@pytest.fixture
def mock_worktree_manager():
    """Create a mock worktree manager."""
    from pathlib import Path
    from unittest.mock import MagicMock

    manager = MagicMock()
    manager.create_worktree.return_value = Path("/tmp/worktree")
    manager.get_worktree_path.return_value = Path("/tmp/worktree")
    manager.get_log_path.return_value = Path("/tmp/logs")
    manager.worktree_exists.return_value = False
    manager.has_uncommitted_changes.return_value = False
    manager.has_changes.return_value = False
    manager.commit_changes.return_value = True
    return manager


@pytest.fixture
def mock_agent_runner():
    """Create a mock agent runner."""
    from unittest.mock import AsyncMock, MagicMock

    from orchestrator.models import AgentResult

    runner = MagicMock()
    runner.run_phase = AsyncMock(
        return_value=AgentResult(completed=True, suspended=False)
    )
    return runner


@pytest.fixture
def orchestrator_config():
    """Create test config for orchestrator scheduler tests."""
    from orchestrator.models import OrchestratorConfig

    return OrchestratorConfig(max_agents=2, dispatch_interval_seconds=0.1)


@pytest.fixture
def scheduler(state_store, mock_worktree_manager, mock_agent_runner, orchestrator_config, tmp_path):
    """Create a scheduler for testing."""
    from orchestrator.scheduler import Scheduler

    return Scheduler(
        store=state_store,
        worktree_manager=mock_worktree_manager,
        agent_runner=mock_agent_runner,
        config=orchestrator_config,
        project_dir=tmp_path,
    )
