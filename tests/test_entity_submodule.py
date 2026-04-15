"""Tests for entity submodule operations: attach, detach, list.

# Chunk: docs/chunks/entity_attach_detach - Submodule lifecycle tests
"""

import subprocess
from pathlib import Path

import pytest

from entity_repo import (
    AttachedEntityInfo,
    attach_entity,
    create_entity_repo,
    detach_entity,
    is_entity_repo,
    list_attached_entities,
)
from conftest import make_ve_initialized_git_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in the given path."""
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
    )


def make_entity_origin(tmp_path: Path) -> tuple[Path, Path]:
    """Create an entity repo and a bare clone to simulate a hosted origin.

    Returns:
        (entity_src, bare_origin) where bare_origin is used as the URL in tests.
    """
    entity_src = create_entity_repo(tmp_path / "entity-src", "my-entity")
    # Configure git user on entity_src
    _git(entity_src, "config", "user.email", "test@test.com")
    _git(entity_src, "config", "user.name", "Test User")

    # Clone to bare repo
    bare_origin = tmp_path / "entity-origin.git"
    result = subprocess.run(
        ["git", "clone", "--bare", str(entity_src), str(bare_origin)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"bare clone failed: {result.stderr}"

    # Point entity_src origin at the bare clone
    _git(entity_src, "remote", "add", "origin", str(bare_origin))

    return entity_src, bare_origin


# ---------------------------------------------------------------------------
# TestAttachEntity
# ---------------------------------------------------------------------------


class TestAttachEntity:
    """Tests for attach_entity()."""

    def test_attach_clones_into_entities_dir(self, tmp_path):
        """After attach, .entities/<name>/ exists and is_entity_repo returns True."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        attach_entity(project, str(bare_origin), "my-entity")

        entity_path = project / ".entities" / "my-entity"
        assert entity_path.is_dir()
        assert is_entity_repo(entity_path)

    def test_attach_creates_entities_dir_if_missing(self, tmp_path):
        """attach_entity works even if .entities/ doesn't exist yet."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        # Ensure .entities/ does not exist
        assert not (project / ".entities").exists()

        attach_entity(project, str(bare_origin), "my-entity")

        assert (project / ".entities").is_dir()
        assert (project / ".entities" / "my-entity").is_dir()

    def test_attach_returns_correct_path(self, tmp_path):
        """Return value is project/.entities/<name>."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        result = attach_entity(project, str(bare_origin), "my-entity")

        assert result == project / ".entities" / "my-entity"

    def test_attach_registers_submodule(self, tmp_path):
        """.gitmodules exists after attach and contains the URL."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        attach_entity(project, str(bare_origin), "my-entity")

        gitmodules = project / ".gitmodules"
        assert gitmodules.exists()
        content = gitmodules.read_text()
        assert str(bare_origin) in content

    def test_attach_rejects_non_git_project(self, tmp_path):
        """Raises RuntimeError if project_dir has no .git."""
        _, bare_origin = make_entity_origin(tmp_path)
        non_git = tmp_path / "not-a-git-repo"
        non_git.mkdir()

        with pytest.raises(RuntimeError, match="not a git repository"):
            attach_entity(non_git, str(bare_origin), "my-entity")

    def test_attach_rejects_non_entity_repo(self, tmp_path):
        """Raises ValueError if the cloned repo lacks ENTITY.md."""
        # Create a plain git repo (not an entity repo)
        plain_repo = tmp_path / "plain-repo"
        plain_repo.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=plain_repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=plain_repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=plain_repo, capture_output=True)
        (plain_repo / "README.md").write_text("# Not an entity\n")
        subprocess.run(["git", "add", "."], cwd=plain_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=plain_repo, capture_output=True)

        # Clone to bare
        bare_plain = tmp_path / "plain-origin.git"
        subprocess.run(
            ["git", "clone", "--bare", str(plain_repo), str(bare_plain)],
            capture_output=True,
        )

        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        with pytest.raises(ValueError, match="missing ENTITY.md"):
            attach_entity(project, str(bare_plain), "not-entity")

    def test_attach_with_local_path_url(self, tmp_path):
        """Accepts a local path string as the URL."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        # Pass local path as string
        result = attach_entity(project, str(bare_origin), "local-entity")

        assert result == project / ".entities" / "local-entity"
        assert is_entity_repo(result)


# ---------------------------------------------------------------------------
# TestDetachEntity
# ---------------------------------------------------------------------------


class TestDetachEntity:
    """Tests for detach_entity()."""

    def _attach(self, tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path]:
        """Helper: create project with attached entity, return (project, entity_path)."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), name)
        # Commit .gitmodules so the index is clean
        _git(project, "add", ".gitmodules", f".entities/{name}")
        _git(project, "commit", "-m", f"Add {name} submodule")
        return project, project / ".entities" / name

    def test_detach_removes_entities_dir(self, tmp_path):
        """After detach, .entities/<name>/ no longer exists."""
        project, entity_path = self._attach(tmp_path)

        detach_entity(project, "my-entity")

        assert not entity_path.exists()

    def test_detach_removes_from_gitmodules(self, tmp_path):
        """After detach, .gitmodules no longer references the submodule."""
        project, _ = self._attach(tmp_path)

        detach_entity(project, "my-entity")

        gitmodules = project / ".gitmodules"
        if gitmodules.exists():
            content = gitmodules.read_text()
            assert "my-entity" not in content

    def test_detach_refuses_uncommitted_changes(self, tmp_path):
        """Raises RuntimeError when submodule has uncommitted changes and force=False."""
        project, entity_path = self._attach(tmp_path)

        # Write an untracked file in the entity
        (entity_path / "new_file.txt").write_text("uncommitted")

        with pytest.raises(RuntimeError, match="uncommitted changes"):
            detach_entity(project, "my-entity", force=False)

    def test_detach_force_proceeds_with_uncommitted_changes(self, tmp_path):
        """With force=True, detach succeeds even with uncommitted changes."""
        project, entity_path = self._attach(tmp_path)

        # Write an untracked file in the entity
        (entity_path / "new_file.txt").write_text("uncommitted")

        # Should not raise
        detach_entity(project, "my-entity", force=True)

        assert not entity_path.exists()

    def test_detach_raises_if_entity_not_found(self, tmp_path):
        """Raises ValueError when .entities/<name>/ doesn't exist."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        with pytest.raises(ValueError, match="not found"):
            detach_entity(project, "nonexistent")


# ---------------------------------------------------------------------------
# TestListAttachedEntities
# ---------------------------------------------------------------------------


class TestListAttachedEntities:
    """Tests for list_attached_entities()."""

    def test_list_returns_empty_for_no_entities(self, tmp_path):
        """Returns [] when .entities/ is missing."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        result = list_attached_entities(project)

        assert result == []

    def test_list_returns_attached_entities(self, tmp_path):
        """After attaching two entities, list returns both with correct fields."""
        # Create two entity origins
        entity1_src = create_entity_repo(tmp_path / "e1-src", "alpha")
        bare1 = tmp_path / "alpha-origin.git"
        subprocess.run(["git", "clone", "--bare", str(entity1_src), str(bare1)], capture_output=True)

        entity2_src = create_entity_repo(tmp_path / "e2-src", "beta")
        bare2 = tmp_path / "beta-origin.git"
        subprocess.run(["git", "clone", "--bare", str(entity2_src), str(bare2)], capture_output=True)

        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        attach_entity(project, str(bare1), "alpha")
        attach_entity(project, str(bare2), "beta")

        entities = list_attached_entities(project)
        names = {e.name for e in entities}
        assert "alpha" in names
        assert "beta" in names

        alpha = next(e for e in entities if e.name == "alpha")
        assert alpha.remote_url is not None
        assert str(bare1) in alpha.remote_url

    def test_list_status_clean_for_fresh_attach(self, tmp_path):
        """Freshly attached entity has status 'clean'."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), "my-entity")

        entities = list_attached_entities(project)
        assert len(entities) == 1
        assert entities[0].status == "clean"

    def test_list_status_uncommitted_after_modification(self, tmp_path):
        """After writing a file in the submodule, status is 'uncommitted'."""
        _, bare_origin = make_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), "my-entity")

        # Write an untracked file in the entity
        entity_path = project / ".entities" / "my-entity"
        (entity_path / "dirty.txt").write_text("changes")

        entities = list_attached_entities(project)
        assert len(entities) == 1
        assert entities[0].status == "uncommitted"
