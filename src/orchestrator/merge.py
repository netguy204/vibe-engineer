# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_merge_safety - Checkout-free merge strategies (original implementation)
# Chunk: docs/chunks/worktree_merge_extract - Extracted merge logic from worktree.py
# Chunk: docs/chunks/merge_strategy_simplify - Simplified to branch-aware merge strategy
"""Merge strategies for orchestrator worktrees.

This module provides merge strategies for merging completed chunk branches
back to their base branches. The primary function, merge_without_checkout,
uses a branch-aware strategy:

1. If user is on target branch with clean working tree: use native git merge
   (atomic update of index, working tree, and ref)
2. Otherwise: use git plumbing commands to update the ref only, without
   touching the user's working tree

Merge strategies:
- merge_without_checkout: Primary entry point with branch-aware strategy
- merge_native: Uses native git merge (for on-branch, clean-tree case)
- merge_via_index: Fallback plumbing strategy for older Git
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class WorktreeError(Exception):
    """Exception raised for worktree and merge-related errors."""

    pass


# Chunk: docs/chunks/merge_strategy_simplify - Helper to detect current branch
def is_on_branch(branch: str, repo_dir: Path) -> bool:
    """Check if the current HEAD is on the given branch.

    Args:
        branch: Branch name to check
        repo_dir: Repository directory

    Returns:
        True if the current HEAD is on the given branch
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return result.stdout.strip() == branch


# Chunk: docs/chunks/merge_strategy_simplify - Helper to detect clean working tree
def has_clean_working_tree(repo_dir: Path) -> bool:
    """Check if the working tree is clean (no staged or unstaged changes to tracked files).

    Untracked files are ignored.

    Args:
        repo_dir: Repository directory

    Returns:
        True if working tree is clean
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    # Filter out untracked files (lines starting with "??")
    changes = [
        line for line in result.stdout.strip().split("\n")
        if line and not line.startswith("??")
    ]
    return len(changes) == 0


# Chunk: docs/chunks/orch_merge_rebase_retry - Helper to detect merge conflict errors
def is_merge_conflict_error(error: "WorktreeError | str") -> bool:
    """Check if an error indicates a merge conflict vs other errors.

    Used by the scheduler to distinguish merge conflicts (which can be
    retried via REBASE) from other finalization errors (which should
    escalate to NEEDS_ATTENTION).

    Args:
        error: A WorktreeError exception or error message string

    Returns:
        True if the error indicates a merge conflict
    """
    error_str = str(error) if isinstance(error, WorktreeError) else error
    return "Merge conflict" in error_str or "CONFLICT" in error_str


# Chunk: docs/chunks/merge_strategy_simplify - Native git merge for clean on-branch merges
def merge_native(source_branch: str, target_branch: str, repo_dir: Path) -> None:
    """Perform a merge using native git merge command.

    This function assumes the caller has verified we're on the target branch
    with a clean working tree. It uses `git merge` which handles index,
    working tree, and ref updates atomically.

    Args:
        source_branch: Branch to merge from (e.g., orch/chunk_name)
        target_branch: Branch to merge into (e.g., main) - must be current branch
        repo_dir: Repository directory

    Raises:
        WorktreeError: If merge fails (e.g., conflicts). On conflict, the merge
                      is aborted before raising.
    """
    result = subprocess.run(
        ["git", "merge", "--no-edit", source_branch],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Check if it's a conflict
        if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
            # Abort the merge to leave working tree clean
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=repo_dir,
                capture_output=True,
            )
            raise WorktreeError(
                f"Merge conflict between {source_branch} and {target_branch}"
            )
        raise WorktreeError(
            f"Failed to merge {source_branch} into {target_branch}: {result.stderr}"
        )


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
# Chunk: docs/chunks/worktree_merge_extract - Extracted from WorktreeManager._merge_without_checkout
# Chunk: docs/chunks/merge_strategy_simplify - Branch-aware merge strategy
def merge_without_checkout(
    source_branch: str, target_branch: str, repo_dir: Path
) -> None:
    """Perform a merge, using native git merge when possible.

    This function uses a branch-aware strategy:
    1. If user is on target branch with clean tree: use native git merge
    2. Otherwise: use plumbing commands (update-ref) without touching working tree

    Strategy:
    1. Check if source is an ancestor of target (already merged) - no-op
    2. If on target branch with clean working tree: use git merge (atomic)
    3. Otherwise, use plumbing commands to update the ref without checkout

    Args:
        source_branch: Branch to merge from (e.g., orch/chunk_name)
        target_branch: Branch to merge into (e.g., main)
        repo_dir: Repository directory

    Raises:
        WorktreeError: If merge fails (e.g., conflicts)
    """
    # Get commit SHAs for both branches
    result = subprocess.run(
        ["git", "rev-parse", source_branch],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(f"Branch {source_branch} not found")
    source_sha = result.stdout.strip()

    result = subprocess.run(
        ["git", "rev-parse", target_branch],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(f"Branch {target_branch} not found")
    target_sha = result.stdout.strip()

    # Check if source is already an ancestor of target (already merged)
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_sha, target_sha],
        cwd=repo_dir,
        capture_output=True,
    )
    if result.returncode == 0:
        # Already merged, nothing to do
        return

    # Branch-aware strategy: if on target branch with clean tree, use native merge
    # This handles both fast-forward and real merges atomically
    if is_on_branch(target_branch, repo_dir) and has_clean_working_tree(repo_dir):
        merge_native(source_branch, target_branch, repo_dir)
        return

    # Not on target branch (or dirty tree): use plumbing approach
    # No working tree update needed - user will see changes when they checkout target branch

    # Check if target is an ancestor of source (fast-forward possible)
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", target_sha, source_sha],
        cwd=repo_dir,
        capture_output=True,
    )
    if result.returncode == 0:
        # Fast-forward: update the target branch ref to source
        result = subprocess.run(
            ["git", "update-ref", f"refs/heads/{target_branch}", source_sha],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to fast-forward {target_branch} to {source_branch}: {result.stderr}"
            )
        return

    # Need a real merge - use git merge-tree (Git 2.38+) for clean merge detection
    # First get the merge base
    result = subprocess.run(
        ["git", "merge-base", source_sha, target_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(f"Failed to find merge base: {result.stderr}")

    # Try git merge-tree --write-tree (Git 2.38+)
    result = subprocess.run(
        ["git", "merge-tree", "--write-tree", target_sha, source_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        # Merge conflict or git merge-tree not available
        # Check if it's a conflict (indicated by CONFLICT in output)
        if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
            raise WorktreeError(
                f"Merge conflict between {source_branch} and {target_branch}"
            )
        # Might be older Git without merge-tree --write-tree
        # Fall back to index-based merge
        merge_via_index(
            source_branch, source_sha, target_branch, target_sha, repo_dir
        )
        return

    # Parse the tree SHA from merge-tree output
    lines = result.stdout.strip().split("\n")
    tree_sha = lines[0]  # First line is the tree SHA

    # Create the merge commit
    commit_msg = f"Merge branch '{source_branch}' into {target_branch}"
    result = subprocess.run(
        [
            "git",
            "commit-tree",
            tree_sha,
            "-p",
            target_sha,
            "-p",
            source_sha,
            "-m",
            commit_msg,
        ],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(f"Failed to create merge commit: {result.stderr}")
    merge_commit = result.stdout.strip()

    # Update the target branch ref
    result = subprocess.run(
        ["git", "update-ref", f"refs/heads/{target_branch}", merge_commit],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(
            f"Failed to update {target_branch} ref: {result.stderr}"
        )


# Chunk: docs/chunks/orch_merge_safety - Fallback merge for older Git
# Chunk: docs/chunks/worktree_merge_extract - Extracted from WorktreeManager._merge_via_index
def merge_via_index(
    source_branch: str,
    source_sha: str,
    target_branch: str,
    target_sha: str,
    repo_dir: Path,
) -> None:
    """Perform merge using git index operations (fallback for older Git).

    Uses a temporary index file to perform the merge without affecting
    the working directory.

    Args:
        source_branch: Branch name being merged
        source_sha: Source commit SHA
        target_branch: Target branch name
        target_sha: Target commit SHA
        repo_dir: Repository directory

    Raises:
        WorktreeError: If merge fails
    """
    # Get merge base
    result = subprocess.run(
        ["git", "merge-base", source_sha, target_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise WorktreeError(f"Failed to find merge base: {result.stderr}")
    merge_base = result.stdout.strip()

    # Create a temporary index file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".idx") as tmp:
        tmp_index = tmp.name

    try:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = tmp_index

        # Read the base tree into the temp index
        result = subprocess.run(
            ["git", "read-tree", merge_base],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to read base tree: {result.stderr}")

        # Perform a three-way merge into the temp index
        result = subprocess.run(
            ["git", "read-tree", "-m", merge_base, target_sha, source_sha],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"Merge conflict between {source_branch} and {target_branch}"
            )

        # Write the tree from the index
        result = subprocess.run(
            ["git", "write-tree"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to write tree: {result.stderr}")
        tree_sha = result.stdout.strip()

        # Create the merge commit
        commit_msg = f"Merge branch '{source_branch}' into {target_branch}"
        result = subprocess.run(
            [
                "git",
                "commit-tree",
                tree_sha,
                "-p",
                target_sha,
                "-p",
                source_sha,
                "-m",
                commit_msg,
            ],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to create merge commit: {result.stderr}")
        merge_commit = result.stdout.strip()

        # Update the target branch ref
        result = subprocess.run(
            ["git", "update-ref", f"refs/heads/{target_branch}", merge_commit],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to update {target_branch} ref: {result.stderr}"
            )
        # No working tree update needed - merge_without_checkout routes through
        # merge_native when on target branch with clean tree

    finally:
        # Clean up temp index
        if Path(tmp_index).exists():
            Path(tmp_index).unlink()


