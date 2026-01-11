"""Integration tests for task-aware subsystem listing.

# Chunk: docs/chunks/task_aware_subsystem_cmds - Task-aware subsystem list tests
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli


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
    config_content = f"""external_artifact_repo: acme/{external_name}
projects:
{projects_yaml}
"""
    (task_dir / ".ve-task.yaml").write_text(config_content)

    return task_dir, external_path, project_paths


def create_subsystem_in_external_repo(
    external_path, short_name, status="DISCOVERING", dependents=None
):
    """Create a subsystem directory with OVERVIEW.md in the external repo.

    Args:
        external_path: Path to the external repository
        short_name: e.g., "validation"
        status: Subsystem status (default "DISCOVERING")
        dependents: List of {artifact_type, artifact_id, repo} dicts (optional)

    Returns:
        Path to the created subsystem directory
    """
    subsystem_dir = external_path / "docs" / "subsystems" / short_name
    subsystem_dir.mkdir(parents=True, exist_ok=True)

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
chunks: []
code_references: []
proposed_chunks: []
{dependents_yaml}
---

# Subsystem: {short_name}

## Intent

Test subsystem for {short_name}.

## Scope

### In Scope

- Test scope items

### Out of Scope

- Nothing

## Invariants

- Test invariant

## Code References

None yet.
"""
    (subsystem_dir / "OVERVIEW.md").write_text(overview_content)
    return subsystem_dir


class TestSubsystemListInTaskDirectory:
    """Tests for ve subsystem list in task directory context."""

    def test_lists_subsystems_from_external_repo(self, tmp_path):
        """Lists subsystems from external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create subsystems in external repo
        create_subsystem_in_external_repo(external_path, "validation")
        create_subsystem_in_external_repo(external_path, "template_system")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/validation" in result.output
        assert "docs/subsystems/template_system" in result.output

    def test_shows_dependents_for_each_subsystem(self, tmp_path):
        """Displays dependents for each subsystem when in task directory."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["service_a", "service_b"]
        )

        # Create subsystem with dependents in external repo
        dependents = [
            {"artifact_type": "subsystem", "artifact_id": "validation", "repo": "acme/service_a"},
            {"artifact_type": "subsystem", "artifact_id": "validation", "repo": "acme/service_b"},
        ]
        create_subsystem_in_external_repo(
            external_path, "validation", status="DISCOVERING", dependents=dependents
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/validation" in result.output
        assert "dependents:" in result.output
        assert "acme/service_a" in result.output
        assert "acme/service_b" in result.output

    def test_shows_status(self, tmp_path):
        """Displays subsystem status when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        create_subsystem_in_external_repo(external_path, "validation", status="DISCOVERING")
        create_subsystem_in_external_repo(external_path, "template_system", status="STABLE")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "[DISCOVERING]" in result.output
        assert "[STABLE]" in result.output

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
            cli, ["subsystem", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External" in result.output
        assert "not found" in result.output

    def test_error_when_no_subsystems_in_external_repo(self, tmp_path):
        """Reports 'No subsystems found' when external repo has no subsystems."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No subsystems found" in result.output


class TestSubsystemListOutsideTaskDirectory:
    """Tests for ve subsystem list outside task directory context."""

    def test_single_repo_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create a subsystem directly
        subsystem_dir = project_path / "docs" / "subsystems" / "my_subsystem"
        subsystem_dir.mkdir(parents=True)
        overview_content = """---
status: DISCOVERING
chunks: []
code_references: []
proposed_chunks: []
---

# Subsystem

Test subsystem.
"""
        (subsystem_dir / "OVERVIEW.md").write_text(overview_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["subsystem", "list", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/subsystems/my_subsystem [DISCOVERING]" in result.output
        # Should NOT have dependents line in single-repo mode
        assert "dependents:" not in result.output
