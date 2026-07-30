"""CLI tests for `ve entity attach` / `ve entity detach` / `ve entity list`
on the worktree-based attach pathway.

# Chunk: docs/chunks/entity_worktree_attach - CLI surfaces for worktree attach/detach
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.entity import entity
from conftest import make_ve_initialized_git_repo


# ---------------------------------------------------------------------------
# Helpers (mirror test_entity_worktree_attach.py)
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
    src = tmp_path / f"{name}-src"
    src.mkdir()
    _git(src, "init", "-b", "main")
    _git(src, "config", "user.email", "test@test.com")
    _git(src, "config", "user.name", "Test User")
    (src / "ENTITY.md").write_text("---\nname: " + name + "\n---\n")
    _git(src, "add", ".")
    _git(src, "commit", "-m", "seed")

    bare = tmp_path / f"{name}.git"
    subprocess.run(
        ["git", "clone", "--bare", str(src), str(bare)],
        capture_output=True, text=True, check=True,
    )
    return bare


def _setup(tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path]:
    """Return (project_dir, config_path) with origin bare repo in place."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_origin(origin, name)
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    return project, cfg


# ---------------------------------------------------------------------------
# `ve entity attach`
# ---------------------------------------------------------------------------


class TestAttachCLI:
    def test_attach_happy_path(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert (project / ".entities" / "my-entity").is_dir()
        assert (project / ".entities" / "my-entity" / ".git").is_file()
        assert "my-entity" in result.output
        assert "Branch" in result.output

    def test_attach_missing_repo_friendly_error(self, tmp_path):
        # git_base points at an empty directory → repo not found
        origin = tmp_path / "origin"
        origin.mkdir()
        entities_dir = tmp_path / "Entities"
        cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", "ghost",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert result.exit_code != 0
        # Either the friendly "No repository" message or the helper's missing
        # remote repo message — both should mention the entity or URL.
        assert "ghost" in result.output

    def test_attach_already_attached_is_friendly(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        first = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert first.exit_code == 0, first.output

        second = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert second.exit_code == 0, second.output
        assert "already attached" in second.output.lower()


# ---------------------------------------------------------------------------
# `ve entity detach`
# ---------------------------------------------------------------------------


class TestDetachCLI:
    def test_detach_happy_path(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        attach_result = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert attach_result.exit_code == 0, attach_result.output

        result = runner.invoke(
            entity,
            ["detach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert not (project / ".entities" / "my-entity").exists()
        assert "my-entity" in result.output

    def test_detach_uncommitted_without_force_exits_nonzero(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        attach_result = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert attach_result.exit_code == 0, attach_result.output

        # Dirty the worktree
        (project / ".entities" / "my-entity" / "dirty.txt").write_text("x")

        result = runner.invoke(
            entity,
            ["detach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert result.exit_code != 0
        assert "uncommitted" in result.output.lower()

    def test_detach_force_succeeds_with_uncommitted(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        attach_result = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert attach_result.exit_code == 0
        (project / ".entities" / "my-entity" / "dirty.txt").write_text("x")

        result = runner.invoke(
            entity,
            ["detach", "my-entity", "--force",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert not (project / ".entities" / "my-entity").exists()


# ---------------------------------------------------------------------------
# `ve entity list`
# ---------------------------------------------------------------------------


class TestListCLI:
    def test_list_shows_worktree_attached_entity(self, tmp_path):
        project, cfg = _setup(tmp_path)
        runner = CliRunner()
        attach_result = runner.invoke(
            entity,
            ["attach", "my-entity",
             "--config", str(cfg),
             "--project-dir", str(project)],
        )
        assert attach_result.exit_code == 0, attach_result.output

        result = runner.invoke(
            entity,
            ["list", "--project-dir", str(project)],
        )
        assert result.exit_code == 0, result.output
        assert "my-entity" in result.output

    def test_list_empty_when_no_entities(self, tmp_path):
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        runner = CliRunner()
        result = runner.invoke(entity, ["list", "--project-dir", str(project)])
        assert result.exit_code == 0, result.output
        assert "No entities found" in result.output
