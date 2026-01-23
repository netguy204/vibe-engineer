"""Tests for external_resolve module."""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from external_resolve import (
    ResolveResult,
    find_chunk_in_project,
    find_artifact_in_project,
    resolve_task_directory,
    resolve_single_repo,
    resolve_artifact_task_directory,
    resolve_artifact_single_repo,
)
from models import ArtifactType
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
        "external_artifact_repo: acme/chunks-repo\n"
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
        assert result.artifact_type == ArtifactType.CHUNK
        assert result.artifact_id == "0001-shared_feature"
        assert result.track == "main"
        assert result.resolved_sha == expected_sha
        assert "External Goal" in result.main_content
        assert "External Plan" in result.secondary_content

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
            "external_artifact_repo: acme/chunks-repo\n"
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
        assert result.artifact_type == ArtifactType.CHUNK
        assert result.artifact_id == "0001-feature"
        assert result.resolved_sha == mock_sha
        assert "Goal content" in result.main_content
        assert "Plan content" in result.secondary_content

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

        assert result.main_content == "# Goal content"
        assert result.secondary_content is None

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


class TestFindArtifactInProject:
    """Tests for find_artifact_in_project function."""

    def test_finds_narrative(self, tmp_path):
        """Finds narrative by directory name."""
        narratives_dir = tmp_path / "docs" / "narratives" / "0001-feature_work"
        narratives_dir.mkdir(parents=True)
        (narratives_dir / "OVERVIEW.md").write_text("# Overview\n")

        result = find_artifact_in_project(tmp_path, "0001-feature_work", ArtifactType.NARRATIVE)

        assert result == narratives_dir

    def test_finds_investigation(self, tmp_path):
        """Finds investigation by directory name."""
        investigations_dir = tmp_path / "docs" / "investigations" / "0001-memory_leak"
        investigations_dir.mkdir(parents=True)
        (investigations_dir / "OVERVIEW.md").write_text("# Overview\n")

        result = find_artifact_in_project(tmp_path, "0001-memory_leak", ArtifactType.INVESTIGATION)

        assert result == investigations_dir

    def test_finds_subsystem(self, tmp_path):
        """Finds subsystem by directory name."""
        subsystems_dir = tmp_path / "docs" / "subsystems" / "workflow_artifacts"
        subsystems_dir.mkdir(parents=True)
        (subsystems_dir / "OVERVIEW.md").write_text("# Overview\n")

        result = find_artifact_in_project(tmp_path, "workflow_artifacts", ArtifactType.SUBSYSTEM)

        assert result == subsystems_dir

    def test_finds_by_prefix(self, tmp_path):
        """Finds artifact by numeric prefix match."""
        narratives_dir = tmp_path / "docs" / "narratives" / "0003-big_feature"
        narratives_dir.mkdir(parents=True)
        (narratives_dir / "OVERVIEW.md").write_text("# Overview\n")

        result = find_artifact_in_project(tmp_path, "0003", ArtifactType.NARRATIVE)

        assert result == narratives_dir

    def test_returns_none_for_wrong_type(self, tmp_path):
        """Returns None when artifact exists but in wrong directory."""
        chunks_dir = tmp_path / "docs" / "chunks" / "0001-feature"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "GOAL.md").write_text("# Goal\n")

        result = find_artifact_in_project(tmp_path, "0001-feature", ArtifactType.NARRATIVE)

        assert result is None


class TestResolveArtifactSingleRepo:
    """Tests for resolve_artifact_single_repo with different artifact types."""

    def test_resolves_narrative_via_cache(self, git_repo, monkeypatch):
        """Resolves external narrative using repo cache."""
        narratives_dir = git_repo / "docs" / "narratives" / "0001-feature"
        narratives_dir.mkdir(parents=True)
        (narratives_dir / "external.yaml").write_text(
            "artifact_type: narrative\n"
            "artifact_id: 0001-big_feature\n"
            "repo: acme/narratives\n"
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
        monkeypatch.setattr(
            external_resolve.repo_cache,
            "get_file_at_ref",
            lambda repo, ref, path: "# Narrative Overview" if "OVERVIEW" in path else None,
        )

        result = resolve_artifact_single_repo(git_repo, "0001-feature", ArtifactType.NARRATIVE)

        assert result.repo == "acme/narratives"
        assert result.artifact_type == ArtifactType.NARRATIVE
        assert result.artifact_id == "0001-big_feature"
        assert result.resolved_sha == mock_sha
        assert "Narrative Overview" in result.main_content
        assert result.secondary_content is None  # Narratives don't have secondary files

    def test_resolves_investigation_via_cache(self, git_repo, monkeypatch):
        """Resolves external investigation using repo cache."""
        investigations_dir = git_repo / "docs" / "investigations" / "0001-bug"
        investigations_dir.mkdir(parents=True)
        (investigations_dir / "external.yaml").write_text(
            "artifact_type: investigation\n"
            "artifact_id: 0001-memory_issue\n"
            "repo: acme/investigations\n"
            "track: main\n"
            "pinned: null\n"
        )

        mock_sha = "c" * 40

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
            lambda repo, ref, path: "# Investigation Findings" if "OVERVIEW" in path else None,
        )

        result = resolve_artifact_single_repo(git_repo, "0001-bug", ArtifactType.INVESTIGATION)

        assert result.repo == "acme/investigations"
        assert result.artifact_type == ArtifactType.INVESTIGATION
        assert result.artifact_id == "0001-memory_issue"
        assert "Investigation Findings" in result.main_content
        assert result.secondary_content is None

    def test_resolves_subsystem_via_cache(self, git_repo, monkeypatch):
        """Resolves external subsystem using repo cache."""
        subsystems_dir = git_repo / "docs" / "subsystems" / "validation"
        subsystems_dir.mkdir(parents=True)
        (subsystems_dir / "external.yaml").write_text(
            "artifact_type: subsystem\n"
            "artifact_id: 0001-validation\n"
            "repo: acme/subsystems\n"
            "track: main\n"
            "pinned: null\n"
        )

        mock_sha = "d" * 40

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
            lambda repo, ref, path: "# Subsystem Overview" if "OVERVIEW" in path else None,
        )

        result = resolve_artifact_single_repo(git_repo, "validation", ArtifactType.SUBSYSTEM)

        assert result.repo == "acme/subsystems"
        assert result.artifact_type == ArtifactType.SUBSYSTEM
        assert result.artifact_id == "0001-validation"
        assert "Subsystem Overview" in result.main_content
        assert result.secondary_content is None


@pytest.fixture
def narrative_task_directory(tmp_path, tmp_path_factory):
    """Create a task directory with external narrative reference."""
    task_dir = tmp_path

    # Create external narrative repo
    external_repo = tmp_path_factory.mktemp("external_narratives")
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

    # Create external narrative in external repo
    external_narrative_dir = external_repo / "docs" / "narratives" / "0001-big_feature"
    external_narrative_dir.mkdir(parents=True)
    (external_narrative_dir / "OVERVIEW.md").write_text("---\nstatus: ACTIVE\n---\n# External Narrative\n\nThis is a narrative.")

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
    (task_dir / "narratives-repo").symlink_to(external_repo)

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

    # Create external narrative reference
    narratives_dir = project_dir / "docs" / "narratives" / "0001-big_feature"
    narratives_dir.mkdir(parents=True)
    (narratives_dir / "external.yaml").write_text(
        f"artifact_type: narrative\n"
        f"artifact_id: 0001-big_feature\n"
        f"repo: acme/narratives-repo\n"
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
        "external_artifact_repo: acme/narratives-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
        "project_dir": project_dir,
    }


class TestResolveArtifactTaskDirectory:
    """Tests for resolve_artifact_task_directory with different artifact types."""

    def test_resolves_narrative_from_worktree(self, narrative_task_directory):
        """Resolves external narrative from local worktree."""
        task_dir = narrative_task_directory["task_dir"]
        expected_sha = narrative_task_directory["external_sha"]

        result = resolve_artifact_task_directory(
            task_dir, "0001-big_feature", ArtifactType.NARRATIVE
        )

        assert result.repo == "acme/narratives-repo"
        assert result.artifact_type == ArtifactType.NARRATIVE
        assert result.artifact_id == "0001-big_feature"
        assert result.track == "main"
        assert result.resolved_sha == expected_sha
        assert "External Narrative" in result.main_content
        assert result.secondary_content is None  # Narratives don't have secondary files

    def test_error_on_nonexistent_narrative(self, narrative_task_directory):
        """Raises error for nonexistent narrative."""
        task_dir = narrative_task_directory["task_dir"]

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_artifact_task_directory(task_dir, "9999-nonexistent", ArtifactType.NARRATIVE)

        assert "not found" in str(exc_info.value)

    def test_error_on_non_external_narrative(self, narrative_task_directory):
        """Raises error if narrative is not an external reference."""
        task_dir = narrative_task_directory["task_dir"]
        project_dir = narrative_task_directory["project_dir"]

        # Create a normal narrative (with OVERVIEW.md)
        normal_narrative = project_dir / "docs" / "narratives" / "0002-normal"
        normal_narrative.mkdir(parents=True)
        (normal_narrative / "OVERVIEW.md").write_text("# Overview\n")

        with pytest.raises(TaskChunkError) as exc_info:
            resolve_artifact_task_directory(task_dir, "0002-normal", ArtifactType.NARRATIVE)

        assert "not an external reference" in str(exc_info.value)
