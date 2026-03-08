# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/merge_strategy_simplify - Branch-aware merge strategy tests
"""Tests for orchestrator merge module with branch-aware merge strategy.

These tests verify:
- Native git merge is used when on target branch with clean tree
- Plumbing approach is used when on different branch or dirty tree
- Merge conflicts are properly detected and aborted
"""

import subprocess

import pytest

from orchestrator.merge import (
    WorktreeError,
    has_clean_working_tree,
    is_on_branch,
    merge_without_checkout,
)


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


class TestHelperFunctions:
    """Tests for helper functions is_on_branch and has_clean_working_tree."""

    def test_is_on_branch_returns_true_when_on_branch(self, git_repo):
        """is_on_branch returns True when HEAD is on the specified branch."""
        # We're on main by default
        assert is_on_branch("main", git_repo) is True
        # And not on a non-existent branch
        assert is_on_branch("feature", git_repo) is False

    def test_is_on_branch_after_checkout(self, git_repo):
        """is_on_branch returns correct value after branch checkout."""
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert is_on_branch("feature", git_repo) is True
        assert is_on_branch("main", git_repo) is False

    def test_has_clean_working_tree_when_clean(self, git_repo):
        """has_clean_working_tree returns True with no uncommitted changes."""
        assert has_clean_working_tree(git_repo) is True

    def test_has_clean_working_tree_with_unstaged_changes(self, git_repo):
        """has_clean_working_tree returns False with unstaged modifications."""
        (git_repo / "README.md").write_text("# Modified\n")
        assert has_clean_working_tree(git_repo) is False

    def test_has_clean_working_tree_with_staged_changes(self, git_repo):
        """has_clean_working_tree returns False with staged changes."""
        (git_repo / "README.md").write_text("# Staged\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert has_clean_working_tree(git_repo) is False

    def test_has_clean_working_tree_ignores_untracked_files(self, git_repo):
        """has_clean_working_tree ignores untracked files."""
        (git_repo / "untracked.txt").write_text("untracked\n")
        assert has_clean_working_tree(git_repo) is True


class TestMergeOnTargetBranchCleanTree:
    """Tests for merge behavior when on target branch with clean working tree.

    When the user is on the target branch with a clean tree, merge_without_checkout
    should use native git merge, which atomically updates index, working tree, and ref.
    """

    def test_merge_on_target_branch_clean_tree_updates_working_tree(self, git_repo):
        """Given user on target branch with clean tree, working tree is updated after merge."""
        # Create a source branch with new content
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("new content\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main (target branch)
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Verify new_file.txt doesn't exist yet
        assert not (git_repo / "new_file.txt").exists()

        # Merge source into main while on main with clean tree
        merge_without_checkout("source", "main", git_repo)

        # Verify new_file.txt now exists in working tree (atomic update)
        assert (git_repo / "new_file.txt").exists()
        assert (git_repo / "new_file.txt").read_text() == "new content\n"

        # Verify git status is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", "git status should be clean after merge"

    def test_merge_on_target_branch_real_merge_creates_merge_commit(self, git_repo):
        """Given diverged branches on target branch, merge creates a merge commit."""
        # Create diverged branches
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "source_file.txt").write_text("source\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "main_file.txt").write_text("main\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add main file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Merge
        merge_without_checkout("source", "main", git_repo)

        # Both files should exist
        assert (git_repo / "source_file.txt").exists()
        assert (git_repo / "main_file.txt").exists()

        # Should have a merge commit (two parents)
        result = subprocess.run(
            ["git", "log", "--oneline", "-1", "--format=%P"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        parents = result.stdout.strip().split()
        assert len(parents) == 2, "Merge commit should have two parents"


class TestMergeOnTargetBranchConflict:
    """Tests for merge conflict handling when on target branch."""

    def test_merge_conflict_aborts_and_raises(self, git_repo):
        """Given conflicting changes, merge is aborted and WorktreeError raised."""
        # Create conflicting branches
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "README.md").write_text("# Source version\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Change README on source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "README.md").write_text("# Main version\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Change README on main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Attempt merge - should raise WorktreeError
        with pytest.raises(WorktreeError) as exc_info:
            merge_without_checkout("source", "main", git_repo)

        assert "Merge conflict" in str(exc_info.value)

        # Working tree should be clean (merge was aborted)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", "Working tree should be clean after abort"


class TestMergeOnDifferentBranch:
    """Tests for merge behavior when on a different branch than target.

    When not on the target branch, merge_without_checkout uses plumbing
    commands to update only the ref, without touching working tree.
    """

    def test_merge_on_different_branch_updates_ref_only(self, git_repo):
        """Given user on different branch, target ref is updated but working tree unchanged."""
        # Create a source branch with new content
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "source_file.txt").write_text("source content\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        source_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Create a different branch to be on during merge
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "other"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "other_file.txt").write_text("other content\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add other file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Verify we're on 'other', not 'main'
        assert is_on_branch("other", git_repo)

        # Verify source_file.txt doesn't exist in our working tree
        assert not (git_repo / "source_file.txt").exists()
        assert (git_repo / "other_file.txt").exists()

        # Merge source into main while we're on 'other'
        merge_without_checkout("source", "main", git_repo)

        # Working tree should be unchanged - we're still on 'other'
        assert not (git_repo / "source_file.txt").exists()
        assert (git_repo / "other_file.txt").exists()

        # But main should now point to source's commit (fast-forward)
        main_sha = subprocess.run(
            ["git", "rev-parse", "main"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert main_sha == source_sha, "main should be fast-forwarded to source"


class TestMergeOnTargetBranchDirtyTree:
    """Tests for merge behavior when on target branch with dirty working tree.

    When on target branch but with uncommitted changes, merge_without_checkout
    uses the plumbing approach to avoid destroying user's changes.
    """

    def test_merge_with_dirty_tree_preserves_uncommitted_changes(self, git_repo):
        """Given uncommitted changes on target branch, changes are preserved after merge."""
        # Create a source branch with new content
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "source_file.txt").write_text("source content\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main and make uncommitted changes
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "README.md").write_text("# Modified but not committed\n")

        # Verify we have uncommitted changes
        assert not has_clean_working_tree(git_repo)

        # Merge source into main
        merge_without_checkout("source", "main", git_repo)

        # Uncommitted changes should be preserved
        assert (git_repo / "README.md").read_text() == "# Modified but not committed\n"

        # The ref should be updated (fast-forward)
        # Note: the working tree won't have source_file.txt until user reconciles
        result = subprocess.run(
            ["git", "rev-parse", "main"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        main_sha = result.stdout.strip()
        result = subprocess.run(
            ["git", "rev-parse", "source"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        source_sha = result.stdout.strip()
        assert main_sha == source_sha, "main ref should be updated"


class TestMergeAlreadyMerged:
    """Tests for already-merged case."""

    def test_merge_already_merged_is_noop(self, git_repo):
        """Given source already merged into target, no changes are made."""
        # Create source branch
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "source_file.txt").write_text("source\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        source_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Go to main and merge source
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "source", "--no-edit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        main_sha_before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Now call merge_without_checkout again - should be a no-op
        merge_without_checkout("source", "main", git_repo)

        main_sha_after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        assert main_sha_before == main_sha_after, "No changes should be made when already merged"


class TestMergeFastForward:
    """Tests for fast-forward merge scenarios."""

    def test_fast_forward_on_target_branch_updates_working_tree(self, git_repo):
        """Given fast-forward possible on target branch, working tree is updated."""
        # Create source branch ahead of main
        subprocess.run(
            ["git", "checkout", "-b", "source"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "source_file.txt").write_text("source\n")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add source file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # source_file.txt shouldn't exist yet
        assert not (git_repo / "source_file.txt").exists()

        # Merge (fast-forward) - should use native merge since on target with clean tree
        merge_without_checkout("source", "main", git_repo)

        # source_file.txt should now exist (working tree updated)
        assert (git_repo / "source_file.txt").exists()
        assert (git_repo / "source_file.txt").read_text() == "source\n"
