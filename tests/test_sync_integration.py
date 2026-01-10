"""Integration tests for ve sync command.

These tests exercise the full sync flow end-to-end.
"""

import subprocess

import pytest
import yaml
from click.testing import CliRunner

from ve import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def full_task_directory(tmp_path, tmp_path_factory):
    """Create a full task directory setup for integration testing.

    This fixture creates:
    - An external chunk repo with a proper git history
    - Two project repos with external chunk references
    - Proper .ve-task.yaml configuration
    """
    task_dir = tmp_path

    # Create external chunk repo with proper structure
    external_repo = tmp_path_factory.mktemp("external")
    subprocess.run(["git", "init"], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Create chunk structure in external repo
    chunks_dir = external_repo / "docs" / "chunks" / "0001-shared_feature"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "GOAL.md").write_text(
        "---\n"
        "status: IMPLEMENTING\n"
        "ticket: null\n"
        "---\n"
        "# Shared Feature\n\n"
        "This is a shared feature for testing.\n"
    )

    subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add shared feature chunk"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Get external repo SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=external_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    external_sha = result.stdout.strip()

    # Symlink external repo into task dir
    (task_dir / "chunks-repo").symlink_to(external_repo)

    # Create project repos
    project_dirs = {}
    for project_name in ["service-a", "service-b"]:
        project_dir = tmp_path_factory.mktemp(project_name)
        subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        (project_dir / "README.md").write_text(f"# {project_name}\n")
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )

        # Symlink into task dir
        (task_dir / project_name).symlink_to(project_dir)

        # Create external chunk reference with outdated SHA
        chunks_dir = project_dir / "docs" / "chunks" / "0001-shared_feature"
        chunks_dir.mkdir(parents=True)
        outdated_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: acme/chunks-repo\n"
            f"chunk: 0001-shared_feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"
        )

        project_dirs[project_name] = project_dir

    # Create .ve-task.yaml
    (task_dir / ".ve-task.yaml").write_text(
        "external_chunk_repo: acme/chunks-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
        "  - acme/service-b\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
        "project_dirs": project_dirs,
    }


class TestEndToEndTaskDirectory:
    """End-to-end tests for task directory sync."""

    def test_full_sync_updates_all_projects(self, runner, full_task_directory):
        """Full sync updates external.yaml in all projects."""
        task_dir = full_task_directory["task_dir"]
        expected_sha = full_task_directory["external_sha"]
        project_dirs = full_task_directory["project_dirs"]

        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "Updated 2 of 2" in result.output

        # Verify both projects were updated
        for project_name, project_dir in project_dirs.items():
            external_yaml = (
                project_dir / "docs" / "chunks" / "0001-shared_feature" / "external.yaml"
            )
            content = yaml.safe_load(external_yaml.read_text())
            assert content["pinned"] == expected_sha, f"{project_name} not updated"

    def test_sync_after_external_commit(self, runner, full_task_directory):
        """Sync updates to new SHA after commit in external repo."""
        task_dir = full_task_directory["task_dir"]
        external_repo = full_task_directory["external_repo"]
        project_dirs = full_task_directory["project_dirs"]

        # First sync to current state
        runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        # Make a new commit in external repo
        (external_repo / "docs" / "chunks" / "0001-shared_feature" / "PLAN.md").write_text(
            "# Implementation Plan\n\nThis is the plan.\n"
        )
        subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add plan"],
            cwd=external_repo,
            check=True,
            capture_output=True,
        )

        # Get new SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=external_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        new_sha = result.stdout.strip()

        # Sync again
        result = runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        assert result.exit_code == 0
        assert "Updated 2 of 2" in result.output

        # Verify projects updated to new SHA
        for project_name, project_dir in project_dirs.items():
            external_yaml = (
                project_dir / "docs" / "chunks" / "0001-shared_feature" / "external.yaml"
            )
            content = yaml.safe_load(external_yaml.read_text())
            assert content["pinned"] == new_sha, f"{project_name} not updated to new SHA"

    def test_yaml_serialization_correct(self, runner, full_task_directory):
        """Verify YAML serialization doesn't add extra fields or corrupt format."""
        task_dir = full_task_directory["task_dir"]
        project_dirs = full_task_directory["project_dirs"]

        runner.invoke(cli, ["sync", "--project-dir", str(task_dir)])

        for project_dir in project_dirs.values():
            external_yaml = (
                project_dir / "docs" / "chunks" / "0001-shared_feature" / "external.yaml"
            )
            content = yaml.safe_load(external_yaml.read_text())

            # Should only have the expected fields
            expected_keys = {"repo", "chunk", "track", "pinned"}
            assert set(content.keys()) == expected_keys

            # Values should be correct types
            assert isinstance(content["repo"], str)
            assert isinstance(content["chunk"], str)
            assert isinstance(content["track"], str)
            assert isinstance(content["pinned"], str)
            assert len(content["pinned"]) == 40


class TestEndToEndSingleRepo:
    """End-to-end tests for single repo sync."""

    def test_single_repo_sync_with_real_remote(self, runner, tmp_path):
        """Sync single repo using git ls-remote against a real public repo."""
        # Create a git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("# Test\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create external reference to a real public repo
        chunks_dir = tmp_path / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        old_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: octocat/Hello-World\n"
            f"chunk: 0001-feature\n"
            f"track: master\n"
            f"pinned: '{old_sha}'\n"
        )

        result = runner.invoke(cli, ["sync", "--project-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Updated 1 of 1" in result.output

        # Verify SHA was updated to a valid 40-char hex
        content = yaml.safe_load((chunks_dir / "external.yaml").read_text())
        assert len(content["pinned"]) == 40
        assert content["pinned"] != old_sha
        assert all(c in "0123456789abcdef" for c in content["pinned"])
