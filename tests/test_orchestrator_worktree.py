# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - Worktree manager tests
# Chunk: docs/chunks/orch_mechanical_commit - Mechanical commit tests
"""Tests for the orchestrator worktree manager."""

import subprocess
import pytest
from pathlib import Path

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


class TestWorktreeManager:
    """Tests for WorktreeManager."""

    def test_get_worktree_path(self, git_repo):
        """Returns expected path for worktree."""
        manager = WorktreeManager(git_repo)

        path = manager.get_worktree_path("test_chunk")

        assert path == git_repo / ".ve" / "chunks" / "test_chunk" / "worktree"

    def test_get_log_path(self, git_repo):
        """Returns expected path for log directory."""
        manager = WorktreeManager(git_repo)

        path = manager.get_log_path("test_chunk")

        assert path == git_repo / ".ve" / "chunks" / "test_chunk" / "log"

    def test_get_branch_name(self, git_repo):
        """Returns expected branch name format."""
        manager = WorktreeManager(git_repo)

        branch = manager.get_branch_name("test_chunk")

        assert branch == "orch/test_chunk"

    def test_worktree_exists_false(self, git_repo):
        """Returns False when worktree doesn't exist."""
        manager = WorktreeManager(git_repo)

        assert manager.worktree_exists("test_chunk") is False

    def test_create_worktree(self, git_repo):
        """Creates worktree successfully."""
        manager = WorktreeManager(git_repo)

        worktree_path = manager.create_worktree("test_chunk")

        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()
        assert manager.worktree_exists("test_chunk")

    def test_create_worktree_creates_log_dir(self, git_repo):
        """Creates log directory along with worktree."""
        manager = WorktreeManager(git_repo)

        manager.create_worktree("test_chunk")

        log_path = manager.get_log_path("test_chunk")
        assert log_path.exists()

    def test_create_worktree_creates_branch(self, git_repo):
        """Creates branch when creating worktree."""
        manager = WorktreeManager(git_repo)

        manager.create_worktree("test_chunk")

        # Check branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_create_worktree_idempotent(self, git_repo):
        """Creating worktree twice returns same path."""
        manager = WorktreeManager(git_repo)

        path1 = manager.create_worktree("test_chunk")
        path2 = manager.create_worktree("test_chunk")

        assert path1 == path2

    def test_remove_worktree(self, git_repo):
        """Removes worktree successfully."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk")

        assert not manager.worktree_exists("test_chunk")

    def test_remove_worktree_keeps_branch(self, git_repo):
        """Removing worktree keeps branch by default."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk", remove_branch=False)

        # Branch should still exist
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_remove_worktree_with_branch(self, git_repo):
        """Can remove branch along with worktree."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk", remove_branch=True)

        # Branch should be gone
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode != 0

    def test_remove_nonexistent_worktree(self, git_repo):
        """Removing nonexistent worktree doesn't raise."""
        manager = WorktreeManager(git_repo)

        # Should not raise
        manager.remove_worktree("nonexistent")

    def test_list_worktrees_empty(self, git_repo):
        """Returns empty list when no worktrees exist."""
        manager = WorktreeManager(git_repo)

        worktrees = manager.list_worktrees()

        assert worktrees == []

    def test_list_worktrees(self, git_repo):
        """Lists created worktrees."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("chunk_a")
        manager.create_worktree("chunk_b")

        worktrees = manager.list_worktrees()

        assert set(worktrees) == {"chunk_a", "chunk_b"}

    def test_worktree_has_correct_content(self, git_repo):
        """Worktree contains same content as main."""
        # Add a file to main
        (git_repo / "test.txt").write_text("test content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add test file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Worktree should have the file
        assert (worktree_path / "test.txt").exists()
        assert (worktree_path / "test.txt").read_text() == "test content"


class TestWorktreeCleanup:
    """Tests for worktree cleanup operations."""

    def test_cleanup_orphaned_worktrees(self, git_repo):
        """Cleanup returns list of worktree chunk names."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("chunk_a")
        manager.create_worktree("chunk_b")

        orphaned = manager.cleanup_orphaned_worktrees()

        # Returns the worktree names
        assert set(orphaned) == {"chunk_a", "chunk_b"}


class TestBaseBranch:
    """Tests for base branch handling."""

    def test_base_branch_defaults_to_current(self, git_repo):
        """Base branch defaults to current branch."""
        manager = WorktreeManager(git_repo)

        # Should be 'main' or 'master' depending on git config
        assert manager.base_branch in ("main", "master")

    def test_base_branch_can_be_specified(self, git_repo):
        """Base branch can be explicitly set."""
        # Create a feature branch first
        subprocess.run(
            ["git", "branch", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(git_repo, base_branch="feature")

        assert manager.base_branch == "feature"

    def test_worktree_branches_from_base(self, git_repo):
        """Worktree branches are created from base branch."""
        # Make a commit on a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("feature content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create worktree manager with feature as base
        manager = WorktreeManager(git_repo, base_branch="feature")
        worktree_path = manager.create_worktree("test_chunk")

        # The worktree should have the feature file
        assert (worktree_path / "feature.txt").exists()


class TestMergeToBase:
    """Tests for merging back to base branch."""

    def test_merge_to_base_success(self, git_repo):
        """Successfully merges chunk branch back to base."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree before merge
        manager.remove_worktree("test_chunk", remove_branch=False)

        # Merge back to base
        manager.merge_to_base("test_chunk", delete_branch=True)

        # The new file should be on the base branch
        assert (git_repo / "new_file.txt").exists()

        # The orch branch should be deleted
        assert not manager._branch_exists("orch/test_chunk")

    def test_merge_to_base_no_changes(self, git_repo):
        """has_changes returns False for branch with no new commits."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No changes made
        assert manager.has_changes("test_chunk") is False

    def test_merge_to_base_with_changes(self, git_repo):
        """has_changes returns True for branch with commits."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change
        (worktree_path / "change.txt").write_text("change")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add change"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        assert manager.has_changes("test_chunk") is True

    def test_merge_nonexistent_branch_raises(self, git_repo):
        """Merging nonexistent branch raises WorktreeError."""
        manager = WorktreeManager(git_repo)

        with pytest.raises(WorktreeError):
            manager.merge_to_base("nonexistent")

    def test_merge_keeps_branch_when_requested(self, git_repo):
        """merge_to_base can keep the branch after merge."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change
        (worktree_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree and merge with delete_branch=False
        manager.remove_worktree("test_chunk", remove_branch=False)
        manager.merge_to_base("test_chunk", delete_branch=False)

        # Branch should still exist
        assert manager._branch_exists("orch/test_chunk")


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
