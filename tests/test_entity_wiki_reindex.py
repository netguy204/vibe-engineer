"""Tests for ve wiki reindex command.

# Chunk: docs/chunks/wiki_reindex_command - Tests for wiki reindex logic and CLI
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from ve import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FRONTMATTER_TEMPLATE = """\
---
title: {title}
created: 2026-01-01T00:00:00+00:00
updated: 2026-01-01T00:00:00+00:00
---
Body content here.
"""


def make_wiki_entity(tmp_path: Path, pages: dict[str, str] | None = None) -> Path:
    """Create a minimal wiki directory structure for testing.

    Args:
        tmp_path: Base temporary directory.
        pages: Optional mapping of relative paths (from wiki/) to page titles.
               Defaults to a standard set of pages across all sections.

    Returns:
        Path to the wiki/ directory.
    """
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    for subdir in ("domain", "techniques", "projects", "relationships"):
        (wiki_dir / subdir).mkdir()

    # Always create wiki_schema.md (stub)
    (wiki_dir / "wiki_schema.md").write_text("# Wiki Schema\n")

    if pages is None:
        pages = {
            "identity.md": "Identity",
            "log.md": "Log",
            "domain/caching.md": "Caching",
            "techniques/refactoring.md": "Refactoring",
            "projects/alpha.md": "Alpha",
            "relationships/alice.md": "Alice",
        }

    for rel_path, title in pages.items():
        full_path = wiki_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(FRONTMATTER_TEMPLATE.format(title=title))

    return wiki_dir


# ---------------------------------------------------------------------------
# Unit tests: reindex_wiki()
# ---------------------------------------------------------------------------


class TestReindexWiki:

    def test_reindex_produces_index_md(self, tmp_path):
        """After reindex, index.md exists in the wiki dir."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path)
        reindex_wiki(wiki_dir, entity_name="testbot")

        assert (wiki_dir / "index.md").exists()

    def test_reindex_includes_all_sections(self, tmp_path):
        """Generated index contains Core, Domain, Projects, Techniques, Relationships headers."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path)
        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        assert "## Core" in content
        assert "## Domain Knowledge" in content
        assert "## Projects" in content
        assert "## Techniques" in content
        assert "## Relationships" in content

    def test_reindex_lists_pages_by_directory(self, tmp_path):
        """Pages in domain/ appear in Domain section, pages in techniques/ appear in Techniques, etc."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path)
        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()

        # Find section positions
        domain_pos = content.index("## Domain Knowledge")
        techniques_pos = content.index("## Techniques")
        projects_pos = content.index("## Projects")
        relationships_pos = content.index("## Relationships")

        # caching should appear in Domain section (before Techniques)
        caching_pos = content.index("[[caching]]")
        assert domain_pos < caching_pos < techniques_pos

        # refactoring should appear in Techniques section (after Domain)
        refactoring_pos = content.index("[[refactoring]]")
        assert techniques_pos < refactoring_pos

        # alpha should appear in Projects section
        alpha_pos = content.index("[[alpha]]")
        assert projects_pos < alpha_pos

        # alice should appear in Relationships section
        alice_pos = content.index("[[alice]]")
        assert relationships_pos < alice_pos

    def test_reindex_excludes_index_and_schema(self, tmp_path):
        """index.md and wiki_schema.md are not listed as pages."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path)
        # Create a pre-existing index.md to ensure it's not listed as a page
        (wiki_dir / "index.md").write_text("# Old Index\n")
        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        assert "[[index]]" not in content
        assert "[[wiki_schema]]" not in content

    def test_reindex_alphabetical_order(self, tmp_path):
        """Within each section, pages are sorted alphabetically by title."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(
            tmp_path,
            pages={
                "domain/zebra.md": "Zebra",
                "domain/apple.md": "Apple",
                "domain/mango.md": "Mango",
            },
        )
        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        apple_pos = content.index("[[apple]]")
        mango_pos = content.index("[[mango]]")
        zebra_pos = content.index("[[zebra]]")
        assert apple_pos < mango_pos < zebra_pos

    def test_reindex_overwrites_existing_index(self, tmp_path):
        """An existing index.md with stale rows is replaced entirely."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path, pages={"identity.md": "Identity"})
        # Write a stale index with a reference to a page that no longer exists
        (wiki_dir / "index.md").write_text(
            "---\ntitle: old\n---\n\n| [[stale_page]] | Old summary |\n"
        )

        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        assert "[[stale_page]]" not in content
        assert "[[identity]]" in content

    def test_reindex_preserves_existing_summaries(self, tmp_path):
        """Summaries from the existing index are kept for pages that still exist."""
        from entity_repo import reindex_wiki

        wiki_dir = make_wiki_entity(tmp_path, pages={"identity.md": "Identity"})
        # Pre-populate index with a summary for identity
        (wiki_dir / "index.md").write_text(
            "---\ntitle: Index\n---\n\n| [[identity]] | Who I am and what I stand for |\n"
        )

        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        assert "Who I am and what I stand for" in content

    def test_reindex_returns_page_count(self, tmp_path):
        """reindex_wiki() returns a result with correct pages_total."""
        from entity_repo import reindex_wiki

        pages = {
            "identity.md": "Identity",
            "log.md": "Log",
            "domain/caching.md": "Caching",
        }
        wiki_dir = make_wiki_entity(tmp_path, pages=pages)
        result = reindex_wiki(wiki_dir, entity_name="testbot")

        assert result.pages_total == len(pages)

    def test_reindex_empty_subdirectory(self, tmp_path):
        """Sections with no pages render an empty table (headers only), not an error."""
        from entity_repo import reindex_wiki

        # Only create a core page; all subdirs are empty
        wiki_dir = make_wiki_entity(tmp_path, pages={"identity.md": "Identity"})
        reindex_wiki(wiki_dir, entity_name="testbot")

        content = (wiki_dir / "index.md").read_text()
        # All section headers should be present despite empty subdirs
        assert "## Domain Knowledge" in content
        assert "## Projects" in content
        assert "## Techniques" in content
        assert "## Relationships" in content

    def test_reindex_missing_wiki_dir_raises(self, tmp_path):
        """reindex_wiki() raises FileNotFoundError when wiki_dir does not exist."""
        from entity_repo import reindex_wiki

        with pytest.raises(FileNotFoundError):
            reindex_wiki(tmp_path / "nonexistent_wiki", entity_name="testbot")


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


class TestWikiReindexCli:

    def _make_entities_dir(self, tmp_path: Path, entity_name: str) -> Path:
        """Create a minimal .entities/ structure with a wiki entity."""
        entities_dir = tmp_path / ".entities"
        entity_dir = entities_dir / entity_name
        wiki_dir = entity_dir / "wiki"
        wiki_dir.mkdir(parents=True)
        for subdir in ("domain", "techniques", "projects", "relationships"):
            (wiki_dir / subdir).mkdir()
        (wiki_dir / "wiki_schema.md").write_text("# Schema\n")
        (wiki_dir / "identity.md").write_text(
            FRONTMATTER_TEMPLATE.format(title="Identity")
        )
        return tmp_path

    def test_cli_reindex_exits_zero(self, runner, tmp_path):
        """ve wiki reindex <entity> exits 0 for a valid wiki entity."""
        project_dir = self._make_entities_dir(tmp_path, "mybot")
        result = runner.invoke(
            cli,
            ["wiki", "reindex", "mybot", "--project-dir", str(project_dir)],
        )
        assert result.exit_code == 0, result.output
        assert "mybot" in result.output

    def test_cli_reindex_missing_entity_exits_nonzero(self, runner, tmp_path):
        """ve wiki reindex for an unknown entity exits non-zero."""
        # Create a valid project dir but with no entities
        (tmp_path / ".entities").mkdir()
        result = runner.invoke(
            cli,
            ["wiki", "reindex", "ghost", "--project-dir", str(tmp_path)],
        )
        assert result.exit_code != 0
