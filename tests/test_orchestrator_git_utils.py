# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_empty_repo_handling - Empty repo detection
"""Tests for orchestrator git_utils module."""

import subprocess

import pytest

from orchestrator.git_utils import GitError, get_current_branch, repo_has_commits


@pytest.fixture
def git_repo(tmp_path):
    """Create a bare git init repo (no commits)."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


@pytest.fixture
def git_repo_with_commit(git_repo):
    """Create a git repo with one commit."""
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
            "HOME": str(git_repo),
            "PATH": subprocess.check_output(
                ["bash", "-c", "echo $PATH"], text=True
            ).strip(),
        },
    )
    return git_repo


class TestRepoHasCommits:
    """Tests for repo_has_commits()."""

    def test_returns_true_after_initial_commit(self, git_repo_with_commit):
        """Returns True for a repo with at least one commit."""
        assert repo_has_commits(git_repo_with_commit) is True

    def test_returns_false_for_empty_repo(self, git_repo):
        """Returns False for a freshly initialized repo with no commits."""
        assert repo_has_commits(git_repo) is False


class TestGetCurrentBranchEmptyRepo:
    """Tests for get_current_branch() in empty repo scenarios."""

    def test_raises_git_error_with_clear_message_for_empty_repo(self, git_repo):
        """Raises GitError with a helpful message when repo has no commits."""
        with pytest.raises(GitError, match="no commits"):
            get_current_branch(git_repo)

    def test_error_suggests_initial_commit(self, git_repo):
        """Error message suggests making an initial commit."""
        with pytest.raises(GitError, match="Make an initial commit first"):
            get_current_branch(git_repo)
