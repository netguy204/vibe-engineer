"""Unit tests for fork_entity and merge_entity library functions.

# Chunk: docs/chunks/entity_fork_merge - fork/merge unit tests
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from entity_repo import (
    ConflictResolution,
    ForkResult,
    MergeConflictsPending,
    MergeResult,
    abort_merge,
    commit_resolved_merge,
    create_entity_repo,
    fork_entity,
    is_entity_repo,
    merge_entity,
    read_entity_metadata,
)
import entity_merge
from conftest import make_entity_with_origin, make_entity_no_origin


def _git(path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True,
    )


def _make_entity(tmp_path: Path, name: str = "my-entity") -> Path:
    entity_path = create_entity_repo(tmp_path / name, name)
    _git(entity_path, "config", "user.email", "test@test.com")
    _git(entity_path, "config", "user.name", "Test User")
    return entity_path


# ---------------------------------------------------------------------------
# TestForkEntity
# ---------------------------------------------------------------------------


class TestForkEntity:
    def test_fork_creates_independent_clone(self, tmp_path):
        source = _make_entity(tmp_path / "source")
        result = fork_entity(source, tmp_path / "forks", "my-fork")
        assert is_entity_repo(result.dest_path)

    def test_fork_preserves_full_history(self, tmp_path):
        source = _make_entity(tmp_path / "source")
        # Add an extra commit to source
        (source / "extra.txt").write_text("extra")
        _git(source, "add", "extra.txt")
        _git(source, "commit", "-m", "Extra commit")

        result = fork_entity(source, tmp_path / "forks", "my-fork")

        # Fork should have the same or more commits (full history + fork commit)
        source_commits = _git(source, "rev-list", "--count", "HEAD").stdout.strip()
        fork_commits = _git(result.dest_path, "rev-list", "--count", "HEAD").stdout.strip()
        # fork has source history + 1 fork metadata commit
        assert int(fork_commits) == int(source_commits) + 1

    def test_fork_updates_entity_name(self, tmp_path):
        source = _make_entity(tmp_path / "source", "original")
        result = fork_entity(source, tmp_path / "forks", "my-fork")
        metadata = read_entity_metadata(result.dest_path)
        assert metadata.name == "my-fork"

    def test_fork_records_forked_from(self, tmp_path):
        source = _make_entity(tmp_path / "source", "original")
        result = fork_entity(source, tmp_path / "forks", "my-fork")
        metadata = read_entity_metadata(result.dest_path)
        assert metadata.forked_from == "original"

    def test_fork_commit_message_contains_source(self, tmp_path):
        source = _make_entity(tmp_path / "source", "original")
        result = fork_entity(source, tmp_path / "forks", "my-fork")
        log = _git(result.dest_path, "log", "--oneline", "-1").stdout
        assert "Forked from" in log

    def test_fork_returns_fork_result(self, tmp_path):
        source = _make_entity(tmp_path / "source", "original")
        result = fork_entity(source, tmp_path / "forks", "my-fork")
        assert isinstance(result, ForkResult)
        assert result.source_name == "original"
        assert result.new_name == "my-fork"

    def test_fork_raises_if_source_not_entity_repo(self, tmp_path):
        not_entity = tmp_path / "not-entity"
        not_entity.mkdir()
        with pytest.raises(ValueError, match="[Ee]ntity"):
            fork_entity(not_entity, tmp_path / "forks", "my-fork")

    def test_fork_raises_if_dest_exists(self, tmp_path):
        source = _make_entity(tmp_path / "source")
        dest_dir = tmp_path / "forks"
        dest_dir.mkdir()
        (dest_dir / "my-fork").mkdir()  # pre-existing
        with pytest.raises(ValueError, match="[Ee]xists|already"):
            fork_entity(source, dest_dir, "my-fork")

    def test_fork_raises_if_invalid_name(self, tmp_path):
        source = _make_entity(tmp_path / "source")
        with pytest.raises(ValueError, match="[Ii]nvalid|[Nn]ame"):
            fork_entity(source, tmp_path / "forks", "Invalid Name")

    def test_fork_is_independent(self, tmp_path):
        source = _make_entity(tmp_path / "source", "original")
        result = fork_entity(source, tmp_path / "forks", "my-fork")

        # Add a commit to source after forking
        (source / "source_only.txt").write_text("source only")
        _git(source, "add", "source_only.txt")
        _git(source, "commit", "-m", "Source-only commit")

        # Fork should NOT have this file
        assert not (result.dest_path / "source_only.txt").exists()


# ---------------------------------------------------------------------------
# TestMergeEntityClean
# ---------------------------------------------------------------------------


class TestMergeEntityClean:
    def _setup_source_with_new_page(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create target and source entities where source has an extra wiki page.

        Source is forked from target so they share history — this ensures a
        clean merge (no unrelated histories conflict on shared template files).
        """
        target = _make_entity(tmp_path / "target", "target-entity")

        # Fork target to create source (shared history)
        fork_dir = tmp_path / "forks"
        fork_result = fork_entity(target, fork_dir, "source-entity")
        source = fork_result.dest_path
        _git(source, "config", "user.email", "test@test.com")
        _git(source, "config", "user.name", "Test User")

        # Add a new wiki page only in source
        wiki_dir = source / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "pagerduty.md").write_text("# PagerDuty\n\nKnowledge from source.")
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "Add PagerDuty knowledge")

        return target, source

    def test_clean_merge_integrates_new_pages(self, tmp_path):
        target, source = self._setup_source_with_new_page(tmp_path)
        merge_entity(target, str(source))
        assert (target / "wiki" / "domain" / "pagerduty.md").exists()

    def test_clean_merge_returns_merge_result(self, tmp_path):
        target, source = self._setup_source_with_new_page(tmp_path)
        result = merge_entity(target, str(source))
        assert isinstance(result, MergeResult)

    def test_clean_merge_commits_with_summary_message(self, tmp_path):
        target, source = self._setup_source_with_new_page(tmp_path)
        merge_entity(target, str(source))
        log = _git(target, "log", "--oneline", "-1").stdout
        assert "Merge learnings from" in log

    def test_clean_merge_counts_new_pages(self, tmp_path):
        target, source = self._setup_source_with_new_page(tmp_path)
        result = merge_entity(target, str(source))
        assert isinstance(result, MergeResult)
        assert result.new_pages >= 1

    def test_merge_raises_if_target_not_entity_repo(self, tmp_path):
        source = _make_entity(tmp_path / "source")
        not_entity = tmp_path / "not-entity"
        not_entity.mkdir()
        with pytest.raises(ValueError, match="[Ee]ntity"):
            merge_entity(not_entity, str(source))

    def test_merge_raises_if_dirty(self, tmp_path):
        target, source = self._setup_source_with_new_page(tmp_path)
        # Dirty the target
        (target / "dirty.txt").write_text("uncommitted")
        with pytest.raises(RuntimeError, match="[Uu]ncommitted|[Cc]hange"):
            merge_entity(target, str(source))


# ---------------------------------------------------------------------------
# TestMergeEntityWithConflicts
# ---------------------------------------------------------------------------


class TestMergeEntityWithConflicts:
    def _setup_conflicting_entities(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create target and source with conflicting edits to the same wiki page."""
        # Create base entity
        base = _make_entity(tmp_path / "base", "base-entity")
        wiki_dir = base / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "shared.md").write_text("# Shared\n\nOriginal content.\n")
        _git(base, "add", "-A")
        _git(base, "commit", "-m", "Add shared page")

        # Fork to create target
        target_dir = tmp_path / "entities"
        target_dir.mkdir()
        fork_result = fork_entity(base, target_dir, "target-entity")
        target = fork_result.dest_path
        _git(target, "config", "user.email", "test@test.com")
        _git(target, "config", "user.name", "Test User")

        # Fork to create source (independent from target)
        fork_result2 = fork_entity(base, target_dir, "source-entity")
        source = fork_result2.dest_path
        _git(source, "config", "user.email", "test@test.com")
        _git(source, "config", "user.name", "Test User")

        # Add different commits to the same file in target and source
        (target / "wiki" / "domain" / "shared.md").write_text(
            "# Shared\n\nTarget-specific knowledge about CI pipelines.\n"
        )
        _git(target, "add", "-A")
        _git(target, "commit", "-m", "Target: CI pipeline knowledge")

        (source / "wiki" / "domain" / "shared.md").write_text(
            "# Shared\n\nSource-specific knowledge about PagerDuty alerting.\n"
        )
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "Source: PagerDuty knowledge")

        return target, source

    def test_conflict_returns_merge_conflicts_pending(self, tmp_path):
        target, source = self._setup_conflicting_entities(tmp_path)
        with patch.object(entity_merge, "anthropic", MagicMock()) as mock_anthropic:
            # Set up mock to return synthesized content
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text="# Shared\n\nSynthesized knowledge.\n")]
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

            result = merge_entity(target, str(source))

        assert isinstance(result, MergeConflictsPending)

    def test_conflict_resolutions_contain_synthesized_content(self, tmp_path):
        target, source = self._setup_conflicting_entities(tmp_path)
        synthesized = "# Shared\n\nBest of both worlds.\n"

        with patch.object(entity_merge, "anthropic", MagicMock()) as mock_anthropic:
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text=synthesized)]
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

            result = merge_entity(target, str(source))

        assert isinstance(result, MergeConflictsPending)
        assert len(result.resolutions) >= 1
        assert result.resolutions[0].synthesized == synthesized

    def test_commit_resolved_merge_writes_files_and_commits(self, tmp_path):
        target, source = self._setup_conflicting_entities(tmp_path)
        synthesized = "# Shared\n\nFinal synthesized content.\n"

        with patch.object(entity_merge, "anthropic", MagicMock()) as mock_anthropic:
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text=synthesized)]
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

            result = merge_entity(target, str(source))

        assert isinstance(result, MergeConflictsPending)

        commit_resolved_merge(target, result.resolutions, result.source)

        # File should have synthesized content
        shared_path = target / "wiki" / "domain" / "shared.md"
        assert shared_path.read_text() == synthesized

        # HEAD should be a merge commit
        log = _git(target, "log", "--oneline", "-1").stdout
        assert "Merge learnings from" in log

    def test_abort_merge_restores_clean_state(self, tmp_path):
        target, source = self._setup_conflicting_entities(tmp_path)

        with patch.object(entity_merge, "anthropic", MagicMock()) as mock_anthropic:
            mock_msg = MagicMock()
            mock_msg.content = [MagicMock(text="synthesized")]
            mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_msg

            # Get the pending result (merge is in-progress)
            result = merge_entity(target, str(source))

        assert isinstance(result, MergeConflictsPending)

        # Abort the merge
        abort_merge(target)

        # Status should be clean
        status = _git(target, "status", "--porcelain").stdout
        assert not status.strip()
