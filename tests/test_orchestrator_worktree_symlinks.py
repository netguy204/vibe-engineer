# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/agentskills_migration - Updated for AGENTS.md and .agents/ structure
"""Tests for symlink creation in task context mode."""

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


class TestTaskContextSymlinks:
    """Tests for symlink creation in task context mode."""

    @pytest.fixture
    def task_directory_with_config(self, tmp_path):
        """Create a task directory with AGENTS.md, .agents/, and compat symlinks for testing."""
        task_dir, external, projects = setup_task_directory(
            tmp_path,
            external_name="external",
            project_names=["project_a"],
        )
        # Create task-level AGENTS.md (canonical)
        (task_dir / "AGENTS.md").write_text("# Task-level guidance\n")
        # Create CLAUDE.md symlink for backwards compatibility
        (task_dir / "CLAUDE.md").symlink_to("AGENTS.md")
        # Create task-level .agents/ directory with skills
        (task_dir / ".agents").mkdir()
        (task_dir / ".agents" / "skills").mkdir()
        # Create task-level .claude/ directory with a command symlink
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

    def test_creates_agents_md_symlink(self, task_directory_with_config):
        """Creates symlink to AGENTS.md in work/ directory."""
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

        # Check AGENTS.md symlink exists
        agents_md_symlink = work_dir / "AGENTS.md"
        assert agents_md_symlink.is_symlink()
        assert agents_md_symlink.resolve() == (task_dir / "AGENTS.md").resolve()

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

        # Check CLAUDE.md symlink exists (may be a symlink to a symlink)
        claude_md_symlink = work_dir / "CLAUDE.md"
        assert claude_md_symlink.is_symlink()

    def test_creates_agents_dir_symlink(self, task_directory_with_config):
        """Creates symlink to .agents/ directory in work/ directory."""
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

        # Check .agents/ symlink exists
        agents_dir_symlink = work_dir / ".agents"
        assert agents_dir_symlink.is_symlink()
        assert agents_dir_symlink.resolve() == (task_dir / ".agents").resolve()

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
        assert (work_dir / "AGENTS.md").read_text() == "# Task-level guidance\n"
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
        assert (work_dir / "AGENTS.md").is_symlink()
        assert (work_dir / "CLAUDE.md").is_symlink()
        assert (work_dir / ".agents").is_symlink()
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
        assert not (worktree_path / "AGENTS.md").is_symlink()
        assert not (worktree_path / "CLAUDE.md").is_symlink()
        assert not (worktree_path / ".agents").is_symlink()
        assert not (worktree_path / ".claude").is_symlink()

    def test_missing_agents_md_skipped(self, task_directory_with_config):
        """Missing AGENTS.md doesn't cause error, just skips that symlink."""
        from orchestrator.models import TaskContextInfo

        task_dir = task_directory_with_config["task_dir"]
        external = task_directory_with_config["external"]

        # Remove AGENTS.md and CLAUDE.md symlink from task directory
        (task_dir / "CLAUDE.md").unlink()
        (task_dir / "AGENTS.md").unlink()

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
        # AGENTS.md symlink should NOT exist (source missing)
        assert not (work_dir / "AGENTS.md").exists()
        # CLAUDE.md symlink should NOT exist (source missing)
        assert not (work_dir / "CLAUDE.md").exists()
        # .agents/ symlink should exist
        assert (work_dir / ".agents").is_symlink()
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
        # AGENTS.md symlink should exist
        assert (work_dir / "AGENTS.md").is_symlink()
        # CLAUDE.md symlink should exist (it's a symlink to AGENTS.md, which exists)
        assert (work_dir / "CLAUDE.md").is_symlink()
        # .agents/ symlink should exist
        assert (work_dir / ".agents").is_symlink()
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
        assert not (work_dir / "AGENTS.md").is_symlink()
        assert not (work_dir / "CLAUDE.md").is_symlink()
        assert not (work_dir / ".agents").is_symlink()
        assert not (work_dir / ".claude").is_symlink()
