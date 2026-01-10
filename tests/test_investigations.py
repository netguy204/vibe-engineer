"""Tests for the Investigations class."""

import pytest


class TestInvestigationCreatedAfterPopulation:
    """Tests for created_after population during investigation creation.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_first_investigation_has_empty_created_after(self, temp_project):
        """When creating the first investigation, created_after is empty list."""
        from investigations import Investigations

        investigations = Investigations(temp_project)
        investigations.create_investigation("first_investigation")

        frontmatter = investigations.parse_investigation_frontmatter("first_investigation")
        assert frontmatter is not None
        assert frontmatter.created_after == []

    def test_second_investigation_references_first_as_created_after(self, temp_project):
        """When creating second investigation, created_after contains first investigation's name."""
        from investigations import Investigations

        investigations = Investigations(temp_project)
        investigations.create_investigation("first_investigation")
        investigations.create_investigation("second_investigation")

        frontmatter = investigations.parse_investigation_frontmatter("second_investigation")
        assert frontmatter is not None
        assert "first_investigation" in frontmatter.created_after


class TestInvestigationsCreateInvestigation:
    """Tests for Investigations.create_investigation() method.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_create_investigation_first_investigation(self, temp_project):
        """First investigation uses short_name only (no prefix)."""
        from investigations import Investigations

        investigations = Investigations(temp_project)
        result = investigations.create_investigation("memory_leak")

        expected_path = temp_project / "docs" / "investigations" / "memory_leak"
        assert result == expected_path
        assert expected_path.exists()
        assert (expected_path / "OVERVIEW.md").exists()

    def test_create_investigation_uses_short_name_only(self, temp_project):
        """Subsequent investigations use short_name only."""
        from investigations import Investigations

        investigations = Investigations(temp_project)

        # Create first investigation
        investigations.create_investigation("memory_leak")

        # Create second investigation
        result = investigations.create_investigation("graphql_migration")

        expected_path = temp_project / "docs" / "investigations" / "graphql_migration"
        assert result == expected_path
        assert expected_path.exists()

    def test_create_investigation_creates_directory_if_not_exists(self, temp_project):
        """Creates docs/investigations/ directory if it doesn't exist."""
        from investigations import Investigations

        investigations = Investigations(temp_project)
        # Ensure investigations directory doesn't exist
        investigations_dir = temp_project / "docs" / "investigations"
        assert not investigations_dir.exists()

        investigations.create_investigation("memory_leak")

        assert investigations_dir.exists()

    def test_create_investigation_overview_has_correct_frontmatter(self, temp_project):
        """Created OVERVIEW.md has correct frontmatter with ONGOING status."""
        from investigations import Investigations
        from models import InvestigationStatus

        investigations = Investigations(temp_project)
        result = investigations.create_investigation("memory_leak")

        frontmatter = investigations.parse_investigation_frontmatter("memory_leak")

        assert frontmatter is not None
        assert frontmatter.status == InvestigationStatus.ONGOING
        assert frontmatter.proposed_chunks == []


class TestInvestigationsParseInvestigationFrontmatter:
    """Tests for Investigations.parse_investigation_frontmatter() method."""

    def test_parse_frontmatter_valid(self, temp_project):
        """parse_investigation_frontmatter() returns validated frontmatter."""
        from investigations import Investigations
        from models import InvestigationStatus

        # Create a valid investigation with frontmatter
        investigations_dir = temp_project / "docs" / "investigations"
        investigation_path = investigations_dir / "0001-memory_leak"
        investigation_path.mkdir(parents=True)

        overview_content = """---
status: ONGOING
trigger: "Memory usage spikes during batch jobs"
proposed_chunks:
  - prompt: "Fix the ImageCache memory leak"
    chunk_directory: null
---

# Memory Leak Investigation
"""
        (investigation_path / "OVERVIEW.md").write_text(overview_content)

        investigations = Investigations(temp_project)
        frontmatter = investigations.parse_investigation_frontmatter("0001-memory_leak")

        assert frontmatter is not None
        assert frontmatter.status == InvestigationStatus.ONGOING
        assert frontmatter.trigger == "Memory usage spikes during batch jobs"
        assert len(frontmatter.proposed_chunks) == 1

    def test_parse_frontmatter_nonexistent(self, temp_project):
        """parse_investigation_frontmatter() returns None for non-existent investigation."""
        from investigations import Investigations

        investigations = Investigations(temp_project)
        result = investigations.parse_investigation_frontmatter("0001-nonexistent")
        assert result is None

    def test_parse_frontmatter_no_overview(self, temp_project):
        """parse_investigation_frontmatter() returns None when OVERVIEW.md is missing."""
        from investigations import Investigations

        # Create investigation directory without OVERVIEW.md
        investigations_dir = temp_project / "docs" / "investigations"
        investigation_path = investigations_dir / "0001-memory_leak"
        investigation_path.mkdir(parents=True)

        investigations = Investigations(temp_project)
        result = investigations.parse_investigation_frontmatter("0001-memory_leak")
        assert result is None

    def test_parse_frontmatter_invalid_frontmatter(self, temp_project):
        """parse_investigation_frontmatter() returns None for invalid frontmatter."""
        from investigations import Investigations

        # Create an investigation with invalid frontmatter
        investigations_dir = temp_project / "docs" / "investigations"
        investigation_path = investigations_dir / "0001-memory_leak"
        investigation_path.mkdir(parents=True)

        overview_content = """---
status: INVALID_STATUS
---

# Memory Leak Investigation
"""
        (investigation_path / "OVERVIEW.md").write_text(overview_content)

        investigations = Investigations(temp_project)
        result = investigations.parse_investigation_frontmatter("0001-memory_leak")
        assert result is None
