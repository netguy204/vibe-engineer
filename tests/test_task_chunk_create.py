"""Integration tests for task-aware chunk creation."""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from task_utils import load_external_ref, load_task_config


def make_ve_initialized_git_repo(path):
    """Helper to create a VE-initialized git repository with a commit."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
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
    (path / "docs" / "chunks").mkdir(parents=True)
    # Create initial commit so HEAD exists
    (path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def setup_task_directory(tmp_path, external_name="ext", project_names=None):
    """Create a complete task directory setup for testing.

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
    config_content = f"""external_chunk_repo: acme/{external_name}
projects:
{projects_yaml}
"""
    (task_dir / ".ve-task.yaml").write_text(config_content)

    return task_dir, external_path, project_paths


class TestChunkCreateInTaskDirectory:
    """Tests for ve chunk start in task directory context."""

    def test_creates_external_chunk(self, tmp_path):
        """Creates chunk in external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created chunk in external repo" in result.output

        # Verify chunk was created in external repo
        chunk_dir = external_path / "docs" / "chunks" / "0001-auth_token"
        assert chunk_dir.exists()
        assert (chunk_dir / "GOAL.md").exists()

    def test_creates_external_yaml_in_each_project(self, tmp_path):
        """Creates external.yaml in each project's chunk directory."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify external.yaml in each project
        for project_path in project_paths:
            chunk_dir = project_path / "docs" / "chunks" / "0001-auth_token"
            assert chunk_dir.exists()
            external_yaml = chunk_dir / "external.yaml"
            assert external_yaml.exists()

            # Verify content
            ref = load_external_ref(chunk_dir)
            assert ref.repo == "acme/ext"
            assert ref.chunk == "0001-auth_token"
            assert ref.track == "main"
            assert len(ref.pinned) == 40  # SHA length

    def test_populates_dependents_in_external_chunk(self, tmp_path):
        """Updates external chunk GOAL.md with dependents list."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify dependents in external chunk GOAL.md
        goal_path = external_path / "docs" / "chunks" / "0001-auth_token" / "GOAL.md"
        content = goal_path.read_text()

        assert "dependents:" in content
        assert "acme/proj1" in content
        assert "acme/proj2" in content
        assert "0001-auth_token" in content

    def test_uses_correct_sequential_ids_per_project(self, tmp_path):
        """Each project gets its own sequential chunk ID."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Pre-create some chunks in proj2
        proj2_chunks = project_paths[1] / "docs" / "chunks"
        (proj2_chunks / "0001-existing").mkdir()
        (proj2_chunks / "0002-another").mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # proj1 should get 0001, proj2 should get 0003
        assert (project_paths[0] / "docs" / "chunks" / "0001-auth_token").exists()
        assert (project_paths[1] / "docs" / "chunks" / "0003-auth_token").exists()

    def test_resolves_pinned_sha_from_external_repo(self, tmp_path):
        """Pinned SHA matches HEAD of external repo at creation time."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Get expected SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=external_path,
            check=True,
            capture_output=True,
            text=True,
        )
        expected_sha = sha_result.stdout.strip()

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify pinned SHA
        chunk_dir = project_paths[0] / "docs" / "chunks" / "0001-auth_token"
        ref = load_external_ref(chunk_dir)
        assert ref.pinned == expected_sha

    def test_reports_all_created_paths(self, tmp_path):
        """Output includes all created paths."""
        task_dir, _, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created chunk in external repo:" in result.output
        assert "Created reference in acme/proj1:" in result.output
        assert "Created reference in acme/proj2:" in result.output


class TestChunkCreateOutsideTaskDirectory:
    """Tests for ve chunk start outside task directory context."""

    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "my_feature", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "Created docs/chunks/0001-my_feature" in result.output

        # Verify regular chunk was created (with GOAL.md, not external.yaml)
        chunk_dir = project_path / "docs" / "chunks" / "0001-my_feature"
        assert (chunk_dir / "GOAL.md").exists()
        assert not (chunk_dir / "external.yaml").exists()


class TestChunkCreateErrorHandling:
    """Tests for error handling in task-aware chunk creation."""

    def test_error_when_external_repo_inaccessible(self, tmp_path):
        """Reports clear error when external repo directory missing."""
        task_dir = tmp_path

        # Create project but not external repo
        project_path = task_dir / "proj"
        make_ve_initialized_git_repo(project_path)

        # Create config referencing missing external repo
        config_content = """external_chunk_repo: acme/missing_ext
projects:
  - acme/proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External chunk repository" in result.output
        assert "not found" in result.output

    def test_error_when_project_inaccessible(self, tmp_path):
        """Reports clear error when project directory missing."""
        task_dir = tmp_path

        # Create external repo but not project
        external_path = task_dir / "ext"
        make_ve_initialized_git_repo(external_path)

        # Create config referencing missing project
        config_content = """external_chunk_repo: acme/ext
projects:
  - acme/missing_proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "Project directory" in result.output
        assert "not found" in result.output

    def test_error_when_external_repo_not_git(self, tmp_path):
        """Reports clear error when external repo is not a git repository."""
        task_dir = tmp_path

        # Create external dir (not a git repo)
        external_path = task_dir / "ext"
        external_path.mkdir()
        (external_path / "docs" / "chunks").mkdir(parents=True)

        # Create project
        project_path = task_dir / "proj"
        make_ve_initialized_git_repo(project_path)

        config_content = """external_chunk_repo: acme/ext
projects:
  - acme/proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "start", "auth_token", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "Failed to resolve HEAD SHA" in result.output
