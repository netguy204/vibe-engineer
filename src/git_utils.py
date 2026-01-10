"""Git utility functions for working with local repositories and worktrees.

These utilities operate entirely on local worktrees within a task directory,
avoiding network operations. They form the foundation for the `ve sync` command.
"""
# Chunk: docs/chunks/0008-ve_sync_foundation - Git utility functions

import subprocess
from pathlib import Path


# Chunk: docs/chunks/0008-ve_sync_foundation - Get HEAD SHA
def get_current_sha(repo_path: Path) -> str:
    """Get the current HEAD SHA of a local git repository.

    Args:
        repo_path: Path to the git repository (or worktree)

    Returns:
        The full 40-character SHA of HEAD

    Raises:
        ValueError: If the path does not exist or is not a git repository
    """
    if not repo_path.exists():
        raise ValueError(f"Path does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise ValueError(f"Path is not a directory: {repo_path}")

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Not a git repository: {repo_path}") from e


# Chunk: docs/chunks/0008-ve_sync_foundation - Resolve git ref to SHA
def resolve_ref(repo_path: Path, ref: str) -> str:
    """Resolve a git ref (branch, tag, or symbolic ref) to its SHA.

    Args:
        repo_path: Path to the git repository (or worktree)
        ref: The ref to resolve (e.g., "main", "v1.0.0", "HEAD", "HEAD~1")

    Returns:
        The full 40-character SHA that the ref points to

    Raises:
        ValueError: If the path is not a git repository or the ref doesn't exist
    """
    if not repo_path.exists():
        raise ValueError(f"Path does not exist: {repo_path}")

    if not repo_path.is_dir():
        raise ValueError(f"Path is not a directory: {repo_path}")

    try:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Check if it's a git repo issue or a ref issue
        stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
        if "not a git repository" in stderr.lower():
            raise ValueError(f"Not a git repository: {repo_path}") from e
        raise ValueError(f"Cannot resolve ref '{ref}' in {repo_path}") from e


# Chunk: docs/chunks/0034-ve_sync_command - Resolve remote ref to SHA
def resolve_remote_ref(repo_url: str, ref: str = "HEAD") -> str:
    """Resolve a git ref from a remote repository using git ls-remote.

    Args:
        repo_url: The remote repository URL. Can be:
            - Full URL (https://github.com/org/repo.git)
            - GitHub shorthand (org/repo)
        ref: The ref to resolve (default: "HEAD" for default branch)

    Returns:
        The full 40-character SHA

    Raises:
        ValueError: If the remote is not accessible or ref doesn't exist
    """
    # Expand GitHub shorthand to full URL
    if "/" in repo_url and not repo_url.startswith(("https://", "http://", "git@", "ssh://")):
        repo_url = f"https://github.com/{repo_url}.git"

    try:
        result = subprocess.run(
            ["git", "ls-remote", repo_url, ref],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Remote not accessible: {repo_url}") from e

    # Parse output: "<sha>\t<ref>"
    output = result.stdout.strip()
    if not output:
        raise ValueError(f"Could not resolve ref '{ref}' from {repo_url}")

    # Take the first line (in case of multiple matches like HEAD)
    first_line = output.split("\n")[0]
    sha = first_line.split("\t")[0]

    if len(sha) != 40:
        raise ValueError(f"Unexpected SHA format from remote: {sha}")

    return sha


# Chunk: docs/chunks/0008-ve_sync_foundation - Check if directory is git repo
def is_git_repository(path: Path) -> bool:
    """Check if path is a git repository (or worktree).

    Args:
        path: Path to check

    Returns:
        True if path is a git repository, False otherwise
    """
    if not path.exists():
        return False

    if not path.is_dir():
        return False

    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
