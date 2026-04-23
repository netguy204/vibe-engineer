"""Tests for ve wiki rename — wiki page rename and wikilink rewriting.

# Chunk: docs/chunks/wiki_rename_command - Tests for wiki_rename() and ve wiki rename CLI
"""

import pathlib

import pytest
from click.testing import CliRunner

import entity_repo
from entity_repo import WikiRenameResult, create_entity_repo, wiki_rename
from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(tmp_path: pathlib.Path, name: str = "test-entity") -> pathlib.Path:
    """Create a minimal entity repo and return its path."""
    entity_path = create_entity_repo(tmp_path / "entity", name)
    return entity_path


def _write_wiki_page(entity_path: pathlib.Path, rel_path: str, content: str) -> pathlib.Path:
    """Write a wiki page at wiki/<rel_path>.md within the entity repo.

    Creates any intermediate directories automatically.
    Returns the absolute Path to the created file.
    """
    page_file = entity_path / "wiki" / f"{rel_path}.md"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text(content)
    return page_file


# ---------------------------------------------------------------------------
# Unit tests for wiki_rename()
# ---------------------------------------------------------------------------


class TestWikiRename:
    """Tests for entity_repo.wiki_rename()."""

    def test_moves_file_to_new_path(self, tmp_path):
        """Old file is removed and new file exists after rename."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")

        wiki_rename(entity_path, "domain/foo", "domain/bar")

        assert not (entity_path / "wiki" / "domain" / "foo.md").exists()
        assert (entity_path / "wiki" / "domain" / "bar.md").exists()

    def test_creates_destination_subdirectory(self, tmp_path):
        """New page in a new subdirectory is created with necessary parent dirs."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")

        wiki_rename(entity_path, "domain/foo", "techniques/foo-technique")

        assert not (entity_path / "wiki" / "domain" / "foo.md").exists()
        assert (entity_path / "wiki" / "techniques" / "foo-technique.md").exists()

    def test_rewrites_full_path_wikilinks(self, tmp_path):
        """[[domain/foo]] links in other pages are rewritten to [[domain/bar]]."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/other", "See [[domain/foo]] for details.\n")

        wiki_rename(entity_path, "domain/foo", "domain/bar")

        other_content = (entity_path / "wiki" / "domain" / "other.md").read_text()
        assert "[[domain/bar]]" in other_content
        assert "[[domain/foo]]" not in other_content

    def test_rewrites_stem_only_wikilinks(self, tmp_path):
        """[[foo]] bare-stem links are rewritten when stem changes."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/other", "Check [[foo]] and also [[domain/foo]].\n")

        wiki_rename(entity_path, "domain/foo", "domain/bar")

        other_content = (entity_path / "wiki" / "domain" / "other.md").read_text()
        assert "[[bar]]" in other_content
        assert "[[domain/bar]]" in other_content
        assert "[[foo]]" not in other_content
        assert "[[domain/foo]]" not in other_content

    def test_preserves_display_text_in_wikilinks(self, tmp_path):
        """[[old|Display]] is rewritten to [[new|Display]] preserving display text."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(
            entity_path,
            "domain/other",
            "See [[domain/foo|Foo Page]] and [[foo|Just Foo]].\n",
        )

        wiki_rename(entity_path, "domain/foo", "domain/bar")

        other_content = (entity_path / "wiki" / "domain" / "other.md").read_text()
        assert "[[domain/bar|Foo Page]]" in other_content
        assert "[[bar|Just Foo]]" in other_content
        assert "[[domain/foo" not in other_content
        assert "[[foo" not in other_content

    def test_updates_multiple_pages_with_inbound_links(self, tmp_path):
        """Files updated count reflects all pages that had wikilinks rewritten."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/page1", "See [[domain/foo]].\n")
        _write_wiki_page(entity_path, "domain/page2", "Also [[foo]] here.\n")
        _write_wiki_page(entity_path, "domain/page3", "No links to foo here.\n")

        result = wiki_rename(entity_path, "domain/foo", "domain/bar")

        assert result.files_updated == 2

    def test_index_md_wikilinks_are_updated(self, tmp_path):
        """index.md links to the renamed page are rewritten."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/world-model", "# World Model\n")

        # Add a reference to the renamed page in index.md
        index_path = entity_path / "wiki" / "index.md"
        index_content = index_path.read_text()
        index_path.write_text(
            index_content + "\n| [[domain/world-model]] | World model knowledge |\n"
        )

        wiki_rename(entity_path, "domain/world-model", "domain/world-model-v2")

        updated_index = index_path.read_text()
        assert "[[domain/world-model-v2]]" in updated_index
        assert "[[domain/world-model]]" not in updated_index

    def test_returns_wiki_rename_result(self, tmp_path):
        """wiki_rename returns a WikiRenameResult with old and new paths."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/alpha", "# Alpha\n")

        result = wiki_rename(entity_path, "domain/alpha", "domain/beta")

        assert isinstance(result, WikiRenameResult)
        assert result.old_path == "domain/alpha"
        assert result.new_path == "domain/beta"

    def test_stem_unchanged_does_not_rewrite_stem_links(self, tmp_path):
        """Moving foo/bar to baz/bar (same stem) doesn't rewrite [[bar]] links."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/bar", "# Bar\n")
        _write_wiki_page(entity_path, "domain/other", "See [[bar]] and [[domain/bar]].\n")

        wiki_rename(entity_path, "domain/bar", "techniques/bar")

        other_content = (entity_path / "wiki" / "domain" / "other.md").read_text()
        # Full path should be updated
        assert "[[techniques/bar]]" in other_content
        assert "[[domain/bar]]" not in other_content
        # Bare stem stays since stem didn't change
        assert "[[bar]]" in other_content

    def test_raises_if_no_wiki_directory(self, tmp_path):
        """ValueError raised when entity has no wiki/ directory."""
        entity_path = tmp_path / "bare-entity"
        entity_path.mkdir()

        with pytest.raises(ValueError, match="no wiki/ directory"):
            wiki_rename(entity_path, "domain/foo", "domain/bar")

    def test_raises_if_old_page_not_found(self, tmp_path):
        """ValueError raised when old_path doesn't exist in wiki."""
        entity_path = _make_entity(tmp_path)

        with pytest.raises(ValueError, match="not found"):
            wiki_rename(entity_path, "domain/nonexistent", "domain/bar")

    def test_raises_if_new_page_already_exists(self, tmp_path):
        """ValueError raised when new_path already exists in wiki."""
        entity_path = _make_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/bar", "# Bar\n")

        with pytest.raises(ValueError, match="already exists"):
            wiki_rename(entity_path, "domain/foo", "domain/bar")


# ---------------------------------------------------------------------------
# CLI integration tests for 've wiki rename'
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


def _setup_project_with_entity(
    tmp_path: pathlib.Path,
    entity_name: str = "skippy",
) -> tuple[pathlib.Path, pathlib.Path]:
    """Create a project dir with an entity attached at .entities/<name>/.

    Returns (project_dir, entity_path).
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    entities_dir = project_dir / ".entities"
    entities_dir.mkdir()

    # create_entity_repo(dest, name) creates dest/name/
    entity_path = create_entity_repo(entities_dir, entity_name)

    return project_dir, entity_path


class TestWikiRenameCLI:
    """CLI integration tests for 've wiki rename'."""

    def test_rename_moves_page_and_reports(self, tmp_path, runner):
        """Successful rename prints the old→new paths and files updated."""
        project_dir, entity_path = _setup_project_with_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/world-model", "# World Model\n")

        result = runner.invoke(
            cli,
            [
                "wiki", "rename",
                "skippy",
                "domain/world-model",
                "domain/world-model-v2",
                "--project-dir", str(project_dir),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Output: {result.output}"
        assert "domain/world-model" in result.output
        assert "domain/world-model-v2" in result.output
        assert "Files updated" in result.output

    def test_rename_actually_moves_file(self, tmp_path, runner):
        """After ve wiki rename, old file is gone and new file exists."""
        project_dir, entity_path = _setup_project_with_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/alpha", "# Alpha\n")

        runner.invoke(
            cli,
            [
                "wiki", "rename",
                "skippy",
                "domain/alpha",
                "domain/beta",
                "--project-dir", str(project_dir),
            ],
            catch_exceptions=False,
        )

        assert not (entity_path / "wiki" / "domain" / "alpha.md").exists()
        assert (entity_path / "wiki" / "domain" / "beta.md").exists()

    def test_rename_rewrites_inbound_links_from_multiple_pages(self, tmp_path, runner):
        """CLI rename rewrites wikilinks across multiple wiki pages."""
        project_dir, entity_path = _setup_project_with_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/page1", "See [[domain/foo]].\n")
        _write_wiki_page(entity_path, "domain/page2", "Also [[foo]] here.\n")

        result = runner.invoke(
            cli,
            [
                "wiki", "rename",
                "skippy",
                "domain/foo",
                "domain/bar",
                "--project-dir", str(project_dir),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        page1_content = (entity_path / "wiki" / "domain" / "page1.md").read_text()
        assert "[[domain/bar]]" in page1_content
        assert "[[domain/foo]]" not in page1_content

        page2_content = (entity_path / "wiki" / "domain" / "page2.md").read_text()
        assert "[[bar]]" in page2_content
        assert "[[foo]]" not in page2_content

    def test_nonexistent_entity_fails_with_error(self, tmp_path, runner):
        """ve wiki rename with an unknown entity name exits non-zero."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".entities").mkdir()

        result = runner.invoke(
            cli,
            [
                "wiki", "rename",
                "no-such-entity",
                "domain/foo",
                "domain/bar",
                "--project-dir", str(project_dir),
            ],
        )

        assert result.exit_code != 0
        assert "no-such-entity" in result.output

    def test_nonexistent_page_fails_with_error(self, tmp_path, runner):
        """ve wiki rename with unknown old_path exits non-zero."""
        project_dir, _ = _setup_project_with_entity(tmp_path)

        result = runner.invoke(
            cli,
            [
                "wiki", "rename",
                "skippy",
                "domain/does-not-exist",
                "domain/bar",
                "--project-dir", str(project_dir),
            ],
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_rename_to_existing_page_fails_with_error(self, tmp_path, runner):
        """ve wiki rename fails when new_path already exists."""
        project_dir, entity_path = _setup_project_with_entity(tmp_path)
        _write_wiki_page(entity_path, "domain/foo", "# Foo\n")
        _write_wiki_page(entity_path, "domain/bar", "# Bar\n")

        result = runner.invoke(
            cli,
            [
                "wiki", "rename",
                "skippy",
                "domain/foo",
                "domain/bar",
                "--project-dir", str(project_dir),
            ],
        )

        assert result.exit_code != 0
        assert "already exists" in result.output
