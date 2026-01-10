"""Tests for external_resolve module."""
# Chunk: docs/chunks/external_resolve - External resolve tests

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from external_resolve import (
    ResolveResult,
    find_chunk_in_project,
    resolve_task_directory,
    resolve_single_repo,
)
from task_utils import TaskChunkError


class TestFindChunkInProject:
    """Tests for find_chunk_in_project function."""

    def test_finds_exact_match(self, tmp_path):
        """Finds chunk by exact directory name."""
        chunks_dir = tmp_path / "docs" / "chunks" / "0001-feature"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text("# Goal\n")

        result = find_chunk_in_project(tmp_path, "0001-feature")

        assert result == chunks_dir

    def test_finds_by_number_prefix(self, tmp_path):
        """Finds chunk by number prefix match."""
        chunks_dir = tmp_path / "docs" / "chunks" / "0001-feature_name"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text("# Goal\n")

        result = find_chunk_in_project(tmp_path, "0001")

        assert result == chunks_dir

    def test_returns_none_for_missing_chunk(self, tmp_path):
        """Returns None when chunk doesn't exist."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)

        result = find_chunk_in_project(tmp_path, "0001-feature")

        assert result is None

    def test_returns_none_for_missing_chunks_dir(self, tmp_path):
        """Returns None when docs/chunks doesn't exist."""
        result = find_chunk_in_project(tmp_path, "0001-feature")

        assert result is None


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with one commit."""
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def task_directory(tmp_path, tmp_path_factory):
    """Create a task directory with external repo and project."""
    task_dir = tmp_path

    # Create external chunk repo
    external_repo = tmp_path_factory.mktemp("external")
    subprocess.run(["git", "init"], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Create external chunk in external repo
    external_chunk_dir = external_repo / "docs" / "chunks" / "0001-shared_feature"
    external_chunk_dir.mkdir(parents=True)
    (external_chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# External Goal\n")
    (external_chunk_dir / "PLAN.md").write_text("# External Plan\n")

    subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=external_repo,
        check=True,
        capture_output=True,
    )

    # Get external repo SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=external_repo,
        check=True,
        capture_output=True,
        text=True,
    )
    external_sha = result.stdout.strip()

    # Symlink external repo into task dir
    (task_dir / "chunks-repo").symlink_to(external_repo)

    # Create project repo
    project_dir = tmp_path_factory.mktemp("service-a")
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )
    (project_dir / "README.md").write_text("# Service A\n")

    # Create external chunk reference (using ExternalArtifactRef format)
    # Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
    chunks_dir = project_dir / "docs" / "chunks" / "0001-shared_feature"
    chunks_dir.mkdir(parents=True)
    (chunks_dir / "external.yaml").write_text(
        f"artifact_type: chunk\n"
        f"artifact_id: 0001-shared_feature\n"
        f"repo: acme/chunks-repo\n"
        f"track: main\n"
        f"pinned: {external_sha}\n"
    )

    subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=project_dir,
        check=True,
        capture_output=True,
    )

    # Symlink into task dir
    (task_dir / "service-a").symlink_to(project_dir)

    # Create .ve-task.yaml
    (task_dir / ".ve-task.yaml").write_text(
        "external_chunk_repo: acme/chunks-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
        "project_dir": project_dir,
    }


class TestResolveTaskDirectory:
    """Tests for resolve_task_directory function."""

    def test_resolves_from_local_worktree(self, task_directory):
        """Resolves external chunk from local worktree."""
        task_dir = task_directory["task_dir"]
        expected_sha = task_directory["external_sha"]

        result = resolve_task_directory(task_dir, "0001-shared_feature")

        assert result.repo == "acme/chunks-repo"
        assert result.external_chunk_id == "0001-shared_feature"
        assert result.track == "main"
        assert result.resolved_sha == expected_sha
        assert "External Goal" in result.goal_content
        assert "External Plan" in result.plan_content

    def test_at_pinned_reads_historical_state(self, task_directory):
        """Uses pinned SHA when --at-pinned is specified."""
        task_dir = task_directory["task_dir"]
        external_repo = task_directory["external_repo"]
        original_sha = task_directory["external_sha"]

        # Make a new commit to external repo
        external_chunk_dir = external_repo / "docs" / "chunks" / "0001-shared_feature"
        (external_chunk_dir / "GOAL.md").write_text("---\nstatus: IMPLEMENTING\n---\n# Updated Goal\n")
        subprocess.run(["git", "add", "."], cwd=external_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update"],
            cwd=external_repo,
            check=True,
            capture_output=True,
        )

        # Resolve at pinned should show original content
        result = resolve_task_directory(task_dir, "0001-shared_feature", at_pinned=True)

        assert result.resolved_sha == original_sha
        assert "External Goal" in result.goal_content
        assert "Updated Goal" not in result.goal_content

    def test_project_filter_selects_correct_project(self, task_directory, tmp_path_factory):
        """Disambiguates when chunk exists in multiple projects."""
        task_dir = task_directory["task_dir"]

        # Add another project with same chunk ID
        project_b = tmp_path_factory.mktemp("service-b")
        subprocess.run(["git", "init"], cwd=project_b, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )

        # Create external chunk reference (using ExternalArtifactRef format)
        chunks_dir = project_b / "docs" / "chunks" / "0001-shared_feature"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            f"artifact_type: chunk\n"
            f"artifact_id: 0001-shared_feature\n"
            f"repo: acme/chunks-repo\n"
            f"track: main\n"
            f"pinned: {'a' * 40}\n"
        )
        subprocess.run(["git", "add", "."], cwd=project_b, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_b,
            check=True,
            capture_output=True,
        )

        (task_dir / "service-b").symlink_to(project_b)

        # Update task config
        (task_dir / ".ve-task.yaml").write_text(
            "external_chunk_repo: acme/chunks-repo\n"
            "projects:\n"
            "  - acme/service-a\n"
            "  - acme/service-b\n"
        )

        # Without filter should error
        with pytest.raises(TaskChunkError) as exc_info:
            resolve_task_directory(task_dir, "0001-shared_feature")
        assert "multiple projects" in str(exc_info.value)

        # With filter should succeed
        result = resolve_task_directory(
            task_dir, "0001-shared_feature", project_filter="acme/service-a"
        )
        assert result.repo == "acme/chunks-repo"

    def test_error_on_nonexistent_chunk(self, task_directory):
        """Raises error for nonexistent chunk."""
        task_dir = task_directory["task_dir"]

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_task_directory(task_dir, "9999-nonexistent")

        assert "not found" in str(exc_info.value)

    def test_error_on_non_external_chunk(self, task_directory):
        """Raises error if chunk is not an external reference."""
        task_dir = task_directory["task_dir"]
        project_dir = task_directory["project_dir"]

        # Create a normal chunk (with GOAL.md)
        normal_chunk = project_dir / "docs" / "chunks" / "0002-normal"
        normal_chunk.mkdir(parents=True)
        (normal_chunk / "GOAL.md").write_text("# Goal\n")

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_task_directory(task_dir, "0002-normal")

        assert "not an external reference" in str(exc_info.value)

    def test_error_when_pinned_null_with_at_pinned(self, task_directory):
        """Raises error when --at-pinned used but pinned is null."""
        task_dir = task_directory["task_dir"]
        project_dir = task_directory["project_dir"]

        # Update external.yaml to have no pinned value (using ExternalArtifactRef format)
        external_yaml = project_dir / "docs" / "chunks" / "0001-shared_feature" / "external.yaml"
        external_yaml.write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-shared_feature\n"
            "repo: acme/chunks-repo\n"
            "track: main\n"
            "pinned: null\n"
        )

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_task_directory(task_dir, "0001-shared_feature", at_pinned=True)

        assert "no pinned SHA" in str(exc_info.value)

    def test_qualified_chunk_id_format(self, task_directory):
        """Accepts project:chunk format for disambiguation."""
        task_dir = task_directory["task_dir"]

        result = resolve_task_directory(task_dir, "acme/service-a:0001-shared_feature")

        assert result.repo == "acme/chunks-repo"


class TestResolveSingleRepo:
    """Tests for resolve_single_repo function."""

    def test_resolves_via_cache(self, git_repo, monkeypatch):
        """Resolves external chunk using repo cache."""
        # Create external chunk reference (using ExternalArtifactRef format)
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-feature\n"
            "repo: acme/chunks\n"
            "track: main\n"
            "pinned: null\n"
        )

        mock_sha = "a" * 40

        # Mock repo_cache functions
        import external_resolve

        monkeypatch.setattr(
            external_resolve.repo_cache, "ensure_cached", lambda repo: git_repo
        )
        monkeypatch.setattr(
            external_resolve.repo_cache, "resolve_ref", lambda repo, ref: mock_sha
        )
        monkeypatch.setattr(
            external_resolve.repo_cache,
            "get_file_at_ref",
            lambda repo, ref, path: "# Goal content" if "GOAL" in path else "# Plan content",
        )

        result = resolve_single_repo(git_repo, "0001-external")

        assert result.repo == "acme/chunks"
        assert result.external_chunk_id == "0001-feature"
        assert result.resolved_sha == mock_sha
        assert "Goal content" in result.goal_content
        assert "Plan content" in result.plan_content

    def test_at_pinned_uses_pinned_sha(self, git_repo, monkeypatch):
        """Uses pinned SHA when --at-pinned is specified."""
        pinned_sha = "b" * 40

        # Using ExternalArtifactRef format
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            f"artifact_type: chunk\n"
            f"artifact_id: 0001-feature\n"
            f"repo: acme/chunks\n"
            f"track: main\n"
            f"pinned: {pinned_sha}\n"
        )

        import external_resolve

        monkeypatch.setattr(
            external_resolve.repo_cache, "ensure_cached", lambda repo: git_repo
        )
        monkeypatch.setattr(
            external_resolve.repo_cache,
            "get_file_at_ref",
            lambda repo, ref, path: f"content at {ref[:7]}" if "GOAL" in path else None,
        )

        result = resolve_single_repo(git_repo, "0001-external", at_pinned=True)

        assert result.resolved_sha == pinned_sha
        assert pinned_sha[:7] in result.goal_content

    def test_error_when_pinned_null_and_at_pinned(self, git_repo, monkeypatch):
        """Raises error when --at-pinned but pinned is null."""
        # Using ExternalArtifactRef format
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-feature\n"
            "repo: acme/chunks\n"
            "track: main\n"
            "pinned: null\n"
        )

        import external_resolve

        monkeypatch.setattr(
            external_resolve.repo_cache, "ensure_cached", lambda repo: git_repo
        )

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_single_repo(git_repo, "0001-external", at_pinned=True)

        assert "no pinned SHA" in str(exc_info.value)

    def test_handles_missing_plan_md(self, git_repo, monkeypatch):
        """Gracefully handles missing PLAN.md."""
        # Using ExternalArtifactRef format
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-feature\n"
            "repo: acme/chunks\n"
            "track: main\n"
            "pinned: null\n"
        )

        mock_sha = "a" * 40

        import external_resolve

        monkeypatch.setattr(
            external_resolve.repo_cache, "ensure_cached", lambda repo: git_repo
        )
        monkeypatch.setattr(
            external_resolve.repo_cache, "resolve_ref", lambda repo, ref: mock_sha
        )

        def mock_get_file(repo, ref, path):
            if "GOAL" in path:
                return "# Goal content"
            raise ValueError("file not found")

        monkeypatch.setattr(external_resolve.repo_cache, "get_file_at_ref", mock_get_file)

        result = resolve_single_repo(git_repo, "0001-external")

        assert result.goal_content == "# Goal content"
        assert result.plan_content is None

    def test_error_on_nonexistent_chunk(self, git_repo):
        """Raises error for nonexistent chunk."""
        with pytest.raises(TaskChunkError) as exc_info:
            resolve_single_repo(git_repo, "9999-nonexistent")

        assert "not found" in str(exc_info.value)

    def test_error_on_non_external_chunk(self, git_repo):
        """Raises error if chunk is not an external reference."""
        # Create a normal chunk (with GOAL.md)
        chunks_dir = git_repo / "docs" / "chunks" / "0001-normal"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text("# Goal\n")

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_single_repo(git_repo, "0001-normal")

        assert "not an external reference" in str(exc_info.value)

    def test_error_on_inaccessible_repo(self, git_repo, monkeypatch):
        """Raises error when external repo cannot be accessed."""
        # Using ExternalArtifactRef format
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "external.yaml").write_text(
            "artifact_type: chunk\n"
            "artifact_id: 0001-feature\n"
            "repo: nonexistent/repo\n"
            "track: main\n"
            "pinned: null\n"
        )

        import external_resolve

        def mock_ensure_cached(repo):
            raise ValueError("Failed to clone")

        monkeypatch.setattr(external_resolve.repo_cache, "ensure_cached", mock_ensure_cached)

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_single_repo(git_repo, "0001-external")

        assert "Failed to access" in str(exc_info.value)
