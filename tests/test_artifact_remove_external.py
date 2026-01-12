"""Tests for removing external artifact references.

# Chunk: docs/chunks/remove_external_ref - Remove artifact from external project tests
"""

import re

import pytest
import yaml
from click.testing import CliRunner

from ve import cli
from conftest import make_ve_initialized_git_repo, setup_task_directory


def _parse_frontmatter(file_path):
    """Helper to parse YAML frontmatter from a file."""
    content = file_path.read_text()
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


class TestRemoveArtifactFromExternalCoreFunction:
    """Tests for the remove_artifact_from_external() core function."""

    def test_happy_path_removes_external_yaml(self, tmp_path):
        """Removes external.yaml from project artifact directory."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

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
dependents: []
---

# Chunk Goal

A feature chunk.
""")

        # Copy as external reference to the project
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify external.yaml exists before removal
        external_yaml_path = project_path / "docs" / "chunks" / "my_feature" / "external.yaml"
        assert external_yaml_path.exists()

        # Remove the external reference
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify external.yaml was removed
        assert not external_yaml_path.exists()
        assert result["removed"] is True

    def test_removes_dependent_from_artifact_frontmatter(self, tmp_path):
        """Updates dependents list in external repo to remove the project entry."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

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
dependents: []
---

# Chunk Goal

A feature chunk.
""")

        # Copy as external reference to the project
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify dependent was added
        frontmatter = _parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(frontmatter["dependents"]) == 1

        # Remove the external reference
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify dependent was removed
        frontmatter = _parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(frontmatter["dependents"]) == 0
        assert result["dependent_removed"] is True

    def test_idempotent_no_error_when_external_yaml_missing(self, tmp_path):
        """No error if external.yaml doesn't exist (idempotent)."""
        from task_utils import remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an artifact in the external repo (but don't copy as external)
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk Goal
""")

        # Just create an empty directory in the project (as if it was already removed)
        (project_path / "docs" / "chunks" / "my_feature").mkdir(parents=True, exist_ok=True)

        # Removing should not raise an error
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Result should indicate nothing was removed
        assert result["removed"] is False

    def test_cleans_up_empty_artifact_directory(self, tmp_path):
        """Removes empty directory after deleting external.yaml."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an artifact in the external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk Goal
""")

        # Copy as external reference to the project
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify directory exists before removal
        artifact_dir = project_path / "docs" / "chunks" / "my_feature"
        assert artifact_dir.exists()

        # Remove the external reference
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify empty directory was cleaned up
        assert not artifact_dir.exists()
        assert result["directory_cleaned"] is True

    def test_preserves_other_files_in_artifact_directory(self, tmp_path):
        """Doesn't delete directory if other files are present."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create an artifact in the external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk Goal
""")

        # Copy as external reference to the project
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Add an extra file to the artifact directory
        artifact_dir = project_path / "docs" / "chunks" / "my_feature"
        (artifact_dir / "extra_file.txt").write_text("Extra content")

        # Remove the external reference
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify external.yaml was removed but directory was preserved
        assert not (artifact_dir / "external.yaml").exists()
        assert artifact_dir.exists()
        assert (artifact_dir / "extra_file.txt").exists()
        assert result["directory_cleaned"] is False

    def test_error_when_not_in_task_directory(self, tmp_path):
        """Errors when not in task directory context."""
        from task_utils import remove_artifact_from_external, TaskRemoveExternalError

        # Create a standalone project (no .ve-task.yaml)
        project_path = tmp_path / "standalone"
        make_ve_initialized_git_repo(project_path)

        with pytest.raises(TaskRemoveExternalError) as exc_info:
            remove_artifact_from_external(
                task_dir=project_path,
                artifact_path="docs/chunks/my_chunk",
                target_project="acme/proj",
            )

        assert "task" in str(exc_info.value).lower()

    def test_error_when_artifact_not_in_external_repo(self, tmp_path):
        """Errors when artifact doesn't exist in external repo."""
        from task_utils import remove_artifact_from_external, TaskRemoveExternalError

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        with pytest.raises(TaskRemoveExternalError) as exc_info:
            remove_artifact_from_external(
                task_dir=task_dir,
                artifact_path="docs/chunks/nonexistent",
                target_project="acme/proj",
            )

        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()

    def test_error_when_project_not_in_task_config(self, tmp_path):
        """Errors when target project is not in task configuration."""
        from task_utils import remove_artifact_from_external, TaskRemoveExternalError

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

        with pytest.raises(TaskRemoveExternalError) as exc_info:
            remove_artifact_from_external(
                task_dir=task_dir,
                artifact_path="docs/chunks/my_feature",
                target_project="acme/unknown_project",
            )

        assert "not found" in str(exc_info.value).lower() or "not a valid" in str(exc_info.value).lower()

    def test_removes_all_artifact_types(self, tmp_path):
        """Works for chunks, investigations, narratives, subsystems."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Test each artifact type
        artifact_configs = [
            ("chunks", "test_chunk", "GOAL.md", "ACTIVE"),
            ("narratives", "test_narrative", "OVERVIEW.md", "ACTIVE"),
            ("investigations", "test_investigation", "OVERVIEW.md", "ONGOING"),
            ("subsystems", "test_subsystem", "OVERVIEW.md", "STABLE"),
        ]

        for dir_name, artifact_name, main_file, status in artifact_configs:
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
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path=f"docs/{dir_name}/{artifact_name}",
                target_project="acme/proj",
            )

            # Verify it exists
            target_dir = project_path / "docs" / dir_name / artifact_name
            assert (target_dir / "external.yaml").exists(), f"Failed for {dir_name}"

            # Remove the external reference
            result = remove_artifact_from_external(
                task_dir=task_dir,
                artifact_path=f"docs/{dir_name}/{artifact_name}",
                target_project="acme/proj",
            )

            # Verify removal
            assert result["removed"] is True, f"Failed for {dir_name}"
            assert not (target_dir / "external.yaml").exists(), f"Failed for {dir_name}"

    def test_flexible_path_input(self, tmp_path):
        """Accepts 'my_chunk', 'chunks/my_chunk', 'docs/chunks/my_chunk'."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create three artifacts to test flexible paths
        for i, name in enumerate(["flex_a", "flex_b", "flex_c"]):
            chunk_dir = external_path / "docs" / "chunks" / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text(f"""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk {i}
""")

            # Copy as external reference
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path=f"docs/chunks/{name}",
                target_project="acme/proj",
            )

        # Test different path formats
        path_formats = [
            ("docs/chunks/flex_a", "flex_a"),  # Full path
            ("chunks/flex_b", "flex_b"),        # Without docs/
            ("flex_c", "flex_c"),               # Just name
        ]

        for path_input, artifact_name in path_formats:
            target_dir = project_path / "docs" / "chunks" / artifact_name

            # Verify it exists before removal
            assert (target_dir / "external.yaml").exists(), f"Pre-check failed for {path_input}"

            # Remove using the flexible path
            result = remove_artifact_from_external(
                task_dir=task_dir,
                artifact_path=path_input,
                target_project="acme/proj",
            )

            # Verify removal
            assert result["removed"] is True, f"Failed for {path_input}"

    def test_flexible_project_input(self, tmp_path):
        """Accepts 'proj' or 'acme/proj' formats."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create two artifacts
        for name in ["proj_test_a", "proj_test_b"]:
            chunk_dir = external_path / "docs" / "chunks" / name
            chunk_dir.mkdir(parents=True)
            (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk
""")

            # Copy as external reference
            copy_artifact_as_external(
                task_dir=task_dir,
                artifact_path=f"docs/chunks/{name}",
                target_project="acme/proj",
            )

        # Test with short project name
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/proj_test_a",
            target_project="proj",  # Short name
        )
        assert result["removed"] is True

        # Test with full project name
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/proj_test_b",
            target_project="acme/proj",  # Full name
        )
        assert result["removed"] is True

    def test_warns_when_removing_last_project_link(self, tmp_path):
        """Returns warning flag when artifact becomes orphaned."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create an artifact in the external repo
        chunk_dir = external_path / "docs" / "chunks" / "orphan_test"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Chunk Goal
""")

        # Copy as external reference (single project)
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/orphan_test",
            target_project="acme/proj",
        )

        # Verify only one dependent
        frontmatter = _parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(frontmatter["dependents"]) == 1

        # Remove the external reference
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/orphan_test",
            target_project="acme/proj",
        )

        # Should warn about orphaned artifact
        assert result["orphaned"] is True

    def test_preserves_other_dependents(self, tmp_path):
        """Only removes matching dependent entry, preserves others."""
        from task_utils import copy_artifact_as_external, remove_artifact_from_external

        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, project_names=["proj1", "proj2"]
        )

        # Create an artifact in the external repo
        chunk_dir = external_path / "docs" / "chunks" / "shared_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Shared Feature
""")

        # Copy as external reference to both projects
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/shared_feature",
            target_project="acme/proj1",
        )
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/shared_feature",
            target_project="acme/proj2",
        )

        # Verify both dependents exist
        frontmatter = _parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(frontmatter["dependents"]) == 2

        # Remove only from proj1
        result = remove_artifact_from_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/shared_feature",
            target_project="acme/proj1",
        )

        # Verify only proj1's dependent was removed
        frontmatter = _parse_frontmatter(chunk_dir / "GOAL.md")
        assert len(frontmatter["dependents"]) == 1
        assert frontmatter["dependents"][0]["repo"] == "acme/proj2"
        assert result["orphaned"] is False  # Still has one dependent


class TestRemoveArtifactFromExternalCLI:
    """Tests for ve artifact remove-external CLI command."""

    def test_cli_command_exists(self, tmp_path):
        """ve artifact remove-external command exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["artifact", "remove-external", "--help"])

        assert result.exit_code == 0
        assert "remove-external" in result.output.lower() or "remove" in result.output.lower()

    def test_cli_happy_path(self, tmp_path):
        """CLI removes external reference and reports success."""
        from task_utils import copy_artifact_as_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)
        project_path = project_paths[0]

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Feature
""")

        # Copy as external reference
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/my_feature",
            target_project="acme/proj",
        )

        # Verify it exists before CLI removal
        external_yaml_path = project_path / "docs" / "chunks" / "my_feature" / "external.yaml"
        assert external_yaml_path.exists()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "remove-external",
                "docs/chunks/my_feature",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        assert not external_yaml_path.exists()

    def test_cli_idempotent(self, tmp_path):
        """Exit code 0 when external.yaml already missing."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo (but don't copy to project)
        chunk_dir = external_path / "docs" / "chunks" / "my_feature"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Feature
""")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "remove-external",
                "docs/chunks/my_feature",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        # Should still exit with 0 (idempotent)
        assert result.exit_code == 0

    def test_cli_error_handling(self, tmp_path):
        """Non-zero exit for errors."""
        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "remove-external",
                "docs/chunks/nonexistent",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code != 0

    def test_cli_warns_on_orphan(self, tmp_path):
        """Output includes warning when last link removed."""
        from task_utils import copy_artifact_as_external

        task_dir, external_path, project_paths = setup_task_directory(tmp_path)

        # Create artifact in external repo
        chunk_dir = external_path / "docs" / "chunks" / "orphan_warning_test"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: ACTIVE
created_after: []
dependents: []
---

# Feature
""")

        # Copy as external reference (single project)
        copy_artifact_as_external(
            task_dir=task_dir,
            artifact_path="docs/chunks/orphan_warning_test",
            target_project="acme/proj",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "artifact", "remove-external",
                "docs/chunks/orphan_warning_test",
                "acme/proj",
                "--cwd", str(task_dir),
            ],
        )

        assert result.exit_code == 0
        # Check for warning text about orphan/no project links
        assert "warning" in result.output.lower() or "orphan" in result.output.lower() or "no project" in result.output.lower()
