"""Repository cache for efficient single-repo mode operations.

This module provides a local cache of external repositories at ~/.ve/cache/repos/.
The cache enables reading files and resolving refs without network round-trips
after the initial clone.

# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/external_resolve - Repository cache infrastructure
# Chunk: docs/chunks/external_resolve_enhance - Regular clones with working tree access
"""

import subprocess
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def _run_git(
    *args: str, cwd: Path | None = None, error_msg: str
) -> subprocess.CompletedProcess[str]:
    """Run a git command with standard arguments and error handling.

    Wraps subprocess.run with check=True, capture_output=True, text=True.
    Catches CalledProcessError and re-raises as ValueError with the provided
    error message and stderr content.

    Args:
        *args: Git command arguments (e.g., "fetch", "--all", "--quiet")
        cwd: Working directory for the git command (optional, e.g., for clone)
        error_msg: Base error message to use if the command fails

    Returns:
        CompletedProcess result on success

    Raises:
        ValueError: If the git command fails, with error_msg and stderr details
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"{error_msg}: {e.stderr.strip() if e.stderr else 'unknown error'}"
        ) from e


def _with_fetch_retry(fn: Callable[[], T], cache_path: Path) -> T:
    """Execute a function with retry-after-fetch on ValueError.

    If fn() raises ValueError, attempts to fetch from remote and retries.
    This encapsulates the common pattern of trying an operation, fetching
    if it fails (e.g., unknown ref), then retrying.

    Args:
        fn: Callable that may raise ValueError (typically a git operation)
        cache_path: Path to the cached repository for fetching

    Returns:
        The result of fn() (either on first success or after retry)

    Raises:
        ValueError: If fn() fails both before and after fetch
    """
    try:
        return fn()
    except ValueError:
        # Ref might be unknown, try fetching first.
        # Note: This intentionally uses raw subprocess.run instead of _run_git
        # because fetch failures are silently swallowed (the ref might already
        # be local, or the retry might succeed for other reasons).
        try:
            subprocess.run(
                ["git", "fetch", "--all", "--quiet"],
                cwd=cache_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            # Fetch failed, but retry the original operation anyway
            pass
        # Retry after fetch (let any exception propagate)
        return fn()


def get_cache_dir() -> Path:
    """Return ~/.ve/cache/repos/, creating if needed."""
    cache_dir = Path.home() / ".ve" / "cache" / "repos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def repo_to_cache_path(repo: str) -> Path:
    """Convert org/repo to cache path (~/.ve/cache/repos/org/repo).

    Args:
        repo: Repository identifier in org/repo format

    Returns:
        Path to the cached repository directory
    """
    cache_dir = get_cache_dir()
    return cache_dir / repo


def _repo_to_url(repo: str) -> str:
    """Convert org/repo format to full GitHub URL.

    Args:
        repo: Repository identifier (org/repo or full URL)

    Returns:
        Full git-compatible URL
    """
    if repo.startswith(("https://", "http://", "git@", "ssh://")):
        return repo
    return f"https://github.com/{repo}.git"


def _is_bare_repo(path: Path) -> bool:
    """Check if a git repository is a bare clone (no working tree).

    Note: This function intentionally does not use _run_git because its
    error-handling semantics differ. Instead of raising ValueError on failure,
    it returns False (treating failures as "not a bare repo").

    Args:
        path: Path to the git repository

    Returns:
        True if the repository is bare, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-bare-repository"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().lower() == "true"
    except subprocess.CalledProcessError:
        return False


def _remove_directory(path: Path) -> None:
    """Remove a directory and all its contents.

    Args:
        path: Path to the directory to remove
    """
    import shutil

    shutil.rmtree(path)


def ensure_cached(repo: str) -> Path:
    """Clone repo if not cached, fetch and reset if cached. Return path to cached repo.

    Uses regular clones (with working tree) to provide filesystem access to content.
    On each call, fetches from remote and resets to origin/HEAD to ensure the cache
    always reflects the latest remote state.

    Handles migration from legacy bare clones by detecting and replacing them.

    Args:
        repo: Repository identifier in org/repo format

    Returns:
        Path to the cached repository with working tree

    Raises:
        ValueError: If the repository cannot be cloned or fetched
    """
    cache_path = repo_to_cache_path(repo)
    url = _repo_to_url(repo)

    if cache_path.exists():
        # Check if this is a legacy bare clone that needs migration
        if _is_bare_repo(cache_path):
            # Delete the bare clone and re-clone as regular repo
            _remove_directory(cache_path)
        else:
            # Regular repo: fetch and reset to latest
            _run_git(
                "fetch", "--all", "--quiet",
                cwd=cache_path,
                error_msg=f"Failed to fetch/reset '{repo}'",
            )
            _run_git(
                "reset", "--hard", "origin/HEAD",
                cwd=cache_path,
                error_msg=f"Failed to fetch/reset '{repo}'",
            )
            return cache_path

    # Clone as regular repo (not --bare)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _run_git(
        "clone", "--quiet", url, str(cache_path),
        error_msg=f"Failed to clone '{repo}'",
    )

    return cache_path


def get_repo_path(repo: str) -> Path:
    """Return filesystem path to cached repo working tree.

    Does NOT fetch/reset - call ensure_cached() first if you need latest.

    Args:
        repo: Repository identifier in org/repo format

    Returns:
        Path to the cached repository directory
    """
    return repo_to_cache_path(repo)


def get_file_at_ref(repo: str, ref: str, file_path: str) -> str:
    """Get file content at a specific ref using git show.

    If the ref is not found locally, fetches first then retries.

    Args:
        repo: Repository identifier in org/repo format
        ref: Git ref (SHA, branch, tag)
        file_path: Path to the file within the repository

    Returns:
        The file content as a string

    Raises:
        ValueError: If the file cannot be read (missing file, bad ref, etc.)
    """
    cache_path = ensure_cached(repo)

    def try_read() -> str:
        result = _run_git(
            "show", f"{ref}:{file_path}",
            cwd=cache_path,
            error_msg=f"Cannot read '{file_path}' at ref '{ref}' in '{repo}'",
        )
        return result.stdout

    return _with_fetch_retry(try_read, cache_path)


def resolve_ref(repo: str, ref: str) -> str:
    """Resolve a ref to SHA. Fetches if ref not found locally.

    Args:
        repo: Repository identifier in org/repo format
        ref: Git ref to resolve (branch, tag, SHA, HEAD)

    Returns:
        The full 40-character SHA

    Raises:
        ValueError: If the ref cannot be resolved
    """
    cache_path = ensure_cached(repo)

    def try_resolve() -> str:
        result = _run_git(
            "rev-parse", ref,
            cwd=cache_path,
            error_msg=f"Cannot resolve ref '{ref}' in '{repo}'",
        )
        sha = result.stdout.strip()
        if len(sha) != 40:
            raise ValueError(f"Unexpected SHA format: {sha}")
        return sha

    return _with_fetch_retry(try_resolve, cache_path)


def list_directory_at_ref(repo: str, ref: str, dir_path: str) -> list[str]:
    """List files in a directory at a specific ref using git ls-tree.

    Args:
        repo: Repository identifier in org/repo format
        ref: Git ref (SHA, branch, tag)
        dir_path: Path to the directory within the repository

    Returns:
        List of filenames in the directory (not full paths)

    Raises:
        ValueError: If the directory cannot be listed
    """
    cache_path = ensure_cached(repo)

    # Normalize dir_path to not have trailing slash for ls-tree
    dir_path = dir_path.rstrip("/")

    def try_list() -> list[str]:
        result = _run_git(
            "ls-tree", "--name-only", ref, f"{dir_path}/",
            cwd=cache_path,
            error_msg=f"Cannot list directory '{dir_path}' at ref '{ref}' in '{repo}'",
        )
        # ls-tree returns full paths like "docs/chunks/foo/GOAL.md"
        # We want just the filename part
        files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                # Extract just the filename from the full path
                filename = line.split("/")[-1]
                files.append(filename)
        return files

    return _with_fetch_retry(try_list, cache_path)
