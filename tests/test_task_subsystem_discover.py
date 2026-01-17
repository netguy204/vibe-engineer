"""Integration tests for task-aware subsystem discovery.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from task_utils import load_external_ref
from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestSubsystemDiscoverInTaskDirectory:
    """Tests for ve subsystem discover in task directory context."""

    def test_creates_external_subsystem(self, tmp_path):
        """Creates subsystem in external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created subsystem in external repo" in result.output

        # Verify subsystem was created in external repo
        subsystem_dir = external_path / "docs" / "subsystems" / "validation"
        assert subsystem_dir.exists()
        assert (subsystem_dir / "OVERVIEW.md").exists()

    def test_creates_external_yaml_in_each_project(self, tmp_path):
        """Creates external.yaml in each project's subsystem directory."""
        task_dir, _, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify external.yaml in each project
        for project_path in project_paths:
            subsystem_dir = project_path / "docs" / "subsystems" / "validation"
            assert subsystem_dir.exists()
            external_yaml = subsystem_dir / "external.yaml"
            assert external_yaml.exists()

            # Verify content
            ref = load_external_ref(subsystem_dir)
            assert ref.repo == "acme/ext"
            assert ref.artifact_id == "validation"
            assert ref.track == "main"
            assert len(ref.pinned) == 40  # SHA length

    def test_populates_dependents_in_external_subsystem(self, tmp_path):
        """Updates external subsystem OVERVIEW.md with dependents list."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify dependents in external subsystem OVERVIEW.md
        overview_path = external_path / "docs" / "subsystems" / "validation" / "OVERVIEW.md"
        content = overview_path.read_text()

        assert "dependents:" in content
        assert "acme/proj1" in content
        assert "acme/proj2" in content
        assert "validation" in content

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
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0

        # Verify pinned SHA
        subsystem_dir = project_paths[0] / "docs" / "subsystems" / "validation"
        ref = load_external_ref(subsystem_dir)
        assert ref.pinned == expected_sha

    def test_reports_all_created_paths(self, tmp_path):
        """Output includes all created paths."""
        task_dir, _, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "Created subsystem in external repo:" in result.output
        assert "Created reference in acme/proj1:" in result.output
        assert "Created reference in acme/proj2:" in result.output


class TestSubsystemDiscoverOutsideTaskDirectory:
    """Tests for ve subsystem discover outside task directory context."""

    def test_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "discover", "validation", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "Created docs/subsystems/validation" in result.output

        # Verify regular subsystem was created (with OVERVIEW.md, not external.yaml)
        subsystem_dir = project_path / "docs" / "subsystems" / "validation"
        assert (subsystem_dir / "OVERVIEW.md").exists()
        assert not (subsystem_dir / "external.yaml").exists()


class TestSubsystemDiscoverErrorHandling:
    """Tests for error handling in task-aware subsystem creation."""

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
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
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
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
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
        (external_path / "docs" / "subsystems").mkdir(parents=True)

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
            cli, ["subsystem", "discover", "validation", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "Failed to resolve HEAD SHA" in result.output


class TestSubsystemDiscoverSelectiveProjects:
    """Tests for ve subsystem discover with --projects flag."""

    def test_creates_external_yaml_only_in_specified_projects(self, tmp_path):
        """--projects flag creates external.yaml only in specified projects."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2", "proj3"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "subsystem", "discover", "validation",
                "--projects", "proj1,proj3",
                "--project-dir", str(task_dir)
            ],
        )

        assert result.exit_code == 0

        # proj1 and proj3 should have external.yaml
        assert (project_paths[0] / "docs" / "subsystems" / "validation" / "external.yaml").exists()
        assert (project_paths[2] / "docs" / "subsystems" / "validation" / "external.yaml").exists()

        # proj2 should NOT have external.yaml
        assert not (project_paths[1] / "docs" / "subsystems" / "validation").exists()

        # Verify dependents only include linked projects
        overview_path = external_path / "docs" / "subsystems" / "validation" / "OVERVIEW.md"
        content = overview_path.read_text()
        assert "acme/proj1" in content
        assert "acme/proj3" in content
        assert "acme/proj2" not in content

    def test_creates_external_yaml_in_all_projects_when_flag_omitted(self, tmp_path):
        """Omitting --projects flag links to all projects (backward compatible)."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2", "proj3"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0

        # All projects should have external.yaml
        for project_path in project_paths:
            assert (project_path / "docs" / "subsystems" / "validation" / "external.yaml").exists()

    def test_error_on_invalid_project_ref(self, tmp_path):
        """Reports clear error when invalid project is specified."""
        task_dir, _, _ = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "subsystem", "discover", "validation",
                "--projects", "proj1,nonexistent",
                "--project-dir", str(task_dir)
            ],
        )

        assert result.exit_code == 1
        assert "nonexistent" in result.output
        assert "not found" in result.output
