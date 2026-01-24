"""Tests for copying external artifacts as references.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/copy_as_external - Copy artifact as external reference
# Chunk: docs/chunks/artifact_copy_backref - Back-reference creation on copy
"""

import re
import subprocess

import pytest
import yaml
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
        assert ref.pinned is None  # No pinned SHA - always resolve to HEAD

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


class TestCopyArtifactAsExternalBackReference:
    """Tests for back-reference creation when copying artifacts as external."""

    def _parse_frontmatter(self, file_path):
        """Helper to parse YAML frontmatter from a file."""
        content = file_path.read_text()
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not match:
            return {}
        return yaml.safe_load(match.group(1)) or {}

    def test_back_reference_created_on_copy(self, tmp_path):
        """After copy_artifact_as_external(), source artifact's frontmatter has dependents entry."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
dependents: []
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

        # Verify source artifact's frontmatter has dependents entry
        source_frontmatter = self._parse_frontmatter(chunk_dir / "GOAL.md")
        assert "dependents" in source_frontmatter
        assert len(source_frontmatter["dependents"]) == 1

        dependent = source_frontmatter["dependents"][0]
        assert dependent["artifact_type"] == "chunk"
        assert dependent["artifact_id"] == "my_feature"  # Dest name (same as source since no --name)
        assert dependent["repo"] == "acme/proj"  # Target project
        # No pinned SHA in back-reference anymore - always resolve to HEAD
        assert "pinned" not in dependent

        # Verify result indicates source was updated
        assert result.get("source_updated") is True

    def test_existing_dependents_preserved(self, tmp_path):
        """Existing dependents entries are preserved when adding new back-reference."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Create artifact with existing dependent
        chunk_dir = external_path / "docs" / "chunks" / "shared_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
dependents:
  - artifact_type: chunk
    artifact_id: old_feature
    repo: acme/old_project
    pinned: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
---

# Chunk Goal

A shared feature.
""")

        # Copy as external reference to the first project
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/shared_feature",
            target_project="acme/proj1",
        )

        # Verify both old and new dependents exist
        source_frontmatter = self._parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(source_frontmatter["dependents"]) == 2

        # Find old dependent
        old_dep = next(
            (d for d in source_frontmatter["dependents"] if d["repo"] == "acme/old_project"),
            None,
        )
        assert old_dep is not None
        assert old_dep["artifact_id"] == "old_feature"
        assert old_dep["pinned"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        # Find new dependent
        new_dep = next(
            (d for d in source_frontmatter["dependents"] if d["repo"] == "acme/proj1"),
            None,
        )
        assert new_dep is not None
        assert new_dep["artifact_id"] == "shared_feature"

    def test_idempotent_copy_no_duplicates(self, tmp_path):
        """Re-running copy with same params doesn't create duplicate dependents."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths: []
code_references: []
created_after: []
dependents: []
---

# Chunk Goal

A feature chunk.
""")

        # Copy as external reference once
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Check dependent was added
        first_frontmatter = self._parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(first_frontmatter["dependents"]) == 1

        # Remove the external.yaml directory so we can copy again (simulating re-run scenario)
        import shutil
        external_yaml_dir = project_paths[0] / "docs" / "chunks" / "my_feature"
        shutil.rmtree(external_yaml_dir)

        # Copy again - this should not create duplicate dependent
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify only one dependent entry exists (no duplicates)
        source_frontmatter = self._parse_frontmatter(chunk_dir / "GOAL.md")
        proj_deps = [
            d for d in source_frontmatter["dependents"]
            if d["repo"] == "acme/proj"
            and d["artifact_type"] == "chunk"
            and d["artifact_id"] == "my_feature"
        ]
        assert len(proj_deps) == 1

    def test_back_reference_all_artifact_types(self, tmp_path):
        """Back-reference works for all artifact types."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Test each artifact type
        artifact_configs = [
            ("chunks", "test_chunk", "GOAL.md", "chunk", "ACTIVE"),
            ("narratives", "test_narrative", "OVERVIEW.md", "narrative", "ACTIVE"),
            ("investigations", "test_investigation", "OVERVIEW.md", "investigation", "ONGOING"),
            ("subsystems", "test_subsystem", "OVERVIEW.md", "subsystem", "STABLE"),
        ]

        for dir_name, artifact_name, main_file, type_value, status in artifact_configs:
            # Create artifact in external repo
            artifact_dir = external_path / "docs" / dir_name / artifact_name
            artifact_dir.mkdir(parents=True)
            (artifact_dir / main_file).write_text(f"""---
status: {status}
created_after: []
dependents: []
---

# {artifact_name}
""")

            # Copy as external reference
            result = copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path=f"docs/{dir_name}/{artifact_name}",
                target_project="acme/proj",
            )

            # Verify back-reference was created
            source_frontmatter = self._parse_frontmatter(artifact_dir / main_file)
            assert "dependents" in source_frontmatter, f"Failed for {dir_name}"
            assert len(source_frontmatter["dependents"]) == 1, f"Failed for {dir_name}"

            dependent = source_frontmatter["dependents"][0]
            assert dependent["artifact_type"] == type_value, f"Failed for {dir_name}"
            assert dependent["artifact_id"] == artifact_name, f"Failed for {dir_name}"
            assert dependent["repo"] == "acme/proj", f"Failed for {dir_name}"
            # No pinned SHA in back-reference anymore - always resolve to HEAD
            assert "pinned" not in dependent, f"Failed for {dir_name}"

    def test_back_reference_with_new_name(self, tmp_path):
        """Back-reference uses destination name when --name is provided."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "original_name"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Original
""")

        # Copy with a new name
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/original_name",
            target_project="acme/proj",
            new_name="renamed_feature",
        )

        # Verify back-reference uses the destination name
        source_frontmatter = self._parse_frontmatter(chunk_dir / "GOAL.md")
        dependent = source_frontmatter["dependents"][0]
        assert dependent["artifact_id"] == "renamed_feature"  # Destination name
