# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Git worktree manager for isolated chunk execution.

Provides worktree lifecycle management for parallel agent execution.
Each work unit gets its own worktree for isolation.

Supports two modes:
1. Single-repo mode: Creates worktree at .ve/chunks/<chunk>/worktree/
2. Task context mode: Creates worktrees for multiple repos under .ve/chunks/<chunk>/work/<repo-name>/
"""

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from orchestrator.models import TaskContextInfo


class WorktreeError(Exception):
    """Exception raised for worktree-related errors."""

    pass


class WorktreeManager:
    """Manages git worktrees for isolated chunk execution.

    Creates and removes worktrees at .ve/chunks/<chunk>/worktree/
    on branches named orch/<chunk>. Branches are created from the
    base branch (the branch active when the manager was initialized),
    and completed work is merged back to that base branch.

    In task context mode (when task_info is provided):
    - Uses resolve_affected_repos() to determine which project repos
      to create worktrees for based on the chunk's dependents field
    - Creates worktrees under .ve/chunks/<chunk>/work/<repo-name>/
    """

    def __init__(
        self,
        project_dir: Path,
        base_branch: Optional[str] = None,
        task_info: Optional["TaskContextInfo"] = None,
    ):
        """Initialize the worktree manager.

        Args:
            project_dir: The root project directory (where .git lives),
                         or task directory in task context mode
            base_branch: Branch to use as base for worktree branches.
                         If None, uses the current branch (single-repo mode only).
            task_info: Task context information (None for single-repo mode)
        """
        self.project_dir = project_dir.resolve()
        self.task_info = task_info

        # In task context mode, base_branch may be None (determined per-repo)
        if task_info and task_info.is_task_context:
            self._base_branch = base_branch  # Can be None in task context
        else:
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
        """Get the worktree path for a chunk (single-repo mode).

        Args:
            chunk: Chunk name

        Returns:
            Path to the worktree directory
        """
        return self._get_worktree_base_path(chunk) / "worktree"

    def get_work_directory(self, chunk: str) -> Path:
        """Get the work directory for a chunk in task context mode.

        Args:
            chunk: Chunk name

        Returns:
            Path to the work/ directory containing repo worktrees
        """
        return self._get_worktree_base_path(chunk) / "work"

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

    def is_task_context(self, chunk: str) -> bool:
        """Check if a chunk uses task context (multi-repo) structure.

        Args:
            chunk: Chunk name

        Returns:
            True if chunk has work/ directory with at least one repo
        """
        work_dir = self.get_work_directory(chunk)
        if not work_dir.exists():
            return False
        # Check for at least one repo subdirectory with .git
        for subdir in work_dir.iterdir():
            if subdir.is_dir() and (subdir / ".git").exists():
                return True
        return False

    def worktree_exists(self, chunk: str) -> bool:
        """Check if a worktree exists for a chunk.

        Handles both single-repo mode (worktree/) and task context mode (work/<repo>/).

        Args:
            chunk: Chunk name

        Returns:
            True if worktree exists
        """
        # Check single-repo mode
        worktree_path = self.get_worktree_path(chunk)
        if worktree_path.exists() and (worktree_path / ".git").exists():
            return True

        # Check task context mode
        return self.is_task_context(chunk)

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

    def _create_branch(self, branch: str, repo_dir: Optional[Path] = None) -> None:
        """Create a branch from the base branch.

        Args:
            branch: Branch name to create
            repo_dir: Repository directory (defaults to project_dir)
        """
        cwd = repo_dir or self.project_dir
        if not self._branch_exists_in_repo(branch, cwd):
            # Get the current branch as base for this repo
            base = self._get_repo_current_branch(cwd)
            result = subprocess.run(
                ["git", "branch", branch, base],
                cwd=cwd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise WorktreeError(f"Failed to create branch {branch}: {result.stderr}")

    def _branch_exists_in_repo(self, branch: str, repo_dir: Path) -> bool:
        """Check if a branch exists in a specific repository.

        Args:
            branch: Branch name
            repo_dir: Repository directory

        Returns:
            True if branch exists
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            cwd=repo_dir,
            capture_output=True,
        )
        return result.returncode == 0

    def _get_repo_current_branch(self, repo_dir: Path) -> str:
        """Get the current branch of a repository.

        Args:
            repo_dir: Repository directory

        Returns:
            Current branch name

        Raises:
            WorktreeError: If not on a branch or git command fails
        """
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir,
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
                cwd=repo_dir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise WorktreeError("Failed to get current commit in detached HEAD state")
            return result.stdout.strip()

        return branch

    def create_worktree(
        self, chunk: str, repo_paths: Optional[list[Path]] = None
    ) -> Path:
        """Create a git worktree for a chunk.

        In single-repo mode (repo_paths=None and no task_info):
            Creates a branch orch/<chunk> from the base branch if it doesn't exist,
            then creates a worktree at .ve/chunks/<chunk>/worktree/.

        In task context mode (repo_paths provided or task_info.is_task_context):
            Creates worktrees for each repo under .ve/chunks/<chunk>/work/<repo-name>/.
            Each repo gets its own orch/<chunk> branch.
            If repo_paths not provided, uses resolve_affected_repos() to determine them.

        Args:
            chunk: Chunk name
            repo_paths: Optional list of repository paths for task context mode

        Returns:
            Path to the created worktree (single-repo) or work directory (task context)

        Raises:
            WorktreeError: If worktree creation fails
        """
        # Create log directory (used by both modes)
        log_path = self.get_log_path(chunk)
        log_path.mkdir(parents=True, exist_ok=True)

        # Determine if we should use task context mode
        if repo_paths is not None:
            # Explicit repo_paths provided
            return self._create_task_context_worktrees(chunk, repo_paths)
        elif self.task_info and self.task_info.is_task_context:
            # Task context mode - resolve affected repos from chunk dependents
            from orchestrator.models import resolve_affected_repos
            affected_repos = resolve_affected_repos(self.task_info, chunk)
            if affected_repos:
                return self._create_task_context_worktrees(chunk, affected_repos)
            else:
                raise WorktreeError(
                    f"No accessible repositories found for chunk {chunk} in task context"
                )
        else:
            return self._create_single_repo_worktree(chunk)

    def _create_single_repo_worktree(self, chunk: str) -> Path:
        """Create a single-repo worktree.

        Args:
            chunk: Chunk name

        Returns:
            Path to the created worktree
        """
        worktree_path = self.get_worktree_path(chunk)
        branch = self.get_branch_name(chunk)

        # Create parent directories
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if worktree already exists
        if worktree_path.exists() and (worktree_path / ".git").exists():
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

    def _create_task_context_worktrees(self, chunk: str, repo_paths: list[Path]) -> Path:
        """Create worktrees for multiple repos in task context mode.

        Args:
            chunk: Chunk name
            repo_paths: List of repository paths

        Returns:
            Path to the work directory containing all repo worktrees
        """
        work_dir = self.get_work_directory(chunk)
        work_dir.mkdir(parents=True, exist_ok=True)
        branch = self.get_branch_name(chunk)

        for repo_path in repo_paths:
            repo_name = repo_path.name
            repo_worktree_path = work_dir / repo_name

            # Skip if already exists
            if repo_worktree_path.exists() and (repo_worktree_path / ".git").exists():
                continue

            # Create branch in this repo
            self._create_branch(branch, repo_path)

            # Create worktree for this repo
            result = subprocess.run(
                ["git", "worktree", "add", str(repo_worktree_path), branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Check if it's because the branch is already checked out
                if "is already checked out" in result.stderr:
                    # Try with --force
                    result = subprocess.run(
                        ["git", "worktree", "add", "--force", str(repo_worktree_path), branch],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )

                if result.returncode != 0:
                    raise WorktreeError(
                        f"Failed to create worktree for {repo_name}: {result.stderr}"
                    )

        return work_dir

    def remove_worktree(
        self,
        chunk: str,
        remove_branch: bool = False,
        repo_paths: Optional[list[Path]] = None,
    ) -> None:
        """Remove a git worktree for a chunk.

        In single-repo mode (repo_paths=None):
            Removes worktree at .ve/chunks/<chunk>/worktree/.

        In task context mode (repo_paths provided):
            Removes worktrees for each repo under .ve/chunks/<chunk>/work/<repo-name>/.

        Args:
            chunk: Chunk name
            remove_branch: If True, also delete the branch
            repo_paths: Optional list of repository paths for task context mode

        Raises:
            WorktreeError: If worktree removal fails
        """
        if repo_paths is not None:
            self._remove_task_context_worktrees(chunk, remove_branch, repo_paths)
        else:
            self._remove_single_repo_worktree(chunk, remove_branch)

    def _remove_single_repo_worktree(self, chunk: str, remove_branch: bool) -> None:
        """Remove a single-repo worktree.

        Args:
            chunk: Chunk name
            remove_branch: If True, also delete the branch
        """
        worktree_path = self.get_worktree_path(chunk)
        branch = self.get_branch_name(chunk)

        if worktree_path.exists():
            self._remove_worktree_from_repo(worktree_path, self.project_dir)

        # Prune worktrees to clean up any stale entries
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.project_dir,
            capture_output=True,
        )

        # Optionally remove the branch
        if remove_branch and self._branch_exists(branch):
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            # Don't raise on branch deletion failure - it's not critical

    def _remove_task_context_worktrees(
        self, chunk: str, remove_branch: bool, repo_paths: list[Path]
    ) -> None:
        """Remove worktrees for multiple repos in task context mode.

        Args:
            chunk: Chunk name
            remove_branch: If True, also delete the branches
            repo_paths: List of repository paths
        """
        work_dir = self.get_work_directory(chunk)
        branch = self.get_branch_name(chunk)

        for repo_path in repo_paths:
            repo_name = repo_path.name
            repo_worktree_path = work_dir / repo_name

            if repo_worktree_path.exists():
                self._remove_worktree_from_repo(repo_worktree_path, repo_path)

            # Prune worktrees in this repo
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=repo_path,
                capture_output=True,
            )

            # Optionally remove the branch in this repo
            if remove_branch and self._branch_exists_in_repo(branch, repo_path):
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )

        # Remove the work directory if it exists
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

    def _remove_worktree_from_repo(self, worktree_path: Path, repo_path: Path) -> None:
        """Remove a worktree from a repository.

        Args:
            worktree_path: Path to the worktree to remove
            repo_path: Path to the repository that owns the worktree
        """
        result = subprocess.run(
            ["git", "worktree", "remove", str(worktree_path), "--force"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Try prune first
            subprocess.run(
                ["git", "worktree", "prune"],
                cwd=repo_path,
                capture_output=True,
            )

            # Try removal again
            result = subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            # If still failing, just remove the directory
            if result.returncode != 0 and worktree_path.exists():
                shutil.rmtree(worktree_path, ignore_errors=True)

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

        Includes both single-repo worktrees (worktree/) and task context
        worktrees (work/<repo>/).

        Returns:
            List of chunk names that have worktrees
        """
        chunks_dir = self.project_dir / ".ve" / "chunks"
        if not chunks_dir.exists():
            return []

        worktrees = []
        for chunk_dir in chunks_dir.iterdir():
            if chunk_dir.is_dir():
                # Check single-repo mode
                worktree_path = chunk_dir / "worktree"
                if worktree_path.exists() and (worktree_path / ".git").exists():
                    worktrees.append(chunk_dir.name)
                    continue

                # Check task context mode
                work_dir = chunk_dir / "work"
                if work_dir.exists():
                    for subdir in work_dir.iterdir():
                        if subdir.is_dir() and (subdir / ".git").exists():
                            worktrees.append(chunk_dir.name)
                            break  # Found at least one, that's enough

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

    def merge_to_base(
        self,
        chunk: str,
        delete_branch: bool = True,
        repo_paths: Optional[list[Path]] = None,
    ) -> None:
        """Merge a chunk's branch back to the base branch.

        This should be called when a work unit completes successfully.
        The merge is performed in the main project directory (not the worktree).

        In task context mode (repo_paths provided):
            Merges the chunk branch in each repository independently.

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge
            repo_paths: Optional list of repository paths for task context mode

        Raises:
            WorktreeError: If merge fails (e.g., conflicts)
        """
        if repo_paths is not None:
            self._merge_to_base_multi_repo(chunk, delete_branch, repo_paths)
        else:
            self._merge_to_base_single_repo(chunk, delete_branch)

    def _merge_to_base_single_repo(self, chunk: str, delete_branch: bool) -> None:
        """Merge a chunk's branch to base in single-repo mode.

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge
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
            subprocess.run(
                ["git", "branch", "-d", branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            # Don't raise on branch deletion failure - merge succeeded

    def _merge_to_base_multi_repo(
        self, chunk: str, delete_branch: bool, repo_paths: list[Path]
    ) -> None:
        """Merge a chunk's branch to base in each repository.

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge
            repo_paths: List of repository paths
        """
        branch = self.get_branch_name(chunk)
        merged_repos: list[tuple[Path, str]] = []  # (repo_path, original_branch)

        try:
            for repo_path in repo_paths:
                repo_name = repo_path.name

                # Skip if branch doesn't exist in this repo
                if not self._branch_exists_in_repo(branch, repo_path):
                    continue

                # Get the base branch for this repo
                base = self._get_repo_current_branch(repo_path)

                # First, ensure we're on the base branch in this repo
                result = subprocess.run(
                    ["git", "checkout", base],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise WorktreeError(
                        f"Failed to checkout base branch {base} in {repo_name}: {result.stderr}"
                    )

                # Merge the chunk branch
                result = subprocess.run(
                    ["git", "merge", branch, "--no-edit"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    # Abort the merge if it failed
                    subprocess.run(
                        ["git", "merge", "--abort"],
                        cwd=repo_path,
                        capture_output=True,
                    )
                    raise WorktreeError(
                        f"Failed to merge {branch} into {base} in {repo_name}: {result.stderr}"
                    )

                merged_repos.append((repo_path, base))

                # Delete the branch if requested
                if delete_branch:
                    subprocess.run(
                        ["git", "branch", "-d", branch],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )

        except WorktreeError:
            # Rollback successful merges by resetting to pre-merge state
            for repo_path, base in merged_repos:
                subprocess.run(
                    ["git", "reset", "--hard", f"{base}@{{1}}"],
                    cwd=repo_path,
                    capture_output=True,
                )
            raise

    def has_changes(
        self, chunk: str, repo_paths: Optional[list[Path]] = None
    ) -> Union[bool, dict[str, bool]]:
        """Check if a chunk's branch has changes relative to base.

        In single-repo mode (repo_paths=None):
            Returns True if the chunk branch has commits not in base.

        In task context mode (repo_paths provided):
            Returns a dict mapping repo name to whether it has changes.

        Args:
            chunk: Chunk name
            repo_paths: Optional list of repository paths for task context mode

        Returns:
            bool for single-repo mode, dict[str, bool] for task context mode
        """
        if repo_paths is not None:
            return self._has_changes_multi_repo(chunk, repo_paths)
        else:
            return self._has_changes_single_repo(chunk)

    def _has_changes_single_repo(self, chunk: str) -> bool:
        """Check if a chunk has changes in single-repo mode.

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

    def _has_changes_multi_repo(
        self, chunk: str, repo_paths: list[Path]
    ) -> dict[str, bool]:
        """Check if a chunk has changes in each repository.

        Args:
            chunk: Chunk name
            repo_paths: List of repository paths

        Returns:
            Dict mapping repo name to whether it has changes
        """
        branch = self.get_branch_name(chunk)
        changes: dict[str, bool] = {}

        for repo_path in repo_paths:
            repo_name = repo_path.name

            if not self._branch_exists_in_repo(branch, repo_path):
                changes[repo_name] = False
                continue

            # Get the base branch for this repo
            base = self._get_repo_current_branch(repo_path)

            # Check if there are any commits in branch that aren't in base
            result = subprocess.run(
                ["git", "rev-list", f"{base}..{branch}", "--count"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                changes[repo_name] = False
            else:
                count = int(result.stdout.strip())
                changes[repo_name] = count > 0

        return changes

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
