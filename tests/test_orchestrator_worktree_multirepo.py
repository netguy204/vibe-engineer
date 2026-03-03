# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator worktree manager - multi-repo specific tests."""

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
class TestMultiRepoBaseBranchPersistence:
    """Tests for base branch persistence in multi-repo mode."""

    @pytest.fixture
    def task_repos(self, tmp_path):
        """Create a task directory with multiple repos for testing."""
        _, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a", "project_b"],
        )
        return {
            "external": external,
            "project_a": projects[0],
            "project_b": projects[1],
        }

    def test_multi_repo_base_branch_files_created(self, task_repos):
        """Base branch files are created for each repo in task context mode."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Each repo should have its own base_branch file
        base_branches_dir = external / ".ve" / "chunks" / "test_chunk" / "base_branches"
        assert (base_branches_dir / "external").exists()
        assert (base_branches_dir / "project_a").exists()

    def test_multi_repo_base_branch_files_contain_correct_values(self, task_repos):
        """Each repo's base_branch file contains that repo's base branch."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        base_branches_dir = external / ".ve" / "chunks" / "test_chunk" / "base_branches"
        external_branch = (base_branches_dir / "external").read_text().strip()
        project_a_branch = (base_branches_dir / "project_a").read_text().strip()

        # Both should be "main" since that's what make_ve_initialized_git_repo creates
        assert external_branch == "main"
        assert project_a_branch == "main"

    def test_multi_repo_merge_uses_persisted_branches(self, task_repos):
        """Multi-repo merge uses persisted base branches, not current branches."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Make changes in each repo worktree
        (work_dir / "external" / "external_file.txt").write_text("external content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add external file"],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )

        (work_dir / "project_a" / "project_file.txt").write_text("project content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add project file"],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )

        # Remove worktrees before merge
        manager.remove_worktree("test_chunk", remove_branch=False, repo_paths=repo_paths)

        # Switch each main repo to a different branch
        for repo_path in repo_paths:
            subprocess.run(
                ["git", "checkout", "-b", "different_branch"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        # Merge should still target the original base branches (main)
        manager.merge_to_base("test_chunk", repo_paths=repo_paths)

        # Switch back to main and verify the files are there
        for repo_path in repo_paths:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        assert (task_repos["external"] / "external_file.txt").exists()
        assert (task_repos["project_a"] / "project_file.txt").exists()


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
class TestMultiRepoCheckoutFreeMerge:
    """Tests for checkout-free merge in multi-repo mode."""

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

    def test_multi_repo_merge_does_not_change_checked_out_branches(self, task_repos):
        """Multi-repo merge does NOT change checked-out branches in any repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Make changes in each repo worktree
        (work_dir / "external" / "external_file.txt").write_text("external content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add external file"],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )

        (work_dir / "project_a" / "project_file.txt").write_text("project content")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add project file"],
            cwd=work_dir / "project_a",
            check=True,
            capture_output=True,
        )

        # Remove worktrees before merge
        manager.remove_worktree("test_chunk", remove_branch=False, repo_paths=repo_paths)

        # Switch each main repo to a different branch
        for repo_path in repo_paths:
            subprocess.run(
                ["git", "checkout", "-b", "working_branch"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

        # Merge to base - should NOT checkout a different branch in any repo
        manager.merge_to_base("test_chunk", repo_paths=repo_paths)

        # Check current branches after merge - should all be unchanged
        for repo_path in repo_paths:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "working_branch"


# Chunk: docs/chunks/orch_merge_safety - Merge safety without git checkout
class TestMultiRepoWorktreeLocking:
    """Tests for worktree locking in multi-repo mode."""

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

    def test_multi_repo_worktrees_are_locked_after_creation(self, task_repos):
        """All worktrees are locked after creation in multi-repo mode."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check each repo for locked worktrees
        for repo_path in repo_paths:
            repo_name = repo_path.name
            worktree_path = work_dir / repo_name

            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

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

            assert is_locked, f"Worktree for {repo_name} should be locked after creation"

    def test_multi_repo_remove_unlocks_all_worktrees(self, task_repos):
        """Remove unlocks and removes all worktrees in multi-repo mode."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Remove should succeed
        manager.remove_worktree("test_chunk", repo_paths=repo_paths)

        assert not work_dir.exists()


# Chunk: docs/chunks/orch_prune_consolidate - Tests for finalize_work_unit
class TestFinalizeWorkUnit:
    """Tests for WorktreeManager.finalize_work_unit()."""

    def test_finalize_work_unit_commits_and_merges(self, git_repo):
        """finalize_work_unit commits, removes worktree, and merges to base."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make uncommitted changes in the worktree
        (worktree_path / "new_file.txt").write_text("new content")

        # Finalize the work unit
        manager.finalize_work_unit("test_chunk")

        # Worktree should be removed
        assert not worktree_path.exists()

        # Branch should be deleted
        assert not manager._branch_exists("orch/test_chunk")

        # Changes should be on base branch
        assert (git_repo / "new_file.txt").exists()
        assert (git_repo / "new_file.txt").read_text() == "new content"

    def test_finalize_work_unit_handles_no_changes(self, git_repo):
        """finalize_work_unit cleans up empty branch when no changes made."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # No changes made - finalize should clean up
        manager.finalize_work_unit("test_chunk")

        # Worktree should be removed
        assert not worktree_path.exists()

        # Branch should be deleted (empty branch cleanup)
        assert not manager._branch_exists("orch/test_chunk")

    def test_finalize_work_unit_removes_worktree(self, git_repo):
        """finalize_work_unit removes the worktree directory."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change
        (worktree_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Finalize
        manager.finalize_work_unit("test_chunk")

        # Worktree should be gone
        assert not worktree_path.exists()
        assert not manager.worktree_exists("test_chunk")

    def test_finalize_work_unit_raises_on_merge_conflict(self, git_repo):
        """finalize_work_unit raises WorktreeError on merge conflict."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Create a file on base branch that will conflict
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

        # Finalize should raise due to merge conflict
        with pytest.raises(WorktreeError):
            manager.finalize_work_unit("test_chunk")

    def test_finalize_work_unit_with_already_committed_changes(self, git_repo):
        """finalize_work_unit works when changes are already committed."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make and commit changes
        (worktree_path / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # Finalize
        manager.finalize_work_unit("test_chunk")

        # Changes should be on base branch
        assert (git_repo / "file.txt").exists()

    def test_finalize_work_unit_idempotent_on_nonexistent_worktree(self, git_repo):
        """finalize_work_unit handles missing worktree gracefully."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change
        (worktree_path / "file.txt").write_text("content")

        # Finalize once
        manager.finalize_work_unit("test_chunk")

        # Calling finalize again should not raise (worktree already gone)
        # It may raise on merge if branch was already deleted - that's expected
        # but shouldn't crash with an unhandled exception
        try:
            manager.finalize_work_unit("test_chunk")
        except WorktreeError:
            # Expected - branch was already deleted in first finalize
            pass
