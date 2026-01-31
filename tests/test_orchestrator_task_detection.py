# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_task_detection - Task context detection tests
"""Tests for task context detection in the orchestrator."""

import pytest
from pathlib import Path

from conftest import make_ve_initialized_git_repo, setup_task_directory
from orchestrator.models import (
    TaskContextInfo,
    detect_task_context,
    get_chunk_location,
    get_chunk_dependents,
    resolve_affected_repos,
)


class TestDetectTaskContext:
    """Tests for detect_task_context function."""

    def test_single_repo_mode(self, tmp_path):
        """Returns single-repo context when no .ve-task.yaml present."""
        # Create a normal git repo without .ve-task.yaml
        make_ve_initialized_git_repo(tmp_path)

        result = detect_task_context(tmp_path)

        assert result.is_task_context is False
        assert result.root_dir == tmp_path
        assert result.external_repo is None
        assert result.external_repo_path is None
        assert result.projects == []
        assert result.project_paths == []

    def test_task_context_mode(self, tmp_path):
        """Returns task context info when .ve-task.yaml present."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, external_name="ext", project_names=["proj1", "proj2"]
        )

        result = detect_task_context(task_dir)

        assert result.is_task_context is True
        assert result.root_dir == task_dir
        assert result.external_repo == "acme/ext"
        assert result.external_repo_path == external_path
        assert result.projects == ["acme/proj1", "acme/proj2"]
        assert len(result.project_paths) == 2
        assert project_paths[0] in result.project_paths
        assert project_paths[1] in result.project_paths

    def test_task_context_missing_external_repo(self, tmp_path):
        """Handles missing external repo gracefully."""
        # Create task config pointing to non-existent repo
        task_dir = tmp_path / "task"
        task_dir.mkdir()
        (task_dir / ".ve-task.yaml").write_text("""
external_artifact_repo: acme/missing
projects:
  - acme/proj1
""")
        # Create proj1 as it exists
        proj1 = task_dir / "proj1"
        make_ve_initialized_git_repo(proj1)

        result = detect_task_context(task_dir)

        assert result.is_task_context is True
        assert result.root_dir == task_dir
        assert result.external_repo == "acme/missing"
        assert result.external_repo_path is None  # Not resolved
        assert len(result.project_paths) == 1

    def test_resolves_to_absolute_path(self, tmp_path):
        """Root dir is always resolved to absolute path."""
        make_ve_initialized_git_repo(tmp_path)

        # Use relative path
        result = detect_task_context(Path("."))

        assert result.root_dir.is_absolute()


class TestGetChunkLocation:
    """Tests for get_chunk_location function."""

    def test_single_repo_mode(self, tmp_path):
        """Returns chunk path in project docs/chunks for single-repo mode."""
        make_ve_initialized_git_repo(tmp_path)
        task_info = TaskContextInfo(
            is_task_context=False,
            root_dir=tmp_path,
        )

        path = get_chunk_location(task_info, "my_chunk")

        assert path == tmp_path / "docs" / "chunks" / "my_chunk"

    def test_task_context_mode(self, tmp_path):
        """Returns chunk path in external repo for task context mode."""
        external_path = tmp_path / "external"
        make_ve_initialized_git_repo(external_path)

        task_info = TaskContextInfo(
            is_task_context=True,
            root_dir=tmp_path,
            external_repo="acme/external",
            external_repo_path=external_path,
        )

        path = get_chunk_location(task_info, "my_chunk")

        assert path == external_path / "docs" / "chunks" / "my_chunk"

    def test_task_context_without_external_path(self, tmp_path):
        """Falls back to root_dir when external path not resolved."""
        task_info = TaskContextInfo(
            is_task_context=True,
            root_dir=tmp_path,
            external_repo="acme/external",
            external_repo_path=None,  # Not resolved
        )

        path = get_chunk_location(task_info, "my_chunk")

        # Falls back to root_dir
        assert path == tmp_path / "docs" / "chunks" / "my_chunk"


class TestGetChunkDependents:
    """Tests for get_chunk_dependents function."""

    def test_no_goal_file(self, tmp_path):
        """Returns empty list when GOAL.md doesn't exist."""
        chunk_path = tmp_path / "my_chunk"
        chunk_path.mkdir(parents=True)

        result = get_chunk_dependents(chunk_path)

        assert result == []

    def test_no_frontmatter(self, tmp_path):
        """Returns empty list when GOAL.md has no frontmatter."""
        chunk_path = tmp_path / "my_chunk"
        chunk_path.mkdir(parents=True)
        (chunk_path / "GOAL.md").write_text("# My Chunk\n\nNo frontmatter here.\n")

        result = get_chunk_dependents(chunk_path)

        assert result == []

    def test_no_dependents_field(self, tmp_path):
        """Returns empty list when frontmatter has no dependents field."""
        chunk_path = tmp_path / "my_chunk"
        chunk_path.mkdir(parents=True)
        (chunk_path / "GOAL.md").write_text("""---
status: FUTURE
---
# My Chunk
""")

        result = get_chunk_dependents(chunk_path)

        assert result == []

    def test_with_dependents(self, tmp_path):
        """Returns dependents list from frontmatter."""
        chunk_path = tmp_path / "my_chunk"
        chunk_path.mkdir(parents=True)
        (chunk_path / "GOAL.md").write_text("""---
status: FUTURE
dependents:
  - artifact_type: subsystem
    artifact_id: template_system
    repo: acme/proj1
  - artifact_type: chunk
    artifact_id: other_chunk
    repo: acme/proj2
---
# My Chunk
""")

        result = get_chunk_dependents(chunk_path)

        assert len(result) == 2
        assert result[0]["repo"] == "acme/proj1"
        assert result[1]["repo"] == "acme/proj2"


class TestResolveAffectedRepos:
    """Tests for resolve_affected_repos function."""

    def test_single_repo_mode(self, tmp_path):
        """Returns only root_dir in single-repo mode."""
        make_ve_initialized_git_repo(tmp_path)
        task_info = TaskContextInfo(
            is_task_context=False,
            root_dir=tmp_path,
        )

        result = resolve_affected_repos(task_info, "my_chunk")

        assert result == [tmp_path]

    def test_task_context_no_dependents(self, tmp_path):
        """Returns all project repos when chunk has no dependents."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, external_name="ext", project_names=["proj1", "proj2"]
        )
        task_info = detect_task_context(task_dir)

        # Create chunk without dependents field
        chunk_dir = external_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: FUTURE
---
# My Chunk
""")

        result = resolve_affected_repos(task_info, "my_chunk")

        # Should return all project repos
        assert len(result) == 2
        assert set(result) == set(project_paths)

    def test_task_context_with_dependents(self, tmp_path):
        """Returns only repos mentioned in dependents field."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, external_name="ext", project_names=["proj1", "proj2", "proj3"]
        )
        task_info = detect_task_context(task_dir)

        # Create chunk with specific dependents
        chunk_dir = external_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: FUTURE
dependents:
  - artifact_type: subsystem
    artifact_id: auth_system
    repo: acme/proj1
  - artifact_type: chunk
    artifact_id: related_chunk
    repo: acme/proj2
---
# My Chunk
""")

        result = resolve_affected_repos(task_info, "my_chunk")

        # Should only return proj1 and proj2
        assert len(result) == 2
        assert project_paths[0] in result  # proj1
        assert project_paths[1] in result  # proj2
        assert project_paths[2] not in result  # proj3 excluded

    def test_task_context_unreachable_repos_ignored(self, tmp_path):
        """Silently ignores unreachable repos in dependents."""
        task_dir, external_path, project_paths = setup_task_directory(
            tmp_path, external_name="ext", project_names=["proj1"]
        )
        task_info = detect_task_context(task_dir)

        # Create chunk with a repo that doesn't exist
        chunk_dir = external_path / "docs" / "chunks" / "my_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text("""---
status: FUTURE
dependents:
  - artifact_type: subsystem
    artifact_id: something
    repo: acme/proj1
  - artifact_type: chunk
    artifact_id: something_else
    repo: acme/nonexistent
---
# My Chunk
""")

        result = resolve_affected_repos(task_info, "my_chunk")

        # Should only return proj1
        assert len(result) == 1
        assert project_paths[0] in result


class TestTaskContextInfoDataclass:
    """Tests for TaskContextInfo dataclass."""

    def test_default_values(self):
        """TaskContextInfo has expected default values."""
        info = TaskContextInfo(
            is_task_context=False,
            root_dir=Path("/tmp/test"),
        )

        assert info.external_repo is None
        assert info.external_repo_path is None
        assert info.projects == []
        assert info.project_paths == []

    def test_with_all_fields(self):
        """TaskContextInfo can be constructed with all fields."""
        info = TaskContextInfo(
            is_task_context=True,
            root_dir=Path("/tmp/task"),
            external_repo="acme/ext",
            external_repo_path=Path("/tmp/task/ext"),
            projects=["acme/proj1", "acme/proj2"],
            project_paths=[Path("/tmp/task/proj1"), Path("/tmp/task/proj2")],
        )

        assert info.is_task_context is True
        assert info.external_repo == "acme/ext"
        assert len(info.projects) == 2
        assert len(info.project_paths) == 2
