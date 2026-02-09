# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_merge_safety - Checkout-free merge strategies (original implementation)
# Chunk: docs/chunks/worktree_merge_extract - Extracted merge logic from worktree.py
"""Checkout-free merge strategies for orchestrator worktrees.

This module provides merge strategies that don't require checking out
the target branch, preserving the user's working directory state.
The merge operations are used by WorktreeManager to merge completed
chunk branches back to their base branches without disrupting the
user's checkout or uncommitted changes.

Merge strategies:
- merge_without_checkout: Primary strategy using git merge-tree --write-tree (Git 2.38+)
- merge_via_index: Fallback strategy using a temporary index file for older Git
- update_working_tree_if_on_branch: Syncs working tree after ref update
"""

import os
import subprocess
import tempfile
from pathlib import Path


class WorktreeError(Exception):
    """Exception raised for worktree and merge-related errors."""

    pass


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
# Chunk: docs/chunks/worktree_merge_extract - Extracted from WorktreeManager._merge_without_checkout
def merge_without_checkout(
    source_branch: str, target_branch: str, repo_dir: Path
) -> None:
    """Perform a merge without checking out the target branch.

    This preserves the user's current checkout and any uncommitted changes.

    Strategy:
    1. Check if source is an ancestor of target (already merged) - no-op
    2. Check if target is an ancestor of source (fast-forward possible)
       - Use git update-ref to fast-forward
    3. Otherwise, create a merge commit using git plumbing commands:
       - Use git merge-tree to compute the merge
       - If clean, create merge commit with git commit-tree
       - Update ref with git update-ref

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

    # Check if target is an ancestor of source (fast-forward possible)
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", target_sha, source_sha],
        cwd=repo_dir,
        capture_output=True,
    )
    if result.returncode == 0:
        # Fast-forward: update the target branch ref to source
        # Use update-ref instead of branch -f to handle checked-out branches
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
        # If the working tree is on the target branch, update it
        update_working_tree_if_on_branch(target_branch, repo_dir)
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
    merge_base = result.stdout.strip()

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
    # If the working tree is on the target branch, update it
    update_working_tree_if_on_branch(target_branch, repo_dir)


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
        # If the working tree is on the target branch, update it
        update_working_tree_if_on_branch(target_branch, repo_dir)

    finally:
        # Clean up temp index
        if Path(tmp_index).exists():
            Path(tmp_index).unlink()


# Chunk: docs/chunks/orch_merge_safety - Update working tree after ref update
# Chunk: docs/chunks/worktree_merge_extract - Extracted from WorktreeManager._update_working_tree_if_on_branch
def update_working_tree_if_on_branch(
    target_branch: str, repo_dir: Path
) -> None:
    """Update the working tree if it's currently on the target branch.

    After updating a branch ref with update-ref, the working tree is out
    of sync if the user is on that branch. This method checks if the user
    is on the target branch and updates their working tree to match.

    Args:
        target_branch: Branch that was just updated
        repo_dir: Repository directory
    """
    # Check if working tree is on the target branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return  # Can't determine current branch, skip update

    current_branch = result.stdout.strip()
    if current_branch != target_branch:
        return  # Not on target branch, no update needed

    # Reset the working tree to match the new HEAD
    # Use --mixed to update index but not touch uncommitted changes
    subprocess.run(
        ["git", "reset", "--mixed", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
    )
    # Checkout to update the working tree files
    subprocess.run(
        ["git", "checkout", "--", "."],
        cwd=repo_dir,
        capture_output=True,
    )
