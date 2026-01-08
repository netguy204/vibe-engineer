"""Tests for git utility functions."""

import re
import subprocess

import pytest

from git_utils import get_current_sha, is_git_repository, resolve_ref


# Regex to match a valid 40-character hex SHA
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class TestIsGitRepository:
    """Tests for is_git_repository function."""

    def test_returns_true_for_git_repo(self, tmp_path):
        """Returns True for a valid git repository."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        assert is_git_repository(tmp_path) is True

    def test_returns_false_for_non_git_directory(self, tmp_path):
        """Returns False for a directory that is not a git repository."""
        assert is_git_repository(tmp_path) is False

    def test_returns_true_for_empty_git_repo(self, tmp_path):
        """Returns True for git repo without any commits."""
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        # No commit made - still a valid git repo
        assert is_git_repository(tmp_path) is True

    def test_returns_false_for_nonexistent_path(self, tmp_path):
        """Returns False for a path that does not exist."""
        nonexistent = tmp_path / "does_not_exist"
        assert is_git_repository(nonexistent) is False


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
    # Create a file and commit it
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


class TestGetCurrentSha:
    """Tests for get_current_sha function."""

    def test_returns_sha_from_git_repo(self, git_repo):
        """Returns the current HEAD SHA from a valid git repository."""
        sha = get_current_sha(git_repo)
        assert SHA_PATTERN.match(sha), f"SHA '{sha}' is not a valid 40-char hex string"

    def test_sha_matches_git_rev_parse(self, git_repo):
        """Returned SHA matches git rev-parse HEAD output."""
        sha = get_current_sha(git_repo)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        expected = result.stdout.strip()
        assert sha == expected

    def test_raises_for_non_git_directory(self, tmp_path):
        """Raises ValueError when path is not a git repository."""
        with pytest.raises(ValueError) as exc_info:
            get_current_sha(tmp_path)
        assert str(tmp_path) in str(exc_info.value)

    def test_raises_for_nonexistent_path(self, tmp_path):
        """Raises ValueError when path does not exist."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(ValueError) as exc_info:
            get_current_sha(nonexistent)
        assert "does_not_exist" in str(exc_info.value)

    def test_sha_is_exactly_40_characters(self, git_repo):
        """Returned SHA is exactly 40 hex characters (no truncation)."""
        sha = get_current_sha(git_repo)
        assert len(sha) == 40


@pytest.fixture
def git_repo_with_refs(git_repo):
    """Extend git_repo with branches and tags."""
    # Create a branch
    subprocess.run(
        ["git", "branch", "feature/test-branch"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    # Create a tag
    subprocess.run(
        ["git", "tag", "v1.0.0"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    # Add another commit to main so HEAD differs from the tag
    (git_repo / "file2.txt").write_text("content\n")
    subprocess.run(
        ["git", "add", "file2.txt"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Second commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return git_repo


class TestResolveRef:
    """Tests for resolve_ref function."""

    def test_resolves_branch_name(self, git_repo_with_refs):
        """Resolves a branch name to its SHA."""
        sha = resolve_ref(git_repo_with_refs, "feature/test-branch")
        assert SHA_PATTERN.match(sha)

    def test_resolves_tag_name(self, git_repo_with_refs):
        """Resolves a tag name to its SHA."""
        sha = resolve_ref(git_repo_with_refs, "v1.0.0")
        assert SHA_PATTERN.match(sha)

    def test_resolves_head(self, git_repo_with_refs):
        """Resolves HEAD symbolic ref."""
        sha = resolve_ref(git_repo_with_refs, "HEAD")
        expected = get_current_sha(git_repo_with_refs)
        assert sha == expected

    def test_resolves_head_tilde(self, git_repo_with_refs):
        """Resolves HEAD~1 to parent commit."""
        sha = resolve_ref(git_repo_with_refs, "HEAD~1")
        assert SHA_PATTERN.match(sha)
        # HEAD~1 should differ from HEAD
        head_sha = get_current_sha(git_repo_with_refs)
        assert sha != head_sha

    def test_tag_and_branch_resolve_to_same_sha(self, git_repo_with_refs):
        """Tag and branch both point to the same initial commit."""
        branch_sha = resolve_ref(git_repo_with_refs, "feature/test-branch")
        tag_sha = resolve_ref(git_repo_with_refs, "v1.0.0")
        assert branch_sha == tag_sha

    def test_raises_for_non_git_directory(self, tmp_path):
        """Raises ValueError when path is not a git repository."""
        with pytest.raises(ValueError) as exc_info:
            resolve_ref(tmp_path, "HEAD")
        assert str(tmp_path) in str(exc_info.value)

    def test_raises_for_nonexistent_ref(self, git_repo):
        """Raises ValueError when ref does not exist."""
        with pytest.raises(ValueError) as exc_info:
            resolve_ref(git_repo, "nonexistent-branch")
        assert "nonexistent-branch" in str(exc_info.value)

    def test_sha_is_exactly_40_characters(self, git_repo_with_refs):
        """Returned SHA is exactly 40 hex characters."""
        sha = resolve_ref(git_repo_with_refs, "v1.0.0")
        assert len(sha) == 40


@pytest.fixture
def git_repo_with_worktree(git_repo, tmp_path_factory):
    """Create a git repo with a worktree that has a different HEAD."""
    # Create a branch for the worktree
    subprocess.run(
        ["git", "branch", "worktree-branch"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Create a worktree in a separate directory
    worktree_dir = tmp_path_factory.mktemp("worktree")
    subprocess.run(
        ["git", "worktree", "add", str(worktree_dir), "worktree-branch"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Add a commit to the worktree so its HEAD differs from main repo
    (worktree_dir / "worktree-file.txt").write_text("worktree content\n")
    subprocess.run(
        ["git", "add", "worktree-file.txt"],
        cwd=worktree_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Worktree commit"],
        cwd=worktree_dir,
        check=True,
        capture_output=True,
    )

    return {"main_repo": git_repo, "worktree": worktree_dir}


class TestWorktreeSupport:
    """Tests for worktree support in git utilities."""

    def test_get_current_sha_from_worktree(self, git_repo_with_worktree):
        """get_current_sha works from a worktree."""
        worktree = git_repo_with_worktree["worktree"]
        sha = get_current_sha(worktree)
        assert SHA_PATTERN.match(sha)

    def test_resolve_ref_from_worktree(self, git_repo_with_worktree):
        """resolve_ref works from a worktree."""
        worktree = git_repo_with_worktree["worktree"]
        sha = resolve_ref(worktree, "HEAD")
        assert SHA_PATTERN.match(sha)

    def test_worktree_head_differs_from_main_repo(self, git_repo_with_worktree):
        """Worktree HEAD differs from main repo HEAD."""
        main_repo = git_repo_with_worktree["main_repo"]
        worktree = git_repo_with_worktree["worktree"]

        main_sha = get_current_sha(main_repo)
        worktree_sha = get_current_sha(worktree)

        # They should be different since we made a commit in the worktree
        assert main_sha != worktree_sha

    def test_resolve_ref_from_worktree_matches_worktree_head(self, git_repo_with_worktree):
        """resolve_ref HEAD from worktree matches worktree's current SHA."""
        worktree = git_repo_with_worktree["worktree"]

        sha_from_get = get_current_sha(worktree)
        sha_from_resolve = resolve_ref(worktree, "HEAD")

        assert sha_from_get == sha_from_resolve

    def test_can_resolve_main_repo_refs_from_worktree(self, git_repo_with_worktree):
        """Can resolve refs from main repo when in worktree."""
        worktree = git_repo_with_worktree["worktree"]

        # Should be able to resolve the main branch from the worktree
        # Git 2.28+ uses 'main' as default, older uses 'master'
        # Try both to be compatible
        try:
            sha = resolve_ref(worktree, "main")
        except ValueError:
            sha = resolve_ref(worktree, "master")

        assert SHA_PATTERN.match(sha)
