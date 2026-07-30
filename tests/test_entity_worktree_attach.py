"""Tests for worktree-based entity attach/detach.

# Chunk: docs/chunks/entity_worktree_attach - Worktree-based attach/detach
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cli.canonical_clone import CanonicalCloneError
from cli.entity_worktree import (
    AttachResult,
    WorktreeAttachError,
    attach_branch_name,
    do_attach,
    do_detach,
    project_slug,
)
from entity_repo import create_entity_repo
from conftest import make_ve_initialized_git_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True,
    )


def _write_config(tmp_path: Path, *, entities_dir: Path, git_base: str) -> Path:
    cfg = tmp_path / "ve-config.toml"
    cfg.write_text(
        f'entities_dir = "{entities_dir}"\n'
        f'git_base = "{git_base}"\n'
    )
    return cfg


def _make_bare_origin(tmp_path: Path, name: str) -> Path:
    """Create a bare git repo at <tmp_path>/<name>.git with one commit + 'main'."""
    src = tmp_path / f"{name}-src"
    src.mkdir()
    _git(src, "init", "-b", "main")
    _git(src, "config", "user.email", "test@test.com")
    _git(src, "config", "user.name", "Test User")
    (src / "ENTITY.md").write_text("---\nname: " + name + "\n---\n")
    _git(src, "add", ".")
    _git(src, "commit", "-m", "seed")

    bare = tmp_path / f"{name}.git"
    result = subprocess.run(
        ["git", "clone", "--bare", str(src), str(bare)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return bare


def _seed_canonical_clone(
    entities_dir: Path, name: str, bare_origin: Path,
) -> Path:
    """Pre-seed entities_dir/<name> by cloning bare_origin. Mimics what
    ensure_canonical_clone would do without the test having to set up
    the full operator config.
    """
    entities_dir.mkdir(parents=True, exist_ok=True)
    canonical = entities_dir / name
    result = subprocess.run(
        ["git", "clone", str(bare_origin), str(canonical)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    _git(canonical, "config", "user.email", "test@test.com")
    _git(canonical, "config", "user.name", "Test User")
    return canonical


# ---------------------------------------------------------------------------
# project_slug / attach_branch_name
# ---------------------------------------------------------------------------


def test_project_slug_lowercases_and_dashes(tmp_path):
    """Slug derived from basename: lowercased, alnum runs collapsed to dashes."""
    assert project_slug(Path("/Users/x/Projects/vibe-engineer")) == "vibe-engineer"
    assert project_slug(Path("/var/tmp/Foo Bar 1.2")) == "foo-bar-1-2"
    assert project_slug(Path("/tmp/_internal_")) == "internal"
    assert project_slug(Path("/tmp/UPPER")) == "upper"


def test_project_slug_rejects_empty(tmp_path):
    """An all-punctuation basename yields an empty slug → ValueError."""
    with pytest.raises(ValueError):
        project_slug(Path("/tmp/!!!"))


def test_attach_branch_name_uses_ve_attach_prefix(tmp_path):
    """attach_branch_name combines the prefix and the slug."""
    assert attach_branch_name(Path("/tmp/my-proj")) == "ve-attach/my-proj"


# ---------------------------------------------------------------------------
# do_attach happy paths
# ---------------------------------------------------------------------------


def test_attach_fresh_canonical_clone_present(tmp_path):
    """When the canonical clone already exists, attach makes a worktree of it."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")

    entities_dir = tmp_path / "Entities"
    _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    result = do_attach("my-entity", project, config_path=cfg)

    assert isinstance(result, AttachResult)
    assert result.already_attached is False
    assert result.entity_path == project / ".entities" / "my-entity"
    assert result.entity_path.is_dir()
    # Worktree marker: .git is a file (not a directory)
    git_marker = result.entity_path / ".git"
    assert git_marker.is_file()
    gitdir_line = git_marker.read_text().splitlines()[0]
    assert gitdir_line.startswith("gitdir:")
    # Branch is project-scoped
    assert result.branch == "ve-attach/project"
    # The worktree's HEAD is the new branch
    current = _git(result.entity_path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    assert current == "ve-attach/project"


def test_attach_invokes_canonical_clone_helper(tmp_path):
    """When the canonical clone is missing, attach composes ensure_canonical_clone."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_origin(origin, "my-entity")  # <origin>/my-entity.git

    entities_dir = tmp_path / "Entities"
    # Do NOT seed the canonical clone — let ensure_canonical_clone do it.
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    result = do_attach("my-entity", project, config_path=cfg)

    assert (entities_dir / "my-entity" / ".git").exists()
    assert result.entity_path.is_dir()
    assert (result.entity_path / ".git").is_file()


def test_attach_idempotent_no_op(tmp_path):
    """Re-attaching the same entity to the same project is an idempotent no-op."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    first = do_attach("my-entity", project, config_path=cfg)
    assert first.already_attached is False

    second = do_attach("my-entity", project, config_path=cfg)
    assert second.already_attached is True
    assert second.entity_path == first.entity_path
    assert second.branch == first.branch


def test_attach_refuses_existing_plain_directory(tmp_path):
    """A pre-existing non-worktree at .entities/<name> raises WorktreeAttachError."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    # Stash a stray directory where the worktree would land.
    stray = project / ".entities" / "my-entity"
    stray.mkdir(parents=True)
    (stray / "notes.txt").write_text("something")

    with pytest.raises(WorktreeAttachError) as exc:
        do_attach("my-entity", project, config_path=cfg)
    assert "already exists" in str(exc.value)


def test_attach_refuses_non_git_project(tmp_path):
    """A non-git project_dir raises WorktreeAttachError before any clone work."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    non_git = tmp_path / "not-git"
    non_git.mkdir()

    with pytest.raises(WorktreeAttachError) as exc:
        do_attach("my-entity", non_git, config_path=cfg)
    assert "not a git repository" in str(exc.value)


def test_attach_canonical_clone_missing_repo_propagates(tmp_path):
    """When the bare origin doesn't exist, CanonicalCloneError propagates up."""
    origin = tmp_path / "origin"
    origin.mkdir()  # No bare repo inside
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    with pytest.raises(CanonicalCloneError):
        do_attach("my-entity", project, config_path=cfg)


# ---------------------------------------------------------------------------
# do_attach default-branch resolution
# ---------------------------------------------------------------------------


def test_attach_resolves_default_branch_via_origin_HEAD(tmp_path):
    """Attach picks the canonical clone's origin/HEAD as the base ref."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    canonical = _seed_canonical_clone(entities_dir, "my-entity", bare)
    # origin/HEAD should be set to main by the clone
    head = _git(canonical, "symbolic-ref", "refs/remotes/origin/HEAD").stdout.strip()
    assert head == "refs/remotes/origin/main"

    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    do_attach("my-entity", project, config_path=cfg)

    # Project-scoped branch should be based off main: its tip should match the
    # canonical clone's origin/main tip.
    proj_branch_sha = _git(
        canonical, "rev-parse", "ve-attach/project",
    ).stdout.strip()
    main_sha = _git(canonical, "rev-parse", "origin/main").stdout.strip()
    assert proj_branch_sha == main_sha


# ---------------------------------------------------------------------------
# do_detach
# ---------------------------------------------------------------------------


def test_detach_removes_worktree_and_branch(tmp_path):
    """Detach removes .entities/<name>, the project branch, but not the clone."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    canonical = _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    do_attach("my-entity", project, config_path=cfg)
    assert (project / ".entities" / "my-entity").exists()

    do_detach("my-entity", project, config_path=cfg)

    assert not (project / ".entities" / "my-entity").exists()
    # Canonical clone preserved
    assert canonical.is_dir()
    assert (canonical / ".git").is_dir()
    # Branch removed from canonical clone
    show = _git(
        canonical, "show-ref", "--verify", "--quiet",
        "refs/heads/ve-attach/project",
    )
    assert show.returncode != 0


def test_detach_refuses_uncommitted_without_force(tmp_path):
    """Detach refuses to remove a worktree with uncommitted changes."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    result = do_attach("my-entity", project, config_path=cfg)
    (result.entity_path / "dirty.txt").write_text("uncommitted")

    with pytest.raises(WorktreeAttachError) as exc:
        do_detach("my-entity", project, config_path=cfg)
    assert "uncommitted" in str(exc.value).lower()
    # Worktree still on disk
    assert result.entity_path.is_dir()


def test_detach_force_proceeds(tmp_path):
    """force=True detaches even with uncommitted changes."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    result = do_attach("my-entity", project, config_path=cfg)
    (result.entity_path / "dirty.txt").write_text("uncommitted")

    do_detach("my-entity", project, config_path=cfg, force=True)
    assert not result.entity_path.exists()


def test_detach_unattached_raises(tmp_path):
    """Detaching an entity that isn't attached raises WorktreeAttachError."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    with pytest.raises(WorktreeAttachError) as exc:
        do_detach("my-entity", project, config_path=cfg)
    assert "not attached" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Two-projects-same-entity (the headline narrative behavior)
# ---------------------------------------------------------------------------


def test_two_projects_share_canonical_clone(tmp_path):
    """Two projects can each attach the same entity simultaneously."""
    origin = tmp_path / "origin"
    origin.mkdir()
    bare = _make_bare_origin(origin, "my-entity")
    entities_dir = tmp_path / "Entities"
    canonical = _seed_canonical_clone(entities_dir, "my-entity", bare)
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))

    project_a = tmp_path / "proj-alpha"
    project_b = tmp_path / "proj-beta"
    make_ve_initialized_git_repo(project_a)
    make_ve_initialized_git_repo(project_b)

    r_a = do_attach("my-entity", project_a, config_path=cfg)
    r_b = do_attach("my-entity", project_b, config_path=cfg)

    # Both .entities/my-entity directories exist
    assert r_a.entity_path.is_dir()
    assert r_b.entity_path.is_dir()
    # Both share the same canonical clone
    assert r_a.canonical_clone == canonical == r_b.canonical_clone
    # Branches are distinct (project-scoped naming)
    assert r_a.branch == "ve-attach/proj-alpha"
    assert r_b.branch == "ve-attach/proj-beta"
    assert r_a.branch != r_b.branch

    # Detach project A leaves project B's worktree intact
    do_detach("my-entity", project_a, config_path=cfg)
    assert not r_a.entity_path.exists()
    assert r_b.entity_path.is_dir()
    # And canonical clone still has B's branch
    show = _git(
        canonical, "show-ref", "--verify", "--quiet",
        "refs/heads/ve-attach/proj-beta",
    )
    assert show.returncode == 0
