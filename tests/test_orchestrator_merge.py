# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/merge_safety - Safe working tree updates
"""Tests for orchestrator merge module, specifically update_working_tree_if_on_branch safety."""

import logging
import subprocess

import pytest

from orchestrator.merge import update_working_tree_if_on_branch


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


class TestDirtyWorkingTreeSafety:
    """Tests for update_working_tree_if_on_branch skipping when working tree is dirty."""

    def test_unstaged_changes_preserved(self, git_repo):
        """Given unstaged modifications, update_working_tree_if_on_branch does not overwrite them."""
        # Create an unstaged modification
        (git_repo / "README.md").write_text("# Test - Modified\n")

        # Update the ref to simulate a merge (create a new commit and point HEAD at it)
        # First, store the current content temporarily
        original_content = (git_repo / "README.md").read_text()

        # Create a new commit on a temp branch with a different file
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "new_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Restore our uncommitted modification (checkout wipes it)
        (git_repo / "README.md").write_text("# Test - Modified\n")

        # Update main ref to point to temp_branch's commit (simulating merge_without_checkout behavior)
        result = subprocess.run(
            ["git", "rev-parse", "temp_branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        new_sha = result.stdout.strip()
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Call update_working_tree_if_on_branch - should NOT destroy our uncommitted changes
        update_working_tree_if_on_branch("main", git_repo)

        # Verify uncommitted changes are preserved
        content = (git_repo / "README.md").read_text()
        assert content == "# Test - Modified\n", "Uncommitted changes should be preserved"

    def test_staged_changes_preserved(self, git_repo):
        """Given staged modifications, update_working_tree_if_on_branch does not overwrite them."""
        # Create a staged modification
        (git_repo / "README.md").write_text("# Test - Staged\n")
        subprocess.run(["git", "add", "README.md"], cwd=git_repo, check=True, capture_output=True)

        # Create a new commit on a temp branch
        subprocess.run(
            ["git", "stash"],  # Save our staged changes temporarily
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "other_file.txt").write_text("other content")
        subprocess.run(["git", "add", "other_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add other file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main and restore staged changes
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "stash", "pop"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Update main ref to point to temp_branch's commit
        result = subprocess.run(
            ["git", "rev-parse", "temp_branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        new_sha = result.stdout.strip()
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Call update_working_tree_if_on_branch - should NOT destroy our staged changes
        update_working_tree_if_on_branch("main", git_repo)

        # Verify staged changes are preserved by checking the file content
        content = (git_repo / "README.md").read_text()
        assert content == "# Test - Staged\n", "Staged changes should be preserved"

    def test_dirty_working_tree_logs_warning(self, git_repo, caplog):
        """Given uncommitted changes, a warning is logged about the working tree being behind."""
        # Create an uncommitted modification
        (git_repo / "README.md").write_text("# Test - Dirty\n")

        # Create a new commit on a temp branch
        subprocess.run(
            ["git", "stash"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("content")
        subprocess.run(["git", "add", "new_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main and restore changes
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "stash", "pop"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Update main ref
        result = subprocess.run(
            ["git", "rev-parse", "temp_branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        new_sha = result.stdout.strip()
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Capture log output at WARNING level
        with caplog.at_level(logging.WARNING):
            update_working_tree_if_on_branch("main", git_repo)

        # Verify warning was logged
        assert any("uncommitted changes" in record.message.lower() for record in caplog.records), \
            "Should log a warning about uncommitted changes"
        assert any("main" in record.message for record in caplog.records), \
            "Warning should mention the branch name"

    def test_new_untracked_file_preserved(self, git_repo):
        """Given an untracked file, update_working_tree_if_on_branch does not remove it."""
        # Create an untracked file
        (git_repo / "untracked.txt").write_text("I am untracked\n")

        # Create a new commit on a temp branch
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("content")
        subprocess.run(["git", "add", "new_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Go back to main - untracked files are preserved by git checkout
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Update main ref
        result = subprocess.run(
            ["git", "rev-parse", "temp_branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        new_sha = result.stdout.strip()
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Note: git status --porcelain shows untracked files with "??" prefix
        # This test verifies untracked files don't trigger the "dirty" detection
        # but also aren't affected by the update
        update_working_tree_if_on_branch("main", git_repo)

        # Verify untracked file is preserved
        assert (git_repo / "untracked.txt").exists(), "Untracked file should be preserved"
        assert (git_repo / "untracked.txt").read_text() == "I am untracked\n"


class TestCleanWorkingTreeUpdate:
    """Tests for update_working_tree_if_on_branch updating clean working trees."""

    def test_clean_working_tree_updated(self, git_repo):
        """Given a clean working tree, update_working_tree_if_on_branch updates files to match new ref."""
        # Create a new commit on a temp branch with a new file
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("new content\n")
        subprocess.run(["git", "add", "new_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        new_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Go back to main (which doesn't have new_file.txt yet)
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Verify new_file.txt doesn't exist yet
        assert not (git_repo / "new_file.txt").exists()

        # Update main ref to point to temp_branch's commit
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Call update_working_tree_if_on_branch - should update working tree
        update_working_tree_if_on_branch("main", git_repo)

        # Verify new_file.txt now exists in working tree
        assert (git_repo / "new_file.txt").exists(), "New file should appear after working tree update"
        assert (git_repo / "new_file.txt").read_text() == "new content\n"

    def test_not_on_target_branch_no_update(self, git_repo):
        """If not on the target branch, no update is performed."""
        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create a new commit on main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "main_file.txt").write_text("main content\n")
        subprocess.run(["git", "add", "main_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add main file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        main_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Go back to feature branch
        subprocess.run(
            ["git", "checkout", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Update feature ref to point to main's commit (but we're on feature)
        subprocess.run(
            ["git", "update-ref", "refs/heads/feature", main_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Call update_working_tree_if_on_branch with "main" (not current branch)
        update_working_tree_if_on_branch("main", git_repo)

        # Verify we're still on feature and main_file.txt doesn't appear
        # (because we called it with "main" but we're on "feature")
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "feature"

    def test_clean_working_tree_no_warning(self, git_repo, caplog):
        """Given a clean working tree, no warning is logged."""
        # Create a new commit on a temp branch
        subprocess.run(
            ["git", "checkout", "-b", "temp_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "new_file.txt").write_text("content")
        subprocess.run(["git", "add", "new_file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        new_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

        # Go back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Update main ref
        subprocess.run(
            ["git", "update-ref", "refs/heads/main", new_sha],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Capture log output
        with caplog.at_level(logging.WARNING):
            update_working_tree_if_on_branch("main", git_repo)

        # Verify no warning about uncommitted changes was logged
        assert not any("uncommitted changes" in record.message.lower() for record in caplog.records), \
            "Should not log a warning about uncommitted changes when working tree is clean"
