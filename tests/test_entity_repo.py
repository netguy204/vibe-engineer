"""Tests for entity_repo.py — standalone git-repo-based entity creation.

# Chunk: docs/chunks/entity_repo_structure - Entity repo structure tests
"""

import subprocess
from pathlib import Path

import pytest

import entity_repo
from entity_repo import (
    EntityRepoMetadata,
    create_entity_repo,
    derive_entity_name_from_url,
    is_entity_repo,
    read_entity_metadata,
)


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
# create_entity_repo — success cases
# ---------------------------------------------------------------------------


class TestCreateEntityRepo:
    """Tests for create_entity_repo()."""

    def test_create_produces_valid_git_repo(self, tmp_path):
        """After creation, git log shows exactly one commit."""
        repo = create_entity_repo(tmp_path, "my_agent")
        result = _git(repo, "log", "--oneline")
        assert result.returncode == 0
        lines = [l for l in result.stdout.strip().splitlines() if l]
        assert len(lines) == 1
        assert "Initial entity state" in lines[0]

    def test_create_all_required_directories_exist(self, tmp_path):
        """All required directories are present after creation."""
        repo = create_entity_repo(tmp_path, "my_agent")
        required_dirs = [
            "wiki",
            "wiki/domain",
            "wiki/projects",
            "wiki/techniques",
            "wiki/relationships",
            "memories/journal",
            "memories/consolidated",
            "memories/core",
            "episodic",
        ]
        for d in required_dirs:
            assert (repo / d).is_dir(), f"Missing directory: {d}"

    def test_create_entity_md_has_correct_frontmatter(self, tmp_path):
        """ENTITY.md has valid frontmatter with required fields."""
        repo = create_entity_repo(tmp_path, "my_agent")
        entity_md = repo / "ENTITY.md"
        assert entity_md.exists()

        metadata = read_entity_metadata(repo)
        assert metadata.name == "my_agent"
        assert metadata.created  # non-empty ISO string
        assert metadata.specialization is None
        assert metadata.origin is None

    def test_create_wiki_pages_exist(self, tmp_path):
        """All wiki pages are present after creation."""
        repo = create_entity_repo(tmp_path, "my_agent")
        wiki_pages = [
            "wiki/wiki_schema.md",
            "wiki/identity.md",
            "wiki/index.md",
            "wiki/log.md",
        ]
        for page in wiki_pages:
            assert (repo / page).is_file(), f"Missing wiki page: {page}"

    def test_create_initial_commit_includes_all_files(self, tmp_path):
        """The initial commit includes ENTITY.md, wiki files, and .gitkeep sentinels."""
        repo = create_entity_repo(tmp_path, "my_agent")
        result = _git(repo, "show", "--stat", "HEAD")
        assert result.returncode == 0
        stat = result.stdout
        assert "ENTITY.md" in stat
        assert "wiki/wiki_schema.md" in stat
        assert "wiki/identity.md" in stat
        assert "wiki/index.md" in stat
        assert "wiki/log.md" in stat
        # .gitkeep sentinels for empty directories
        assert ".gitkeep" in stat

    def test_create_rejects_invalid_name_starts_with_digit(self, tmp_path):
        """Name starting with digit raises ValueError."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            create_entity_repo(tmp_path, "123bad")

    def test_create_rejects_invalid_name_uppercase(self, tmp_path):
        """Name with uppercase raises ValueError."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            create_entity_repo(tmp_path, "My_Entity")

    def test_create_rejects_invalid_name_with_space(self, tmp_path):
        """Name with space raises ValueError."""
        with pytest.raises(ValueError, match="Invalid entity name"):
            create_entity_repo(tmp_path, "has space")

    def test_create_rejects_existing_directory(self, tmp_path):
        """Raises ValueError if destination directory already exists."""
        create_entity_repo(tmp_path, "my_agent")
        with pytest.raises(ValueError, match="already exists"):
            create_entity_repo(tmp_path, "my_agent")

    def test_create_supports_kebab_case_name(self, tmp_path):
        """Kebab-case entity name (my-specialist) is accepted."""
        repo = create_entity_repo(tmp_path, "my-specialist")
        assert repo.is_dir()
        metadata = read_entity_metadata(repo)
        assert metadata.name == "my-specialist"

    def test_create_supports_underscore_name(self, tmp_path):
        """Snake-case entity name is accepted."""
        repo = create_entity_repo(tmp_path, "infra_agent")
        assert repo.is_dir()

    def test_create_with_role_sets_role_in_entity_md(self, tmp_path):
        """--role value appears in ENTITY.md metadata."""
        repo = create_entity_repo(tmp_path, "my_agent", role="Infrastructure expert")
        metadata = read_entity_metadata(repo)
        assert metadata.role == "Infrastructure expert"

    def test_create_returns_repo_path(self, tmp_path):
        """Returns path to the created repo."""
        repo = create_entity_repo(tmp_path, "my_agent")
        assert repo == tmp_path / "my_agent"
        assert repo.is_dir()

    def test_create_git_author_env_does_not_require_global_config(self, tmp_path, monkeypatch):
        """Creation succeeds even in environments without a global git config."""
        monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
        monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_NAME", raising=False)
        monkeypatch.delenv("GIT_COMMITTER_EMAIL", raising=False)
        # Should not raise even without global git config
        repo = create_entity_repo(tmp_path, "my_agent")
        result = _git(repo, "log", "--oneline")
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# is_entity_repo
# ---------------------------------------------------------------------------


class TestIsEntityRepo:
    """Tests for is_entity_repo()."""

    def test_is_entity_repo_true_for_valid_repo(self, tmp_path):
        """Returns True for a freshly created entity repo."""
        repo = create_entity_repo(tmp_path, "my_agent")
        assert is_entity_repo(repo) is True

    def test_is_entity_repo_false_for_missing_entity_md(self, tmp_path):
        """Returns False for a directory without ENTITY.md."""
        d = tmp_path / "no_entity"
        d.mkdir()
        assert is_entity_repo(d) is False

    def test_is_entity_repo_false_for_invalid_entity_md(self, tmp_path):
        """Returns False if ENTITY.md frontmatter is missing required fields."""
        d = tmp_path / "bad_entity"
        d.mkdir()
        (d / "ENTITY.md").write_text("---\nfoo: bar\n---\n# Nothing\n")
        assert is_entity_repo(d) is False

    def test_is_entity_repo_false_for_nonexistent_dir(self, tmp_path):
        """Returns False for a path that doesn't exist."""
        assert is_entity_repo(tmp_path / "nonexistent") is False

    def test_is_entity_repo_false_for_no_frontmatter(self, tmp_path):
        """Returns False if ENTITY.md has no frontmatter."""
        d = tmp_path / "no_fm"
        d.mkdir()
        (d / "ENTITY.md").write_text("# Just a heading\nNo frontmatter.\n")
        assert is_entity_repo(d) is False


# ---------------------------------------------------------------------------
# read_entity_metadata
# ---------------------------------------------------------------------------


class TestReadEntityMetadata:
    """Tests for read_entity_metadata()."""

    def test_read_entity_metadata_returns_correct_fields(self, tmp_path):
        """name and role match what was passed to create_entity_repo."""
        repo = create_entity_repo(tmp_path, "my_agent", role="Debugger")
        metadata = read_entity_metadata(repo)
        assert isinstance(metadata, EntityRepoMetadata)
        assert metadata.name == "my_agent"
        assert metadata.role == "Debugger"
        assert metadata.specialization is None
        assert metadata.origin is None

    def test_read_entity_metadata_created_is_iso_string(self, tmp_path):
        """created field is a non-empty string."""
        repo = create_entity_repo(tmp_path, "my_agent")
        metadata = read_entity_metadata(repo)
        assert isinstance(metadata.created, str)
        assert len(metadata.created) > 0

    def test_read_entity_metadata_raises_on_missing_entity_md(self, tmp_path):
        """Raises ValueError or FileNotFoundError when ENTITY.md is missing."""
        d = tmp_path / "no_entity"
        d.mkdir()
        with pytest.raises((ValueError, FileNotFoundError)):
            read_entity_metadata(d)

    def test_read_entity_metadata_raises_on_invalid_frontmatter(self, tmp_path):
        """Raises ValueError when frontmatter is missing required fields."""
        d = tmp_path / "bad_entity"
        d.mkdir()
        (d / "ENTITY.md").write_text("---\nfoo: bar\n---\n# Nothing\n")
        with pytest.raises(ValueError):
            read_entity_metadata(d)


# ---------------------------------------------------------------------------
# derive_entity_name_from_url
# ---------------------------------------------------------------------------


class TestDeriveEntityNameFromUrl:
    """Tests for derive_entity_name_from_url()."""

    def test_https_url_with_git_suffix(self):
        """HTTPS URL with .git suffix: strips suffix and entity- prefix."""
        assert derive_entity_name_from_url(
            "https://github.com/user/entity-slack-watcher.git"
        ) == "slack-watcher"

    def test_https_url_without_git_suffix(self):
        """HTTPS URL without .git: last component returned as-is."""
        assert derive_entity_name_from_url(
            "https://github.com/user/my-specialist"
        ) == "my-specialist"

    def test_ssh_url(self):
        """SSH URL: last component after / minus .git suffix."""
        assert derive_entity_name_from_url(
            "git@github.com:user/my-entity.git"
        ) == "my-entity"

    def test_local_relative_path(self):
        """Local relative path: last component."""
        assert derive_entity_name_from_url("../local-entity") == "local-entity"

    def test_local_absolute_path(self):
        """Local absolute path: last component."""
        assert derive_entity_name_from_url("/some/path/to/my-entity") == "my-entity"

    def test_trailing_slash_stripped(self):
        """Trailing slash is stripped before extraction."""
        assert derive_entity_name_from_url("../my-agent/") == "my-agent"

    def test_generic_name_without_entity_prefix(self):
        """Generic name without entity- prefix returned as-is."""
        assert derive_entity_name_from_url("https://github.com/user/ops-specialist") == "ops-specialist"

    def test_entity_prefix_stripped(self):
        """Name starting with entity- has prefix stripped."""
        assert derive_entity_name_from_url(
            "https://github.com/user/entity-ops-specialist"
        ) == "ops-specialist"


# ---------------------------------------------------------------------------
# is_merge_in_progress
# Chunk: docs/chunks/entity_merge_preserve_conflicts - Merge-in-progress detection tests
# ---------------------------------------------------------------------------


class TestIsMergeInProgress:
    """Tests for is_merge_in_progress()."""

    def test_false_when_no_merge_head(self, tmp_path):
        """Returns False when .git/MERGE_HEAD does not exist."""
        entity_path = create_entity_repo(tmp_path, "test-entity")
        assert entity_repo.is_merge_in_progress(entity_path) is False

    def test_true_when_merge_head_present(self, tmp_path):
        """Returns True when .git/MERGE_HEAD exists."""
        entity_path = create_entity_repo(tmp_path, "test-entity")
        merge_head = entity_path / ".git" / "MERGE_HEAD"
        merge_head.write_text("deadbeef\n")
        assert entity_repo.is_merge_in_progress(entity_path) is True


# ---------------------------------------------------------------------------
# apply_resolutions
# Chunk: docs/chunks/entity_merge_preserve_conflicts - apply_resolutions tests
# ---------------------------------------------------------------------------


def _make_conflicting_entity_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Set up two entity repos with shared history, a conflicting file, and a merge in progress.

    Returns (target_path, source_path) where target has a merge in progress.
    The conflicting file is wiki/domain/shared.md.

    Strategy: clone target → source (shared history), diverge both sides on the same
    file, then start a merge in target from source's branch so MERGE_HEAD is set.
    """
    # Create target with the initial wiki page
    target = create_entity_repo(tmp_path / "target-parent", "target")
    _git(target, "config", "user.email", "test@test.com")
    _git(target, "config", "user.name", "Test User")

    wiki_dir = target / "wiki" / "domain"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "shared.md").write_text("# Shared\n\nOriginal content.\n")
    _git(target, "add", "-A")
    _git(target, "commit", "-m", "Add shared page")

    # Clone target to create source (shared history)
    source = tmp_path / "source"
    subprocess.run(
        ["git", "clone", str(target), str(source)],
        capture_output=True, text=True, check=True,
    )
    _git(source, "config", "user.email", "test@test.com")
    _git(source, "config", "user.name", "Test User")

    # Diverge source: modify shared.md
    (source / "wiki" / "domain" / "shared.md").write_text("# Shared\n\nSource content.\n")
    _git(source, "add", "-A")
    _git(source, "commit", "-m", "Source modification")

    # Diverge target: modify shared.md differently
    (target / "wiki" / "domain" / "shared.md").write_text("# Shared\n\nTarget content.\n")
    _git(target, "add", "-A")
    _git(target, "commit", "-m", "Target modification")

    # Fetch source's main branch into target and start a conflicting merge
    _git(target, "fetch", str(source), "main:refs/remotes/source/main")
    # This will conflict and leave MERGE_HEAD set
    _git(target, "merge", "--no-commit", "--no-ff", "refs/remotes/source/main")

    return target, source


class TestApplyResolutions:
    """Tests for apply_resolutions()."""

    def test_writes_synthesized_content_and_stages(self, tmp_path):
        """After apply_resolutions, the resolved file has synthesized content and is staged."""
        target, _ = _make_conflicting_entity_pair(tmp_path)

        # Confirm merge is in progress
        assert entity_repo.is_merge_in_progress(target)

        resolution = entity_repo.ConflictResolution(
            relative_path="wiki/domain/shared.md",
            synthesized="# Shared\n\nSynthesized content.\n",
            is_wiki=True,
        )
        entity_repo.apply_resolutions(target, [resolution])

        # File should have synthesized content
        content = (target / "wiki" / "domain" / "shared.md").read_text()
        assert content == "# Shared\n\nSynthesized content.\n"

        # File should be staged (no longer UU in git status --porcelain)
        status = _git(target, "status", "--porcelain", "wiki/domain/shared.md")
        # A staged file shows as "M " (modified, staged) not "UU"
        assert "UU" not in status.stdout

    def test_does_not_touch_unresolvable_files(self, tmp_path):
        """apply_resolutions with one resolution leaves other conflicting files untouched."""
        # Create target with two conflicting files
        target = create_entity_repo(tmp_path / "target-parent", "target")
        _git(target, "config", "user.email", "test@test.com")
        _git(target, "config", "user.name", "Test User")

        wiki_dir = target / "wiki" / "domain"
        wiki_dir.mkdir(parents=True, exist_ok=True)
        (wiki_dir / "file_a.md").write_text("# A\n\nOriginal A.\n")
        (wiki_dir / "file_b.md").write_text("# B\n\nOriginal B.\n")
        _git(target, "add", "-A")
        _git(target, "commit", "-m", "Initial commit")

        # Clone to create source with shared history
        source = tmp_path / "source"
        subprocess.run(
            ["git", "clone", str(target), str(source)],
            capture_output=True, text=True, check=True,
        )
        _git(source, "config", "user.email", "test@test.com")
        _git(source, "config", "user.name", "Test User")

        # Diverge source on both files
        (source / "wiki" / "domain" / "file_a.md").write_text("# A\n\nSource A.\n")
        (source / "wiki" / "domain" / "file_b.md").write_text("# B\n\nSource B.\n")
        _git(source, "add", "-A")
        _git(source, "commit", "-m", "Source modifications")

        # Diverge target on both files
        (target / "wiki" / "domain" / "file_a.md").write_text("# A\n\nTarget A.\n")
        (target / "wiki" / "domain" / "file_b.md").write_text("# B\n\nTarget B.\n")
        _git(target, "add", "-A")
        _git(target, "commit", "-m", "Target modifications")

        # Start conflicting merge in target
        _git(target, "fetch", str(source), "main:refs/remotes/source/main")
        _git(target, "merge", "--no-commit", "--no-ff", "refs/remotes/source/main")

        assert entity_repo.is_merge_in_progress(target)

        # Resolve only file_a
        resolution_a = entity_repo.ConflictResolution(
            relative_path="wiki/domain/file_a.md",
            synthesized="# A\n\nSynthesized A.\n",
            is_wiki=True,
        )
        entity_repo.apply_resolutions(target, [resolution_a])

        # file_a should be staged
        status_a = _git(target, "status", "--porcelain", "wiki/domain/file_a.md")
        assert "UU" not in status_a.stdout

        # file_b should still be in conflict (UU)
        status_b = _git(target, "status", "--porcelain", "wiki/domain/file_b.md")
        assert "UU" in status_b.stdout
