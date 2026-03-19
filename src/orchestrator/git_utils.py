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


# Chunk: docs/chunks/orch_empty_repo_handling - Empty repo detection
def repo_has_commits(repo_dir: Path) -> bool:
    """Check whether a git repository has any commits.

    Args:
        repo_dir: The repository directory

    Returns:
        True if the repo has at least one commit, False otherwise
    """
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


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
        if "unknown revision" in result.stderr or "bad default revision" in result.stderr:
            raise GitError(
                "Cannot determine current branch: repository has no commits. "
                "Make an initial commit first."
            )
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
