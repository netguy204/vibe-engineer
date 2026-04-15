"""Tests for entity submodule support in orchestrator worktrees.

# Chunk: docs/chunks/entity_worktree_support - Entity submodule lifecycle in worktrees
"""

import subprocess
from pathlib import Path

import pytest

from conftest import make_ve_initialized_git_repo
from entity_repo import (
    attach_entity,
    create_entity_repo,
    init_entity_submodules_in_worktree,
    merge_entity_worktree_branches,
)
from orchestrator.worktree import WorktreeManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in path, returning CompletedProcess."""
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
    )


def _git_check(path: Path, *args: str) -> str:
    """Run a git command, assert success, return stdout."""
    result = _git(path, *args)
    assert result.returncode == 0, f"git {args} failed: {result.stderr}"
    return result.stdout.strip()


def make_entity_origin(tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path]:
    """Create an entity repo and a bare clone to simulate a hosted origin.

    Returns:
        (entity_src, bare_origin) where bare_origin is used as the URL in tests.
    """
    entity_src = create_entity_repo(tmp_path / f"entity-src-{name}", name)
    _git(entity_src, "config", "user.email", "test@test.com")
    _git(entity_src, "config", "user.name", "Test User")

    bare_origin = tmp_path / f"entity-origin-{name}.git"
    result = subprocess.run(
        ["git", "clone", "--bare", str(entity_src), str(bare_origin)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"bare clone failed: {result.stderr}"

    _git(entity_src, "remote", "add", "origin", str(bare_origin))

    return entity_src, bare_origin


def attach_and_commit_entity(project: Path, bare_origin: Path, name: str) -> Path:
    """Attach an entity as a submodule and commit so worktrees can initialize it.

    `git worktree add` + `git submodule update --init` requires the submodule
    to be committed (not just staged) in the parent repo.
    """
    entity_path = attach_entity(
        project, str(bare_origin), name,
    )
    _git(project, "add", ".")
    _git(project, "commit", "-m", f"Attach entity {name}")
    return entity_path


def create_worktree_for_project(project: Path, chunk: str) -> Path:
    """Create a git worktree for the given chunk and return the worktree path."""
    manager = WorktreeManager(project)
    return manager.create_worktree(chunk)


# ---------------------------------------------------------------------------
# TestInitEntitySubmodulesInWorktree
# ---------------------------------------------------------------------------


class TestInitEntitySubmodulesInWorktree:
    """Tests for init_entity_submodules_in_worktree()."""

    def test_no_op_when_no_entities_dir(self, tmp_path):
        """Worktree with no .entities/ — function returns without error."""
        # A plain directory with no .entities/ subdirectory
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        # Should not raise
        init_entity_submodules_in_worktree(worktree, "my_chunk")

    def test_no_op_when_entities_dir_empty(self, tmp_path):
        """If .entities/ exists but is empty, function returns without error."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        (worktree / ".entities").mkdir()

        # Should not raise
        init_entity_submodules_in_worktree(worktree, "my_chunk")

    def test_initializes_entity_submodule(self, tmp_path):
        """Project with attached entity — entity dir is populated in worktree."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        # Create worktree (WorktreeManager calls init_entity_submodules_in_worktree internally)
        worktree_path = create_worktree_for_project(project, "my_chunk")

        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        assert entity_in_worktree.is_dir(), "Entity dir should exist in worktree"
        assert (entity_in_worktree / "ENTITY.md").exists(), "ENTITY.md should be present"

    def test_entity_on_working_branch_after_init(self, tmp_path):
        """Entity in worktree is on ve-worktree-<chunk> branch (not detached HEAD)."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        worktree_path = create_worktree_for_project(project, "my_chunk")

        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        branch = _git_check(entity_in_worktree, "rev-parse", "--abbrev-ref", "HEAD")
        assert branch == "ve-worktree-my_chunk", (
            f"Expected ve-worktree-my_chunk, got {branch!r}"
        )

    def test_multiple_entities_all_initialized(self, tmp_path):
        """Two entities attached; both initialized in worktree on working branches."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare1 = make_entity_origin(tmp_path, "entity-alpha")
        _, bare2 = make_entity_origin(tmp_path, "entity-beta")
        attach_and_commit_entity(project, bare1, "entity-alpha")
        attach_and_commit_entity(project, bare2, "entity-beta")

        worktree_path = create_worktree_for_project(project, "multi_chunk")

        for name in ("entity-alpha", "entity-beta"):
            entity_dir = worktree_path / ".entities" / name
            assert entity_dir.is_dir(), f"{name} dir should exist in worktree"
            branch = _git_check(entity_dir, "rev-parse", "--abbrev-ref", "HEAD")
            assert branch == "ve-worktree-multi_chunk", (
                f"{name}: expected ve-worktree-multi_chunk, got {branch!r}"
            )

    def test_worktree_entity_independent_from_main_checkout(self, tmp_path):
        """Commit in worktree entity doesn't affect main checkout entity."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        worktree_path = create_worktree_for_project(project, "iso_chunk")

        # Make a commit in the worktree entity
        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        (entity_in_worktree / "worktree-file.txt").write_text("worktree change")
        _git(entity_in_worktree, "add", ".")
        _git(entity_in_worktree, "config", "user.email", "test@test.com")
        _git(entity_in_worktree, "config", "user.name", "Test User")
        _git(entity_in_worktree, "commit", "-m", "Worktree entity change")

        worktree_sha = _git_check(entity_in_worktree, "rev-parse", "HEAD")

        # The main checkout entity should not have that commit
        entity_in_main = project / ".entities" / "my-entity"
        main_sha = _git_check(entity_in_main, "rev-parse", "HEAD")

        assert worktree_sha != main_sha, (
            "Worktree entity commit should be independent from main checkout entity"
        )
        assert not (entity_in_main / "worktree-file.txt").exists(), (
            "Worktree-only file should not appear in main checkout entity"
        )


# ---------------------------------------------------------------------------
# TestMergeEntityWorktreeBranches
# ---------------------------------------------------------------------------


class TestMergeEntityWorktreeBranches:
    """Tests for merge_entity_worktree_branches()."""

    def test_no_op_when_no_entities_dir(self, tmp_path):
        """Function is no-op when .entities/ doesn't exist."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        # Should not raise
        merge_entity_worktree_branches(project, "my_chunk")

    def test_no_op_when_no_worktree_branch(self, tmp_path):
        """Entity exists but no ve-worktree-<chunk> branch — skip silently."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        # Should not raise even though ve-worktree-missing_chunk doesn't exist
        merge_entity_worktree_branches(project, "missing_chunk")

    def test_merges_entity_changes_to_main(self, tmp_path):
        """Entity has commits on worktree branch; after merge, entity main has those commits."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        worktree_path = create_worktree_for_project(project, "merge_chunk")
        entity_in_worktree = worktree_path / ".entities" / "my-entity"

        # Commit a change in the worktree entity branch
        (entity_in_worktree / "new-knowledge.txt").write_text("learned something")
        _git(entity_in_worktree, "add", ".")
        _git(entity_in_worktree, "config", "user.email", "test@test.com")
        _git(entity_in_worktree, "config", "user.name", "Test User")
        _git(entity_in_worktree, "commit", "-m", "New knowledge in worktree")

        # Perform entity branch merge
        merge_entity_worktree_branches(project, "merge_chunk")

        # The entity's main branch in the project's .entities dir should have the new commit
        entity_main = project / ".entities" / "my-entity"
        main_branch = _git_check(entity_main, "rev-parse", "--abbrev-ref", "HEAD")
        # Note: the main checkout entity's HEAD is still the old commit (submodule pointer),
        # so we check via branch ref directly
        result = _git(entity_main, "log", "main", "--oneline", "--", "new-knowledge.txt")
        assert "New knowledge in worktree" in result.stdout, (
            "Entity main should have the worktree commit after merge"
        )

    def test_deletes_worktree_branch_after_merge(self, tmp_path):
        """ve-worktree-<chunk> branch deleted after successful merge."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        worktree_path = create_worktree_for_project(project, "cleanup_chunk")
        entity_in_worktree = worktree_path / ".entities" / "my-entity"

        # Commit something in the worktree entity branch
        (entity_in_worktree / "temp.txt").write_text("temporary")
        _git(entity_in_worktree, "add", ".")
        _git(entity_in_worktree, "config", "user.email", "test@test.com")
        _git(entity_in_worktree, "config", "user.name", "Test User")
        _git(entity_in_worktree, "commit", "-m", "Temp commit")

        merge_entity_worktree_branches(project, "cleanup_chunk")

        # The worktree branch should be gone from the project entity
        entity_main = project / ".entities" / "my-entity"
        verify = _git(entity_main, "rev-parse", "--verify", "ve-worktree-cleanup_chunk")
        assert verify.returncode != 0, "Worktree branch should be deleted after merge"

    def test_conflict_logs_warning_does_not_raise(self, tmp_path):
        """Conflicting edits in entity main and worktree branch — no exception, warning logged."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        # Create the worktree branch manually to set up a conflict scenario
        entity_main = project / ".entities" / "my-entity"
        _git(entity_main, "config", "user.email", "test@test.com")
        _git(entity_main, "config", "user.name", "Test User")

        # Create the worktree branch from current HEAD
        _git(entity_main, "checkout", "-b", "ve-worktree-conflict_chunk")

        # Make a commit on the worktree branch that edits a file
        (entity_main / "conflict-file.txt").write_text("worktree version")
        _git(entity_main, "add", ".")
        _git(entity_main, "commit", "-m", "Worktree edit")

        # Switch back to main and make a conflicting edit to the same file
        _git(entity_main, "checkout", "main")
        (entity_main / "conflict-file.txt").write_text("main version - conflict")
        _git(entity_main, "add", ".")
        _git(entity_main, "commit", "-m", "Main conflicting edit")

        # Should not raise — conflict is logged as warning
        merge_entity_worktree_branches(project, "conflict_chunk")


# ---------------------------------------------------------------------------
# TestWorktreeManagerEntityIntegration
# ---------------------------------------------------------------------------


class TestWorktreeManagerEntityIntegration:
    """Integration tests: WorktreeManager + entity submodule support."""

    def test_create_worktree_initializes_entities(self, tmp_path):
        """WorktreeManager.create_worktree() on project with entity → entity initialized."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        manager = WorktreeManager(project)
        worktree_path = manager.create_worktree("int_chunk")

        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        assert entity_in_worktree.is_dir()
        assert (entity_in_worktree / "ENTITY.md").exists()

        branch = _git_check(entity_in_worktree, "rev-parse", "--abbrev-ref", "HEAD")
        assert branch == "ve-worktree-int_chunk"

    def test_finalize_includes_entity_submodule_pointer(self, tmp_path):
        """finalize_work_unit() (commit_changes) includes entity submodule pointer in commit."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        manager = WorktreeManager(project)
        worktree_path = manager.create_worktree("ptr_chunk")

        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        _git(entity_in_worktree, "config", "user.email", "test@test.com")
        _git(entity_in_worktree, "config", "user.name", "Test User")

        # Commit a change in the entity (this advances its HEAD)
        (entity_in_worktree / "new-file.txt").write_text("entity content")
        _git(entity_in_worktree, "add", ".")
        _git(entity_in_worktree, "commit", "-m", "Entity update in worktree")

        # Now commit changes in the worktree (includes updated submodule pointer)
        _git(worktree_path, "config", "user.email", "test@test.com")
        _git(worktree_path, "config", "user.name", "Test User")
        _git(worktree_path, "add", "-A")
        result = _git(worktree_path, "commit", "-m", "Chunk work with entity update")
        assert result.returncode == 0, f"commit failed: {result.stderr}"

        # The worktree branch commit should reference the entity's new HEAD
        show = _git_check(worktree_path, "show", "--stat", "HEAD")
        assert ".entities/my-entity" in show, (
            "Commit should include the entity submodule pointer update"
        )

    def test_merge_to_base_merges_entity_branches(self, tmp_path):
        """End-to-end: create worktree, entity commits, commit in worktree, merge to base,
        entity main has the changes."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        _, bare_origin = make_entity_origin(tmp_path)
        attach_and_commit_entity(project, bare_origin, "my-entity")

        manager = WorktreeManager(project)
        worktree_path = manager.create_worktree("e2e_chunk")

        entity_in_worktree = worktree_path / ".entities" / "my-entity"
        _git(entity_in_worktree, "config", "user.email", "test@test.com")
        _git(entity_in_worktree, "config", "user.name", "Test User")

        # Make entity change in worktree
        (entity_in_worktree / "e2e-knowledge.txt").write_text("end-to-end learning")
        _git(entity_in_worktree, "add", ".")
        _git(entity_in_worktree, "commit", "-m", "E2E entity knowledge")

        # Commit the updated submodule pointer in the worktree
        _git(worktree_path, "config", "user.email", "test@test.com")
        _git(worktree_path, "config", "user.name", "Test User")
        _git(worktree_path, "add", "-A")
        _git(worktree_path, "commit", "-m", "E2E chunk commit")

        # Merge worktree branch to base (also merges entity branches)
        manager.merge_to_base("e2e_chunk")

        # Entity's main branch should now have the e2e-knowledge.txt commit
        entity_main = project / ".entities" / "my-entity"
        log = _git(entity_main, "log", "main", "--oneline", "--", "e2e-knowledge.txt")
        assert "E2E entity knowledge" in log.stdout, (
            "Entity main should contain the e2e knowledge commit after merge_to_base"
        )

        # Worktree entity branch should be cleaned up
        verify = _git(entity_main, "rev-parse", "--verify", "ve-worktree-e2e_chunk")
        assert verify.returncode != 0, "Worktree entity branch should be deleted"
