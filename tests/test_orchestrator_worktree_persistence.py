# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for orchestrator worktree persistence and locking."""

import subprocess
import pytest
from pathlib import Path

from conftest import make_ve_initialized_git_repo, setup_task_directory
from orchestrator.worktree import WorktreeManager, WorktreeError


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository for testing."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
class TestBaseBranchPersistence:
    """Tests for base branch capture at worktree creation time."""

    def test_single_repo_base_branch_file_created(self, git_repo):
        """A base_branch file is created when a worktree is created."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        base_branch_file = git_repo / ".ve" / "chunks" / "test_chunk" / "base_branch"
        assert base_branch_file.exists()

    def test_single_repo_base_branch_file_contains_branch_name(self, git_repo):
        """The base_branch file contains the branch name at creation time."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        base_branch_file = git_repo / ".ve" / "chunks" / "test_chunk" / "base_branch"
        stored_branch = base_branch_file.read_text().strip()
        # The base branch should be main or master
        assert stored_branch in ("main", "master")

    def test_single_repo_base_branch_captured_from_explicit_branch(self, git_repo):
        """When base_branch is explicitly set, that value is persisted."""
        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(git_repo, base_branch="feature")
        manager.create_worktree("test_chunk")

        base_branch_file = git_repo / ".ve" / "chunks" / "test_chunk" / "base_branch"
        stored_branch = base_branch_file.read_text().strip()
        assert stored_branch == "feature"

    def test_merge_uses_persisted_base_branch_not_current(self, git_repo):
        """merge_to_base uses the persisted base branch, not current branch."""
        # Start on main
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree before merge
        manager.remove_worktree("test_chunk", remove_branch=False)

        # Switch main repo to a different branch
        subprocess.run(
            ["git", "checkout", "-b", "different_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Merge should still target the original base branch (main), not different_branch
        manager.merge_to_base("test_chunk", delete_branch=True)

        # Switch back to main and verify the file is there
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert (git_repo / "new_file.txt").exists()

    def test_load_base_branch_returns_persisted_value(self, git_repo):
        """_load_base_branch returns the value stored in the base_branch file."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        loaded_branch = manager._load_base_branch("test_chunk")
        assert loaded_branch in ("main", "master")


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
class TestCheckoutFreeMerge:
    """Tests for merging without git checkout in main repo."""

    def test_merge_does_not_change_main_repo_branch(self, git_repo):
        """merge_to_base does NOT change the checked-out branch in main repo."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "new_file.txt").write_text("new content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree before merge
        manager.remove_worktree("test_chunk", remove_branch=False)

        # Switch main repo to a different branch
        subprocess.run(
            ["git", "checkout", "-b", "working_branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get current branch before merge
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        branch_before = result.stdout.strip()

        # Merge to base - should NOT checkout a different branch
        manager.merge_to_base("test_chunk", delete_branch=True)

        # Check current branch after merge - should be unchanged
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        branch_after = result.stdout.strip()

        assert branch_before == branch_after == "working_branch"

    def test_merge_preserves_working_tree_changes(self, git_repo):
        """A file modified in main repo's working tree remains after merge."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree and commit
        (worktree_path / "worktree_file.txt").write_text("worktree content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add worktree file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree before merge
        manager.remove_worktree("test_chunk", remove_branch=False)

        # Create an uncommitted change in the main repo
        (git_repo / "uncommitted_change.txt").write_text("I am uncommitted")

        # Merge to base
        manager.merge_to_base("test_chunk", delete_branch=True)

        # Uncommitted file should still exist
        assert (git_repo / "uncommitted_change.txt").exists()
        assert (git_repo / "uncommitted_change.txt").read_text() == "I am uncommitted"

    def test_merge_conflict_still_detected(self, git_repo):
        """Merge conflicts are still detected and reported with WorktreeError."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Create a file in main repo on base branch
        (git_repo / "conflict_file.txt").write_text("main version")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add conflict file on main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create a conflicting change in the worktree
        (worktree_path / "conflict_file.txt").write_text("worktree version")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add conflict file in worktree"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Remove worktree before merge
        manager.remove_worktree("test_chunk", remove_branch=False)

        # Merge should fail with WorktreeError due to conflict
        with pytest.raises(WorktreeError):
            manager.merge_to_base("test_chunk", delete_branch=True)


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
class TestWorktreeLocking:
    """Tests for git worktree locking to prevent premature pruning."""

    def test_worktree_is_locked_after_creation(self, git_repo):
        """After create_worktree(), the worktree is locked."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Check worktree list for locked status
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )

        # Parse the porcelain output to find our worktree
        in_our_worktree = False
        is_locked = False
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and str(worktree_path) in line:
                in_our_worktree = True
            elif line.startswith("worktree "):
                in_our_worktree = False
            elif in_our_worktree and line.startswith("locked"):
                is_locked = True
                break

        assert is_locked, "Worktree should be locked after creation"

    def test_locked_worktree_survives_prune(self, git_repo):
        """git worktree prune does not remove a locked worktree."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Run prune
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=git_repo,
            capture_output=True,
        )

        # Worktree should still exist
        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()

    def test_remove_worktree_unlocks_first(self, git_repo):
        """remove_worktree unlocks the worktree before removing it."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Remove should succeed (which requires unlocking first)
        manager.remove_worktree("test_chunk")

        assert not worktree_path.exists()

    def test_unlock_is_idempotent(self, git_repo):
        """Unlocking a worktree that isn't locked doesn't error."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Manually unlock first
        subprocess.run(
            ["git", "worktree", "unlock", str(worktree_path)],
            cwd=git_repo,
            capture_output=True,
        )

        # Remove should still succeed (even though already unlocked)
        manager.remove_worktree("test_chunk")

        assert not worktree_path.exists()


# Chunk: docs/chunks/orch_task_worktrees - Task context detection tests
class TestTaskContextDetection:
    """Tests for task context detection and listing."""

    @pytest.fixture
    def task_repos(self, tmp_path):
        """Create a task directory with multiple repos for testing."""
        _, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a"],
        )
        return {
            "external": external,
            "project_a": projects[0],
        }

    def test_is_task_context_true_for_multi_repo(self, task_repos):
        """is_task_context returns True for chunks with work/ directory."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("task_chunk", repo_paths=repo_paths)

        assert manager.is_task_context("task_chunk") is True

    def test_is_task_context_false_for_single_repo(self, task_repos):
        """is_task_context returns False for single-repo chunks."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        manager.create_worktree("single_chunk")

        assert manager.is_task_context("single_chunk") is False

    def test_worktree_exists_task_context(self, task_repos):
        """worktree_exists works for task context structure."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("task_chunk", repo_paths=repo_paths)

        assert manager.worktree_exists("task_chunk") is True

    def test_list_worktrees_includes_task_context_chunks(self, task_repos):
        """list_worktrees includes both single-repo and task context chunks."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        # Create single-repo worktree
        manager.create_worktree("single_chunk")

        # Create task context worktree
        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("task_chunk", repo_paths=repo_paths)

        worktrees = manager.list_worktrees()

        assert set(worktrees) == {"single_chunk", "task_chunk"}
