"""Tests for `ve entity claude` auto-attach pathway.

# Chunk: docs/chunks/entity_claude_autoattach - Auto-clone + worktree-attach
# in front of the entity claude session lifecycle.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.canonical_clone import (
    AuthFailure,
    CanonicalCloneError,
    MissingRemoteRepo,
    NetworkFailure,
)
from cli.config import ConfigError
from cli.entity_claude import prepare_session_environment
from cli.entity_worktree import (
    WorktreeAttachError,
    do_attach,
    is_attached,
)
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
    """Create a bare git repo at <tmp_path>/<name>.git with one commit + 'main'."""
    src = tmp_path / f"{name}-src"
    src.mkdir()
    _git(src, "init", "-b", "main")
    _git(src, "config", "user.email", "test@test.com")
    _git(src, "config", "user.name", "Test User")
    (src / "ENTITY.md").write_text(f"---\nname: {name}\n---\n")
    _git(src, "add", ".")
    _git(src, "commit", "-m", "seed")

    bare = tmp_path / f"{name}.git"
    subprocess.run(
        ["git", "clone", "--bare", str(src), str(bare)],
        capture_output=True, text=True, check=True,
    )
    return bare


def _setup_origin_and_project(tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path, Path]:
    """Return (project_dir, config_path, entities_dir) with origin bare repo in place."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _make_bare_origin(origin, name)
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    return project, cfg, entities_dir


# ===========================================================================
# is_attached unit tests
# ===========================================================================


class TestIsAttached:
    def test_returns_true_when_attached(self, tmp_path):
        """After do_attach, is_attached returns True."""
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        do_attach("my-entity", project, config_path=cfg)
        assert is_attached("my-entity", project, config_path=cfg) is True

    def test_returns_false_when_entity_dir_absent(self, tmp_path):
        """No .entities/<name> directory → False."""
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        assert is_attached("my-entity", project, config_path=cfg) is False

    def test_returns_false_when_entity_dir_is_plain(self, tmp_path):
        """A plain directory (no .git marker) at .entities/<name> → False."""
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        stray = project / ".entities" / "my-entity"
        stray.mkdir(parents=True)
        (stray / "notes.txt").write_text("not a worktree")
        assert is_attached("my-entity", project, config_path=cfg) is False

    def test_returns_false_when_config_missing(self, tmp_path):
        """Missing config returns False rather than raising."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        nonexistent = tmp_path / "no-such-config.toml"
        assert is_attached("my-entity", project, config_path=nonexistent) is False


# ===========================================================================
# prepare_session_environment unit tests (real do_attach against bare repo)
# ===========================================================================


class TestPrepareSessionEnvironment:
    def test_silent_fast_path_when_already_attached(self, tmp_path, capsys):
        """When already attached, no output and no work."""
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        do_attach("my-entity", project, config_path=cfg)
        # Drain any prior captured output
        capsys.readouterr()

        # Now exercise the auto-attach pathway. It should be silent.
        with patch("cli.entity_claude.do_attach") as mock_do_attach:
            prepare_session_environment("my-entity", project, config_path=cfg)
            mock_do_attach.assert_not_called()
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_cold_start_emits_two_progress_lines(self, tmp_path, capsys):
        """When not attached, emit informative progress output before do_attach."""
        project, cfg, entities_dir = _setup_origin_and_project(tmp_path)
        assert not (entities_dir / "my-entity").exists()
        assert not (project / ".entities" / "my-entity").exists()

        prepare_session_environment("my-entity", project, config_path=cfg)

        captured = capsys.readouterr()
        # First line: Cloning, mentions name, URL, and destination.
        assert "Cloning" in captured.out
        assert "my-entity" in captured.out
        assert str(entities_dir / "my-entity") in captured.out
        # Second line: Attaching as worktree, mentions destination (relative
        # `.entities/<name>`) and branch.
        assert "Attaching as worktree at .entities/my-entity" in captured.out
        assert "ve-attach/project" in captured.out

        # And the actual side effects happened.
        assert (entities_dir / "my-entity" / ".git").exists()
        assert (project / ".entities" / "my-entity" / ".git").is_file()

    def test_legacy_plain_directory_bypasses_autoattach(self, tmp_path, capsys):
        """A pre-existing plain (non-worktree) .entities/<name> is left alone.

        Backward-compat: entities created by `ve entity create` before the
        worktree migration are plain directories. The auto-attach pathway
        must not try to clone over them. The user can detach (no-op) and
        re-attach explicitly if they want the new worktree shape.
        """
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        # Pre-existing plain directory (no .git marker).
        stray = project / ".entities" / "my-entity"
        stray.mkdir(parents=True)
        (stray / "notes.txt").write_text("legacy content")
        capsys.readouterr()  # drain

        with patch("cli.entity_claude.do_attach") as mock_do_attach:
            prepare_session_environment("my-entity", project, config_path=cfg)
            mock_do_attach.assert_not_called()

        captured = capsys.readouterr()
        assert captured.out == ""
        # Legacy content preserved.
        assert (stray / "notes.txt").read_text() == "legacy content"

    def test_already_cloned_but_not_attached(self, tmp_path, capsys):
        """When canonical clone exists but .entities/<name> doesn't, only attach happens."""
        project, cfg, entities_dir = _setup_origin_and_project(tmp_path)
        # Pre-seed the canonical clone by attaching to a different project,
        # then deleting that project's .entities to leave only the canonical.
        other_project = tmp_path / "other"
        make_ve_initialized_git_repo(other_project)
        do_attach("my-entity", other_project, config_path=cfg)
        assert (entities_dir / "my-entity" / ".git").exists()
        capsys.readouterr()  # drain

        # Now run prepare_session_environment for the original project.
        prepare_session_environment("my-entity", project, config_path=cfg)

        captured = capsys.readouterr()
        # Both progress lines still appear (the canonical-clone helper
        # short-circuits internally, but we don't know that ex ante).
        assert "Cloning" in captured.out
        assert "Attaching as worktree" in captured.out
        # Worktree was created for this project.
        assert (project / ".entities" / "my-entity" / ".git").is_file()

    @pytest.mark.parametrize("exc_class,exc_kwargs", [
        (AuthFailure, {"entity_name": "x", "clone_url": "git@example.com:org/x.git"}),
        (MissingRemoteRepo, {"entity_name": "x", "clone_url": "git@example.com:org/x.git"}),
        (NetworkFailure, {"entity_name": "x", "clone_url": "git@example.com:org/x.git"}),
        (CanonicalCloneError, {"entity_name": "x", "clone_url": "git@example.com:org/x.git"}),
    ])
    def test_clone_failure_propagates(self, tmp_path, exc_class, exc_kwargs):
        """All canonical-clone failure classes propagate unchanged."""
        project, cfg, _ = _setup_origin_and_project(tmp_path, name="x")

        with patch(
            "cli.entity_claude.do_attach",
            side_effect=exc_class("boom", **exc_kwargs),
        ):
            with pytest.raises(exc_class):
                prepare_session_environment("x", project, config_path=cfg)

    def test_worktree_attach_error_propagates(self, tmp_path):
        """WorktreeAttachError from do_attach propagates."""
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        with patch(
            "cli.entity_claude.do_attach",
            side_effect=WorktreeAttachError("worktree blew up"),
        ):
            with pytest.raises(WorktreeAttachError):
                prepare_session_environment("my-entity", project, config_path=cfg)

    def test_config_error_propagates(self, tmp_path):
        """Missing config raises ConfigError to the caller."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        nonexistent = tmp_path / "no-such-config.toml"
        with pytest.raises(ConfigError):
            prepare_session_environment("my-entity", project, config_path=nonexistent)


# ===========================================================================
# `ve entity claude` CLI integration tests
# ===========================================================================


def _patch_default_config(monkeypatch, cfg_path: Path) -> None:
    """Monkeypatch ``cli.config.DEFAULT_CONFIG_PATH`` so the CLI loads our
    test config without needing a `--config` flag.

    Note: ``cli.config`` (the package attribute) is the Click group, not the
    module. We resolve the module via ``sys.modules`` to monkeypatch the
    correct namespace.
    """
    import sys
    config_module = sys.modules["cli.config"]
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", cfg_path)


class TestClaudeCmdAutoAttachEndToEnd:
    def test_fresh_machine_path(self, tmp_path, monkeypatch):
        """End-to-end: no entities_dir, no canonical clone, no .entities — one
        invocation auto-clones, attaches, then reaches the session launch."""
        from ve import cli as ve_cli

        # Set up real bare origin BEFORE patching subprocess.Popen.
        origin = tmp_path / "origin"
        origin.mkdir()
        _make_bare_origin(origin, "my-entity")
        entities_dir = tmp_path / "Entities"
        assert not entities_dir.exists()
        cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(origin))
        _patch_default_config(monkeypatch, cfg)

        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        assert not (project / ".entities").exists()

        # Patch subprocess.Popen for the Claude session launch only. The
        # auto-attach pathway uses subprocess.run (which calls Popen internally
        # via context manager) so we patch Popen at the cli.entity layer
        # where claude_cmd invokes it. But cli.entity uses bare `subprocess.Popen`,
        # so we patch the global. Real git work in do_attach uses
        # subprocess.run directly, which constructs a fresh Popen — we have
        # to allow git's Popen through. The cleanest way is to side_effect
        # a callable that distinguishes claude from git.
        real_popen = subprocess.Popen
        claude_procs = []

        def selective_popen(*args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, (list, tuple)) and argv and argv[0] == "claude":
                proc = MagicMock()
                proc.pid = 1234 + len(claude_procs)
                proc.wait.return_value = 0
                claude_procs.append(proc)
                return proc
            return real_popen(*args, **kwargs)

        with patch("subprocess.Popen", side_effect=selective_popen), \
             patch("entities.Entities.archive_transcript", return_value=True), \
             patch("entities.Entities.append_session"), \
             patch("entity_shutdown._capture_baseline_ref", return_value=None), \
             patch(
                 "cli.entity._read_session_id_from_pid_file",
                 return_value="abc-session",
             ):
            runner = CliRunner()
            result = runner.invoke(
                ve_cli,
                [
                    "entity", "claude",
                    "--entity", "my-entity",
                    "--project-dir", str(project),
                ],
            )

        assert result.exit_code == 0, (
            f"exit={result.exit_code}\noutput={result.output}\nexc={result.exception}"
        )
        # Auto-clone produced the canonical clone.
        assert (entities_dir / "my-entity" / ".git").exists()
        # Auto-attach produced the worktree.
        assert (project / ".entities" / "my-entity" / ".git").is_file()
        # Progress output appeared in stdout.
        assert "Cloning my-entity" in result.output
        assert "Attaching as worktree" in result.output
        # Session launch was reached (claude proc was created).
        assert len(claude_procs) >= 1

    def test_already_attached_is_silent_for_autoattach(self, tmp_path, monkeypatch):
        """When entity is already attached, no Cloning/Attaching lines appear."""
        from ve import cli as ve_cli

        # Real setup (do_attach uses subprocess.run) before any Popen patching.
        project, cfg, _ = _setup_origin_and_project(tmp_path)
        _patch_default_config(monkeypatch, cfg)
        do_attach("my-entity", project, config_path=cfg)

        real_popen = subprocess.Popen
        claude_procs = []

        def selective_popen(*args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, (list, tuple)) and argv and argv[0] == "claude":
                proc = MagicMock()
                proc.pid = 1234 + len(claude_procs)
                proc.wait.return_value = 0
                claude_procs.append(proc)
                return proc
            return real_popen(*args, **kwargs)

        with patch("subprocess.Popen", side_effect=selective_popen), \
             patch("entities.Entities.archive_transcript", return_value=True), \
             patch("entities.Entities.append_session"), \
             patch("entity_shutdown._capture_baseline_ref", return_value=None), \
             patch(
                 "cli.entity._read_session_id_from_pid_file",
                 return_value="abc-session",
             ):
            runner = CliRunner()
            result = runner.invoke(
                ve_cli,
                [
                    "entity", "claude",
                    "--entity", "my-entity",
                    "--project-dir", str(project),
                ],
            )

        assert result.exit_code == 0, (
            f"exit={result.exit_code}\noutput={result.output}\nexc={result.exception}"
        )
        # Auto-attach output absent.
        assert "Cloning" not in result.output
        assert "Attaching as worktree" not in result.output
        # Session launch still reached.
        assert len(claude_procs) >= 1


class TestClaudeCmdAutoAttachFailures:
    """Each failure class aborts the command BEFORE the Claude session launches.

    We can't decorate with `@patch("subprocess.Popen")` because pytest sets up
    tmp_path before the patch lifts — but the test setup helpers
    (`_setup_origin_and_project`) need real subprocess.run to build a bare repo.
    Instead, each test creates its origin/project first, then patches Popen
    inside a `with` block to assert it was never called.
    """

    def _run_with_do_attach_failure(
        self, tmp_path, monkeypatch, *, exc, entity="my-entity",
    ):
        """Set up origin+project (real subprocess), patch Popen + do_attach,
        invoke `ve entity claude`, return the CliRunner result and the popen
        mock for assertions.
        """
        from ve import cli as ve_cli

        project, cfg, _ = _setup_origin_and_project(tmp_path)
        _patch_default_config(monkeypatch, cfg)

        with patch("subprocess.Popen") as mock_popen, \
             patch("cli.entity_claude.do_attach", side_effect=exc):
            runner = CliRunner()
            result = runner.invoke(
                ve_cli,
                [
                    "entity", "claude",
                    "--entity", entity,
                    "--project-dir", str(project),
                ],
            )
            return result, mock_popen

    def test_auth_failure_aborts_before_session(self, tmp_path, monkeypatch):
        result, mock_popen = self._run_with_do_attach_failure(
            tmp_path, monkeypatch,
            exc=AuthFailure(
                "auth denied",
                entity_name="my-entity",
                clone_url="git@example.com:org/my-entity.git",
            ),
        )
        assert result.exit_code != 0
        assert "uthentication failed" in result.output  # case-tolerant
        assert "credentials" in result.output.lower()
        mock_popen.assert_not_called()

    def test_missing_repo_aborts_before_session(self, tmp_path, monkeypatch):
        result, mock_popen = self._run_with_do_attach_failure(
            tmp_path, monkeypatch,
            entity="ghost",
            exc=MissingRemoteRepo(
                "404",
                entity_name="ghost",
                clone_url="git@example.com:org/ghost.git",
            ),
        )
        assert result.exit_code != 0
        assert "No repository" in result.output
        assert "ghost" in result.output
        # Hint at corrective action.
        assert "entity name" in result.output.lower() or "git_base" in result.output.lower()
        mock_popen.assert_not_called()

    def test_network_failure_aborts_before_session(self, tmp_path, monkeypatch):
        result, mock_popen = self._run_with_do_attach_failure(
            tmp_path, monkeypatch,
            exc=NetworkFailure(
                "dns blew up",
                entity_name="my-entity",
                clone_url="git@example.com:org/my-entity.git",
            ),
        )
        assert result.exit_code != 0
        assert "Network failure" in result.output
        assert "retry" in result.output.lower()
        mock_popen.assert_not_called()

    def test_missing_config_aborts_with_helpful_hint(self, tmp_path, monkeypatch):
        """Missing ~/.ve-config.toml surfaces with a hint pointing at the file."""
        from ve import cli as ve_cli

        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)
        nonexistent = tmp_path / "no-such-config.toml"
        _patch_default_config(monkeypatch, nonexistent)

        with patch("subprocess.Popen") as mock_popen:
            runner = CliRunner()
            result = runner.invoke(
                ve_cli,
                [
                    "entity", "claude",
                    "--entity", "my-entity",
                    "--project-dir", str(project),
                ],
            )

        assert result.exit_code != 0
        # The CLI message names the config path so the user can find it.
        assert str(nonexistent) in result.output or ".ve-config.toml" in result.output
        # Session was never launched.
        mock_popen.assert_not_called()

    def test_worktree_attach_error_aborts_before_session(self, tmp_path, monkeypatch):
        """Worktree-attach errors abort before the session launches."""
        result, mock_popen = self._run_with_do_attach_failure(
            tmp_path, monkeypatch,
            exc=WorktreeAttachError(
                "'.entities/my-entity' already exists but is not an attached worktree"
            ),
        )
        assert result.exit_code != 0
        assert "already exists" in result.output
        mock_popen.assert_not_called()
