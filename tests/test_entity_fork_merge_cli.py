"""CLI integration tests for 've entity fork' and 've entity merge' commands.

# Chunk: docs/chunks/entity_fork_merge - fork/merge CLI integration tests
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.entity import entity
from entity_repo import create_entity_repo, fork_entity, is_entity_repo
import entity_merge
from conftest import make_ve_initialized_git_repo


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True,
    )


def _make_entity(parent: Path, name: str) -> Path:
    """Create an entity repo at parent/name.

    create_entity_repo(dest, name) creates dest/name, so pass parent directly.
    """
    entity_path = create_entity_repo(parent, name)
    _git(entity_path, "config", "user.email", "test@test.com")
    _git(entity_path, "config", "user.name", "Test User")
    return entity_path


def _setup_project_with_entity(tmp_path: Path, name: str = "my-entity") -> tuple[Path, Path]:
    """Create a project directory with an entity in .entities/<name>/.

    Returns (project_dir, entity_path).
    """
    project = tmp_path / "project"
    make_ve_initialized_git_repo(project)
    entities_dir = project / ".entities"
    entities_dir.mkdir()
    entity_path = _make_entity(entities_dir, name)
    return project, entity_path


# ---------------------------------------------------------------------------
# Fork CLI tests
# ---------------------------------------------------------------------------


class TestForkCLI:
    def test_fork_command_creates_entity_in_entities_dir(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        runner = CliRunner()

        result = runner.invoke(entity, [
            "fork", "original", "my-fork",
            "--project-dir", str(project),
        ])

        assert result.exit_code == 0, result.output
        assert is_entity_repo(project / ".entities" / "my-fork")

    def test_fork_command_exit_code_0(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        runner = CliRunner()

        result = runner.invoke(entity, [
            "fork", "original", "my-fork",
            "--project-dir", str(project),
        ])

        assert result.exit_code == 0

    def test_fork_command_output_contains_new_name(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        runner = CliRunner()

        result = runner.invoke(entity, [
            "fork", "original", "my-fork",
            "--project-dir", str(project),
        ])

        assert "my-fork" in result.output

    def test_fork_command_fails_on_unknown_entity(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        runner = CliRunner()

        result = runner.invoke(entity, [
            "fork", "nonexistent", "my-fork",
            "--project-dir", str(project),
        ])

        assert result.exit_code != 0

    def test_fork_with_output_dir(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        custom_output = tmp_path / "custom-output"
        custom_output.mkdir()
        runner = CliRunner()

        result = runner.invoke(entity, [
            "fork", "original", "my-fork",
            "--project-dir", str(project),
            "--output-dir", str(custom_output),
        ])

        assert result.exit_code == 0, result.output
        assert is_entity_repo(custom_output / "my-fork")


# ---------------------------------------------------------------------------
# Merge CLI tests
# ---------------------------------------------------------------------------


class TestMergeCLI:
    def _setup_clean_merge(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Set up target + source with a new wiki page in source only.

        Source is forked from target so they share history — clean merge.
        Returns (project_dir, target_path, source_path).
        """
        from entity_repo import fork_entity

        project, target = _setup_project_with_entity(tmp_path, "target-entity")

        # Fork target to create source with shared history
        fork_dir = tmp_path / "forks"
        fork_result = fork_entity(target, fork_dir, "source-entity")
        source = fork_result.dest_path
        _git(source, "config", "user.email", "test@test.com")
        _git(source, "config", "user.name", "Test User")

        # Add new wiki page to source only
        wiki_dir = source / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "newpage.md").write_text("# New Knowledge\n\nFrom source.\n")
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "Add new knowledge")

        return project, target, source

    def test_merge_clean_exits_0(self, tmp_path):
        project, target, source = self._setup_clean_merge(tmp_path)
        runner = CliRunner()

        result = runner.invoke(entity, [
            "merge", "target-entity", str(source),
            "--project-dir", str(project),
        ])

        assert result.exit_code == 0, result.output

    def test_merge_clean_output_shows_summary(self, tmp_path):
        project, target, source = self._setup_clean_merge(tmp_path)
        runner = CliRunner()

        result = runner.invoke(entity, [
            "merge", "target-entity", str(source),
            "--project-dir", str(project),
        ])

        # Should mention merged commits or pages
        assert "Merged" in result.output or "up to date" in result.output.lower()

    def test_merge_conflicts_with_yes_flag_commits(self, tmp_path):
        """With --yes flag, LLM resolutions are auto-approved and committed."""
        # Set up conflicting entities
        project, target = _setup_project_with_entity(tmp_path, "target-entity")
        source_dir = tmp_path / "source-entity"

        # Give both entities a conflicting wiki page
        wiki_dir = target / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "shared.md").write_text("# Shared\n\nTarget knowledge.\n")
        _git(target, "add", "-A")
        _git(target, "commit", "-m", "Target knowledge")

        # Create source from scratch with the same file but different content
        source = create_entity_repo(source_dir, "source-entity")
        _git(source, "config", "user.email", "test@test.com")
        _git(source, "config", "user.name", "Test User")
        wiki_dir_s = source / "wiki" / "domain"
        wiki_dir_s.mkdir(parents=True, exist_ok=True)
        (wiki_dir_s / "shared.md").write_text("# Shared\n\nSource knowledge.\n")
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "Source knowledge")

        runner = CliRunner()
        synthesized = "# Shared\n\nBoth knowledge merged.\n"

        with patch.object(entity_merge, "ClaudeSDKClient", None):
            with patch.object(entity_merge, "anthropic", MagicMock()) as mock_anthropic:
                mock_msg = MagicMock()
                mock_msg.content = [MagicMock(text=synthesized)]
                mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

                result = runner.invoke(entity, [
                    "merge", "target-entity", str(source),
                    "--yes",
                    "--project-dir", str(project),
                ])

        # Should succeed (either clean merge or conflicts auto-approved)
        # exit code 0 means it completed
        assert result.exit_code == 0, result.output

    def test_merge_unknown_entity_fails(self, tmp_path):
        project, _ = _setup_project_with_entity(tmp_path, "original")
        runner = CliRunner()

        result = runner.invoke(entity, [
            "merge", "nonexistent", "/some/source",
            "--project-dir", str(project),
        ])

        assert result.exit_code != 0

    def test_merge_resolves_attached_entity_by_name(self, tmp_path):
        """When source matches an entity name in .entities/, resolve it by path."""
        from entity_repo import fork_entity

        project, target = _setup_project_with_entity(tmp_path, "target-entity")

        # Fork target to create a source entity in .entities/ (shared history)
        entities_dir = project / ".entities"
        fork_result = fork_entity(target, entities_dir, "source-entity")
        source_in_entities = fork_result.dest_path
        _git(source_in_entities, "config", "user.email", "test@test.com")
        _git(source_in_entities, "config", "user.name", "Test User")

        # Add new content to source only
        (source_in_entities / "wiki" / "domain" / "extra.md").write_text("Extra knowledge.")
        _git(source_in_entities, "add", "-A")
        _git(source_in_entities, "commit", "-m", "Extra")

        runner = CliRunner()

        # Use entity name (not path) as source
        result = runner.invoke(entity, [
            "merge", "target-entity", "source-entity",
            "--project-dir", str(project),
        ])

        # Should not fail with "repository not found" — should resolve by name
        assert result.exit_code == 0, result.output

    def test_merge_cli_without_source_uses_remote(self, tmp_path):
        """ve entity merge <name> (no SOURCE) merges from the configured origin."""
        import subprocess as _subprocess
        from entity_repo import create_entity_repo, fork_entity

        # Build: entity with a bare origin that has a new commit
        project, target = _setup_project_with_entity(tmp_path, "target-entity")
        target_dir = project / ".entities" / "target-entity"

        # Create bare origin from target
        bare_origin = tmp_path / "origin.git"
        _subprocess.run(
            ["git", "clone", "--bare", str(target_dir), str(bare_origin)],
            capture_output=True, text=True,
        )
        _git(target_dir, "remote", "add", "origin", str(bare_origin))
        _git(target_dir, "push", "origin", "main")

        # Clone origin and push a new commit
        second_clone = tmp_path / "second"
        _subprocess.run(
            ["git", "clone", str(bare_origin), str(second_clone)],
            capture_output=True, text=True,
            env={**__import__("os").environ,
                 "GIT_CONFIG_COUNT": "1",
                 "GIT_CONFIG_KEY_0": "protocol.file.allow",
                 "GIT_CONFIG_VALUE_0": "always"},
        )
        _git(second_clone, "config", "user.email", "other@test.com")
        _git(second_clone, "config", "user.name", "Other User")
        wiki_dir = second_clone / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "new_page.md").write_text("# New Knowledge\n")
        _git(second_clone, "add", "-A")
        _git(second_clone, "commit", "-m", "Add new knowledge")
        _git(second_clone, "push", "origin", "main")

        runner = CliRunner()
        result = runner.invoke(entity, [
            "merge", "target-entity",
            "--project-dir", str(project),
        ])

        assert result.exit_code == 0, result.output
        assert any(word in result.output.lower() for word in ("merged", "up to date"))

    def test_merge_cli_without_source_no_remote_fails(self, tmp_path):
        """ve entity merge <name> (no SOURCE) fails when no origin is configured."""
        project, _ = _setup_project_with_entity(tmp_path, "target-entity")

        runner = CliRunner()
        result = runner.invoke(entity, [
            "merge", "target-entity",
            "--project-dir", str(project),
        ])

        assert result.exit_code != 0
        assert any(word in result.output.lower() for word in ("origin", "remote"))
