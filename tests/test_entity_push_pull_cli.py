"""CLI integration tests for entity push, pull, and set-origin commands.

# Chunk: docs/chunks/entity_push_pull - Push/pull/set-origin CLI integration tests
# Chunk: docs/chunks/entity_worktree_attach - Helpers rewritten to use worktree-based attach
"""

import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.entity import entity
from cli.entity_worktree import do_attach
from entity_repo import create_entity_repo
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


def _write_config(
    tmp_path: Path, *, entities_dir: Path, git_base: str,
) -> Path:
    """Write a temporary ve-config.toml. Caller passes config_path to attach."""
    cfg = tmp_path / "ve-config.toml"
    cfg.write_text(
        f'entities_dir = "{entities_dir}"\n'
        f'git_base = "{git_base}"\n'
    )
    return cfg


def make_entity_with_project(
    tmp_path: Path, name: str = "my-entity",
) -> tuple[Path, Path, Path]:
    """Create a project with an entity attached as a worktree, plus a bare origin.

    The canonical clone is attached as a worktree of a bare origin so push
    and pull both work end-to-end. The CLI is exercised here through ``do_attach``
    (with a per-test config) rather than ``ve entity attach`` because these
    tests target push/pull, not attach itself.

    Returns:
        (project_dir, entity_path, bare_origin)
    """
    # Create entity source and bare origin
    entity_src = create_entity_repo(tmp_path / f"{name}-src", name)
    _git(entity_src, "config", "user.email", "test@test.com")
    _git(entity_src, "config", "user.name", "Test User")

    bare_origin = tmp_path / f"{name}.git"
    result = subprocess.run(
        ["git", "clone", "--bare", str(entity_src), str(bare_origin)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"bare clone failed: {result.stderr}"

    # Operator config: git_base points at tmp_path so {git_base}/{name}.git
    # resolves to the bare_origin we just made.
    entities_dir = tmp_path / "Entities"
    cfg = _write_config(tmp_path, entities_dir=entities_dir, git_base=str(tmp_path))

    # Project repo
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)

    # Attach via worktree pathway
    result = do_attach(name, project, config_path=cfg)
    entity_path = result.entity_path

    # Configure the worktree's identity so commits work
    _git(entity_path, "config", "user.email", "test@test.com")
    _git(entity_path, "config", "user.name", "Test User")

    # The worktree-attached entity sits on a project-scoped local branch
    # (e.g. ve-attach/project) but the bare origin only has 'main'.
    # Configure tracking so push_entity/pull_entity resolve origin/main as
    # the upstream — matches the real-world deployment shape where every
    # project's worktree pushes to the entity's main.
    _git(entity_path, "branch", "--set-upstream-to=origin/main")

    return project, entity_path, bare_origin


def make_entity_submodule_no_origin(
    tmp_path: Path, name: str = "my-entity",
) -> tuple[Path, Path]:
    """Create project with a plain entity directory (no git remote).

    Legacy name retained to minimize test diffs — no submodule is involved.
    The entity is a standalone repo created in-place at .entities/<name>
    with no remote origin configured, which is the relevant state for
    "push without origin" / "set-origin then push" tests.

    Returns:
        (project_dir, entity_path)
    """
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    entities_dir = project / ".entities"
    entities_dir.mkdir()

    # Create entity directly in .entities/ (no attach, no remote)
    entity_path = create_entity_repo(entities_dir, name)
    _git(entity_path, "config", "user.email", "test@test.com")
    _git(entity_path, "config", "user.name", "Test User")

    return project, entity_path


# ---------------------------------------------------------------------------
# Tests for 've entity push <name>'
# ---------------------------------------------------------------------------


class TestPushCLI:
    """Tests for 'entity push' command."""

    def test_push_cli_succeeds_reports_commit_count(self, tmp_path):
        """Exit 0 and output mentions pushed commits."""
        project, entity_path, _ = make_entity_with_project(tmp_path)

        # Make a commit in the entity submodule
        (entity_path / "new_knowledge.txt").write_text("learned something")
        _git(entity_path, "add", "new_knowledge.txt")
        _git(entity_path, "commit", "-m", "Add knowledge")

        runner = CliRunner()
        result = runner.invoke(
            entity, ["push", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        # Output should mention commit(s) pushed or success
        assert any(word in result.output.lower() for word in ("pushed", "commit", "up to date"))

    def test_push_cli_warns_uncommitted_changes(self, tmp_path):
        """Warning present in output when entity has uncommitted changes, exits 0."""
        project, entity_path, _ = make_entity_with_project(tmp_path)

        # Commit something first so there's something to push, then dirty it
        (entity_path / "committed.txt").write_text("committed")
        _git(entity_path, "add", "committed.txt")
        _git(entity_path, "commit", "-m", "Committed file")

        # Now add untracked file (not committed)
        (entity_path / "dirty.txt").write_text("not committed")

        runner = CliRunner()
        result = runner.invoke(
            entity, ["push", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert "uncommitted" in result.output.lower() or "warning" in result.output.lower()

    def test_push_cli_error_no_remote(self, tmp_path):
        """Non-zero exit and error mentions remote/origin when entity has no remote."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            entity, ["push", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code != 0
        assert any(word in result.output.lower() for word in ("remote", "origin"))

    def test_push_cli_error_entity_not_found(self, tmp_path):
        """Non-zero exit when entity name doesn't exist."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity, ["push", "nonexistent", "--project-dir", str(project)]
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests for 've entity pull <name>'
# ---------------------------------------------------------------------------


class TestPullCLI:
    """Tests for 'entity pull' command."""

    def _setup_with_second_clone(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Set up project, attached entity, bare origin, and a second clone.

        The second clone can push new commits to origin that can then be pulled.

        Returns: (project, entity_path, second_clone)
        """
        project, entity_path, bare_origin = make_entity_with_project(tmp_path)

        # Push current entity state to origin's main branch. The worktree's
        # local branch is project-scoped (ve-attach/<project>), so push HEAD
        # explicitly to main rather than relying on a matching branch name.
        _git(entity_path, "push", "origin", "HEAD:main")

        # Create second clone for pushing new commits
        second_clone = tmp_path / "second-clone"
        subprocess.run(
            ["git", "clone", str(bare_origin), str(second_clone)],
            capture_output=True, text=True,
        )
        _git(second_clone, "config", "user.email", "other@test.com")
        _git(second_clone, "config", "user.name", "Other User")

        return project, entity_path, second_clone

    def test_pull_cli_fast_forward_reports_commits_merged(self, tmp_path):
        """Exit 0 and output mentions merged commits when pull fast-forwards."""
        project, entity_path, second_clone = self._setup_with_second_clone(tmp_path)

        # Push new commit from second clone
        (second_clone / "from_remote.txt").write_text("remote knowledge")
        _git(second_clone, "add", "from_remote.txt")
        _git(second_clone, "commit", "-m", "Remote commit")
        _git(second_clone, "push", "origin", "main")

        runner = CliRunner()
        result = runner.invoke(
            entity, ["pull", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert any(word in result.output.lower() for word in ("merged", "commit", "new"))

    def test_pull_cli_already_up_to_date(self, tmp_path):
        """Exit 0 and 'up to date' in output when nothing to pull."""
        project, entity_path, _ = self._setup_with_second_clone(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            entity, ["pull", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert "up to date" in result.output.lower()

    def test_pull_cli_diverged_auto_merges(self, tmp_path):
        """Exit 0 and output mentions merged/auto-merged on diverged histories."""
        project, entity_path, second_clone = self._setup_with_second_clone(tmp_path)

        # Push new commit from second clone
        (second_clone / "remote.txt").write_text("remote")
        _git(second_clone, "add", "remote.txt")
        _git(second_clone, "commit", "-m", "Remote commit")
        _git(second_clone, "push", "origin", "main")

        # Make local commit in entity (diverge)
        (entity_path / "local.txt").write_text("local")
        _git(entity_path, "add", "local.txt")
        _git(entity_path, "commit", "-m", "Local commit")

        runner = CliRunner()
        result = runner.invoke(
            entity, ["pull", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert any(word in result.output.lower() for word in ("merged", "auto-merged"))

    def test_pull_cli_error_no_remote(self, tmp_path):
        """Non-zero exit and error mentions remote when entity has no remote."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            entity, ["pull", "my-entity", "--project-dir", str(project)]
        )

        assert result.exit_code != 0
        assert any(word in result.output.lower() for word in ("remote", "origin"))

    def test_pull_cli_diverged_with_conflicts_prompts(self, tmp_path):
        """When diverged pull produces MergeConflictsPending, the conflict flow runs."""
        from unittest.mock import MagicMock, patch
        import entity_merge
        import entity_repo

        project, entity_path, _ = self._setup_with_second_clone(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[
                entity_repo.ConflictResolution(
                    relative_path="wiki/domain/shared.md",
                    synthesized="# Synthesized\n",
                    is_wiki=True,
                )
            ],
            unresolvable=[],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "commit_resolved_merge") as mock_commit:
                result = runner.invoke(
                    entity, ["pull", "my-entity", "--yes", "--project-dir", str(project)]
                )

        assert result.exit_code == 0, result.output
        mock_commit.assert_called_once()

    def test_pull_cli_yes_flag_auto_approves_conflicts(self, tmp_path):
        """With --yes, MergeConflictsPending is committed without prompting."""
        from unittest.mock import MagicMock, patch
        import entity_repo

        project, entity_path, _ = self._setup_with_second_clone(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[
                entity_repo.ConflictResolution(
                    relative_path="wiki/domain/page.md",
                    synthesized="# Page\n\nContent.\n",
                    is_wiki=True,
                )
            ],
            unresolvable=[],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "commit_resolved_merge") as mock_commit:
                result = runner.invoke(
                    entity, ["pull", "my-entity", "--yes", "--project-dir", str(project)]
                )

        # Should succeed and commit without user input
        assert result.exit_code == 0, result.output
        assert "conflict" in result.output.lower() or "resolved" in result.output.lower()
        mock_commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for 've entity set-origin <name> <url>'
# ---------------------------------------------------------------------------


class TestSetOriginCLI:
    """Tests for 'entity set-origin' command."""

    def test_set_origin_cli_configures_remote(self, tmp_path):
        """Exit 0 and git remote is set to the given URL."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)
        target_url = "https://github.com/org/entity-specialist.git"

        runner = CliRunner()
        result = runner.invoke(
            entity, ["set-origin", "my-entity", target_url, "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        remote_result = _git(entity_path, "remote", "get-url", "origin")
        assert remote_result.returncode == 0
        assert remote_result.stdout.strip() == target_url

    def test_set_origin_cli_replaces_existing_remote(self, tmp_path):
        """Second set-origin wins — second URL is the final remote URL."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)
        first_url = "https://github.com/org/entity-first.git"
        second_url = "https://github.com/org/entity-second.git"

        runner = CliRunner()
        runner.invoke(
            entity, ["set-origin", "my-entity", first_url, "--project-dir", str(project)]
        )
        result = runner.invoke(
            entity, ["set-origin", "my-entity", second_url, "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        remote_result = _git(entity_path, "remote", "get-url", "origin")
        assert remote_result.stdout.strip() == second_url

    def test_set_origin_cli_prints_confirmation(self, tmp_path):
        """Output includes entity name and the new URL."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)
        target_url = "https://github.com/org/entity-specialist.git"

        runner = CliRunner()
        result = runner.invoke(
            entity, ["set-origin", "my-entity", target_url, "--project-dir", str(project)]
        )

        assert result.exit_code == 0, result.output
        assert "my-entity" in result.output
        assert target_url in result.output

    def test_set_origin_cli_error_entity_not_found(self, tmp_path):
        """Non-zero exit when entity does not exist."""
        project = tmp_path / "project"
        make_ve_initialized_git_repo(project)

        runner = CliRunner()
        result = runner.invoke(
            entity,
            ["set-origin", "nonexistent", "https://github.com/org/entity.git",
             "--project-dir", str(project)]
        )

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests for pull conflict-resolution paths
# Chunk: docs/chunks/entity_merge_preserve_conflicts
# ---------------------------------------------------------------------------


class TestPullConflictResolution:
    """Tests for 'entity pull' conflict preservation behaviour."""

    def _make_project(self, tmp_path: Path) -> tuple[Path, Path]:
        """Return (project_dir, entity_path) for a simple entity-with-project."""
        project, entity_path = make_entity_submodule_no_origin(tmp_path)
        return project, entity_path

    def test_pull_zero_resolutions_preserves_merge_state(self, tmp_path):
        """When resolver returns no resolutions, abort_merge is NOT called; exit non-zero."""
        from unittest.mock import patch, MagicMock
        import entity_repo

        project, entity_path = self._make_project(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[],
            unresolvable=["wiki/log.md"],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "abort_merge") as mock_abort:
                result = runner.invoke(
                    entity, ["pull", "my-entity", "--project-dir", str(project)]
                )

        assert result.exit_code != 0
        mock_abort.assert_not_called()
        combined = result.output + (result.exception and str(result.exception) or "")
        assert "wiki/log.md" in combined or "wiki/log.md" in result.output

    def test_pull_zero_resolutions_shows_recovery_instructions(self, tmp_path):
        """Zero-resolutions path prints git add / git commit recovery guidance."""
        from unittest.mock import patch
        import entity_repo

        project, entity_path = self._make_project(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[],
            unresolvable=["wiki/conflict.md"],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "abort_merge"):
                result = runner.invoke(
                    entity, ["pull", "my-entity", "--project-dir", str(project)]
                )

        assert result.exit_code != 0
        # The output includes "git -C <path> add <files>" and "git -C <path> commit"
        assert "add" in result.output and "commit" in result.output

    def test_pull_mixed_resolutions_approved_stages_only_resolved(self, tmp_path):
        """Mixed path: apply_resolutions called, abort_merge NOT called, exit non-zero."""
        from unittest.mock import patch, MagicMock
        import entity_repo

        project, entity_path = self._make_project(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[
                entity_repo.ConflictResolution(
                    relative_path="wiki/domain/resolved.md",
                    synthesized="# Resolved\n",
                    is_wiki=True,
                )
            ],
            unresolvable=["wiki/domain/unresolvable.md"],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "apply_resolutions") as mock_apply:
                with patch.object(entity_repo, "commit_resolved_merge") as mock_commit:
                    with patch.object(entity_repo, "abort_merge") as mock_abort:
                        result = runner.invoke(
                            entity,
                            ["pull", "my-entity", "--yes", "--project-dir", str(project)],
                        )

        assert result.exit_code != 0
        mock_apply.assert_called_once()
        mock_commit.assert_not_called()
        mock_abort.assert_not_called()
        assert "wiki/domain/unresolvable.md" in result.output

    def test_pull_all_resolved_commits_and_exits_zero(self, tmp_path):
        """All-resolved path: commit_resolved_merge called, apply_resolutions NOT called."""
        from unittest.mock import patch
        import entity_repo

        project, entity_path = self._make_project(tmp_path)

        mock_pending = entity_repo.MergeConflictsPending(
            source=str(entity_path),
            resolutions=[
                entity_repo.ConflictResolution(
                    relative_path="wiki/domain/page.md",
                    synthesized="# Page\n",
                    is_wiki=True,
                ),
                entity_repo.ConflictResolution(
                    relative_path="wiki/domain/page2.md",
                    synthesized="# Page2\n",
                    is_wiki=True,
                ),
            ],
            unresolvable=[],
        )

        runner = CliRunner()
        with patch.object(entity_repo, "pull_entity", return_value=mock_pending):
            with patch.object(entity_repo, "commit_resolved_merge") as mock_commit:
                with patch.object(entity_repo, "apply_resolutions") as mock_apply:
                    result = runner.invoke(
                        entity,
                        ["pull", "my-entity", "--yes", "--project-dir", str(project)],
                    )

        assert result.exit_code == 0, result.output
        mock_commit.assert_called_once()
        mock_apply.assert_not_called()

    def test_pull_merge_in_progress_shows_recovery_message(self, tmp_path):
        """If merge is already in progress, pull shows recovery message without calling pull_entity."""
        from unittest.mock import patch
        import entity_repo

        project, entity_path = self._make_project(tmp_path)

        runner = CliRunner()
        with patch.object(entity_repo, "is_merge_in_progress", return_value=True):
            with patch.object(entity_repo, "pull_entity") as mock_pull:
                result = runner.invoke(
                    entity, ["pull", "my-entity", "--project-dir", str(project)]
                )

        assert result.exit_code != 0
        mock_pull.assert_not_called()
        assert "--abort" in result.output or "merge" in result.output.lower()
