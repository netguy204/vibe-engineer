# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - WorktreeManager for isolated chunk execution and merge_to_base
# Chunk: docs/chunks/orch_task_worktrees - Multi-repo worktree support for task context
# Chunk: docs/chunks/orch_task_detection - WorktreeManager with task_info for multi-repo worktrees
# Chunk: docs/chunks/worktree_merge_extract - Merge logic extracted to orchestrator.merge
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

from orchestrator.git_utils import GitError, get_current_branch
# Chunk: docs/chunks/worktree_merge_extract - Import from merge module and re-export for backward compatibility
from orchestrator.merge import WorktreeError, merge_without_checkout

if TYPE_CHECKING:
    from orchestrator.models import TaskContextInfo

# Re-export WorktreeError for backward compatibility
__all__ = ["WorktreeError", "WorktreeManager"]


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

    def _get_task_directory(self) -> Optional[Path]:
        """Get the task directory if in task context mode.

        In task context, task_info.root_dir is the task directory.
        Returns None if not in task context.
        """
        if self.task_info and self.task_info.is_task_context:
            return self.task_info.root_dir
        return None

    def _get_current_branch(self) -> str:
        """Get the current git branch name.

        Returns:
            Current branch name

        Raises:
            WorktreeError: If not on a branch or git command fails
        """
        try:
            return get_current_branch(self.project_dir)
        except GitError as e:
            raise WorktreeError(str(e)) from e

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

    # Chunk: docs/chunks/orch_merge_safety - Lock worktrees to prevent pruning
    def _lock_worktree(self, worktree_path: Path, repo_dir: Path) -> None:
        """Lock a worktree to prevent it from being pruned.

        Args:
            worktree_path: Path to the worktree
            repo_dir: Repository that owns the worktree
        """
        subprocess.run(
            [
                "git",
                "worktree",
                "lock",
                str(worktree_path),
                "--reason",
                "orchestrator active",
            ],
            cwd=repo_dir,
            capture_output=True,
        )
        # Ignore errors - locking may fail if already locked or Git version too old

    # Chunk: docs/chunks/orch_merge_safety - Unlock worktrees before removal
    def _unlock_worktree(self, worktree_path: Path, repo_dir: Path) -> None:
        """Unlock a worktree before removal.

        Args:
            worktree_path: Path to the worktree
            repo_dir: Repository that owns the worktree
        """
        subprocess.run(
            ["git", "worktree", "unlock", str(worktree_path)],
            cwd=repo_dir,
            capture_output=True,
        )
        # Ignore errors - unlocking may fail if already unlocked

    # Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
    def _save_base_branch(
        self, chunk: str, branch: str, repo_dir: Optional[Path] = None
    ) -> None:
        """Save the base branch for a chunk to a file.

        For single-repo mode, saves to .ve/chunks/<chunk>/base_branch.
        For multi-repo mode, saves to .ve/chunks/<chunk>/base_branches/<repo_name>.

        Args:
            chunk: Chunk name
            branch: Branch name to save
            repo_dir: Repository directory (None for single-repo mode)
        """
        base_path = self._get_worktree_base_path(chunk)

        if repo_dir is None:
            # Single-repo mode
            base_branch_file = base_path / "base_branch"
        else:
            # Multi-repo mode - save per-repo base branch
            base_branches_dir = base_path / "base_branches"
            base_branches_dir.mkdir(parents=True, exist_ok=True)
            base_branch_file = base_branches_dir / repo_dir.name

        base_branch_file.parent.mkdir(parents=True, exist_ok=True)
        base_branch_file.write_text(branch)

    # Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
    def _load_base_branch(self, chunk: str, repo_dir: Optional[Path] = None) -> str:
        """Load the base branch for a chunk from file.

        For single-repo mode, reads from .ve/chunks/<chunk>/base_branch.
        For multi-repo mode, reads from .ve/chunks/<chunk>/base_branches/<repo_name>.

        Args:
            chunk: Chunk name
            repo_dir: Repository directory (None for single-repo mode)

        Returns:
            The persisted base branch name

        Raises:
            WorktreeError: If the base branch file doesn't exist
        """
        base_path = self._get_worktree_base_path(chunk)

        if repo_dir is None:
            # Single-repo mode
            base_branch_file = base_path / "base_branch"
        else:
            # Multi-repo mode
            base_branch_file = base_path / "base_branches" / repo_dir.name

        if not base_branch_file.exists():
            raise WorktreeError(
                f"Base branch file not found for chunk {chunk}"
                + (f" repo {repo_dir.name}" if repo_dir else "")
            )

        return base_branch_file.read_text().strip()

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
        try:
            return get_current_branch(repo_dir)
        except GitError as e:
            raise WorktreeError(str(e)) from e

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

        # Chunk: docs/chunks/orch_merge_safety - Persist base branch at creation time
        # Save the base branch before creating the worktree
        self._save_base_branch(chunk, self._base_branch)

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

        # Chunk: docs/chunks/orch_merge_safety - Lock worktree to prevent pruning
        self._lock_worktree(worktree_path, self.project_dir)

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

            # Chunk: docs/chunks/orch_merge_safety - Persist per-repo base branch at creation time
            # Get and save the base branch for this repo before creating the worktree
            repo_base_branch = self._get_repo_current_branch(repo_path)
            self._save_base_branch(chunk, repo_base_branch, repo_path)

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

            # Chunk: docs/chunks/orch_merge_safety - Lock worktree to prevent pruning
            self._lock_worktree(repo_worktree_path, repo_path)

        # Set up agent environment symlinks
        self._setup_agent_environment_symlinks(work_dir)

        return work_dir

    def _setup_agent_environment_symlinks(self, work_dir: Path) -> None:
        """Create symlinks to task-level configuration in work/ directory.

        Creates symlinks for:
        - .ve-task.yaml -> task_directory/.ve-task.yaml
        - CLAUDE.md -> task_directory/CLAUDE.md
        - .claude/ -> task_directory/.claude/

        Missing source files are skipped (not an error).

        Args:
            work_dir: The work/ directory where symlinks should be created
        """
        task_dir = self._get_task_directory()
        if task_dir is None:
            return

        symlink_targets = [
            (".ve-task.yaml", task_dir / ".ve-task.yaml"),
            ("CLAUDE.md", task_dir / "CLAUDE.md"),
            (".claude", task_dir / ".claude"),
        ]

        for link_name, target_path in symlink_targets:
            link_path = work_dir / link_name
            if target_path.exists() and not link_path.exists():
                link_path.symlink_to(target_path)

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

        # Clean up symlinks before removing work directory
        if work_dir.exists():
            self._cleanup_agent_environment_symlinks(work_dir)
            shutil.rmtree(work_dir, ignore_errors=True)

    def _cleanup_agent_environment_symlinks(self, work_dir: Path) -> None:
        """Remove symlinks from work/ directory.

        Args:
            work_dir: The work/ directory containing symlinks
        """
        symlink_names = [".ve-task.yaml", "CLAUDE.md", ".claude"]

        for link_name in symlink_names:
            link_path = work_dir / link_name
            if link_path.is_symlink():
                link_path.unlink()

    def _remove_worktree_from_repo(self, worktree_path: Path, repo_path: Path) -> None:
        """Remove a worktree from a repository.

        Args:
            worktree_path: Path to the worktree to remove
            repo_path: Path to the repository that owns the worktree
        """
        # Chunk: docs/chunks/orch_merge_safety - Unlock worktree before removal
        self._unlock_worktree(worktree_path, repo_path)

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

    # Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
    def _merge_to_base_single_repo(self, chunk: str, delete_branch: bool) -> None:
        """Merge a chunk's branch to base in single-repo mode.

        Uses a checkout-free merge strategy to avoid disrupting the user's
        working directory. The merge is performed by:
        1. Loading the persisted base branch (captured at worktree creation time)
        2. First trying fast-forward via branch -f (if branch is ancestor)
        3. If not fast-forward, creating a merge commit using git plumbing commands

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge
        """
        branch = self.get_branch_name(chunk)

        if not self._branch_exists(branch):
            raise WorktreeError(f"Branch {branch} does not exist")

        # Load the persisted base branch instead of using self._base_branch
        # which may be stale if the manager was created before branch changes
        try:
            base_branch = self._load_base_branch(chunk)
        except WorktreeError:
            # Fall back to the manager's base branch if file doesn't exist
            # (for backwards compatibility with existing worktrees)
            base_branch = self._base_branch

        # Perform checkout-free merge
        self._merge_without_checkout(branch, base_branch, self.project_dir)

        # Delete the branch if requested
        if delete_branch:
            subprocess.run(
                ["git", "branch", "-d", branch],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
            )
            # Don't raise on branch deletion failure - merge succeeded

    # Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
    # Chunk: docs/chunks/worktree_merge_extract - Delegates to orchestrator.merge module
    def _merge_without_checkout(
        self, source_branch: str, target_branch: str, repo_dir: Path
    ) -> None:
        """Perform a merge without checking out the target branch.

        This preserves the user's current checkout and any uncommitted changes.
        Delegates to the merge_without_checkout function in orchestrator.merge.

        Args:
            source_branch: Branch to merge from (e.g., orch/chunk_name)
            target_branch: Branch to merge into (e.g., main)
            repo_dir: Repository directory

        Raises:
            WorktreeError: If merge fails (e.g., conflicts)
        """
        merge_without_checkout(source_branch, target_branch, repo_dir)

    # Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
    def _merge_to_base_multi_repo(
        self, chunk: str, delete_branch: bool, repo_paths: list[Path]
    ) -> None:
        """Merge a chunk's branch to base in each repository.

        Uses checkout-free merge to avoid disrupting the user's working directory.

        Args:
            chunk: Chunk name
            delete_branch: If True, delete the chunk branch after merge
            repo_paths: List of repository paths
        """
        branch = self.get_branch_name(chunk)
        merged_repos: list[tuple[Path, str, str]] = []  # (repo_path, base, old_sha)

        try:
            for repo_path in repo_paths:
                repo_name = repo_path.name

                # Skip if branch doesn't exist in this repo
                if not self._branch_exists_in_repo(branch, repo_path):
                    continue

                # Load the persisted base branch for this repo
                try:
                    base = self._load_base_branch(chunk, repo_path)
                except WorktreeError:
                    # Fall back to current branch if file doesn't exist
                    # (for backwards compatibility)
                    base = self._get_repo_current_branch(repo_path)

                # Save the old base SHA for potential rollback
                result = subprocess.run(
                    ["git", "rev-parse", base],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise WorktreeError(
                        f"Base branch {base} not found in {repo_name}"
                    )
                old_sha = result.stdout.strip()

                # Perform checkout-free merge
                try:
                    self._merge_without_checkout(branch, base, repo_path)
                except WorktreeError as e:
                    raise WorktreeError(f"in {repo_name}: {e}")

                merged_repos.append((repo_path, base, old_sha))

                # Delete the branch if requested
                if delete_branch:
                    subprocess.run(
                        ["git", "branch", "-d", branch],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                    )

        except WorktreeError:
            # Rollback successful merges by resetting refs to pre-merge state
            for repo_path, base, old_sha in merged_repos:
                subprocess.run(
                    ["git", "update-ref", f"refs/heads/{base}", old_sha],
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

        # Chunk: docs/chunks/orch_mechanical_commit - Mechanical commit after COMPLETE phase

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

    # Chunk: docs/chunks/scheduler_decompose - Extracted branch deletion as public API
    def delete_branch(self, chunk: str) -> bool:
        """Delete the branch for a chunk.

        This method deletes the orch/<chunk> branch. It should be called
        after the worktree has been removed and merged.

        Args:
            chunk: Chunk name

        Returns:
            True if branch was deleted, False if it didn't exist or deletion failed
        """
        branch = self.get_branch_name(chunk)

        if not self._branch_exists(branch):
            return False

        result = subprocess.run(
            ["git", "branch", "-d", branch],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )

        return result.returncode == 0

    # Chunk: docs/chunks/orch_rename_propagation - Rename orchestrator branch
    def rename_branch(self, old_chunk: str, new_chunk: str) -> None:
        """Rename the git branch for a chunk.

        Renames the branch from orch/{old_chunk} to orch/{new_chunk}.
        This should be called as part of rename propagation after a chunk
        is renamed during a phase.

        Args:
            old_chunk: Old chunk name
            new_chunk: New chunk name

        Raises:
            WorktreeError: If branch rename fails
        """
        old_branch = self.get_branch_name(old_chunk)
        new_branch = self.get_branch_name(new_chunk)

        if not self._branch_exists(old_branch):
            raise WorktreeError(f"Branch {old_branch} does not exist")

        if self._branch_exists(new_branch):
            raise WorktreeError(f"Branch {new_branch} already exists")

        result = subprocess.run(
            ["git", "branch", "-m", old_branch, new_branch],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise WorktreeError(f"Failed to rename branch: {result.stderr}")

    # Chunk: docs/chunks/orch_rename_propagation - Rename chunk directory in .ve/chunks/
    def rename_chunk_directory(self, old_chunk: str, new_chunk: str) -> None:
        """Rename the chunk directory in .ve/chunks/.

        Renames .ve/chunks/{old_chunk}/ to .ve/chunks/{new_chunk}/.
        This includes the worktree, logs, and base_branch file.

        Args:
            old_chunk: Old chunk name
            new_chunk: New chunk name

        Raises:
            WorktreeError: If directory rename fails
        """
        old_path = self._get_worktree_base_path(old_chunk)
        new_path = self._get_worktree_base_path(new_chunk)

        if not old_path.exists():
            raise WorktreeError(f"Chunk directory {old_path} does not exist")

        if new_path.exists():
            raise WorktreeError(f"Chunk directory {new_path} already exists")

        # Use shutil.move for cross-filesystem compatibility
        shutil.move(str(old_path), str(new_path))

    # Chunk: docs/chunks/orch_prune_consolidate - Consolidated worktree finalization logic
    def finalize_work_unit(self, chunk: str) -> None:
        """Finalize a completed work unit by committing, removing worktree, and merging.

        This method handles the complete lifecycle cleanup for a work unit:
        1. Commits any uncommitted changes with a standard message
        2. Removes the worktree (but keeps the branch for merge)
        3. Merges changes to base branch (or deletes empty branch)

        This consolidates the prune/merge/cleanup logic that was previously
        duplicated in scheduler._advance_phase, api.prune_work_unit_endpoint,
        and api.prune_all_endpoint.

        Args:
            chunk: Chunk name

        Raises:
            WorktreeError: If any step fails (commit, remove, merge)
        """
        import subprocess

        # Step 1: Commit any uncommitted changes
        worktree_path = self.get_worktree_path(chunk)
        if worktree_path.exists() and self.has_uncommitted_changes(chunk):
            self.commit_changes(chunk)

        # Step 2: Remove worktree (must be done before merge to avoid conflicts)
        self.remove_worktree(chunk, remove_branch=False)

        # Step 3: Merge the branch back to base if it has changes
        if self.has_changes(chunk):
            self.merge_to_base(chunk, delete_branch=True)
        else:
            # Clean up the empty branch
            branch = self.get_branch_name(chunk)
            if self._branch_exists(branch):
                subprocess.run(
                    ["git", "branch", "-d", branch],
                    cwd=self.project_dir,
                    capture_output=True,
                )
