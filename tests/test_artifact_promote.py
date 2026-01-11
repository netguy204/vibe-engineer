"""Tests for artifact promotion to external repository.

# Chunk: docs/chunks/artifact_promote - Artifact promotion tests
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from task_utils import (
    promote_artifact,
    TaskPromoteError,
    load_external_ref,
    load_task_config,
)
from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestPromoteArtifactCoreFunction:
    """Tests for the promote_artifact() core function."""

    def test_happy_path_promotes_local_investigation(self, tmp_path):
        """Promotes a local investigation to external repo."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation in the project
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
trigger: Memory issues observed
created_after: []
---

# Investigation: Memory Leak

## Trigger
Memory issues observed in production.
""")

        # Promote it
        result = promote_artifact(investigation_dir)

        # Verify artifact was copied to external repo
        external_inv_dir = external_path / "docs" / "investigations" / "memory_leak"
        assert external_inv_dir.exists()
        assert (external_inv_dir / "OVERVIEW.md").exists()

        # Verify source directory now has external.yaml
        assert (investigation_dir / "external.yaml").exists()
        # Source should NOT have OVERVIEW.md anymore
        assert not (investigation_dir / "OVERVIEW.md").exists()

        # Verify external.yaml content
        ref = load_external_ref(investigation_dir)
        assert ref.artifact_type.value == "investigation"
        assert ref.artifact_id == "memory_leak"
        assert ref.repo == "acme/ext"
        assert len(ref.pinned) == 40  # SHA

        # Verify result contains paths
        assert result["external_artifact_path"] == external_inv_dir
        assert result["external_yaml_path"] == investigation_dir / "external.yaml"

    def test_promoted_artifact_has_updated_created_after(self, tmp_path):
        """Promoted artifact's created_after is set to external repo tips."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an existing investigation in external repo to be a tip
        existing_inv_dir = external_path / "docs" / "investigations" / "existing_inv"
        existing_inv_dir.mkdir(parents=True)
        (existing_inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Existing Investigation
""")

        # Create a local investigation in the project
        investigation_dir = project_path / "docs" / "investigations" / "new_inv"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# New Investigation
""")

        # Promote it
        promote_artifact(investigation_dir)

        # Verify promoted artifact's created_after includes the external tip
        external_inv_dir = external_path / "docs" / "investigations" / "new_inv"
        content = (external_inv_dir / "OVERVIEW.md").read_text()
        assert "existing_inv" in content

    def test_promoted_artifact_has_dependents_set(self, tmp_path):
        """Promoted artifact's dependents includes source project."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation in the project
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        # Promote it
        promote_artifact(investigation_dir)

        # Verify dependents in promoted artifact
        external_inv_dir = external_path / "docs" / "investigations" / "memory_leak"
        content = (external_inv_dir / "OVERVIEW.md").read_text()
        assert "dependents:" in content
        assert "acme/proj" in content

    def test_external_yaml_preserves_original_created_after(self, tmp_path):
        """External.yaml's created_after matches original artifact's created_after."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an existing local investigation that will be a dependency
        other_inv_dir = project_path / "docs" / "investigations" / "other_inv"
        other_inv_dir.mkdir(parents=True)
        (other_inv_dir / "OVERVIEW.md").write_text("""---
status: SOLVED
created_after: []
---

# Other Investigation
""")

        # Create the investigation to promote, with created_after referencing other_inv
        investigation_dir = project_path / "docs" / "investigations" / "my_inv"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after:
  - other_inv
---

# My Investigation
""")

        # Promote it
        promote_artifact(investigation_dir)

        # Verify external.yaml preserves the original created_after
        ref = load_external_ref(investigation_dir)
        assert ref.created_after == ["other_inv"]

    def test_name_flag_renames_artifact_during_promotion(self, tmp_path):
        """--name flag renames artifact in destination."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "old_name"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        # Promote with new name
        result = promote_artifact(investigation_dir, new_name="new_name")

        # Verify artifact was created with new name in external repo
        external_inv_dir = external_path / "docs" / "investigations" / "new_name"
        assert external_inv_dir.exists()

        # Verify old name doesn't exist in external
        assert not (external_path / "docs" / "investigations" / "old_name").exists()

        # Verify external.yaml references the new name
        ref = load_external_ref(investigation_dir)
        assert ref.artifact_id == "new_name"

    def test_errors_when_destination_exists(self, tmp_path):
        """Errors if destination artifact already exists in external repo."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create conflicting investigation in external repo
        existing_dir = external_path / "docs" / "investigations" / "memory_leak"
        existing_dir.mkdir(parents=True)
        (existing_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Existing Investigation
""")

        # Create local investigation with same name
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Local Investigation
""")

        # Attempt to promote should error
        with pytest.raises(TaskPromoteError) as exc_info:
            promote_artifact(investigation_dir)

        assert "already exists" in str(exc_info.value)

    def test_errors_for_already_external_artifact(self, tmp_path):
        """Errors when artifact is already an external reference."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an external reference (not a local artifact)
        investigation_dir = project_path / "docs" / "investigations" / "external_inv"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "external.yaml").write_text("""artifact_type: investigation
artifact_id: external_inv
repo: acme/other
track: main
pinned: abcd1234abcd1234abcd1234abcd1234abcd1234
""")

        # Attempt to promote should error
        with pytest.raises(TaskPromoteError) as exc_info:
            promote_artifact(investigation_dir)

        assert "already external" in str(exc_info.value).lower()

    def test_errors_when_not_in_task_context(self, tmp_path):
        """Errors with clear message if not in task directory."""
        # Create a standalone project (no .ve-task.yaml)
        project_path = tmp_path / "standalone"
        make_ve_initialized_git_repo(project_path)

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        # Attempt to promote should error
        with pytest.raises(TaskPromoteError) as exc_info:
            promote_artifact(investigation_dir)

        assert "task" in str(exc_info.value).lower()

    def test_promotes_chunk_artifact(self, tmp_path):
        """Promotes a chunk artifact correctly."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local chunk
        chunk_dir = project_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Chunk Goal

A feature chunk.
""")
        (chunk_dir / "PLAN.md").write_text("""# Plan

Implementation plan here.
""")

        # Promote it
        result = promote_artifact(chunk_dir)

        # Verify both files were copied
        external_chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        assert (external_chunk_dir / "GOAL.md").exists()
        assert (external_chunk_dir / "PLAN.md").exists()

        # Verify source is now external reference
        assert (chunk_dir / "external.yaml").exists()
        assert not (chunk_dir / "GOAL.md").exists()
        assert not (chunk_dir / "PLAN.md").exists()

        ref = load_external_ref(chunk_dir)
        assert ref.artifact_type.value == "chunk"

    def test_promotes_narrative_artifact(self, tmp_path):
        """Promotes a narrative artifact correctly."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local narrative
        narrative_dir = project_path / "docs" / "narratives" / "my_story"
        narrative_dir.mkdir(parents=True)
        (narrative_dir / "OVERVIEW.md").write_text("""---
status: ACTIVE
created_after: []
---

# Narrative

A story.
""")

        # Promote it
        result = promote_artifact(narrative_dir)

        # Verify narrative was promoted
        external_narrative_dir = external_path / "docs" / "narratives" / "my_story"
        assert (external_narrative_dir / "OVERVIEW.md").exists()

        ref = load_external_ref(narrative_dir)
        assert ref.artifact_type.value == "narrative"

    def test_promotes_subsystem_artifact(self, tmp_path):
        """Promotes a subsystem artifact correctly."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local subsystem
        subsystem_dir = project_path / "docs" / "subsystems" / "my_subsystem"
        subsystem_dir.mkdir(parents=True)
        (subsystem_dir / "OVERVIEW.md").write_text("""---
status: STABLE
created_after: []
---

# Subsystem

A subsystem.
""")

        # Promote it
        result = promote_artifact(subsystem_dir)

        # Verify subsystem was promoted
        external_subsystem_dir = external_path / "docs" / "subsystems" / "my_subsystem"
        assert (external_subsystem_dir / "OVERVIEW.md").exists()

        ref = load_external_ref(subsystem_dir)
        assert ref.artifact_type.value == "subsystem"


class TestPromoteArtifactCLI:
    """Tests for ve artifact promote CLI command."""

    def test_cli_command_exists(self, tmp_path):
        """ve artifact promote command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "promote", "--help"])

        assert result.exit_code == 0
        assert "promote" in result.output.lower()

    def test_cli_validates_path_exists(self, tmp_path):
        """CLI errors for non-existent path."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["artifact", "promote", str(task_dir / "nonexistent"), "--project-dir", str(task_dir)],
        )

        assert result.exit_code != 0

    def test_cli_promotes_investigation(self, tmp_path):
        """CLI promotes investigation and reports success."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["artifact", "promote", str(investigation_dir), "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        assert "memory_leak" in result.output

        # Verify artifact was promoted
        assert (external_path / "docs" / "investigations" / "memory_leak" / "OVERVIEW.md").exists()
        assert (investigation_dir / "external.yaml").exists()

    def test_cli_name_flag_works(self, tmp_path):
        """CLI --name flag renames during promotion."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "old_name"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "promote", str(investigation_dir),
                "--name", "new_name",
                "--project-dir", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert (external_path / "docs" / "investigations" / "new_name" / "OVERVIEW.md").exists()

    def test_cli_no_git_commands(self, tmp_path):
        """CLI does not run git commands (filesystem changes only)."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Get initial git status
        initial_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["artifact", "promote", str(investigation_dir), "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0

        # Verify changes are uncommitted (no git add/commit was run)
        final_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        # There should be uncommitted changes
        assert final_status.stdout.strip() != ""

    def test_cli_reports_paths(self, tmp_path):
        """CLI output includes created paths."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create a local investigation
        investigation_dir = project_path / "docs" / "investigations" / "memory_leak"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["artifact", "promote", str(investigation_dir), "--project-dir", str(task_dir)],
        )

        assert result.exit_code == 0
        # Should mention the external path and the reference
        assert "external" in result.output.lower() or "promoted" in result.output.lower()

    def test_cli_errors_for_already_external(self, tmp_path):
        """CLI errors with clear message for already-external artifacts."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an external reference
        investigation_dir = project_path / "docs" / "investigations" / "ext_inv"
        investigation_dir.mkdir(parents=True)
        (investigation_dir / "external.yaml").write_text("""artifact_type: investigation
artifact_id: ext_inv
repo: acme/other
track: main
pinned: abcd1234abcd1234abcd1234abcd1234abcd1234
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["artifact", "promote", str(investigation_dir), "--project-dir", str(task_dir)],
        )

        assert result.exit_code != 0
        assert "external" in result.output.lower()
