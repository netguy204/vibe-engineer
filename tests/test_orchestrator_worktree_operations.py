# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for orchestrator worktree operations (commit, multi-repo creation/removal/merge)."""

import subprocess
import pytest
from pathlib import Path

from conftest import make_ve_initialized_git_repo, setup_task_directory
from orchestrator.worktree import WorktreeManager, WorktreeError


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository for testing."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
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

    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path


# Chunk: docs/chunks/orch_mechanical_commit - Unit tests for mechanical commit
class TestCommitChanges:
    """Tests for WorktreeManager.commit_changes()."""

    def test_commit_changes_success(self, git_repo):
        """Commits staged changes with correct message format."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "new_file.txt").write_text("new content")

        # Commit using commit_changes
        result = manager.commit_changes("test_chunk")

        assert result is True

        # Verify the commit message format
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert log_result.stdout.strip() == "feat: chunk test_chunk"

        # Verify the file was committed
        assert not manager.has_uncommitted_changes("test_chunk")

    def test_commit_changes_nothing_to_commit(self, git_repo):
        """Returns False when nothing to commit."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No changes made - should return False
        result = manager.commit_changes("test_chunk")

        assert result is False

    def test_commit_changes_stages_all_files(self, git_repo):
        """Stages all changes including untracked files."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Create multiple files - one new, one modified
        (worktree_path / "new_file.txt").write_text("new content")
        (worktree_path / "README.md").write_text("modified content")

        # Commit using commit_changes
        result = manager.commit_changes("test_chunk")

        assert result is True

        # Verify both files were committed
        assert not manager.has_uncommitted_changes("test_chunk")

        # Check commit includes both files
        show_result = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert "new_file.txt" in show_result.stdout
        assert "README.md" in show_result.stdout

    def test_commit_changes_nonexistent_worktree_raises(self, git_repo):
        """Raises WorktreeError for non-existent worktree."""
        manager = WorktreeManager(git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.commit_changes("nonexistent_chunk")

        assert "does not exist" in str(exc_info.value)

    def test_commit_changes_commit_in_worktree_not_main(self, git_repo):
        """Commit happens in worktree, not main repo."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "worktree_file.txt").write_text("worktree content")

        # Commit
        manager.commit_changes("test_chunk")

        # File should NOT exist in main repo (until merge)
        assert not (git_repo / "worktree_file.txt").exists()

        # File should exist in worktree
        assert (worktree_path / "worktree_file.txt").exists()

    def test_commit_changes_message_format(self, git_repo):
        """Commit message follows expected format: feat: chunk {chunk_name}."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("my_feature_chunk")

        # Make a change
        (worktree_path / "feature.txt").write_text("feature")
        manager.commit_changes("my_feature_chunk")

        # Verify commit message
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert log_result.stdout.strip() == "feat: chunk my_feature_chunk"


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo worktree creation tests
class TestMultiRepoWorktreeCreation:
    """Tests for multi-repo worktree creation in task context."""

    @pytest.fixture
    def task_repos(self, tmp_path):
        """Create a task directory with multiple repos for testing."""
        _, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a", "project_b"],
        )
        return {
            "external": external,
            "project_a": projects[0],
            "project_b": projects[1],
        }

    def test_create_worktree_with_repo_paths_creates_work_dir(self, task_repos):
        """Creates work/ directory structure when repo_paths provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Should return path to work/ directory
        assert work_dir.name == "work"
        assert work_dir.exists()

    def test_create_worktree_with_repo_paths_creates_worktrees_per_repo(self, task_repos):
        """Creates a worktree for each repo under work/<repo-name>/."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Each repo should have a worktree directory under work/
        assert (work_dir / "external" / ".git").exists()
        assert (work_dir / "project_a" / ".git").exists()

    def test_create_worktree_with_repo_paths_uses_correct_branches(self, task_repos):
        """Each worktree uses orch/<chunk> branch in its respective repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check branch in each repo worktree
        for repo_name in ["external", "project_a"]:
            worktree_dir = work_dir / repo_name
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=worktree_dir,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "orch/test_chunk"

    def test_create_worktree_single_repo_unchanged(self, task_repos):
        """Single-repo behavior unchanged when repo_paths not provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        # Without repo_paths - should use existing single-repo behavior
        worktree_path = manager.create_worktree("test_chunk")

        # Should be at worktree/ not work/<repo-name>/
        assert worktree_path.name == "worktree"
        assert (worktree_path / ".git").exists()

    def test_get_work_directory_returns_work_path(self, task_repos):
        """get_work_directory returns correct work/ path."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        work_dir = manager.get_work_directory("test_chunk")

        assert work_dir == external / ".ve" / "chunks" / "test_chunk" / "work"

    def test_create_worktree_creates_log_dir_for_task_context(self, task_repos):
        """Creates log directory for task context worktrees."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        log_path = manager.get_log_path("test_chunk")
        assert log_path.exists()


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo worktree removal tests
class TestMultiRepoWorktreeRemoval:
    """Tests for multi-repo worktree removal."""

    @pytest.fixture
    def task_repos(self, tmp_path):
        """Create a task directory with multiple repos for testing."""
        _, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a", "project_b"],
        )
        return {
            "external": external,
            "project_a": projects[0],
            "project_b": projects[1],
        }

    def test_remove_worktree_with_repo_paths_cleans_all(self, task_repos):
        """Removes all repo worktrees when repo_paths provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)
        assert work_dir.exists()

        manager.remove_worktree("test_chunk", repo_paths=repo_paths)

        # Work directory should be gone
        assert not (external / ".ve" / "chunks" / "test_chunk" / "work").exists()

    def test_remove_worktree_with_repo_paths_removes_branches(self, task_repos):
        """Branches deleted when remove_branch=True for multi-repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        manager.remove_worktree("test_chunk", remove_branch=True, repo_paths=repo_paths)

        # Branches should be gone in each repo
        for repo_path in repo_paths:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
                cwd=repo_path,
                capture_output=True,
            )
            assert result.returncode != 0

    def test_remove_worktree_single_repo_unchanged(self, task_repos):
        """Single-repo removal unchanged when repo_paths not provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        # Create single-repo worktree
        worktree_path = manager.create_worktree("test_chunk")
        assert worktree_path.exists()

        # Remove without repo_paths - should use existing behavior
        manager.remove_worktree("test_chunk")

        assert not manager.worktree_exists("test_chunk")


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo merge operation tests
class TestMultiRepoMerge:
    """Tests for multi-repo merge operations."""

    @pytest.fixture
    def task_repos(self, tmp_path):
        """Create a task directory with multiple repos for testing."""
        _, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a"],
        )
        return {
            "external": external,
            "project_a": projects[0],
        }

    def test_merge_to_base_with_repo_paths_merges_all(self, task_repos):
        """Merges chunk branch in each repo back to base."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Make changes in each repo worktree
        (work_dir / "external" / "external_file.txt").write_text("external content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add external file"],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )

        (work_dir / "project_a" / "project_file.txt").write_text("project content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add project file"],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )

        # Remove worktrees before merge
        manager.remove_worktree("test_chunk", remove_branch=False, repo_paths=repo_paths)

        # Merge in all repos
        manager.merge_to_base("test_chunk", repo_paths=repo_paths)

        # Files should be on base branch in each repo
        assert (task_repos["external"] / "external_file.txt").exists()
        assert (task_repos["project_a"] / "project_file.txt").exists()

    def test_has_changes_with_repo_paths(self, task_repos):
        """has_changes returns dict of changes per repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Make change only in external repo
        (work_dir / "external" / "change.txt").write_text("change")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add change"],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )

        changes = manager.has_changes("test_chunk", repo_paths=repo_paths)

        assert isinstance(changes, dict)
        assert changes["external"] is True
        assert changes["project_a"] is False
