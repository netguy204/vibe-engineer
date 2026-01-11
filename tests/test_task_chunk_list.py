"""Integration tests for task-aware chunk listing."""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from conftest import make_ve_initialized_git_repo, setup_task_directory


def create_chunk_in_external_repo(
    external_path, chunk_id, short_name, status="ACTIVE", dependents=None
):
    """Create a chunk directory with GOAL.md in the external repo.

    Args:
        external_path: Path to the external repository
        chunk_id: e.g., "0001"
        short_name: e.g., "auth_token"
        status: Chunk status (default "ACTIVE")
        dependents: List of {artifact_type, artifact_id, repo} dicts (optional)

    Returns:
        Path to the created chunk directory
    """
    chunk_dir = external_path / "docs" / "chunks" / f"{chunk_id}-{short_name}"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    dependents_yaml = ""
    if dependents:
        dependents_lines = []
        for dep in dependents:
            dependents_lines.append(f"  - artifact_type: {dep['artifact_type']}")
            dependents_lines.append(f"    artifact_id: {dep['artifact_id']}")
            dependents_lines.append(f"    repo: {dep['repo']}")
        dependents_yaml = "dependents:\n" + "\n".join(dependents_lines)

    goal_content = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
code_references: []
{dependents_yaml}
---

# Chunk Goal

Test chunk for {short_name}.
"""
    (chunk_dir / "GOAL.md").write_text(goal_content)
    return chunk_dir


class TestChunkListInTaskDirectory:
    """Tests for ve chunk list in task directory context."""

    def test_lists_chunks_from_external_repo(self, tmp_path):
        """Lists chunks from external repo when in task directory."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create chunks in external repo
        create_chunk_in_external_repo(external_path, "0001", "auth_token")
        create_chunk_in_external_repo(external_path, "0002", "auth_validation")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/chunks/0001-auth_token" in result.output
        assert "docs/chunks/0002-auth_validation" in result.output

    def test_shows_dependents_for_each_chunk(self, tmp_path):
        """Displays dependents for each chunk when in task directory."""
        task_dir, external_path, _ = setup_task_directory(
            tmp_path, project_names=["service_a", "service_b"]
        )

        # Create chunk with dependents in external repo
        dependents = [
            {"artifact_type": "chunk", "artifact_id": "0005-auth_token", "repo": "acme/service_a"},
            {"artifact_type": "chunk", "artifact_id": "0009-auth_token", "repo": "acme/service_b"},
        ]
        create_chunk_in_external_repo(
            external_path, "0001", "auth_token", status="ACTIVE", dependents=dependents
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "docs/chunks/0001-auth_token" in result.output
        assert "dependents:" in result.output
        assert "acme/service_a (0005-auth_token)" in result.output
        assert "acme/service_b (0009-auth_token)" in result.output

    def test_latest_returns_implementing_chunk_from_external_repo(self, tmp_path):
        """--latest returns implementing chunk from external repo."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create ACTIVE and IMPLEMENTING chunks
        create_chunk_in_external_repo(
            external_path, "0001", "auth_token", status="ACTIVE"
        )
        create_chunk_in_external_repo(
            external_path, "0002", "auth_validation", status="IMPLEMENTING"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--latest", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert result.output.strip() == "docs/chunks/0002-auth_validation"

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
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "External chunk repository" in result.output
        assert "not found" in result.output

    def test_error_when_no_chunks_in_external_repo(self, tmp_path):
        """Reports 'No chunks found' when external repo has no chunks."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No chunks found" in result.output

    def test_error_when_no_implementing_chunk_with_latest(self, tmp_path):
        """Reports error when --latest but no IMPLEMENTING chunk exists."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create only ACTIVE chunks
        create_chunk_in_external_repo(
            external_path, "0001", "auth_token", status="ACTIVE"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--latest", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 1
        assert "No implementing chunk found" in result.output


class TestChunkListOutsideTaskDirectory:
    """Tests for ve chunk list outside task directory context."""

    def test_single_repo_behavior_unchanged(self, tmp_path):
        """Single-repo behavior unchanged when not in task directory."""
        # Create a regular VE project (no .ve-task.yaml)
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create a chunk directly
        chunk_dir = project_path / "docs" / "chunks" / "0001-my_feature"
        chunk_dir.mkdir(parents=True)
        goal_content = """---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Test chunk.
"""
        (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert "docs/chunks/0001-my_feature [ACTIVE]" in result.output
        # Should NOT have dependents line in single-repo mode
        assert "dependents:" not in result.output

    def test_latest_returns_implementing_chunk_in_single_repo(self, tmp_path):
        """--latest returns implementing chunk in single-repo mode."""
        project_path = tmp_path / "regular_project"
        make_ve_initialized_git_repo(project_path)

        # Create ACTIVE and IMPLEMENTING chunks
        for chunk_id, status in [("0001-old", "ACTIVE"), ("0002-current", "IMPLEMENTING")]:
            chunk_dir = project_path / "docs" / "chunks" / chunk_id
            chunk_dir.mkdir(parents=True)
            goal_content = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Test chunk.
"""
            (chunk_dir / "GOAL.md").write_text(goal_content)

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--latest", "--project-dir", str(project_path)]
        )

        assert result.exit_code == 0
        assert result.output.strip() == "docs/chunks/0002-current"
