"""Unit tests for entity_repo push/pull/set-origin library functions.

# Chunk: docs/chunks/entity_push_pull - Push/pull/set-origin unit tests
"""

import subprocess
from pathlib import Path

import pytest

from entity_repo import (
    MergeNeededError,
    MergeResult,
    PullResult,
    PushResult,
    create_entity_repo,
    merge_entity,
    pull_entity,
    push_entity,
    set_entity_origin,
)
from conftest import make_entity_with_origin, make_entity_no_origin


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


# ---------------------------------------------------------------------------
# Tests for push_entity
# ---------------------------------------------------------------------------


class TestPushEntity:
    """Tests for push_entity()."""

    def test_push_sends_commits_to_origin(self, tmp_path):
        """Commits appear in origin after push_entity."""
        entity_path, bare_origin = make_entity_with_origin(tmp_path)

        # Make a new commit
        (entity_path / "new_knowledge.txt").write_text("learned something")
        _git(entity_path, "add", "new_knowledge.txt")
        _git(entity_path, "commit", "-m", "Add knowledge")

        result = push_entity(entity_path)

        # Clone origin fresh and verify the commit appears
        fresh_clone = tmp_path / "verify-clone"
        clone_result = subprocess.run(
            ["git", "clone", str(bare_origin), str(fresh_clone)],
            capture_output=True, text=True,
        )
        assert clone_result.returncode == 0, clone_result.stderr
        assert (fresh_clone / "new_knowledge.txt").exists()

        assert isinstance(result, PushResult)
        assert result.commits_pushed >= 1

    def test_push_warns_uncommitted_changes_returns_warning(self, tmp_path):
        """push_entity succeeds with uncommitted changes but sets has_uncommitted=True."""
        entity_path, _ = make_entity_with_origin(tmp_path)

        # Write an untracked file (not committed)
        (entity_path / "dirty.txt").write_text("not committed")

        result = push_entity(entity_path)

        assert isinstance(result, PushResult)
        assert result.has_uncommitted is True

    def test_push_no_uncommitted_when_clean(self, tmp_path):
        """has_uncommitted is False when working tree is clean."""
        entity_path, _ = make_entity_with_origin(tmp_path)

        (entity_path / "clean.txt").write_text("committed")
        _git(entity_path, "add", "clean.txt")
        _git(entity_path, "commit", "-m", "Clean commit")

        result = push_entity(entity_path)

        assert result.has_uncommitted is False

    def test_push_raises_if_no_remote(self, tmp_path):
        """Raises RuntimeError when entity has no remote origin configured."""
        entity_path = make_entity_no_origin(tmp_path)

        with pytest.raises(RuntimeError, match="[Rr]emote|origin"):
            push_entity(entity_path)

    def test_push_raises_if_not_entity_repo(self, tmp_path):
        """Raises ValueError for a path that is not an entity repo."""
        not_entity = tmp_path / "not-an-entity"
        not_entity.mkdir()

        with pytest.raises(ValueError, match="[Ee]ntity"):
            push_entity(not_entity)

    def test_push_zero_commits_when_already_up_to_date(self, tmp_path):
        """commits_pushed is 0 when nothing new to push."""
        entity_path, _ = make_entity_with_origin(tmp_path)

        # Push first time to sync
        push_entity(entity_path)

        # Push again with nothing new
        result = push_entity(entity_path)

        assert result.commits_pushed == 0


# ---------------------------------------------------------------------------
# Tests for pull_entity
# ---------------------------------------------------------------------------


class TestPullEntity:
    """Tests for pull_entity()."""

    def _setup_with_second_clone(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """Set up: entity + bare origin + second clone that can push new commits.

        Returns: (entity_path, bare_origin, second_clone_path)
        """
        entity_path, bare_origin = make_entity_with_origin(tmp_path)

        # Push initial state to origin
        _git(entity_path, "push", "origin", "main")

        # Create a second clone to push new commits from
        second_clone = tmp_path / "second-clone"
        subprocess.run(
            ["git", "clone", str(bare_origin), str(second_clone)],
            capture_output=True, text=True,
        )
        _git(second_clone, "config", "user.email", "other@test.com")
        _git(second_clone, "config", "user.name", "Other User")

        return entity_path, bare_origin, second_clone

    def test_pull_fast_forward_advances_local_branch(self, tmp_path):
        """pull_entity fast-forwards local branch when origin has new commits."""
        entity_path, bare_origin, second_clone = self._setup_with_second_clone(tmp_path)

        # Push a new commit from second clone
        (second_clone / "from_other.txt").write_text("new from other")
        _git(second_clone, "add", "from_other.txt")
        _git(second_clone, "commit", "-m", "New commit from second clone")
        _git(second_clone, "push", "origin", "main")

        pull_entity(entity_path)

        # Local branch should now have the file
        assert (entity_path / "from_other.txt").exists()

    def test_pull_fast_forward_returns_merged_commits(self, tmp_path):
        """pull_entity result includes number of new commits merged."""
        entity_path, bare_origin, second_clone = self._setup_with_second_clone(tmp_path)

        # Push two new commits from second clone
        for i in range(2):
            (second_clone / f"commit_{i}.txt").write_text(f"commit {i}")
            _git(second_clone, "add", f"commit_{i}.txt")
            _git(second_clone, "commit", "-m", f"Commit {i}")
        _git(second_clone, "push", "origin", "main")

        result = pull_entity(entity_path)

        assert isinstance(result, PullResult)
        assert result.commits_merged == 2
        assert result.up_to_date is False

    def test_pull_already_up_to_date(self, tmp_path):
        """pull_entity reports up_to_date=True when origin has no new commits."""
        entity_path, _, _ = self._setup_with_second_clone(tmp_path)

        result = pull_entity(entity_path)

        assert isinstance(result, PullResult)
        assert result.up_to_date is True
        assert result.commits_merged == 0

    def test_pull_diverged_auto_merges_not_raises(self, tmp_path):
        """pull_entity auto-merges diverged histories; MergeNeededError is NOT raised."""
        entity_path, bare_origin, second_clone = self._setup_with_second_clone(tmp_path)

        # Push a commit from second clone
        (second_clone / "remote_commit.txt").write_text("remote")
        _git(second_clone, "add", "remote_commit.txt")
        _git(second_clone, "commit", "-m", "Remote commit")
        _git(second_clone, "push", "origin", "main")

        # Make a local commit on entity_path (diverges from origin)
        (entity_path / "local_commit.txt").write_text("local")
        _git(entity_path, "add", "local_commit.txt")
        _git(entity_path, "commit", "-m", "Local commit")

        # Should NOT raise MergeNeededError — should auto-merge instead
        result = pull_entity(entity_path)
        assert not isinstance(result, MergeNeededError)

    def test_pull_diverged_auto_merges(self, tmp_path):
        """pull_entity returns a MergeResult when histories have diverged."""
        entity_path, bare_origin, second_clone = self._setup_with_second_clone(tmp_path)

        # Push a commit from second clone
        (second_clone / "remote_commit.txt").write_text("remote")
        _git(second_clone, "add", "remote_commit.txt")
        _git(second_clone, "commit", "-m", "Remote commit")
        _git(second_clone, "push", "origin", "main")

        # Make a local commit on entity_path (diverges from origin)
        (entity_path / "local_commit.txt").write_text("local")
        _git(entity_path, "add", "local_commit.txt")
        _git(entity_path, "commit", "-m", "Local commit")

        result = pull_entity(entity_path)

        assert isinstance(result, MergeResult)
        # Remote file should now exist locally after merge
        assert (entity_path / "remote_commit.txt").exists()

    def test_pull_diverged_returns_merge_result_with_commit_count(self, tmp_path):
        """MergeResult.commits_merged reflects the number of incoming commits merged."""
        entity_path, bare_origin, second_clone = self._setup_with_second_clone(tmp_path)

        # Push 2 commits from second clone
        for i in range(2):
            (second_clone / f"remote_{i}.txt").write_text(f"remote {i}")
            _git(second_clone, "add", f"remote_{i}.txt")
            _git(second_clone, "commit", "-m", f"Remote commit {i}")
        _git(second_clone, "push", "origin", "main")

        # Make a local commit (diverge)
        (entity_path / "local_commit.txt").write_text("local")
        _git(entity_path, "add", "local_commit.txt")
        _git(entity_path, "commit", "-m", "Local commit")

        result = pull_entity(entity_path)

        assert isinstance(result, MergeResult)
        assert result.commits_merged == 2

    def test_pull_raises_if_no_remote(self, tmp_path):
        """Raises RuntimeError when entity has no remote configured."""
        entity_path = make_entity_no_origin(tmp_path)

        with pytest.raises(RuntimeError, match="[Rr]emote|origin"):
            pull_entity(entity_path)

    def test_pull_raises_if_not_entity_repo(self, tmp_path):
        """Raises ValueError for a non-entity path."""
        not_entity = tmp_path / "not-entity"
        not_entity.mkdir()

        with pytest.raises(ValueError, match="[Ee]ntity"):
            pull_entity(not_entity)


# ---------------------------------------------------------------------------
# Tests for set_entity_origin
# ---------------------------------------------------------------------------


class TestSetEntityOrigin:
    """Tests for set_entity_origin()."""

    def test_set_origin_configures_remote(self, tmp_path):
        """After set_entity_origin, git remote get-url origin returns the new URL."""
        entity_path = make_entity_no_origin(tmp_path)
        target_url = "https://github.com/org/entity-specialist.git"

        set_entity_origin(entity_path, target_url)

        result = _git(entity_path, "remote", "get-url", "origin")
        assert result.returncode == 0
        assert result.stdout.strip() == target_url

    def test_set_origin_replaces_existing_remote(self, tmp_path):
        """Calling set_entity_origin twice results in the second URL winning."""
        entity_path = make_entity_no_origin(tmp_path)
        first_url = "https://github.com/org/entity-first.git"
        second_url = "https://github.com/org/entity-second.git"

        set_entity_origin(entity_path, first_url)
        set_entity_origin(entity_path, second_url)

        result = _git(entity_path, "remote", "get-url", "origin")
        assert result.returncode == 0
        assert result.stdout.strip() == second_url

    def test_set_origin_works_with_existing_origin(self, tmp_path):
        """set_entity_origin works when entity already has an origin remote."""
        entity_path, bare_origin = make_entity_with_origin(tmp_path)
        new_url = "https://github.com/org/new-origin.git"

        set_entity_origin(entity_path, new_url)

        result = _git(entity_path, "remote", "get-url", "origin")
        assert result.returncode == 0
        assert result.stdout.strip() == new_url

    def test_set_origin_raises_if_not_entity_repo(self, tmp_path):
        """Raises ValueError for a non-entity path."""
        not_entity = tmp_path / "not-entity"
        not_entity.mkdir()

        with pytest.raises(ValueError, match="[Ee]ntity"):
            set_entity_origin(not_entity, "https://github.com/org/entity.git")

    def test_set_origin_raises_for_empty_url(self, tmp_path):
        """Raises ValueError when URL is empty."""
        entity_path = make_entity_no_origin(tmp_path)

        with pytest.raises(ValueError, match="[Uu][Rr][Ll]|empty"):
            set_entity_origin(entity_path, "")


# ---------------------------------------------------------------------------
# Tests for _has_tracked_uncommitted_changes helper
# ---------------------------------------------------------------------------


class TestUncommittedGate:
    """Tests for _has_tracked_uncommitted_changes()."""

    def test_clean_repo_not_flagged(self, tmp_path):
        """A freshly created entity repo has no uncommitted changes."""
        from entity_repo import _has_tracked_uncommitted_changes
        entity_path = make_entity_no_origin(tmp_path)

        assert _has_tracked_uncommitted_changes(entity_path) is False

    def test_untracked_file_not_flagged(self, tmp_path):
        """An untracked file does not trigger the uncommitted gate."""
        from entity_repo import _has_tracked_uncommitted_changes
        entity_path = make_entity_no_origin(tmp_path)

        # Write a file but don't stage or commit it
        (entity_path / "session.jsonl").write_text('{"event": "start"}')

        assert _has_tracked_uncommitted_changes(entity_path) is False

    def test_modified_tracked_file_flagged(self, tmp_path):
        """Modifying a tracked file triggers the uncommitted gate."""
        from entity_repo import _has_tracked_uncommitted_changes
        entity_path = make_entity_no_origin(tmp_path)

        # ENTITY.md is created by create_entity_repo and committed — modify it
        entity_md = entity_path / "ENTITY.md"
        original = entity_md.read_text()
        entity_md.write_text(original + "\n# Extra section\n")

        assert _has_tracked_uncommitted_changes(entity_path) is True

    def test_staged_change_flagged(self, tmp_path):
        """A staged (but not yet committed) new file triggers the uncommitted gate."""
        from entity_repo import _has_tracked_uncommitted_changes
        entity_path = make_entity_no_origin(tmp_path)

        # Stage a new file
        new_file = entity_path / "new_tracked.txt"
        new_file.write_text("new content")
        _git(entity_path, "add", "new_tracked.txt")

        assert _has_tracked_uncommitted_changes(entity_path) is True


# ---------------------------------------------------------------------------
# Tests for merge_entity optional source
# ---------------------------------------------------------------------------


class TestMergeEntityOptionalSource:
    """Tests for merge_entity() with optional source parameter."""

    def _setup_diverged_entities(self, tmp_path: Path) -> tuple[Path, Path]:
        """Set up entity with a bare origin that has a commit entity doesn't have.

        Returns (entity_path, bare_origin).
        """
        from entity_repo import fork_entity

        # Create entity and bare origin
        entity_path, bare_origin = make_entity_with_origin(tmp_path)
        _git(entity_path, "push", "origin", "main")

        # Add a commit to origin via a second clone
        second_clone = tmp_path / "second"
        subprocess.run(
            ["git", "clone", str(bare_origin), str(second_clone)],
            capture_output=True, text=True,
        )
        _git(second_clone, "config", "user.email", "other@test.com")
        _git(second_clone, "config", "user.name", "Other User")

        (second_clone / "new_knowledge.txt").write_text("new")
        _git(second_clone, "add", "new_knowledge.txt")
        _git(second_clone, "commit", "-m", "New knowledge")
        _git(second_clone, "push", "origin", "main")

        return entity_path, bare_origin

    def test_merge_without_source_uses_configured_remote(self, tmp_path):
        """merge_entity with no source resolves from the entity's origin remote."""
        from entity_repo import MergeResult, merge_entity

        entity_path, bare_origin = self._setup_diverged_entities(tmp_path)

        # Fetch so the local tracking ref exists
        _git(entity_path, "fetch", "origin")

        result = merge_entity(entity_path)

        assert isinstance(result, MergeResult)
        assert result.commits_merged > 0

    def test_merge_without_source_raises_when_no_remote(self, tmp_path):
        """merge_entity with no source raises RuntimeError when no origin is configured."""
        from entity_repo import merge_entity

        entity_path = make_entity_no_origin(tmp_path)

        with pytest.raises(RuntimeError, match="[Oo]rigin|remote"):
            merge_entity(entity_path)
