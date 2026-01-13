"""Integration tests for task-aware friction logging.

# Chunk: docs/chunks/selective_artifact_friction - Task-aware friction log tests
"""

import subprocess

import pytest
import yaml
from click.testing import CliRunner

from ve import cli
from conftest import make_ve_initialized_git_repo, setup_task_directory


def create_friction_file(path, themes=None, entries=None):
    """Create a FRICTION.md file with optional themes and entries.

    Args:
        path: Path to the repository root
        themes: Optional list of theme dicts with 'id' and 'name'
        entries: Optional list of entry dicts with 'id', 'date', 'theme', 'title', 'desc', 'impact'
    """
    themes = themes or []
    entries = entries or []

    themes_yaml = yaml.dump({"themes": themes, "proposed_chunks": []}, default_flow_style=False)
    body = "\n# Friction Log\n\n"

    for entry in entries:
        body += f"### {entry['id']}: {entry['date']} [{entry['theme']}] {entry['title']}\n\n"
        body += f"{entry['desc']}\n\n"
        body += f"**Impact**: {entry['impact'].capitalize()}\n\n"

    content = f"---\n{themes_yaml}---\n{body}"

    friction_path = path / "docs" / "trunk" / "FRICTION.md"
    friction_path.parent.mkdir(parents=True, exist_ok=True)
    friction_path.write_text(content)

    # Commit the change
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add FRICTION.md"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def setup_task_directory_with_friction(tmp_path, external_name="ext", project_names=None):
    """Create a task directory with FRICTION.md in external and project repos.

    Returns:
        tuple: (task_dir, external_path, project_paths)
    """
    task_dir, external_path, project_paths = setup_task_directory(
        tmp_path, external_name=external_name, project_names=project_names
    )

    # Add FRICTION.md to external repo
    create_friction_file(
        external_path,
        themes=[{"id": "cli", "name": "CLI Friction"}],
        entries=[],
    )

    # Add FRICTION.md to each project repo
    for project_path in project_paths:
        create_friction_file(
            project_path,
            themes=[],
            entries=[],
        )

    return task_dir, external_path, project_paths


class TestFrictionLogInTaskDirectory:
    """Tests for ve friction log in task directory context."""

    def test_creates_entry_in_external_repo(self, tmp_path):
        """Creates friction entry in external repo's FRICTION.md."""
        task_dir, external_path, _ = setup_task_directory_with_friction(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Created friction entry in external repo" in result.output
        assert "F001" in result.output

        # Verify entry was created in external repo
        friction_path = external_path / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "Config file loading" in content
        assert "[cli]" in content

    def test_updates_project_friction_sources(self, tmp_path):
        """Updates external_friction_sources in each project's FRICTION.md."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # Verify external_friction_sources in each project
        for project_path in project_paths:
            friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
            content = friction_path.read_text()
            assert "external_friction_sources:" in content
            assert "acme/ext" in content
            assert "F001" in content

    def test_uses_new_theme_with_theme_name(self, tmp_path):
        """Creates new theme when --theme-name is provided."""
        task_dir, external_path, _ = setup_task_directory_with_friction(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Memory leak",
                "--description", "App uses too much memory",
                "--impact", "high",
                "--theme", "performance",
                "--theme-name", "Performance Issues",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # Verify theme was created
        friction_path = external_path / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "performance" in content
        assert "Performance Issues" in content

    def test_resolves_pinned_sha_from_external_repo(self, tmp_path):
        """Pinned SHA matches HEAD of external repo at creation time."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(tmp_path)

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
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # Verify pinned SHA in project FRICTION.md
        friction_path = project_paths[0] / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert expected_sha in content


# Chunk: docs/chunks/selective_artifact_friction - Selective project linking tests
class TestFrictionLogSelectiveProjects:
    """Tests for ve friction log with --projects flag."""

    def test_creates_external_friction_source_only_in_specified_projects(self, tmp_path):
        """--projects flag updates FRICTION.md only in specified projects."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(
            tmp_path, project_names=["proj1", "proj2", "proj3"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--projects", "proj1,proj3",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # proj1 and proj3 should have external_friction_sources
        friction_path1 = project_paths[0] / "docs" / "trunk" / "FRICTION.md"
        content1 = friction_path1.read_text()
        assert "external_friction_sources:" in content1
        assert "F001" in content1

        friction_path3 = project_paths[2] / "docs" / "trunk" / "FRICTION.md"
        content3 = friction_path3.read_text()
        assert "external_friction_sources:" in content3
        assert "F001" in content3

        # proj2 should NOT have external_friction_sources (still has empty list)
        friction_path2 = project_paths[1] / "docs" / "trunk" / "FRICTION.md"
        content2 = friction_path2.read_text()
        assert "F001" not in content2

    def test_creates_external_friction_source_in_all_projects_when_flag_omitted(self, tmp_path):
        """Omitting --projects flag updates FRICTION.md in all projects."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(
            tmp_path, project_names=["proj1", "proj2", "proj3"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # All projects should have external_friction_sources
        for project_path in project_paths:
            friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
            content = friction_path.read_text()
            assert "external_friction_sources:" in content
            assert "F001" in content

    def test_error_on_invalid_project_ref(self, tmp_path):
        """Reports clear error when invalid project is specified."""
        task_dir, _, _ = setup_task_directory_with_friction(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--projects", "proj1,nonexistent",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 1
        assert "nonexistent" in result.output
        assert "not found" in result.output

    def test_accepts_flexible_project_refs(self, tmp_path):
        """--projects accepts both repo name and full org/repo format."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(
            tmp_path, project_names=["proj1", "proj2"]
        )

        runner = CliRunner()
        # Mix of short and full format
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--projects", "proj1,acme/proj2",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0

        # Both projects should have external_friction_sources
        for project_path in project_paths:
            friction_path = project_path / "docs" / "trunk" / "FRICTION.md"
            content = friction_path.read_text()
            assert "external_friction_sources:" in content
            assert "F001" in content

    def test_accumulates_entry_ids_in_same_external_source(self, tmp_path):
        """Multiple friction entries accumulate in the same external_friction_sources entry."""
        task_dir, external_path, project_paths = setup_task_directory_with_friction(tmp_path)

        runner = CliRunner()

        # Log first entry
        result1 = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )
        assert result1.exit_code == 0

        # Log second entry
        result2 = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Error handling",
                "--description", "Errors are not clear",
                "--impact", "low",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )
        assert result2.exit_code == 0

        # Verify both entry IDs are in the same external_friction_sources entry
        friction_path = project_paths[0] / "docs" / "trunk" / "FRICTION.md"
        content = friction_path.read_text()
        assert "F001" in content
        assert "F002" in content

        # Should only have one external_friction_sources entry for acme/ext
        assert content.count("acme/ext") == 1


class TestFrictionLogWithoutFriction:
    """Tests for error handling when FRICTION.md is missing."""

    def test_error_when_external_repo_has_no_friction(self, tmp_path):
        """Reports error when external repo has no FRICTION.md."""
        # Use standard setup (no FRICTION.md)
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 1
        assert "does not have FRICTION.md" in result.output

    def test_skips_projects_without_friction(self, tmp_path):
        """Skips projects without FRICTION.md with warning."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Only add FRICTION.md to external repo and proj1
        create_friction_file(
            external_path,
            themes=[{"id": "cli", "name": "CLI Friction"}],
        )
        create_friction_file(project_paths[0])  # proj1 gets FRICTION.md

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "friction", "log",
                "--title", "Config file loading",
                "--description", "Config loading is slow",
                "--impact", "medium",
                "--theme", "cli",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Skipped" in result.output or "no FRICTION.md" in result.output

        # proj1 should have external_friction_sources
        friction_path1 = project_paths[0] / "docs" / "trunk" / "FRICTION.md"
        content1 = friction_path1.read_text()
        assert "external_friction_sources:" in content1

        # proj2 should still not have FRICTION.md at all
        friction_path2 = project_paths[1] / "docs" / "trunk" / "FRICTION.md"
        assert not friction_path2.exists()
