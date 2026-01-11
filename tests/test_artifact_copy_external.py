"""Tests for copying external artifacts as references.

# Chunk: docs/chunks/copy_as_external - Copy artifact as external reference tests
"""

import subprocess

import pytest
from click.testing import CliRunner

from ve import cli
from task_utils import (
    copy_artifact_as_external,
    TaskCopyExternalError,
    load_external_ref,
)
from conftest import make_ve_initialized_git_repo, setup_task_directory


class TestCopyArtifactAsExternalCoreFunction:
    """Tests for the copy_artifact_as_external() core function."""

    def test_happy_path_creates_external_reference(self, tmp_path):
        """Creates external.yaml in target project for artifact in external repo."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an artifact in the external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
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

        # Copy as external reference to the project
        result = copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify external.yaml was created in target project
        external_yaml_path = project_path / "docs" / "chunks" / "my_feature" / "external.yaml"
        assert external_yaml_path.exists()

        # Verify external.yaml content
        ref = load_external_ref(project_path / "docs" / "chunks" / "my_feature")
        assert ref.artifact_type.value == "chunk"
        assert ref.artifact_id == "my_feature"
        assert ref.repo == "acme/ext"
        assert ref.track == "main"
        assert len(ref.pinned) == 40  # SHA

        # Verify result contains created path
        assert result["external_yaml_path"] == external_yaml_path

    def test_created_after_populated_with_target_tips(self, tmp_path):
        """created_after is populated with tips from target project."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create existing chunk in target project to be a tip
        existing_chunk_dir = project_path / "docs" / "chunks" / "existing_chunk"
        existing_chunk_dir.mkdir(parents=True)
        (existing_chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# Existing Chunk
""")

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "new_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
---

# New Feature
""")

        # Copy as external reference
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/new_feature",
            target_project="acme/proj",
        )

        # Verify created_after includes the existing chunk
        ref = load_external_ref(project_path / "docs" / "chunks" / "new_feature")
        assert "existing_chunk" in ref.created_after

    def test_name_flag_renames_artifact_in_destination(self, tmp_path):
        """--name parameter renames artifact in destination project."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "original_name"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Original
""")

        # Copy with new name
        result = copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/original_name",
            target_project="acme/proj",
            new_name="new_name",
        )

        # Verify external reference uses new name
        new_path = project_path / "docs" / "chunks" / "new_name"
        assert new_path.exists()
        assert (new_path / "external.yaml").exists()

        # Original name should NOT exist in target project
        assert not (project_path / "docs" / "chunks" / "original_name").exists()

        # Verify artifact_id still references the original name in external repo
        ref = load_external_ref(new_path)
        assert ref.artifact_id == "original_name"

    def test_error_when_not_in_task_directory(self, tmp_path):
        """Errors when not in task directory context."""
        # Create a standalone project (no .ve-task.yaml)
        project_path = tmp_path / "standalone"
        make_ve_initialized_git_repo(project_path)

        with pytest.raises(TaskCopyExternalError) as exc_info:
            copy_artifact_as_external(
                task_dir=project_path,
                artifact_path="docs/chunks/my_chunk",
                target_project="acme/proj",
            )

        assert "task" in str(exc_info.value).lower()

    def test_error_when_source_artifact_not_in_external_repo(self, tmp_path):
        """Errors when source artifact doesn't exist in external repo."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        with pytest.raises(TaskCopyExternalError) as exc_info:
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path="docs/chunks/nonexistent",
                target_project="acme/proj",
            )

        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()

    def test_error_when_target_project_not_in_task_config(self, tmp_path):
        """Errors when target project is not in task configuration."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Feature
""")

        with pytest.raises(TaskCopyExternalError) as exc_info:
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path="docs/chunks/my_feature",
                target_project="acme/unknown_project",
            )

        assert "not found" in str(exc_info.value).lower() or "not a valid" in str(exc_info.value).lower()

    def test_error_when_artifact_already_exists_in_target(self, tmp_path):
        """Errors when artifact already exists in target project."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Feature
""")

        # Create conflicting artifact in target project
        conflict_dir = project_path / "docs" / "chunks" / "my_feature"
        conflict_dir.mkdir(parents=True)
        (conflict_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Conflicting Feature
""")

        with pytest.raises(TaskCopyExternalError) as exc_info:
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path="docs/chunks/my_feature",
                target_project="acme/proj",
            )

        assert "already exists" in str(exc_info.value).lower()

    def test_copies_investigation_artifact(self, tmp_path):
        """Correctly copies investigation artifact type."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create investigation in external repo
        inv_dir = external_path / "docs" / "investigations" / "memory_leak"
        inv_dir.mkdir(parents=True)
        (inv_dir / "OVERVIEW.md").write_text("""---
status: ONGOING
created_after: []
---

# Investigation
""")

        # Copy as external reference
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/investigations/memory_leak",
            target_project="acme/proj",
        )

        # Verify external reference created
        ref = load_external_ref(project_path / "docs" / "investigations" / "memory_leak")
        assert ref.artifact_type.value == "investigation"
        assert ref.artifact_id == "memory_leak"

    def test_copies_narrative_artifact(self, tmp_path):
        """Correctly copies narrative artifact type."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create narrative in external repo
        narr_dir = external_path / "docs" / "narratives" / "my_story"
        narr_dir.mkdir(parents=True)
        (narr_dir / "OVERVIEW.md").write_text("""---
status: ACTIVE
created_after: []
---

# Narrative
""")

        # Copy as external reference
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/narratives/my_story",
            target_project="acme/proj",
        )

        # Verify external reference created
        ref = load_external_ref(project_path / "docs" / "narratives" / "my_story")
        assert ref.artifact_type.value == "narrative"

    def test_copies_subsystem_artifact(self, tmp_path):
        """Correctly copies subsystem artifact type."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create subsystem in external repo
        sub_dir = external_path / "docs" / "subsystems" / "my_subsystem"
        sub_dir.mkdir(parents=True)
        (sub_dir / "OVERVIEW.md").write_text("""---
status: STABLE
created_after: []
---

# Subsystem
""")

        # Copy as external reference
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/subsystems/my_subsystem",
            target_project="acme/proj",
        )

        # Verify external reference created
        ref = load_external_ref(project_path / "docs" / "subsystems" / "my_subsystem")
        assert ref.artifact_type.value == "subsystem"


class TestCopyArtifactAsExternalCLI:
    """Tests for ve artifact copy-external CLI command."""

    def test_cli_command_exists(self, tmp_path):
        """ve artifact copy-external command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "copy-external", "--help"])

        assert result.exit_code == 0
        assert "copy-external" in result.output.lower() or "copy" in result.output.lower()

    def test_cli_happy_path(self, tmp_path):
        """CLI creates external reference and reports success."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Feature
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "copy-external",
                "docs/chunks/my_feature",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert (project_path / "docs" / "chunks" / "my_feature" / "external.yaml").exists()

    def test_cli_name_flag(self, tmp_path):
        """CLI --name flag works."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "original_name"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
---

# Feature
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "copy-external",
                "docs/chunks/original_name",
                "acme/proj",
                "--name", "new_name",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert (project_path / "docs" / "chunks" / "new_name" / "external.yaml").exists()
        assert not (project_path / "docs" / "chunks" / "original_name").exists()

    def test_cli_error_handling(self, tmp_path):
        """CLI returns non-zero for error cases."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "copy-external",
                "docs/chunks/nonexistent",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code != 0
