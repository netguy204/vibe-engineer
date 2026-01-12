"""Shared pytest fixtures for vibe-engineer tests."""

import pathlib
import subprocess
import sys
import tempfile

import pytest
from click.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from ve import cli
from chunks import Chunks
from project import Project, InitResult


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

    Args:
        path: Path where the repository will be created
        remote_url: Optional remote URL to configure as 'origin'
    """
    import os

    path.mkdir(parents=True, exist_ok=True)

    # Create a clean environment without GIT_DIR/GIT_WORK_TREE
    # These environment variables can leak from parent context (e.g., worktrees)
    # and cause git to use the wrong repository
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True, env=clean_env)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
        env=clean_env,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
        env=clean_env,
    )
    # Create all workflow artifact directories
    (path / "docs" / "chunks").mkdir(parents=True)
    (path / "docs" / "narratives").mkdir(parents=True)
    (path / "docs" / "investigations").mkdir(parents=True)
    (path / "docs" / "subsystems").mkdir(parents=True)
    # Create initial commit so HEAD exists
    (path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, env=clean_env)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        check=True,
        capture_output=True,
        env=clean_env,
    )
    # Optionally configure remote origin
    if remote_url is not None:
        subprocess.run(
            ["git", "remote", "add", "origin", remote_url],
            cwd=path,
            check=True,
            capture_output=True,
            env=clean_env,
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
