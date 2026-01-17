# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Git worktree manager for isolated chunk execution.

Provides worktree lifecycle management for parallel agent execution.
Each work unit gets its own worktree for isolation.
"""

import subprocess
from pathlib import Path
from typing import Optional


class WorktreeError(Exception):
    """Exception raised for worktree-related errors."""

    pass


class WorktreeManager:
    """Manages git worktrees for isolated chunk execution.

    Creates and removes worktrees at .ve/chunks/<chunk>/worktree/
    on branches named orch/<chunk>. Branches are created from the
    base branch (the branch active when the manager was initialized),
    and completed work is merged back to that base branch.
    """

    def __init__(self, project_dir: Path, base_branch: Optional[str] = None):
        """Initialize the worktree manager.

        Args:
            project_dir: The root project directory (where .git lives)
            base_branch: Branch to use as base for worktree branches.
                         If None, uses the current branch.
        """
        self.project_dir = project_dir.resolve()
        self._base_branch = base_branch or self._get_current_branch()

    def _get_current_branch(self) -> str:
        """Get the current git branch name.

        Returns:
            Current branch name

        Raises:
            WorktreeError: If not on a branch or git command fails
        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to get current branch: {result.stderr}")

        branch = result.stdout.strip()
        if branch == "HEAD":
            # Detached HEAD state - get the commit instead
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise WorktreeError("Failed to get current commit in detached HEAD state")
            return result.stdout.strip()

        return branch

    @property
    def base_branch(self) -> str:
        """The base branch that worktree branches are created from."""
        return self._base_branch

    def _get_worktree_base_path(self, chunk: str) -> Path:
        """Get the base path for a chunk's worktree.

        Args:
            chunk: Chunk name

        Returns:
            Path to .ve/chunks/<chunk>/
        """
        return self.project_dir / ".ve" / "chunks" / chunk

    def get_worktree_path(self, chunk: str) -> Path:
        """Get the worktree path for a chunk.

        Args:
            chunk: Chunk name

        Returns:
            Path to the worktree directory
        """
        return self._get_worktree_base_path(chunk) / "worktree"

    def get_log_path(self, chunk: str) -> Path:
        """Get the log directory path for a chunk.

        Args:
            chunk: Chunk name

        Returns:
            Path to the log directory
        """
        return self._get_worktree_base_path(chunk) / "log"

    def get_branch_name(self, chunk: str) -> str:
        """Get the branch name for a chunk.

        Args:
            chunk: Chunk name

        Returns:
            Branch name (orch/<chunk>)
        """
        return f"orch/{chunk}"

    def worktree_exists(self, chunk: str) -> bool:
        """Check if a worktree exists for a chunk.

        Args:
            chunk: Chunk name

        Returns:
            True if worktree exists
        """
        worktree_path = self.get_worktree_path(chunk)
        return worktree_path.exists() and (worktree_path / ".git").exists()

    def _branch_exists(self, branch: str) -> bool:
        """Check if a branch exists.

        Args:
            branch: Branch name

        Returns:
            True if branch exists
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=self.project_dir,
            capture_output=True,
        )
        return result.returncode == 0

    def _create_branch(self, branch: str) -> None:
        """Create a branch from the base branch.

        Args:
            branch: Branch name to create
        """
        if not self._branch_exists(branch):
            result = subprocess.run(
                ["git", "branch", branch, self._base_branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise WorktreeError(f"Failed to create branch {branch}: {result.stderr}")

    def create_worktree(self, chunk: str) -> Path:
        """Create a git worktree for a chunk.

        Creates a branch orch/<chunk> from the base branch if it doesn't exist,
        then creates a worktree at .ve/chunks/<chunk>/worktree/.

        Args:
            chunk: Chunk name

        Returns:
            Path to the created worktree

        Raises:
            WorktreeError: If worktree creation fails
        """
        worktree_path = self.get_worktree_path(chunk)
        branch = self.get_branch_name(chunk)

        # Create parent directories
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Create log directory
        log_path = self.get_log_path(chunk)
        log_path.mkdir(parents=True, exist_ok=True)

        # Check if worktree already exists
        if self.worktree_exists(chunk):
            return worktree_path

        # Create branch if needed
        self._create_branch(branch)

        # Create worktree
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Check if it's because the branch is already checked out
            if "is already checked out" in result.stderr:
                # Try with --force
                result = subprocess.run(
                    ["git", "worktree", "add", "--force", str(worktree_path), branch],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                )

            if result.returncode != 0:
                raise WorktreeError(f"Failed to create worktree: {result.stderr}")

        return worktree_path

    def remove_worktree(self, chunk: str, remove_branch: bool = False) -> None:
        """Remove a git worktree for a chunk.

        Args:
            chunk: Chunk name
            remove_branch: If True, also delete the branch

        Raises:
            WorktreeError: If worktree removal fails
        """
        worktree_path = self.get_worktree_path(chunk)
        branch = self.get_branch_name(chunk)

        if worktree_path.exists():
            # Remove the worktree
            result = subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Try prune first
                subprocess.run(
                    ["git", "worktree", "prune"],
                    cwd=self.project_dir,
                    capture_output=True,
                )

                # Try removal again
                result = subprocess.run(
                    ["git", "worktree", "remove", str(worktree_path), "--force"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                )

                # If still failing, just remove the directory
                if result.returncode != 0 and worktree_path.exists():
                    import shutil

                    shutil.rmtree(worktree_path, ignore_errors=True)

        # Prune worktrees to clean up any stale entries
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.project_dir,
            capture_output=True,
        )

        # Optionally remove the branch
        if remove_branch and self._branch_exists(branch):
            result = subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            # Don't raise on branch deletion failure - it's not critical

    def has_uncommitted_changes(self, chunk: str) -> bool:
        """Check if a worktree has uncommitted changes.

        Args:
            chunk: Chunk name

        Returns:
            True if there are staged or unstaged changes
        """
        worktree_path = self.get_worktree_path(chunk)
        if not worktree_path.exists():
            return False

        # Check for uncommitted changes (staged or unstaged)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        return bool(result.stdout.strip())

    def list_worktrees(self) -> list[str]:
        """List all orchestrator-managed worktrees.

        Returns:
            List of chunk names that have worktrees
        """
        chunks_dir = self.project_dir / ".ve" / "chunks"
        if not chunks_dir.exists():
            return []

        worktrees = []
        for chunk_dir in chunks_dir.iterdir():
            if chunk_dir.is_dir():
                worktree_path = chunk_dir / "worktree"
                if worktree_path.exists() and (worktree_path / ".git").exists():
                    worktrees.append(chunk_dir.name)

        return worktrees

    def cleanup_orphaned_worktrees(self) -> list[str]:
        """Clean up any orphaned worktrees (worktrees without active work units).

        This should be called at daemon startup to recover from crashes.

        Returns:
            List of chunk names that were cleaned up
        """
        # Get list of all worktrees
        worktrees = self.list_worktrees()

        # Prune any stale worktree entries
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.project_dir,
            capture_output=True,
        )

        return worktrees

    def merge_to_base(self, chunk: str, delete_branch: bool = True) -> None:
        """Merge a chunk's branch back to the base branch.

        This should be called when a work unit completes successfully.
        The merge is performed in the main project directory (not the worktree).

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge

        Raises:
            WorktreeError: If merge fails (e.g., conflicts)
        """
        branch = self.get_branch_name(chunk)

        if not self._branch_exists(branch):
            raise WorktreeError(f"Branch {branch} does not exist")

        # First, ensure we're on the base branch in the main repo
        result = subprocess.run(
            ["git", "checkout", self._base_branch],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to checkout base branch {self._base_branch}: {result.stderr}"
            )

        # Merge the chunk branch
        result = subprocess.run(
            ["git", "merge", branch, "--no-edit"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Abort the merge if it failed
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=self.project_dir,
                capture_output=True,
            )
            raise WorktreeError(
                f"Failed to merge {branch} into {self._base_branch}: {result.stderr}"
            )

        # Delete the branch if requested
        if delete_branch:
            result = subprocess.run(
                ["git", "branch", "-d", branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            # Don't raise on branch deletion failure - merge succeeded

    def has_changes(self, chunk: str) -> bool:
        """Check if a chunk's branch has changes relative to base.

        Args:
            chunk: Chunk name

        Returns:
            True if the chunk branch has commits not in base
        """
        branch = self.get_branch_name(chunk)

        if not self._branch_exists(branch):
            return False

        # Check if there are any commits in branch that aren't in base
        result = subprocess.run(
            ["git", "rev-list", f"{self._base_branch}..{branch}", "--count"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return False

        count = int(result.stdout.strip())
        return count > 0

    def commit_changes(self, chunk: str) -> bool:
        """Commit all changes in a worktree with a standard message.

        This is a mechanical commit that stages all changes and commits them
        with a standard message format. Used by the orchestrator to commit
        changes after the COMPLETE phase without involving an agent.

        Args:
            chunk: Chunk name

        Returns:
            True if commit succeeded, False if nothing to commit

        Raises:
            WorktreeError: If git command fails for reasons other than
                           "nothing to commit"
        """
        worktree_path = self.get_worktree_path(chunk)

        if not worktree_path.exists():
            raise WorktreeError(f"Worktree for {chunk} does not exist")

        # Stage all changes
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise WorktreeError(f"git add failed: {result.stderr}")

        # Commit with standard message
        result = subprocess.run(
            ["git", "commit", "-m", f"feat: chunk {chunk}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        # Return False if nothing to commit (exit code 1 with "nothing to commit")
        if result.returncode != 0:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                return False
            raise WorktreeError(f"git commit failed: {result.stderr}")

        return True
