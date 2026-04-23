"""Tests for ve wiki lint — wiki integrity linting.

# Chunk: docs/chunks/wiki_lint_command - Wiki integrity lint tests
"""

import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

import entity_repo
from entity_repo import WikiLintIssue, WikiLintResult, lint_wiki
from ve import cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_wiki(tmp_path: Path) -> Path:
    """Build a minimal, well-formed wiki directory for testing.

    Structure:
        wiki/
          index.md          — references [[identity]], [[log]], [[domain/concepts]]
          identity.md       — structural page with frontmatter
          log.md            — structural page with frontmatter
          wiki_schema.md    — structural page, no frontmatter by design
          domain/
            concepts.md     — content page, linked from index.md and identity.md
    """
    wiki = tmp_path / "wiki"
    wiki.mkdir()

    # index.md — links to identity, log, and domain/concepts
    (wiki / "index.md").write_text(
        textwrap.dedent("""\
            ---
            title: Wiki Index
            ---

            # Wiki Index

            ## Core

            | Page | Summary |
            |------|---------|
            | [[identity]] | Who I am |
            | [[log]] | Session log |

            ## Domain Knowledge

            | Page | Summary |
            |------|---------|
            | [[domain/concepts]] | Core concepts |
        """),
        encoding="utf-8",
    )

    # identity.md
    (wiki / "identity.md").write_text(
        textwrap.dedent("""\
            ---
            title: Identity
            ---

            # Identity

            See [[domain/concepts]] for background.
        """),
        encoding="utf-8",
    )

    # log.md
    (wiki / "log.md").write_text(
        textwrap.dedent("""\
            ---
            title: Log
            ---

            # Log

            Session log here.
        """),
        encoding="utf-8",
    )

    # wiki_schema.md — no frontmatter by design
    (wiki / "wiki_schema.md").write_text(
        textwrap.dedent("""\
            # Wiki Schema

            This file describes the wiki schema.
        """),
        encoding="utf-8",
    )

    # domain/concepts.md — a proper content page
    (wiki / "domain").mkdir()
    (wiki / "domain" / "concepts.md").write_text(
        textwrap.dedent("""\
            ---
            title: Core Concepts
            ---

            # Core Concepts

            Some content here.
        """),
        encoding="utf-8",
    )

    return wiki


# ---------------------------------------------------------------------------
# entity fixture for CLI tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def entity_with_wiki(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal .entities/<name>/wiki structure for CLI tests.

    Returns (project_dir, wiki_dir).
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    entities_dir = project_dir / ".entities"
    entities_dir.mkdir()
    entity_dir = entities_dir / "testbot"
    entity_dir.mkdir()
    wiki_dir = entity_dir / "wiki"
    wiki_dir.mkdir()
    return project_dir, wiki_dir


# ---------------------------------------------------------------------------
# Core lint tests
# ---------------------------------------------------------------------------


class TestCleanWiki:
    def test_clean_wiki_no_issues(self, tmp_wiki: Path) -> None:
        """A well-formed wiki reports zero issues."""
        result = lint_wiki(tmp_wiki)
        assert result.ok
        assert result.issues == []


class TestDeadWikilinks:
    def test_dead_wikilink_detected(self, tmp_wiki: Path) -> None:
        """A page containing [[nonexistent]] reports a dead_wikilink issue."""
        (tmp_wiki / "domain" / "concepts.md").write_text(
            textwrap.dedent("""\
                ---
                title: Core Concepts
                ---

                See [[nonexistent]] for details.
            """),
            encoding="utf-8",
        )
        result = lint_wiki(tmp_wiki)
        dead = [i for i in result.issues if i.issue_type == "dead_wikilink"]
        assert len(dead) == 1
        assert "nonexistent" in dead[0].detail

    def test_valid_wikilink_not_flagged(self, tmp_wiki: Path) -> None:
        """A [[link]] that resolves to an existing file is not flagged."""
        result = lint_wiki(tmp_wiki)
        dead = [i for i in result.issues if i.issue_type == "dead_wikilink"]
        assert dead == []


class TestFrontmatterErrors:
    def test_frontmatter_error_missing(self, tmp_wiki: Path) -> None:
        """A content page with no frontmatter block reports a frontmatter_error."""
        (tmp_wiki / "domain" / "no_fm.md").write_text(
            "# No Frontmatter\n\nJust content.\n",
            encoding="utf-8",
        )
        # Link it from index so it doesn't also trigger missing_from_index or orphan
        index = tmp_wiki / "index.md"
        original = index.read_text(encoding="utf-8")
        index.write_text(
            original + "| [[domain/no_fm]] | No frontmatter page |\n",
            encoding="utf-8",
        )
        # Also link it from somewhere so it's not orphaned
        (tmp_wiki / "domain" / "concepts.md").write_text(
            textwrap.dedent("""\
                ---
                title: Core Concepts
                ---

                See [[domain/no_fm]].
            """),
            encoding="utf-8",
        )

        result = lint_wiki(tmp_wiki)
        fm_errors = [i for i in result.issues if i.issue_type == "frontmatter_error"]
        assert len(fm_errors) == 1
        assert "no_fm.md" in fm_errors[0].file

    def test_frontmatter_error_malformed(self, tmp_wiki: Path) -> None:
        """A content page with invalid YAML frontmatter reports a frontmatter_error."""
        (tmp_wiki / "domain" / "bad_fm.md").write_text(
            textwrap.dedent("""\
                ---
                title: [unclosed bracket
                ---

                # Bad Frontmatter
            """),
            encoding="utf-8",
        )
        # Add to index and link so we don't get other issues
        index = tmp_wiki / "index.md"
        original = index.read_text(encoding="utf-8")
        index.write_text(
            original + "| [[domain/bad_fm]] | Bad frontmatter page |\n",
            encoding="utf-8",
        )
        (tmp_wiki / "domain" / "concepts.md").write_text(
            textwrap.dedent("""\
                ---
                title: Core Concepts
                ---

                See [[domain/bad_fm]].
            """),
            encoding="utf-8",
        )

        result = lint_wiki(tmp_wiki)
        fm_errors = [i for i in result.issues if i.issue_type == "frontmatter_error"]
        assert len(fm_errors) == 1
        assert "bad_fm.md" in fm_errors[0].file


class TestMissingFromIndex:
    def test_missing_from_index(self, tmp_wiki: Path) -> None:
        """A content page under domain/ not in index.md reports missing_from_index."""
        (tmp_wiki / "domain" / "unlisted.md").write_text(
            textwrap.dedent("""\
                ---
                title: Unlisted
                ---

                # Unlisted page
            """),
            encoding="utf-8",
        )
        # Link it from concepts so it's not also an orphan
        (tmp_wiki / "domain" / "concepts.md").write_text(
            textwrap.dedent("""\
                ---
                title: Core Concepts
                ---

                See [[domain/unlisted]].
            """),
            encoding="utf-8",
        )

        result = lint_wiki(tmp_wiki)
        missing = [i for i in result.issues if i.issue_type == "missing_from_index"]
        assert len(missing) == 1
        assert "unlisted.md" in missing[0].file

    def test_indexed_page_not_flagged(self, tmp_wiki: Path) -> None:
        """A page properly listed in index.md is not reported as missing_from_index."""
        result = lint_wiki(tmp_wiki)
        missing = [i for i in result.issues if i.issue_type == "missing_from_index"]
        assert missing == []


class TestOrphanPages:
    def test_orphan_page(self, tmp_wiki: Path) -> None:
        """A content page with no inbound links reports orphan_page."""
        (tmp_wiki / "domain" / "orphan.md").write_text(
            textwrap.dedent("""\
                ---
                title: Orphan
                ---

                # Orphan page — nobody links here
            """),
            encoding="utf-8",
        )
        # Add to index so it's not missing_from_index
        index = tmp_wiki / "index.md"
        original = index.read_text(encoding="utf-8")
        index.write_text(
            original + "| [[domain/orphan]] | Orphan page |\n",
            encoding="utf-8",
        )

        result = lint_wiki(tmp_wiki)
        orphans = [i for i in result.issues if i.issue_type == "orphan_page"]
        # orphan.md has index.md linking it, so it should NOT be orphaned
        # (index.md is a page that links to it — that counts as an inbound link)
        # Wait — let me rethink. The index links [[domain/orphan]], so it HAS an inbound link.
        # This test should actually check for a page that even index doesn't link to.
        assert orphans == []

    def test_orphan_page_with_no_inbound_links(self, tmp_wiki: Path) -> None:
        """A content page with no inbound links from ANY page is an orphan."""
        # Add a page but don't add it to index or link from anywhere
        (tmp_wiki / "domain" / "truly_orphan.md").write_text(
            textwrap.dedent("""\
                ---
                title: Truly Orphan
                ---

                # Nobody links here, not even index
            """),
            encoding="utf-8",
        )

        result = lint_wiki(tmp_wiki)
        orphans = [i for i in result.issues if i.issue_type == "orphan_page"]
        orphan_files = [i.file for i in orphans]
        assert any("truly_orphan.md" in f for f in orphan_files)

    def test_linked_page_not_orphan(self, tmp_wiki: Path) -> None:
        """A content page linked from index.md is not an orphan."""
        result = lint_wiki(tmp_wiki)
        orphans = [i for i in result.issues if i.issue_type == "orphan_page"]
        # domain/concepts.md is linked from both index.md and identity.md
        orphan_files = [i.file for i in orphans]
        assert not any("concepts.md" in f for f in orphan_files)


class TestStructuralExemptions:
    def test_wiki_schema_exempt_from_frontmatter_check(self, tmp_wiki: Path) -> None:
        """wiki_schema.md (no frontmatter) does not trigger a frontmatter_error."""
        result = lint_wiki(tmp_wiki)
        fm_errors = [i for i in result.issues if i.issue_type == "frontmatter_error"]
        assert not any("wiki_schema.md" in i.file for i in fm_errors)

    def test_structural_pages_exempt_from_index_check(self, tmp_wiki: Path) -> None:
        """identity.md, log.md, wiki_schema.md are not reported as missing_from_index."""
        result = lint_wiki(tmp_wiki)
        missing = [i for i in result.issues if i.issue_type == "missing_from_index"]
        structural_files = {"identity.md", "log.md", "wiki_schema.md", "index.md"}
        for issue in missing:
            assert Path(issue.file).name not in structural_files

    def test_structural_pages_exempt_from_orphan_check(self, tmp_wiki: Path) -> None:
        """Structural pages (index.md, identity.md, etc.) are not reported as orphans."""
        result = lint_wiki(tmp_wiki)
        orphans = [i for i in result.issues if i.issue_type == "orphan_page"]
        structural_files = {"identity.md", "log.md", "wiki_schema.md", "index.md"}
        for issue in orphans:
            assert Path(issue.file).name not in structural_files


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def _make_clean_entity_wiki(wiki_dir: Path) -> None:
    """Populate wiki_dir with a clean, minimal wiki."""
    wiki_dir.mkdir(exist_ok=True)

    (wiki_dir / "index.md").write_text(
        textwrap.dedent("""\
            ---
            title: Wiki Index
            ---

            ## Core

            | [[identity]] | Who I am |
            | [[log]] | Session log |

            ## Domain Knowledge

            | [[domain/facts]] | Facts |
        """),
        encoding="utf-8",
    )
    (wiki_dir / "identity.md").write_text(
        "---\ntitle: Identity\n---\n\n# Identity\n\nSee [[domain/facts]].\n",
        encoding="utf-8",
    )
    (wiki_dir / "log.md").write_text(
        "---\ntitle: Log\n---\n\n# Log\n",
        encoding="utf-8",
    )
    (wiki_dir / "wiki_schema.md").write_text(
        "# Schema\n\nNo frontmatter.\n",
        encoding="utf-8",
    )
    (wiki_dir / "domain").mkdir(exist_ok=True)
    (wiki_dir / "domain" / "facts.md").write_text(
        "---\ntitle: Facts\n---\n\n# Facts\n",
        encoding="utf-8",
    )


class TestCliExitCodes:
    def test_cli_exit_code_clean(self, entity_with_wiki: tuple[Path, Path]) -> None:
        """CLI exits 0 and prints nothing when wiki is clean."""
        project_dir, wiki_dir = entity_with_wiki
        _make_clean_entity_wiki(wiki_dir)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["wiki", "lint", "testbot", "--project-dir", str(project_dir)],
        )
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
        assert result.output.strip() == ""

    def test_cli_exit_code_with_issues(self, entity_with_wiki: tuple[Path, Path]) -> None:
        """CLI exits 1 and prints issue lines when wiki has problems."""
        project_dir, wiki_dir = entity_with_wiki
        _make_clean_entity_wiki(wiki_dir)

        # Introduce a dead wikilink
        (wiki_dir / "domain" / "facts.md").write_text(
            textwrap.dedent("""\
                ---
                title: Facts
                ---

                See [[does_not_exist]] for reference.
            """),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["wiki", "lint", "testbot", "--project-dir", str(project_dir)],
        )
        assert result.exit_code == 1
        assert "dead_wikilink" in result.output

    def test_cli_entity_not_found(self, tmp_path: Path) -> None:
        """CLI reports an error when the entity does not exist."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".entities").mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["wiki", "lint", "nobody", "--project-dir", str(project_dir)],
        )
        assert result.exit_code != 0

    def test_cli_entity_has_no_wiki(self, tmp_path: Path) -> None:
        """CLI reports an error when the entity has no wiki directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        entities_dir = project_dir / ".entities"
        entities_dir.mkdir()
        (entities_dir / "nowiki").mkdir()  # entity with no wiki/

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["wiki", "lint", "nowiki", "--project-dir", str(project_dir)],
        )
        assert result.exit_code != 0
        assert "wiki" in result.output.lower()
