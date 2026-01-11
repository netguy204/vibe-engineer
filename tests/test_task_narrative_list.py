"""Integration tests for task-aware narrative listing.

# Chunk: docs/chunks/task_aware_narrative_cmds - Task-aware narrative list tests
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
    (path / "docs" / "narratives").mkdir(parents=True)
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


def create_narrative_in_external_repo(
    external_path, short_name, status="ACTIVE", dependents=None
):
    """Create a narrative directory with OVERVIEW.md in the external repo.

    Args:
        external_path: Path to the external repository
        short_name: e.g., "user_auth"
        status: Narrative status (default "ACTIVE")
        dependents: List of {artifact_type, artifact_id, repo} dicts (optional)

    Returns:
        Path to the created narrative directory
    """
    narrative_dir = external_path / "docs" / "narratives" / short_name
    narrative_dir.mkdir(parents=True, exist_ok=True)

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
advances_trunk_goal: null
proposed_chunks: []
{dependents_yaml}
---

# Narrative: {short_name}

## Advances Trunk Goal

Test narrative for {short_name}.

## Proposed Chunks

No chunks proposed yet.
"""
    (narrative_dir / "OVERVIEW.md").write_text(overview_content)
    return narrative_dir


class TestNarrativeListInTaskDirectory:
    """Tests for ve narrative list in task directory context."""

    def test_lists_narratives_from_external_repo(self, tmp_path):
        """Lists narratives from external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create narratives in external repo
        create_narrative_in_external_repo(external_path, "user_auth")
        create_narrative_in_external_repo(external_path, "payment_flow")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/narratives/user_auth" in result.output
        assert "docs/narratives/payment_flow" in result.output

    def test_shows_dependents_for_each_narrative(self, tmp_path):
        """Displays dependents for each narrative when in task directory."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["service_a", "service_b"]
        )

        # Create narrative with dependents in external repo
        dependents = [
            {"artifact_type": "narrative", "artifact_id": "user_auth", "repo": "acme/service_a"},
            {"artifact_type": "narrative", "artifact_id": "user_auth", "repo": "acme/service_b"},
        ]
        create_narrative_in_external_repo(
            external_path, "user_auth", status="ACTIVE", dependents=dependents
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/narratives/user_auth" in result.output
        assert "dependents:" in result.output
        assert "acme/service_a" in result.output
        assert "acme/service_b" in result.output

    def test_shows_status(self, tmp_path):
        """Displays narrative status when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        create_narrative_in_external_repo(external_path, "user_auth", status="ACTIVE")
        create_narrative_in_external_repo(external_path, "payment_flow", status="COMPLETED")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "[ACTIVE]" in result.output
        assert "[COMPLETED]" in result.output

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
            cli, ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External" in result.output
        assert "not found" in result.output

    def test_error_when_no_narratives_in_external_repo(self, tmp_path):
        """Reports 'No narratives found' when external repo has no narratives."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["narrative", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No narratives found" in result.output


class TestNarrativeListOutsideTaskDirectory:
    """Tests for ve narrative list outside task directory context."""

    def test_single_repo_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create a narrative directly
        narrative_dir = project_path / "docs" / "narratives" / "my_narrative"
        narrative_dir.mkdir(parents=True)
        overview_content = """---
status: ACTIVE
advances_trunk_goal: null
proposed_chunks: []
---

# Narrative

Test narrative.
"""
        (narrative_dir / "OVERVIEW.md").write_text(overview_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["narrative", "list", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/narratives/my_narrative [ACTIVE]" in result.output
        # Should NOT have dependents line in single-repo mode
        assert "dependents:" not in result.output
