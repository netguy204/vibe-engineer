"""Tests for repo_cache module."""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations

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
    _repo_to_url,
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
        """Bare clones the repository on first access."""
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

        # Should have called git clone --bare
        assert any("clone" in cmd and "--bare" in cmd for cmd in clone_called)
        assert result == mock_cache_dir / "acme" / "chunks"

    def test_fetches_on_subsequent_access(self, mock_cache_dir, monkeypatch):
        """Fetches updates when repo is already cached."""
        # Pre-create the cache directory
        cache_path = mock_cache_dir / "acme" / "chunks"
        cache_path.mkdir(parents=True)

        fetch_called = []

        def mock_run(args, **kwargs):
            fetch_called.append(args)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        result = ensure_cached("acme/chunks")

        # Should have called git fetch
        assert any("fetch" in cmd for cmd in fetch_called)
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
            if "fetch" in args:
                raise subprocess.CalledProcessError(128, args, stderr="network error")
            mock = MagicMock()
            mock.returncode = 0
            return mock

        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(ValueError) as exc_info:
            ensure_cached("acme/chunks")

        assert "Failed to fetch" in str(exc_info.value)


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
