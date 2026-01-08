"""Git utility functions for working with local repositories and worktrees.

These utilities operate entirely on local worktrees within a task directory,
avoiding network operations. They form the foundation for the `ve sync` command.
"""

import subprocess
from pathlib import Path


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
