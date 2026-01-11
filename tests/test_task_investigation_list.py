"""Integration tests for task-aware investigation listing.

# Chunk: docs/chunks/task_aware_investigations - Task-aware investigation list tests
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from conftest import make_ve_initialized_git_repo, setup_task_directory


def create_investigation_in_external_repo(
    external_path, short_name, status="ONGOING", dependents=None
):
    """Create an investigation directory with OVERVIEW.md in the external repo.

    Args:
        external_path: Path to the external repository
        short_name: e.g., "memory_leak"
        status: Investigation status (default "ONGOING")
        dependents: List of {artifact_type, artifact_id, repo} dicts (optional)

    Returns:
        Path to the created investigation directory
    """
    investigation_dir = external_path / "docs" / "investigations" / short_name
    investigation_dir.mkdir(parents=True, exist_ok=True)

    dependents_yaml = ""
    if dependents:
        dependents_lines = []
        for dep in dependents:
            dependents_lines.append(f"  - artifact_type: {dep['artifact_type']}")
            dependents_lines.append(f"    artifact_id: {dep['artifact_id']}")
            dependents_lines.append(f"    repo: {dep['repo']}")
        dependents_yaml = "dependents:\n" + "\n".join(dependents_lines)

    overview_content = f"""---
status: {status}
trigger: null
proposed_chunks: []
{dependents_yaml}
---

# Investigation: {short_name}

## Trigger

Test investigation for {short_name}.

## Testable Hypotheses

No hypotheses yet.

## Exploration Log

No explorations yet.

## Findings

No findings yet.
"""
    (investigation_dir / "OVERVIEW.md").write_text(overview_content)
    return investigation_dir


class TestInvestigationListInTaskDirectory:
    """Tests for ve investigation list in task directory context."""

    def test_lists_investigations_from_external_repo(self, tmp_path):
        """Lists investigations from external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create investigations in external repo
        create_investigation_in_external_repo(external_path, "memory_leak")
        create_investigation_in_external_repo(external_path, "slow_query")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/investigations/memory_leak" in result.output
        assert "docs/investigations/slow_query" in result.output

    def test_shows_dependents_for_each_investigation(self, tmp_path):
        """Displays dependents for each investigation when in task directory."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["service_a", "service_b"]
        )

        # Create investigation with dependents in external repo
        dependents = [
            {"artifact_type": "investigation", "artifact_id": "memory_leak", "repo": "acme/service_a"},
            {"artifact_type": "investigation", "artifact_id": "memory_leak", "repo": "acme/service_b"},
        ]
        create_investigation_in_external_repo(
            external_path, "memory_leak", status="ONGOING", dependents=dependents
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/investigations/memory_leak" in result.output
        assert "dependents:" in result.output
        assert "acme/service_a" in result.output
        assert "acme/service_b" in result.output

    def test_shows_status(self, tmp_path):
        """Displays investigation status when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        create_investigation_in_external_repo(external_path, "memory_leak", status="ONGOING")
        create_investigation_in_external_repo(external_path, "slow_query", status="SOLVED")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "[ONGOING]" in result.output
        assert "[SOLVED]" in result.output

    def test_error_when_external_repo_inaccessible(self, tmp_path):
        """Reports clear error when external repo not accessible."""
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
            cli, ["investigation", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External" in result.output
        assert "not found" in result.output

    def test_error_when_no_investigations_in_external_repo(self, tmp_path):
        """Reports 'No investigations found' when external repo has no investigations."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No investigations found" in result.output


class TestInvestigationListOutsideTaskDirectory:
    """Tests for ve investigation list outside task directory context."""

    def test_single_repo_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create an investigation directly
        investigation_dir = project_path / "docs" / "investigations" / "my_investigation"
        investigation_dir.mkdir(parents=True)
        overview_content = """---
status: ONGOING
trigger: null
proposed_chunks: []
---

# Investigation

Test investigation.
"""
        (investigation_dir / "OVERVIEW.md").write_text(overview_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigation", "list", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/investigations/my_investigation [ONGOING]" in result.output
        # Should NOT have dependents line in single-repo mode
        assert "dependents:" not in result.output
