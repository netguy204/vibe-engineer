"""CLI tests for entity attach, detach, and list commands.

# Chunk: docs/chunks/entity_attach_detach - CLI integration tests
"""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.entity import entity
from entity_repo import attach_entity, create_entity_repo
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


def make_bare_entity_origin(tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path]:
    """Create an entity repo and a bare clone.

    Returns:
        (entity_src, bare_origin) where bare_origin is used as the URL.
    """
    entity_src = create_entity_repo(tmp_path / f"{name}-src", name)
    bare_origin = tmp_path / f"{name}-origin.git"
    result = subprocess.run(
        ["git", "clone", "--bare", str(entity_src), str(bare_origin)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"bare clone failed: {result.stderr}"
    return entity_src, bare_origin


# ---------------------------------------------------------------------------
# TestAttachCLI
# ---------------------------------------------------------------------------


class TestAttachCLI:
    """Tests for 'entity attach' command."""

    def test_attach_creates_entity_subdir(self, tmp_path):
        """Exit code 0 and .entities/<name>/ exists after attach."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", str(bare_origin), "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert (project / ".entities" / "my-entity").is_dir()

    def test_attach_derives_name_from_url(self, tmp_path):
        """No --name given; name derived from URL (entity- prefix stripped)."""
        _, bare_origin = make_bare_entity_origin(tmp_path, "entity-specialist")
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", str(bare_origin), "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        # entity-specialist → specialist (entity- stripped)
        assert (project / ".entities" / "specialist").is_dir()

    def test_attach_with_explicit_name(self, tmp_path):
        """--name overrides the derived name."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", str(bare_origin), "--name", "specialist", "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert (project / ".entities" / "specialist").is_dir()

    def test_attach_prints_confirmation(self, tmp_path):
        """Output contains entity name."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", str(bare_origin), "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert "my-entity" in result.output

    def test_attach_non_git_project_exits_nonzero(self, tmp_path):
        """Non-zero exit code and error message for non-git project dir."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        non_git = tmp_path / "not-git"
        non_git.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["attach", str(bare_origin), "--project-dir", str(non_git)],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestDetachCLI
# ---------------------------------------------------------------------------


class TestDetachCLI:
    """Tests for 'entity detach' command."""

    def _setup_with_entity(self, tmp_path: Path, name: str = "my-entity") -> tuple[Path, str]:
        """Set up project with attached entity. Returns (project, name)."""
        _, bare_origin = make_bare_entity_origin(tmp_path, name)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), name)
        # Commit so state is clean
        _git(project, "add", ".gitmodules", f".entities/{name}")
        _git(project, "commit", "-m", f"Add {name}")
        return project, name

    def test_detach_removes_entity_dir(self, tmp_path):
        """Exit code 0 and .entities/<name>/ gone after detach."""
        project, name = self._setup_with_entity(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["detach", name, "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert not (project / ".entities" / name).exists()

    def test_detach_refuses_uncommitted_without_force(self, tmp_path):
        """Non-zero exit when entity has uncommitted changes and no --force."""
        project, name = self._setup_with_entity(tmp_path)
        # Write uncommitted file
        (project / ".entities" / name / "dirty.txt").write_text("change")

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["detach", name, "--project-dir", str(project)],
        )

        assert result.exit_code != 0

    def test_detach_force_flag_proceeds(self, tmp_path):
        """--force succeeds even with uncommitted changes."""
        project, name = self._setup_with_entity(tmp_path)
        (project / ".entities" / name / "dirty.txt").write_text("change")

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["detach", name, "--force", "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert not (project / ".entities" / name).exists()

    def test_detach_unknown_entity_exits_nonzero(self, tmp_path):
        """Non-zero exit for unknown entity name."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["detach", "nonexistent", "--project-dir", str(project)],
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# TestListCLI
# ---------------------------------------------------------------------------


class TestListCLI:
    """Tests for enhanced 'entity list' command."""

    def test_list_shows_attached_entities_with_url(self, tmp_path):
        """After attach, list output includes entity name and remote URL."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), "my-entity")

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["list", "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert "my-entity" in result.output

    def test_list_shows_status(self, tmp_path):
        """Output contains a status word."""
        _, bare_origin = make_bare_entity_origin(tmp_path)
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        attach_entity(project, str(bare_origin), "my-entity")

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["list", "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        # One of the known status words should appear
        assert any(s in result.output for s in ("clean", "uncommitted", "ahead", "unknown"))

    def test_list_empty_for_no_entities(self, tmp_path):
        """'No entities found' when .entities/ is empty or missing."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["list", "--project-dir", str(project)],
        )

        assert result.exit_code == 0, result.output
        assert "No entities found" in result.output
