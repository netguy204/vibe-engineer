# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/low_priority_cleanup - Consolidated git utilities
"""Git utilities for the orchestrator.

Provides common git operations used across orchestrator modules.
"""

import subprocess
from pathlib import Path


class GitError(Exception):
    """Exception raised for git-related errors."""

    pass


def get_current_branch(repo_dir: Path) -> str:
    """Get the current git branch name.

    In detached HEAD state, returns the commit SHA instead of a branch name.

    Args:
        repo_dir: The repository directory

    Returns:
        Current branch name, or commit SHA if in detached HEAD state

    Raises:
        GitError: If not in a git repo or git command fails
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"Failed to get current branch: {result.stderr}")

    branch = result.stdout.strip()
    if branch == "HEAD":
        # Detached HEAD state - get the commit instead
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitError("Failed to get current commit in detached HEAD state")
        return result.stdout.strip()

    return branch
