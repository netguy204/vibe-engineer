# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
"""Tests for the orchestrator worktree manager."""

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


class TestWorktreeManager:
    """Tests for WorktreeManager."""

    def test_get_worktree_path(self, git_repo):
        """Returns expected path for worktree."""
        manager = WorktreeManager(git_repo)

        path = manager.get_worktree_path("test_chunk")

        assert path == git_repo / ".ve" / "chunks" / "test_chunk" / "worktree"

    def test_get_log_path(self, git_repo):
        """Returns expected path for log directory."""
        manager = WorktreeManager(git_repo)

        path = manager.get_log_path("test_chunk")

        assert path == git_repo / ".ve" / "chunks" / "test_chunk" / "log"

    def test_get_branch_name(self, git_repo):
        """Returns expected branch name format."""
        manager = WorktreeManager(git_repo)

        branch = manager.get_branch_name("test_chunk")

        assert branch == "orch/test_chunk"

    def test_worktree_exists_false(self, git_repo):
        """Returns False when worktree doesn't exist."""
        manager = WorktreeManager(git_repo)

        assert manager.worktree_exists("test_chunk") is False

    def test_create_worktree(self, git_repo):
        """Creates worktree successfully."""
        manager = WorktreeManager(git_repo)

        worktree_path = manager.create_worktree("test_chunk")

        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()
        assert manager.worktree_exists("test_chunk")

    def test_create_worktree_creates_log_dir(self, git_repo):
        """Creates log directory along with worktree."""
        manager = WorktreeManager(git_repo)

        manager.create_worktree("test_chunk")

        log_path = manager.get_log_path("test_chunk")
        assert log_path.exists()

    def test_create_worktree_creates_branch(self, git_repo):
        """Creates branch when creating worktree."""
        manager = WorktreeManager(git_repo)

        manager.create_worktree("test_chunk")

        # Check branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_create_worktree_idempotent(self, git_repo):
        """Creating worktree twice returns same path."""
        manager = WorktreeManager(git_repo)

        path1 = manager.create_worktree("test_chunk")
        path2 = manager.create_worktree("test_chunk")

        assert path1 == path2

    def test_remove_worktree(self, git_repo):
        """Removes worktree successfully."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk")

        assert not manager.worktree_exists("test_chunk")

    def test_remove_worktree_keeps_branch(self, git_repo):
        """Removing worktree keeps branch by default."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk", remove_branch=False)

        # Branch should still exist
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode == 0

    def test_remove_worktree_with_branch(self, git_repo):
        """Can remove branch along with worktree."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        manager.remove_worktree("test_chunk", remove_branch=True)

        # Branch should be gone
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
            cwd=git_repo,
            capture_output=True,
        )
        assert result.returncode != 0

    def test_remove_nonexistent_worktree(self, git_repo):
        """Removing nonexistent worktree doesn't raise."""
        manager = WorktreeManager(git_repo)

        # Should not raise
        manager.remove_worktree("nonexistent")

    def test_list_worktrees_empty(self, git_repo):
        """Returns empty list when no worktrees exist."""
        manager = WorktreeManager(git_repo)

        worktrees = manager.list_worktrees()

        assert worktrees == []

    def test_list_worktrees(self, git_repo):
        """Lists created worktrees."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("chunk_a")
        manager.create_worktree("chunk_b")

        worktrees = manager.list_worktrees()

        assert set(worktrees) == {"chunk_a", "chunk_b"}

    def test_worktree_has_correct_content(self, git_repo):
        """Worktree contains same content as main."""
        # Add a file to main
        (git_repo / "test.txt").write_text("test content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add test file"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Worktree should have the file
        assert (worktree_path / "test.txt").exists()
        assert (worktree_path / "test.txt").read_text() == "test content"


class TestWorktreeCleanup:
    """Tests for worktree cleanup operations."""

    def test_cleanup_orphaned_worktrees(self, git_repo):
        """Cleanup returns list of worktree chunk names."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("chunk_a")
        manager.create_worktree("chunk_b")

        orphaned = manager.cleanup_orphaned_worktrees()

        # Returns the worktree names
        assert set(orphaned) == {"chunk_a", "chunk_b"}


class TestBaseBranch:
    """Tests for base branch handling."""

    def test_base_branch_defaults_to_current(self, git_repo):
        """Base branch defaults to current branch."""
        manager = WorktreeManager(git_repo)

        # Should be 'main' or 'master' depending on git config
        assert manager.base_branch in ("main", "master")

    def test_base_branch_can_be_specified(self, git_repo):
        """Base branch can be explicitly set."""
        # Create a feature branch first
        subprocess.run(
            ["git", "branch", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        manager = WorktreeManager(git_repo, base_branch="feature")

        assert manager.base_branch == "feature"

    def test_worktree_branches_from_base(self, git_repo):
        """Worktree branches are created from base branch."""
        # Make a commit on a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("feature content")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Feature commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create worktree manager with feature as base
        manager = WorktreeManager(git_repo, base_branch="feature")
        worktree_path = manager.create_worktree("test_chunk")

        # The worktree should have the feature file
        assert (worktree_path / "feature.txt").exists()


class TestMergeToBase:
    """Tests for merging back to base branch."""

    def test_merge_to_base_success(self, git_repo):
        """Successfully merges chunk branch back to base."""
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

        # Merge back to base
        manager.merge_to_base("test_chunk", delete_branch=True)

        # The new file should be on the base branch
        assert (git_repo / "new_file.txt").exists()

        # The orch branch should be deleted
        assert not manager._branch_exists("orch/test_chunk")

    def test_merge_to_base_no_changes(self, git_repo):
        """has_changes returns False for branch with no new commits."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No changes made
        assert manager.has_changes("test_chunk") is False

    def test_merge_to_base_with_changes(self, git_repo):
        """has_changes returns True for branch with commits."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change
        (worktree_path / "change.txt").write_text("change")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add change"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        assert manager.has_changes("test_chunk") is True

    def test_merge_nonexistent_branch_raises(self, git_repo):
        """Merging nonexistent branch raises WorktreeError."""
        manager = WorktreeManager(git_repo)

        with pytest.raises(WorktreeError):
            manager.merge_to_base("nonexistent")

    def test_merge_keeps_branch_when_requested(self, git_repo):
        """merge_to_base can keep the branch after merge."""
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

        # Remove worktree and merge with delete_branch=False
        manager.remove_worktree("test_chunk", remove_branch=False)
        manager.merge_to_base("test_chunk", delete_branch=False)

        # Branch should still exist
        assert manager._branch_exists("orch/test_chunk")


# Chunk: docs/chunks/orch_mechanical_commit - Unit tests for mechanical commit
class TestCommitChanges:
    """Tests for WorktreeManager.commit_changes()."""

    def test_commit_changes_success(self, git_repo):
        """Commits staged changes with correct message format."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "new_file.txt").write_text("new content")

        # Commit using commit_changes
        result = manager.commit_changes("test_chunk")

        assert result is True

        # Verify the commit message format
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert log_result.stdout.strip() == "feat: chunk test_chunk"

        # Verify the file was committed
        assert not manager.has_uncommitted_changes("test_chunk")

    def test_commit_changes_nothing_to_commit(self, git_repo):
        """Returns False when nothing to commit."""
        manager = WorktreeManager(git_repo)
        manager.create_worktree("test_chunk")

        # No changes made - should return False
        result = manager.commit_changes("test_chunk")

        assert result is False

    def test_commit_changes_stages_all_files(self, git_repo):
        """Stages all changes including untracked files."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Create multiple files - one new, one modified
        (worktree_path / "new_file.txt").write_text("new content")
        (worktree_path / "README.md").write_text("modified content")

        # Commit using commit_changes
        result = manager.commit_changes("test_chunk")

        assert result is True

        # Verify both files were committed
        assert not manager.has_uncommitted_changes("test_chunk")

        # Check commit includes both files
        show_result = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert "new_file.txt" in show_result.stdout
        assert "README.md" in show_result.stdout

    def test_commit_changes_nonexistent_worktree_raises(self, git_repo):
        """Raises WorktreeError for non-existent worktree."""
        manager = WorktreeManager(git_repo)

        with pytest.raises(WorktreeError) as exc_info:
            manager.commit_changes("nonexistent_chunk")

        assert "does not exist" in str(exc_info.value)

    def test_commit_changes_commit_in_worktree_not_main(self, git_repo):
        """Commit happens in worktree, not main repo."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("test_chunk")

        # Make a change in the worktree
        (worktree_path / "worktree_file.txt").write_text("worktree content")

        # Commit
        manager.commit_changes("test_chunk")

        # File should NOT exist in main repo (until merge)
        assert not (git_repo / "worktree_file.txt").exists()

        # File should exist in worktree
        assert (worktree_path / "worktree_file.txt").exists()

    def test_commit_changes_message_format(self, git_repo):
        """Commit message follows expected format: feat: chunk {chunk_name}."""
        manager = WorktreeManager(git_repo)
        worktree_path = manager.create_worktree("my_feature_chunk")

        # Make a change
        (worktree_path / "feature.txt").write_text("feature")
        manager.commit_changes("my_feature_chunk")

        # Verify commit message
        log_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        assert log_result.stdout.strip() == "feat: chunk my_feature_chunk"


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo worktree creation tests
class TestMultiRepoWorktreeCreation:
    """Tests for multi-repo worktree creation in task context."""

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

    def test_create_worktree_with_repo_paths_creates_work_dir(self, task_repos):
        """Creates work/ directory structure when repo_paths provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Should return path to work/ directory
        assert work_dir.name == "work"
        assert work_dir.exists()

    def test_create_worktree_with_repo_paths_creates_worktrees_per_repo(self, task_repos):
        """Creates a worktree for each repo under work/<repo-name>/."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Each repo should have a worktree directory under work/
        assert (work_dir / "external" / ".git").exists()
        assert (work_dir / "project_a" / ".git").exists()

    def test_create_worktree_with_repo_paths_uses_correct_branches(self, task_repos):
        """Each worktree uses orch/<chunk> branch in its respective repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check branch in each repo worktree
        for repo_name in ["external", "project_a"]:
            worktree_dir = work_dir / repo_name
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=worktree_dir,
                capture_output=True,
                text=True,
            )
            assert result.stdout.strip() == "orch/test_chunk"

    def test_create_worktree_single_repo_unchanged(self, task_repos):
        """Single-repo behavior unchanged when repo_paths not provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        # Without repo_paths - should use existing single-repo behavior
        worktree_path = manager.create_worktree("test_chunk")

        # Should be at worktree/ not work/<repo-name>/
        assert worktree_path.name == "worktree"
        assert (worktree_path / ".git").exists()

    def test_get_work_directory_returns_work_path(self, task_repos):
        """get_work_directory returns correct work/ path."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        work_dir = manager.get_work_directory("test_chunk")

        assert work_dir == external / ".ve" / "chunks" / "test_chunk" / "work"

    def test_create_worktree_creates_log_dir_for_task_context(self, task_repos):
        """Creates log directory for task context worktrees."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        log_path = manager.get_log_path("test_chunk")
        assert log_path.exists()


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo worktree removal tests
class TestMultiRepoWorktreeRemoval:
    """Tests for multi-repo worktree removal."""

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

    def test_remove_worktree_with_repo_paths_cleans_all(self, task_repos):
        """Removes all repo worktrees when repo_paths provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)
        assert work_dir.exists()

        manager.remove_worktree("test_chunk", repo_paths=repo_paths)

        # Work directory should be gone
        assert not (external / ".ve" / "chunks" / "test_chunk" / "work").exists()

    def test_remove_worktree_with_repo_paths_removes_branches(self, task_repos):
        """Branches deleted when remove_branch=True for multi-repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        manager.create_worktree("test_chunk", repo_paths=repo_paths)

        manager.remove_worktree("test_chunk", remove_branch=True, repo_paths=repo_paths)

        # Branches should be gone in each repo
        for repo_path in repo_paths:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "refs/heads/orch/test_chunk"],
                cwd=repo_path,
                capture_output=True,
            )
            assert result.returncode != 0

    def test_remove_worktree_single_repo_unchanged(self, task_repos):
        """Single-repo removal unchanged when repo_paths not provided."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        # Create single-repo worktree
        worktree_path = manager.create_worktree("test_chunk")
        assert worktree_path.exists()

        # Remove without repo_paths - should use existing behavior
        manager.remove_worktree("test_chunk")

        assert not manager.worktree_exists("test_chunk")


# Chunk: docs/chunks/orch_task_worktrees - Multi-repo merge operation tests
class TestMultiRepoMerge:
    """Tests for multi-repo merge operations."""

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

    def test_merge_to_base_with_repo_paths_merges_all(self, task_repos):
        """Merges chunk branch in each repo back to base."""
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

        # Merge in all repos
        manager.merge_to_base("test_chunk", repo_paths=repo_paths)

        # Files should be on base branch in each repo
        assert (task_repos["external"] / "external_file.txt").exists()
        assert (task_repos["project_a"] / "project_file.txt").exists()

    def test_has_changes_with_repo_paths(self, task_repos):
        """has_changes returns dict of changes per repo."""
        external = task_repos["external"]
        manager = WorktreeManager(external)

        repo_paths = [task_repos["external"], task_repos["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Make change only in external repo
        (work_dir / "external" / "change.txt").write_text("change")
        subprocess.run(
            ["git", "add", "."],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add change"],
            cwd=work_dir / "external",
            check=True,
            capture_output=True,
        )

        changes = manager.has_changes("test_chunk", repo_paths=repo_paths)

        assert isinstance(changes, dict)
        assert changes["external"] is True
        assert changes["project_a"] is False


class TestTaskContextSymlinks:
    """Tests for symlink creation in task context mode."""

    @pytest.fixture
    def task_directory_with_config(self, tmp_path):
        """Create a task directory with CLAUDE.md and .claude/ for testing."""
        task_dir, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a"],
        )
        # Create task-level CLAUDE.md
        (task_dir / "CLAUDE.md").write_text("# Task-level guidance\n")
        # Create task-level .claude/ directory with a command
        (task_dir / ".claude").mkdir()
        (task_dir / ".claude" / "test-command.md").write_text("# Test command\n")
        return {
            "task_dir": task_dir,
            "external": external,
            "project_a": projects[0],
        }

    def test_creates_ve_task_yaml_symlink(self, task_directory_with_config):
        """Creates symlink to .ve-task.yaml in work/ directory."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        # Create TaskContextInfo to enable task context mode
        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check .ve-task.yaml symlink exists
        ve_task_symlink = work_dir / ".ve-task.yaml"
        assert ve_task_symlink.is_symlink()
        assert ve_task_symlink.resolve() == (task_dir / ".ve-task.yaml").resolve()

    def test_creates_claude_md_symlink(self, task_directory_with_config):
        """Creates symlink to CLAUDE.md in work/ directory."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check CLAUDE.md symlink exists
        claude_md_symlink = work_dir / "CLAUDE.md"
        assert claude_md_symlink.is_symlink()
        assert claude_md_symlink.resolve() == (task_dir / "CLAUDE.md").resolve()

    def test_creates_claude_dir_symlink(self, task_directory_with_config):
        """Creates symlink to .claude/ directory in work/ directory."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Check .claude/ symlink exists
        claude_dir_symlink = work_dir / ".claude"
        assert claude_dir_symlink.is_symlink()
        assert claude_dir_symlink.resolve() == (task_dir / ".claude").resolve()

    def test_symlinks_point_to_task_directory(self, task_directory_with_config):
        """Symlinks resolve to task directory files, not worktree files."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Symlinked files should contain task-level content
        assert (work_dir / "CLAUDE.md").read_text() == "# Task-level guidance\n"
        assert (work_dir / ".claude" / "test-command.md").read_text() == "# Test command\n"

    def test_symlinks_removed_on_worktree_cleanup(self, task_directory_with_config):
        """Symlinks are cleaned up when worktree is removed."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # Verify symlinks exist
        assert (work_dir / ".ve-task.yaml").is_symlink()
        assert (work_dir / "CLAUDE.md").is_symlink()
        assert (work_dir / ".claude").is_symlink()

        # Remove worktree
        manager.remove_worktree("test_chunk", repo_paths=repo_paths)

        # Work directory should be gone (including symlinks)
        assert not work_dir.exists()

    def test_single_repo_mode_no_symlinks(self, task_directory_with_config):
        """No symlinks created in single-repo mode."""
        external = task_directory_with_config["external"]

        # Create WorktreeManager without task_info (single-repo mode)
        manager = WorktreeManager(external)
        worktree_path = manager.create_worktree("test_chunk")

        # Single-repo mode should not have symlinks in the worktree
        # (there's no work/ directory in single-repo mode)
        assert not (worktree_path / ".ve-task.yaml").is_symlink()
        assert not (worktree_path / "CLAUDE.md").is_symlink()
        assert not (worktree_path / ".claude").is_symlink()

    def test_missing_claude_md_skipped(self, task_directory_with_config):
        """Missing CLAUDE.md doesn't cause error, just skips that symlink."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        # Remove CLAUDE.md from task directory
        (task_dir / "CLAUDE.md").unlink()

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]

        # Should not raise
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # .ve-task.yaml symlink should exist
        assert (work_dir / ".ve-task.yaml").is_symlink()
        # CLAUDE.md symlink should NOT exist (source missing)
        assert not (work_dir / "CLAUDE.md").exists()
        # .claude/ symlink should exist
        assert (work_dir / ".claude").is_symlink()

    def test_missing_claude_dir_skipped(self, task_directory_with_config):
        """Missing .claude/ directory doesn't cause error, just skips that symlink."""
        from orchestrator.models import TaskContextInfo
        import shutil

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        # Remove .claude/ from task directory
        shutil.rmtree(task_dir / ".claude")

        task_info = TaskContextInfo(
            root_dir=task_dir,
            is_task_context=True,
            external_repo_path=external,
            project_paths=[task_directory_with_config["project_a"]],
        )

        manager = WorktreeManager(external, task_info=task_info)
        repo_paths = [external, task_directory_with_config["project_a"]]

        # Should not raise
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # .ve-task.yaml symlink should exist
        assert (work_dir / ".ve-task.yaml").is_symlink()
        # CLAUDE.md symlink should exist
        assert (work_dir / "CLAUDE.md").is_symlink()
        # .claude/ symlink should NOT exist (source missing)
        assert not (work_dir / ".claude").exists()

    def test_without_task_info_no_symlinks_even_with_repo_paths(
        self, task_directory_with_config
    ):
        """Without task_info, no symlinks created even when repo_paths provided."""
        external = task_directory_with_config["external"]

        # Create WorktreeManager without task_info
        manager = WorktreeManager(external)
        repo_paths = [external, task_directory_with_config["project_a"]]
        work_dir = manager.create_worktree("test_chunk", repo_paths=repo_paths)

        # No symlinks should be created (task_info is required to know task_dir)
        assert not (work_dir / ".ve-task.yaml").is_symlink()
        assert not (work_dir / "CLAUDE.md").is_symlink()
        assert not (work_dir / ".claude").is_symlink()


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
