"""Tests for repo_cache module."""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/external_resolve - Repository caching for resolution

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from repo_cache import (
    get_cache_dir,
    repo_to_cache_path,
    ensure_cached,
    get_file_at_ref,
    resolve_ref,
    get_repo_path,
    list_directory_at_ref,
    _repo_to_url,
    _is_bare_repo,
)


class TestGetCacheDir:
    """Tests for get_cache_dir function."""

    def test_returns_correct_path(self, monkeypatch, tmp_path):
        """Returns ~/.ve/cache/repos/."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = get_cache_dir()
        assert result == tmp_path / ".ve" / "cache" / "repos"

    def test_creates_directory_if_missing(self, monkeypatch, tmp_path):
        """Creates the cache directory if it doesn't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        cache_dir = get_cache_dir()
        assert cache_dir.exists()
        assert cache_dir.is_dir()


class TestRepoToCachePath:
    """Tests for repo_to_cache_path function."""

    def test_converts_org_repo_to_path(self, monkeypatch, tmp_path):
        """Converts org/repo format to filesystem path."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = repo_to_cache_path("acme/chunks")
        assert result == tmp_path / ".ve" / "cache" / "repos" / "acme" / "chunks"

    def test_handles_nested_org(self, monkeypatch, tmp_path):
        """Handles org/repo format correctly."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = repo_to_cache_path("my-org/my-repo")
        assert result == tmp_path / ".ve" / "cache" / "repos" / "my-org" / "my-repo"


class TestRepoToUrl:
    """Tests for _repo_to_url helper function."""

    def test_converts_shorthand_to_github_url(self):
        """Converts org/repo to full GitHub URL."""
        result = _repo_to_url("acme/chunks")
        assert result == "https://github.com/acme/chunks.git"

    def test_preserves_full_https_url(self):
        """Preserves full HTTPS URLs."""
        url = "https://github.com/acme/chunks.git"
        assert _repo_to_url(url) == url

    def test_preserves_ssh_url(self):
        """Preserves SSH URLs."""
        url = "git@github.com:acme/chunks.git"
        assert _repo_to_url(url) == url


@pytest.fixture
def mock_cache_dir(monkeypatch, tmp_path):
    """Mock the cache directory to use tmp_path."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path / ".ve" / "cache" / "repos"


class TestEnsureCached:
    """Tests for ensure_cached function."""

    def test_clones_on_first_access(self, mock_cache_dir, monkeypatch):
        """Clones the repository with working tree on first access."""
        clone_called = []

        def mock_run(args, **kwargs):
            clone_called.append(args)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            # Create the directory to simulate successful clone
            if "clone" in args:
                cache_path = Path(args[-1])
                cache_path.mkdir(parents=True, exist_ok=True)
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = ensure_cached("acme/chunks")

        # Should have called git clone (without --bare, regular clone with working tree)
        assert any("clone" in cmd for cmd in clone_called)
        # Verify it's NOT a bare clone
        assert not any("clone" in cmd and "--bare" in cmd for cmd in clone_called)
        assert result == mock_cache_dir / "acme" / "chunks"

    def test_fetches_on_subsequent_access(self, mock_cache_dir, monkeypatch):
        """Fetches and resets when repo is already cached."""
        # Pre-create the cache directory
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        commands_called = []

        def mock_run(args, **kwargs):
            commands_called.append(args)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            # Return "false" for is-bare-repository check (regular repo)
            if "is-bare-repository" in args:
                mock.stdout = "false"
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = ensure_cached("acme/chunks")

        # Should have called git fetch and git reset
        assert any("fetch" in cmd for cmd in commands_called)
        assert any("reset" in cmd and "--hard" in cmd for cmd in commands_called)
        assert result == cache_path

    def test_error_on_inaccessible_repo(self, mock_cache_dir, monkeypatch):
        """Raises ValueError when clone fails."""

        def mock_run(args, **kwargs):
            if "clone" in args:
                raise subprocess.CalledProcessError(128, args, stderr="repository not found")
            mock = MagicMock()
            mock.returncode = 0
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            ensure_cached("nonexistent/repo")

        assert "Failed to clone" in str(exc_info.value)

    def test_error_on_fetch_failure(self, mock_cache_dir, monkeypatch):
        """Raises ValueError when fetch fails on existing cache."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            # Return "false" for is-bare-repository check (regular repo)
            if "is-bare-repository" in args:
                mock = MagicMock()
                mock.returncode = 0
                mock.stdout = "false"
                return mock
            if "fetch" in args:
                raise subprocess.CalledProcessError(128, args, stderr="network error")
            mock = MagicMock()
            mock.returncode = 0
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            ensure_cached("acme/chunks")

        # Updated error message
        assert "Failed to fetch/reset" in str(exc_info.value)


class TestGetFileAtRef:
    """Tests for get_file_at_ref function."""

    def test_returns_file_content(self, mock_cache_dir, monkeypatch):
        """Returns file content from git show."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        expected_content = "# Goal\n\nThis is the goal."

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            if "show" in args:
                mock.stdout = expected_content
            else:
                mock.stdout = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_file_at_ref("acme/chunks", "abc123", "docs/chunks/0001-feature/GOAL.md")

        assert result == expected_content

    def test_fetches_if_ref_missing(self, mock_cache_dir, monkeypatch):
        """Fetches and retries if ref is not found locally."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        call_count = {"show": 0, "fetch": 0}

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            if "show" in args:
                call_count["show"] += 1
                if call_count["show"] == 1:
                    # First call fails
                    raise subprocess.CalledProcessError(128, args, stderr="unknown revision")
                else:
                    # Second call succeeds
                    mock.stdout = "file content"
            elif "fetch" in args:
                call_count["fetch"] += 1

            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = get_file_at_ref("acme/chunks", "newref", "file.md")

        assert result == "file content"
        assert call_count["show"] == 2
        assert call_count["fetch"] >= 1

    def test_error_on_missing_file(self, mock_cache_dir, monkeypatch):
        """Raises ValueError when file doesn't exist."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            if "show" in args:
                raise subprocess.CalledProcessError(128, args, stderr="path 'nonexistent' does not exist")
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            get_file_at_ref("acme/chunks", "abc123", "nonexistent.md")

        assert "Cannot read" in str(exc_info.value)


class TestResolveRef:
    """Tests for resolve_ref function."""

    def test_returns_sha(self, mock_cache_dir, monkeypatch):
        """Returns full 40-character SHA."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        expected_sha = "a" * 40

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            if "rev-parse" in args:
                mock.stdout = expected_sha + "\n"
            else:
                mock.stdout = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = resolve_ref("acme/chunks", "main")

        assert result == expected_sha

    def test_fetches_if_ref_unknown(self, mock_cache_dir, monkeypatch):
        """Fetches and retries if ref is unknown locally."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        call_count = {"rev-parse": 0, "fetch": 0}
        expected_sha = "b" * 40

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            if "rev-parse" in args:
                call_count["rev-parse"] += 1
                if call_count["rev-parse"] == 1:
                    raise subprocess.CalledProcessError(128, args, stderr="unknown revision")
                else:
                    mock.stdout = expected_sha + "\n"
            elif "fetch" in args:
                call_count["fetch"] += 1

            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = resolve_ref("acme/chunks", "new-branch")

        assert result == expected_sha
        assert call_count["rev-parse"] == 2
        assert call_count["fetch"] >= 1

    def test_error_on_unresolvable_ref(self, mock_cache_dir, monkeypatch):
        """Raises ValueError when ref cannot be resolved."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            if "rev-parse" in args:
                raise subprocess.CalledProcessError(128, args, stderr="unknown revision")
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            resolve_ref("acme/chunks", "nonexistent-branch")

        assert "Cannot resolve ref" in str(exc_info.value)


class TestGetRepoPath:
    """Tests for get_repo_path function."""

    def test_returns_cache_path(self, mock_cache_dir):
        """Returns the expected cache path."""
        result = get_repo_path("acme/chunks")

        assert result == mock_cache_dir / "acme" / "chunks"

    def test_does_not_fetch(self, mock_cache_dir, monkeypatch):
        """Does not trigger fetch or clone operations."""
        commands_called = []

        def mock_run(args, **kwargs):
            commands_called.append(args)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        get_repo_path("acme/chunks")

        # Should not have called any git commands
        assert len(commands_called) == 0


class TestListDirectoryAtRef:
    """Tests for list_directory_at_ref function."""

    def test_lists_directory_contents(self, mock_cache_dir, monkeypatch):
        """Returns list of files in directory."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            # Return "false" for is-bare-repository check
            if "is-bare-repository" in args:
                mock.stdout = "false"
            elif "ls-tree" in args:
                # Simulate git ls-tree output
                mock.stdout = "docs/chunks/foo/GOAL.md\ndocs/chunks/foo/PLAN.md\n"
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = list_directory_at_ref("acme/chunks", "abc123", "docs/chunks/foo")

        assert "GOAL.md" in result
        assert "PLAN.md" in result

    def test_returns_empty_for_empty_directory(self, mock_cache_dir, monkeypatch):
        """Returns empty list for empty directory."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            # Return "false" for is-bare-repository check
            if "is-bare-repository" in args:
                mock.stdout = "false"
            elif "ls-tree" in args:
                mock.stdout = ""  # Empty directory
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = list_directory_at_ref("acme/chunks", "abc123", "docs/chunks/empty")

        assert result == []

    def test_error_on_nonexistent_directory(self, mock_cache_dir, monkeypatch):
        """Raises ValueError for nonexistent directory."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            # Return "false" for is-bare-repository check
            if "is-bare-repository" in args:
                mock.stdout = "false"
            elif "ls-tree" in args:
                raise subprocess.CalledProcessError(128, args, stderr="path not found")
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            list_directory_at_ref("acme/chunks", "abc123", "nonexistent/path")

        assert "Cannot list directory" in str(exc_info.value)


class TestIsBareRepo:
    """Tests for _is_bare_repo helper function."""

    def test_returns_true_for_bare_repo(self, tmp_path, monkeypatch):
        """Returns True when git rev-parse --is-bare-repository returns true."""
        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = "true\n"
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _is_bare_repo(tmp_path)

        assert result is True

    def test_returns_false_for_regular_repo(self, tmp_path, monkeypatch):
        """Returns False when git rev-parse --is-bare-repository returns false."""
        def mock_run(args, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = "false\n"
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _is_bare_repo(tmp_path)

        assert result is False

    def test_returns_false_on_error(self, tmp_path, monkeypatch):
        """Returns False when git command fails."""
        def mock_run(args, **kwargs):
            raise subprocess.CalledProcessError(128, args)

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = _is_bare_repo(tmp_path)

        assert result is False


class TestEnsureCachedBareCloneMigration:
    """Tests for bare clone migration in ensure_cached."""

    def test_migrates_bare_clone_to_regular(self, mock_cache_dir, monkeypatch):
        """Detects and migrates bare clone to regular clone."""
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        commands_called = []
        is_bare_call_count = [0]  # Use list for mutable closure

        def mock_run(args, **kwargs):
            commands_called.append(list(args))  # Store as list for easy inspection
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""

            # First is-bare-repository call returns True (bare clone detected)
            if "--is-bare-repository" in args:
                is_bare_call_count[0] += 1
                mock.stdout = "true" if is_bare_call_count[0] == 1 else "false"
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock shutil.rmtree to just remove the directory
        import shutil
        original_rmtree = shutil.rmtree
        rmtree_called = []

        def mock_rmtree(path, *args, **kwargs):
            rmtree_called.append(path)
            # Actually remove the directory
            original_rmtree(path, *args, **kwargs)

        monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

        ensure_cached("acme/chunks")

        # Should have detected bare clone (args is a list, so check if string is in args)
        assert any("--is-bare-repository" in cmd for cmd in commands_called)
        # Should have removed the bare clone
        assert len(rmtree_called) == 1
        # Should have cloned (without --bare)
        assert any("clone" in cmd and "--bare" not in cmd for cmd in commands_called)
