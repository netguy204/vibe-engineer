"""Tests for sync module helper functions."""

import subprocess

import pytest
import yaml

from sync import (
    find_external_refs,
    update_external_yaml,
    SyncResult,
    sync_task_directory,
    sync_single_repo,
)


class TestFindExternalRefs:
    """Tests for find_external_refs function."""

    def test_returns_empty_list_when_no_chunks_dir(self, tmp_path):
        """Returns empty list when docs/chunks doesn't exist."""
        result = find_external_refs(tmp_path)
        assert result == []

    def test_returns_empty_list_when_no_external_refs(self, tmp_path):
        """Returns empty list when no external.yaml files exist."""
        chunks_dir = tmp_path / "docs" / "chunks"
        chunks_dir.mkdir(parents=True)
        # Create a normal chunk (no external.yaml)
        (chunks_dir / "0001-feature" / "GOAL.md").parent.mkdir()
        (chunks_dir / "0001-feature" / "GOAL.md").write_text("# Goal\n")

        result = find_external_refs(tmp_path)
        assert result == []

    def test_finds_single_external_ref(self, tmp_path):
        """Finds a single external.yaml file."""
        chunks_dir = tmp_path / "docs" / "chunks"
        external_dir = chunks_dir / "0001-external_feature"
        external_dir.mkdir(parents=True)
        external_yaml = external_dir / "external.yaml"
        external_yaml.write_text(
            "repo: acme/chunks\n"
            "chunk: 0001-feature\n"
            "track: main\n"
            "pinned: " + "a" * 40 + "\n"
        )

        result = find_external_refs(tmp_path)
        assert len(result) == 1
        assert result[0] == external_yaml

    def test_finds_multiple_external_refs(self, tmp_path):
        """Finds multiple external.yaml files."""
        chunks_dir = tmp_path / "docs" / "chunks"

        for i in range(3):
            external_dir = chunks_dir / f"000{i+1}-external_{i}"
            external_dir.mkdir(parents=True)
            (external_dir / "external.yaml").write_text(
                f"repo: acme/chunks\nchunk: 000{i+1}-feature\ntrack: main\npinned: {'a' * 40}\n"
            )

        result = find_external_refs(tmp_path)
        assert len(result) == 3

    def test_ignores_normal_chunks(self, tmp_path):
        """Ignores chunks that have GOAL.md (normal chunks)."""
        chunks_dir = tmp_path / "docs" / "chunks"

        # External chunk
        external_dir = chunks_dir / "0001-external"
        external_dir.mkdir(parents=True)
        (external_dir / "external.yaml").write_text(
            "repo: acme/chunks\nchunk: 0001-feature\ntrack: main\npinned: " + "a" * 40 + "\n"
        )

        # Normal chunk
        normal_dir = chunks_dir / "0002-normal"
        normal_dir.mkdir(parents=True)
        (normal_dir / "GOAL.md").write_text("# Goal\n")

        result = find_external_refs(tmp_path)
        assert len(result) == 1
        assert "0001-external" in str(result[0])


class TestUpdateExternalYaml:
    """Tests for update_external_yaml function."""

    def test_updates_pinned_sha(self, tmp_path):
        """Updates the pinned field when SHA differs."""
        external_yaml = tmp_path / "external.yaml"
        old_sha = "a" * 40
        new_sha = "b" * 40
        external_yaml.write_text(
            f"repo: acme/chunks\nchunk: 0001-feature\ntrack: main\npinned: {old_sha}\n"
        )

        result = update_external_yaml(external_yaml, new_sha)

        assert result is True
        content = yaml.safe_load(external_yaml.read_text())
        assert content["pinned"] == new_sha

    def test_returns_false_when_sha_unchanged(self, tmp_path):
        """Returns False when pinned SHA is already current."""
        external_yaml = tmp_path / "external.yaml"
        sha = "a" * 40
        external_yaml.write_text(
            f"repo: acme/chunks\nchunk: 0001-feature\ntrack: main\npinned: {sha}\n"
        )

        result = update_external_yaml(external_yaml, sha)

        assert result is False

    def test_preserves_other_fields(self, tmp_path):
        """Preserves repo, chunk, track fields when updating pinned."""
        external_yaml = tmp_path / "external.yaml"
        external_yaml.write_text(
            "repo: acme/chunks\n"
            "chunk: 0001-feature\n"
            "track: develop\n"
            "pinned: " + "a" * 40 + "\n"
        )

        update_external_yaml(external_yaml, "b" * 40)

        content = yaml.safe_load(external_yaml.read_text())
        assert content["repo"] == "acme/chunks"
        assert content["chunk"] == "0001-feature"
        assert content["track"] == "develop"

    def test_handles_null_pinned(self, tmp_path):
        """Updates pinned when it was null/missing."""
        external_yaml = tmp_path / "external.yaml"
        external_yaml.write_text(
            "repo: acme/chunks\nchunk: 0001-feature\ntrack: main\n"
        )

        result = update_external_yaml(external_yaml, "b" * 40)

        assert result is True
        content = yaml.safe_load(external_yaml.read_text())
        assert content["pinned"] == "b" * 40


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_sync_result_creation(self):
        """Creates SyncResult with all fields."""
        result = SyncResult(
            chunk_id="0001-feature",
            old_sha="a" * 40,
            new_sha="b" * 40,
            updated=True,
        )
        assert result.chunk_id == "0001-feature"
        assert result.old_sha == "a" * 40
        assert result.new_sha == "b" * 40
        assert result.updated is True
        assert result.error is None

    def test_sync_result_with_error(self):
        """Creates SyncResult with error message."""
        result = SyncResult(
            chunk_id="0001-feature",
            old_sha="a" * 40,
            new_sha="",
            updated=False,
            error="External repo not accessible",
        )
        assert result.error == "External repo not accessible"


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
def task_directory(tmp_path, git_repo, tmp_path_factory):
    """Create a task directory with external repo and projects."""
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
    (external_repo / "README.md").write_text("# External chunks\n")
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

    # Create project repos
    for project_name in ["service-a", "service-b"]:
        project_dir = tmp_path_factory.mktemp(project_name)
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
        (project_dir / "README.md").write_text(f"# {project_name}\n")
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )

        # Symlink into task dir
        (task_dir / project_name).symlink_to(project_dir)

        # Create external chunk reference with outdated SHA
        chunks_dir = project_dir / "docs" / "chunks" / "0001-shared_feature"
        chunks_dir.mkdir(parents=True)
        outdated_sha = "0" * 40  # Outdated SHA
        (chunks_dir / "external.yaml").write_text(
            f"repo: acme/chunks-repo\n"
            f"chunk: 0001-shared_feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"  # Quote to ensure string
        )

    # Create .ve-task.yaml
    (task_dir / ".ve-task.yaml").write_text(
        "external_chunk_repo: acme/chunks-repo\n"
        "projects:\n"
        "  - acme/service-a\n"
        "  - acme/service-b\n"
    )

    return {
        "task_dir": task_dir,
        "external_repo": external_repo,
        "external_sha": external_sha,
    }


class TestSyncTaskDirectory:
    """Tests for sync_task_directory function."""

    def test_updates_external_refs_across_projects(self, task_directory):
        """Updates external.yaml files across multiple projects."""
        task_dir = task_directory["task_dir"]
        expected_sha = task_directory["external_sha"]

        results = sync_task_directory(task_dir)

        assert len(results) == 2
        for result in results:
            assert result.updated is True
            assert result.new_sha == expected_sha
            assert result.old_sha == "0" * 40

    def test_dry_run_does_not_modify_files(self, task_directory):
        """Dry run reports changes without modifying files."""
        task_dir = task_directory["task_dir"]

        results = sync_task_directory(task_dir, dry_run=True)

        # Should report what would change
        assert len(results) == 2
        for result in results:
            assert result.updated is True

        # But files should be unchanged
        service_a_yaml = (
            task_dir
            / "service-a"
            / "docs"
            / "chunks"
            / "0001-shared_feature"
            / "external.yaml"
        )
        content = yaml.safe_load(service_a_yaml.read_text())
        assert content["pinned"] == "0" * 40  # Unchanged

    def test_project_filter(self, task_directory):
        """Syncs only specified projects when filter provided."""
        task_dir = task_directory["task_dir"]

        results = sync_task_directory(task_dir, project_filter=["acme/service-a"])

        assert len(results) == 1
        assert "service-a" in results[0].chunk_id

    def test_chunk_filter(self, task_directory):
        """Syncs only specified chunks when filter provided."""
        task_dir = task_directory["task_dir"]

        # Add another external ref to one project
        chunks_dir = (
            task_dir / "service-a" / "docs" / "chunks" / "0002-another_feature"
        )
        chunks_dir.mkdir(parents=True)
        outdated_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: acme/chunks-repo\n"
            f"chunk: 0002-another_feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"  # Quote to ensure string
        )

        results = sync_task_directory(
            task_dir, chunk_filter=["0001-shared_feature"]
        )

        # Should only sync the filtered chunk across projects
        for result in results:
            assert "0001-shared_feature" in result.chunk_id

    def test_returns_already_current_status(self, task_directory):
        """Reports refs that are already current."""
        task_dir = task_directory["task_dir"]
        expected_sha = task_directory["external_sha"]

        # First sync
        sync_task_directory(task_dir)

        # Second sync - should be no-op
        results = sync_task_directory(task_dir)

        assert len(results) == 2
        for result in results:
            assert result.updated is False
            assert result.old_sha == expected_sha
            assert result.new_sha == expected_sha

    def test_continues_on_error(self, task_directory):
        """Continues processing other refs if one fails."""
        task_dir = task_directory["task_dir"]

        # Make service-b's external.yaml point to non-existent repo
        service_b_yaml = (
            task_dir
            / "service-b"
            / "docs"
            / "chunks"
            / "0001-shared_feature"
            / "external.yaml"
        )
        outdated_sha = "0" * 40
        service_b_yaml.write_text(
            f"repo: nonexistent/repo\n"
            f"chunk: 0001-feature\n"
            f"track: main\n"
            f"pinned: '{outdated_sha}'\n"  # Quote to ensure string
        )

        results = sync_task_directory(task_dir)

        # Should have results for both, one with error
        assert len(results) == 2
        errors = [r for r in results if r.error is not None]
        successes = [r for r in results if r.error is None]
        assert len(errors) == 1
        assert len(successes) == 1


class TestSyncSingleRepo:
    """Tests for sync_single_repo function."""

    def test_updates_external_refs_using_ls_remote(self, git_repo, monkeypatch):
        """Updates external.yaml using git ls-remote for remote resolution."""
        import sync

        # Create external reference
        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        old_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: octocat/Hello-World\n"
            f"chunk: 0001-feature\n"
            f"track: master\n"
            f"pinned: '{old_sha}'\n"
        )

        # Mock resolve_remote_ref to avoid network
        mock_sha = "a" * 40
        monkeypatch.setattr(sync, "resolve_remote_ref", lambda *args, **kwargs: mock_sha)

        results = sync_single_repo(git_repo)

        assert len(results) == 1
        assert results[0].updated is True
        assert results[0].new_sha == mock_sha

    def test_dry_run(self, git_repo, monkeypatch):
        """Dry run reports changes without modifying files."""
        import sync

        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        old_sha = "0" * 40
        external_yaml = chunks_dir / "external.yaml"
        external_yaml.write_text(
            f"repo: octocat/Hello-World\n"
            f"chunk: 0001-feature\n"
            f"track: master\n"
            f"pinned: '{old_sha}'\n"
        )

        mock_sha = "a" * 40
        monkeypatch.setattr(sync, "resolve_remote_ref", lambda *args, **kwargs: mock_sha)

        results = sync_single_repo(git_repo, dry_run=True)

        assert results[0].updated is True
        # File should be unchanged
        content = yaml.safe_load(external_yaml.read_text())
        assert content["pinned"] == old_sha

    def test_chunk_filter(self, git_repo, monkeypatch):
        """Syncs only specified chunks when filter provided."""
        import sync

        # Create two external references
        for i in range(2):
            chunks_dir = git_repo / "docs" / "chunks" / f"000{i+1}-external"
            chunks_dir.mkdir(parents=True)
            old_sha = "0" * 40
            (chunks_dir / "external.yaml").write_text(
                f"repo: octocat/Hello-World\n"
                f"chunk: 000{i+1}-feature\n"
                f"track: master\n"
                f"pinned: '{old_sha}'\n"
            )

        monkeypatch.setattr(sync, "resolve_remote_ref", lambda *args, **kwargs: "a" * 40)

        results = sync_single_repo(git_repo, chunk_filter=["0001-external"])

        assert len(results) == 1
        assert "0001-external" in results[0].chunk_id

    def test_handles_remote_error(self, git_repo, monkeypatch):
        """Handles remote resolution failure with error in result."""
        import sync

        chunks_dir = git_repo / "docs" / "chunks" / "0001-external"
        chunks_dir.mkdir(parents=True)
        old_sha = "0" * 40
        (chunks_dir / "external.yaml").write_text(
            f"repo: nonexistent/repo\n"
            f"chunk: 0001-feature\n"
            f"track: main\n"
            f"pinned: '{old_sha}'\n"
        )

        def raise_error(*args, **kwargs):
            raise ValueError("Remote not accessible")

        monkeypatch.setattr(sync, "resolve_remote_ref", raise_error)

        results = sync_single_repo(git_repo)

        assert len(results) == 1
        assert results[0].error is not None
        assert "not accessible" in results[0].error.lower()
