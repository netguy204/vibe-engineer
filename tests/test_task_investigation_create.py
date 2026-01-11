"""Integration tests for task-aware investigation creation.

# Chunk: docs/chunks/task_aware_investigations - Task-aware investigation create tests
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from task_utils import load_external_ref
from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestInvestigationCreateInTaskDirectory:
    """Tests for ve investigation create in task directory context."""

    def test_creates_external_investigation(self, tmp_path):
        """Creates investigation in external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created investigation in external repo" in result.output

        # Verify investigation was created in external repo
        investigation_dir = external_path / "docs" / "investigations" / "memory_leak"
        assert investigation_dir.exists()
        assert (investigation_dir / "OVERVIEW.md").exists()

    def test_creates_external_yaml_in_each_project(self, tmp_path):
        """Creates external.yaml in each project's investigation directory."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify external.yaml in each project
        for project_path in project_paths:
            investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
            assert investigation_dir.exists()
            external_yaml = investigation_dir / "external.yaml"
            assert external_yaml.exists()

            # Verify content
            ref = load_external_ref(investigation_dir)
            assert ref.repo == "acme/ext"
            assert ref.artifact_id == "memory_leak"
            assert ref.track == "main"
            assert len(ref.pinned) == 40  # SHA length

    def test_populates_dependents_in_external_investigation(self, tmp_path):
        """Updates external investigation OVERVIEW.md with dependents list."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify dependents in external investigation OVERVIEW.md
        overview_path = external_path / "docs" / "investigations" / "memory_leak" / "OVERVIEW.md"
        content = overview_path.read_text()

        assert "dependents:" in content
        assert "acme/proj1" in content
        assert "acme/proj2" in content
        assert "memory_leak" in content

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
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify pinned SHA
        investigation_dir = project_paths[0] / "docs" / "investigations" / "memory_leak"
        ref = load_external_ref(investigation_dir)
        assert ref.pinned == expected_sha

    def test_reports_all_created_paths(self, tmp_path):
        """Output includes all created paths."""
        task_dir, _, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created investigation in external repo:" in result.output
        assert "Created reference in acme/proj1:" in result.output
        assert "Created reference in acme/proj2:" in result.output


class TestInvestigationCreateOutsideTaskDirectory:
    """Tests for ve investigation create outside task directory context."""

    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "Created docs/investigations/memory_leak" in result.output

        # Verify regular investigation was created (with OVERVIEW.md, not external.yaml)
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        assert (investigation_dir / "OVERVIEW.md").exists()
        assert not (investigation_dir / "external.yaml").exists()


class TestInvestigationCreateErrorHandling:
    """Tests for error handling in task-aware investigation creation."""

    def test_error_when_external_repo_inaccessible(self, tmp_path):
        """Reports clear error when external repo directory missing."""
        task_dir = tmp_path

        # Create project but not external repo
        project_path = task_dir / "proj"
        make_ve_initialized_git_repo(project_path)

        # Create config referencing missing external repo
        config_content = """external_artifact_repo: acme/missing_ext
projects:
  - acme/proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External" in result.output
        assert "not found" in result.output

    def test_error_when_project_inaccessible(self, tmp_path):
        """Reports clear error when project directory missing."""
        task_dir = tmp_path

        # Create external repo but not project
        external_path = task_dir / "ext"
        make_ve_initialized_git_repo(external_path)

        # Create config referencing missing project
        config_content = """external_artifact_repo: acme/ext
projects:
  - acme/missing_proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
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
        (external_path / "docs" / "investigations").mkdir(parents=True)

        # Create project
        project_path = task_dir / "proj"
        make_ve_initialized_git_repo(project_path)

        config_content = """external_artifact_repo: acme/ext
projects:
  - acme/proj
"""
        (task_dir / ".ve-task.yaml").write_text(config_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "create", "memory_leak", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "Failed to resolve HEAD SHA" in result.output
