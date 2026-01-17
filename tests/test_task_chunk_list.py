"""Integration tests for task-aware chunk listing.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
"""

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


def create_local_chunk(project_path, short_name, status="ACTIVE"):
    """Create a local chunk in a project (not an external reference).

    Args:
        project_path: Path to the project directory
        short_name: e.g., "local_fix"
        status: Chunk status (default "ACTIVE")

    Returns:
        Path to the created chunk directory
    """
    chunk_dir = project_path / "docs" / "chunks" / short_name
    chunk_dir.mkdir(parents=True, exist_ok=True)

    goal_content = f"""---
status: {status}
ticket: null
parent_chunk: null
code_paths: []
code_references: []
---

# Chunk Goal

Local chunk for {short_name}.
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
        # New grouped output format shows external header
        assert "# External Artifacts (acme/ext)" in result.output
        assert "0001-auth_token" in result.output
        assert "0002-auth_validation" in result.output

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
        assert "0001-auth_token" in result.output
        # New format shows "referenced by:" with repo names only
        assert "→ referenced by:" in result.output
        assert "acme/service_a" in result.output
        assert "acme/service_b" in result.output

    def test_latest_returns_implementing_chunk_from_external_repo(self, tmp_path):
        """--latest returns implementing chunk from external repo with repo prefix."""
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
        # In task context, output format is: {external_artifact_repo}::docs/chunks/{chunk_name}
        assert result.output.strip() == "acme/ext::docs/chunks/0002-auth_validation"

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
        # Error message now comes from generic artifact listing
        assert "External repository" in result.output
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

    def test_shows_grouped_output_with_external_and_local(self, tmp_path):
        """Shows grouped output with both external and local chunks."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["service_a"]
        )

        # Create chunk in external repo
        create_chunk_in_external_repo(external_path, "0001", "cross_cutting")

        # Create local chunk in project
        create_local_chunk(project_paths[0], "local_fix")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # Should show external header first
        assert "# External Artifacts (acme/ext)" in result.output
        assert "cross_cutting" in result.output
        # Should show local project header
        assert "# acme/service_a (local)" in result.output
        assert "local_fix" in result.output

    def test_shows_tip_indicator_for_tip_chunks(self, tmp_path):
        """Shows (tip) indicator for chunks that are tips."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create chunk - should be a tip since nothing depends on it
        create_chunk_in_external_repo(external_path, "0001", "only_chunk")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        assert "(tip)" in result.output

    def test_excludes_external_refs_from_local_listing(self, tmp_path):
        """External references in projects should not appear in local section."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["service_a"]
        )

        # Create chunk in external repo with dependents
        dependents = [
            {"artifact_type": "chunk", "artifact_id": "ext_ref", "repo": "acme/service_a"}
        ]
        create_chunk_in_external_repo(
            external_path, "0001", "cross_cutting", dependents=dependents
        )

        # Create external.yaml reference in project (simulating task chunk creation)
        ext_ref_dir = project_paths[0] / "docs" / "chunks" / "ext_ref"
        ext_ref_dir.mkdir(parents=True)
        (ext_ref_dir / "external.yaml").write_text(
            """artifact_type: chunk
artifact_id: 0001-cross_cutting
repo: acme/ext
track: main
pinned: abc123
"""
        )

        # Also create a real local chunk
        create_local_chunk(project_paths[0], "real_local")

        runner = CliRunner()
        result = runner.invoke(
            cli, ["chunk", "list", "--project-dir", str(task_dir)]
        )

        assert result.exit_code == 0
        # External ref should not appear in local section
        assert "# acme/service_a (local)" in result.output
        assert "real_local" in result.output
        # External reference shouldn't be listed as a local artifact
        lines = result.output.split('\n')
        local_section_started = False
        for line in lines:
            if "# acme/service_a (local)" in line:
                local_section_started = True
            if local_section_started and "ext_ref" in line:
                assert False, "External reference should not appear in local section"


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
