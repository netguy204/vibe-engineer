# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator worktree manager."""

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


# Chunk: docs/chunks/orch_safe_branch_delete - Tests for safe branch deletion
class TestUnmergedCommitsDetection:
    """Tests for has_unmerged_commits method."""

    def test_has_unmerged_commits_detects_unmerged(self, git_repo):
        """Detects commits on branch not reachable from base."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a commit in the worktree
        (worktree_path / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        has_unmerged, count = manager.has_unmerged_commits("test_chunk")

        assert has_unmerged is True
        assert count == 1

    def test_has_unmerged_commits_returns_zero_when_merged(self, git_repo):
        """Returns (False, 0) when branch has no additional commits."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No additional commits made in worktree

        has_unmerged, count = manager.has_unmerged_commits("test_chunk")

        assert has_unmerged is False
        assert count == 0

    def test_has_unmerged_commits_nonexistent_branch(self, git_repo):
        """Returns (False, 0) for non-existent branch."""
        manager = WorktreeManager(git_repo)

        has_unmerged, count = manager.has_unmerged_commits("nonexistent")

        assert has_unmerged is False
        assert count == 0

    def test_has_unmerged_commits_multiple_commits(self, git_repo):
        """Correctly counts multiple unmerged commits."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make multiple commits
        for i in range(3):
            (worktree_path / f"file_{i}.txt").write_text(f"content {i}")
            subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Add file {i}"],
                cwd=worktree_path,
                check=True,
                capture_output=True,
            )

        has_unmerged, count = manager.has_unmerged_commits("test_chunk")

        assert has_unmerged is True
        assert count == 3


class TestSafeBranchDeletion:
    """Tests for safe branch deletion behavior."""

    def test_remove_worktree_uses_safe_delete_by_default(self, git_repo):
        """Verifies -d (safe delete) is used by default, not -D."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a commit that will NOT be merged
        (worktree_path / "unmerged.txt").write_text("unmerged content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Unmerged commit"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree with remove_branch=True but force=False (default)
        manager.remove_worktree("test_chunk", remove_branch=True, force=False)

        # Branch should still exist because -d refuses to delete unmerged branches
        assert manager._branch_exists("orch/test_chunk")

    def test_remove_worktree_force_deletes_unmerged_branch(self, git_repo):
        """Force delete removes branch even with unmerged commits."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a commit that will NOT be merged
        (worktree_path / "unmerged.txt").write_text("unmerged content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Unmerged commit"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree with force=True
        manager.remove_worktree("test_chunk", remove_branch=True, force=True)

        # Branch should be deleted despite unmerged commits
        assert not manager._branch_exists("orch/test_chunk")

    def test_remove_worktree_safe_delete_on_merged_branch_succeeds(self, git_repo):
        """Safe delete successfully removes branch when fully merged."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No commits made - branch is identical to base, so -d will succeed

        manager.remove_worktree("test_chunk", remove_branch=True, force=False)

        # Branch should be deleted since it has no unmerged commits
        assert not manager._branch_exists("orch/test_chunk")


# Chunk: docs/chunks/finalize_double_commit - Test submodule-resilient worktree removal
class TestSubmoduleWorktreeRemoval:
    """Tests that worktree removal handles submodule-containing worktrees."""

    def test_remove_worktree_submodule_fallback(self, git_repo):
        """Worktree removal falls back to rmtree + prune when git worktree remove fails.

        When a worktree contains submodules, `git worktree remove` fails with
        "working trees containing submodules cannot be moved or removed".
        The fallback should use rmtree and then prune stale worktree metadata.
        """
        from unittest.mock import patch, call

        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("submodule_chunk")

        # Create a file so the worktree has content
        (worktree_path / "some_file.txt").write_text("content")

        original_run = subprocess.run

        # Track prune calls
        prune_calls = []

        def mock_run(cmd, **kwargs):
            # Make git worktree remove always fail (simulating submodule error)
            if cmd[:3] == ["git", "worktree", "remove"]:
                result = subprocess.CompletedProcess(
                    cmd, returncode=1,
                    stdout="",
                    stderr="fatal: working trees containing submodules cannot be moved or removed"
                )
                return result
            if cmd[:3] == ["git", "worktree", "prune"]:
                prune_calls.append(cmd)
                return original_run(cmd, **kwargs)
            # Also handle unlock gracefully
            if cmd[:3] == ["git", "worktree", "unlock"]:
                return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
            return original_run(cmd, **kwargs)

        with patch("orchestrator.worktree.subprocess.run", side_effect=mock_run):
            manager.remove_worktree("submodule_chunk", remove_branch=False)

        # Worktree directory should be removed (via rmtree fallback)
        assert not worktree_path.exists()

        # git worktree prune should have been called (both intermediate and after rmtree)
        assert len(prune_calls) >= 2, f"Expected at least 2 prune calls, got {len(prune_calls)}"
