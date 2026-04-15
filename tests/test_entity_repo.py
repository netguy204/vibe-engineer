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
