"""Tests for subsystem-related models and the Subsystems utility class."""

import pytest
from pydantic import ValidationError

from models import (
    SubsystemStatus,
    ChunkRelationship,
    SubsystemFrontmatter,
    SymbolicReference,
)


class TestChunkRelationship:
    """Tests for ChunkRelationship model."""

    def test_invalid_relationship_type(self):
        """Invalid relationship type (not 'implements' or 'uses') fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkRelationship(chunk_id="0003-feature", relationship="extends")
        assert "relationship" in str(exc_info.value).lower()

    def test_empty_chunk_id_fails(self):
        """Empty chunk_id fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkRelationship(chunk_id="", relationship="implements")
        assert "chunk_id" in str(exc_info.value).lower()

    def test_invalid_chunk_id_format_no_hyphen(self):
        """Invalid chunk_id format (missing hyphen) fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkRelationship(chunk_id="0003feature", relationship="implements")
        assert "chunk_id" in str(exc_info.value).lower()

    def test_invalid_chunk_id_format_short_number(self):
        """Invalid chunk_id format (less than 4 digits) fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkRelationship(chunk_id="003-feature", relationship="implements")
        assert "chunk_id" in str(exc_info.value).lower()

    def test_invalid_chunk_id_format_no_name(self):
        """Invalid chunk_id format (missing short name after hyphen) fails."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkRelationship(chunk_id="0003-", relationship="implements")
        assert "chunk_id" in str(exc_info.value).lower()


class TestSubsystemFrontmatter:
    """Tests for SubsystemFrontmatter model."""

    def test_invalid_status_value(self):
        """Invalid status value fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemFrontmatter(status="INVALID_STATUS")
        assert "status" in str(exc_info.value).lower()

    def test_invalid_chunk_relationship_propagates(self):
        """Invalid chunk relationship fails (propagates from ChunkRelationship).

        # Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
        """
        with pytest.raises(ValidationError) as exc_info:
            SubsystemFrontmatter(
                status=SubsystemStatus.DOCUMENTED,
                # Uppercase is invalid in new format
                chunks=[{"chunk_id": "INVALID_UPPERCASE", "relationship": "implements"}],
            )
        assert "chunk_id" in str(exc_info.value).lower()

    def test_invalid_code_reference_propagates(self):
        """Invalid code reference fails (propagates from SymbolicReference)."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemFrontmatter(
                status=SubsystemStatus.DOCUMENTED,
                code_references=[{"ref": "", "implements": "Something"}],
            )
        assert "ref" in str(exc_info.value).lower()


class TestSubsystems:
    """Tests for Subsystems utility class."""

    def test_subsystems_dir_property(self, temp_project):
        """subsystems_dir property returns docs/subsystems/ path."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        expected = temp_project / "docs" / "subsystems"
        assert subsystems.subsystems_dir == expected

    def test_enumerate_subsystems_empty(self, temp_project):
        """enumerate_subsystems() returns empty list when no subsystems exist."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        assert subsystems.enumerate_subsystems() == []

    def test_enumerate_subsystems_no_directory(self, temp_project):
        """enumerate_subsystems() returns empty list when directory doesn't exist."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        # Don't create the subsystems directory
        assert subsystems.enumerate_subsystems() == []

    def test_enumerate_subsystems_returns_list(self, temp_project):
        """enumerate_subsystems() returns list of subsystem directory names."""
        from subsystems import Subsystems

        # Create subsystems directory with some subsystems
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystems_dir.mkdir(parents=True)
        (subsystems_dir / "0001-validation").mkdir()
        (subsystems_dir / "0002-chunk_management").mkdir()

        subsystems = Subsystems(temp_project)
        result = subsystems.enumerate_subsystems()
        assert set(result) == {"0001-validation", "0002-chunk_management"}

    def test_is_subsystem_dir_valid_pattern(self, temp_project):
        """is_subsystem_dir() returns True for valid pattern."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        assert subsystems.is_subsystem_dir("0001-validation") is True
        assert subsystems.is_subsystem_dir("0123-some_feature") is True
        assert subsystems.is_subsystem_dir("9999-test") is True

    def test_is_subsystem_dir_invalid_patterns(self, temp_project):
        """is_subsystem_dir() returns False for invalid patterns.

        """
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        # Uppercase is invalid
        assert subsystems.is_subsystem_dir("INVALID_UPPERCASE") is False
        # Starting with number (but not 4 digits) is invalid
        assert subsystems.is_subsystem_dir("1abc") is False
        # Legacy 3-digit prefix still invalid
        assert subsystems.is_subsystem_dir("001-short") is False
        # No name after legacy hyphen
        assert subsystems.is_subsystem_dir("0001-") is False

    def test_parse_subsystem_frontmatter_valid(self, temp_project):
        """parse_subsystem_frontmatter() returns validated frontmatter."""
        from subsystems import Subsystems

        # Create a valid subsystem with frontmatter
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystem_path = subsystems_dir / "0001-validation"
        subsystem_path.mkdir(parents=True)

        overview_content = """---
status: DOCUMENTED
chunks:
  - chunk_id: "0001-setup"
    relationship: implements
code_references:
  - ref: src/validation.py#validate_input
    implements: Input validation logic
---

# Validation Subsystem

This subsystem handles validation logic.
"""
        (subsystem_path / "OVERVIEW.md").write_text(overview_content)

        subsystems = Subsystems(temp_project)
        frontmatter = subsystems.parse_subsystem_frontmatter("0001-validation")

        assert frontmatter is not None
        assert frontmatter.status == SubsystemStatus.DOCUMENTED
        assert len(frontmatter.chunks) == 1
        assert frontmatter.chunks[0].chunk_id == "0001-setup"
        assert len(frontmatter.code_references) == 1

    def test_parse_subsystem_frontmatter_nonexistent(self, temp_project):
        """parse_subsystem_frontmatter() returns None for non-existent subsystem."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        result = subsystems.parse_subsystem_frontmatter("0001-nonexistent")
        assert result is None

    def test_parse_subsystem_frontmatter_no_overview(self, temp_project):
        """parse_subsystem_frontmatter() returns None when OVERVIEW.md is missing."""
        from subsystems import Subsystems

        # Create subsystem directory without OVERVIEW.md
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystem_path = subsystems_dir / "0001-validation"
        subsystem_path.mkdir(parents=True)

        subsystems = Subsystems(temp_project)
        result = subsystems.parse_subsystem_frontmatter("0001-validation")
        assert result is None

    def test_parse_subsystem_frontmatter_invalid_frontmatter(self, temp_project):
        """parse_subsystem_frontmatter() returns None for invalid frontmatter."""
        from subsystems import Subsystems

        # Create a subsystem with invalid frontmatter
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystem_path = subsystems_dir / "0001-validation"
        subsystem_path.mkdir(parents=True)

        overview_content = """---
status: INVALID_STATUS
---

# Validation Subsystem
"""
        (subsystem_path / "OVERVIEW.md").write_text(overview_content)

        subsystems = Subsystems(temp_project)
        result = subsystems.parse_subsystem_frontmatter("0001-validation")
        assert result is None


class TestSubsystemCreatedAfterPopulation:
    """Tests for created_after population during subsystem creation.

    """

    def test_first_subsystem_has_empty_created_after(self, temp_project):
        """When creating the first subsystem, created_after is empty list."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        subsystems.create_subsystem("first_subsystem")

        frontmatter = subsystems.parse_subsystem_frontmatter("first_subsystem")
        assert frontmatter is not None
        assert frontmatter.created_after == []

    def test_second_subsystem_references_first_as_created_after(self, temp_project):
        """When creating second subsystem, created_after contains first subsystem's name."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        subsystems.create_subsystem("first_subsystem")
        subsystems.create_subsystem("second_subsystem")

        frontmatter = subsystems.parse_subsystem_frontmatter("second_subsystem")
        assert frontmatter is not None
        assert "first_subsystem" in frontmatter.created_after


class TestSubsystemsCreateSubsystem:
    """Tests for Subsystems.create_subsystem() method.

    """

    def test_create_subsystem_first_subsystem(self, temp_project):
        """First subsystem uses short_name only (no prefix)."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        result = subsystems.create_subsystem("validation")

        expected_path = temp_project / "docs" / "subsystems" / "validation"
        assert result == expected_path
        assert expected_path.exists()
        assert (expected_path / "OVERVIEW.md").exists()

    def test_create_subsystem_uses_short_name_only(self, temp_project):
        """Subsequent subsystems use short_name only."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)

        # Create first subsystem
        subsystems.create_subsystem("validation")

        # Create second subsystem
        result = subsystems.create_subsystem("frontmatter_updates")

        expected_path = temp_project / "docs" / "subsystems" / "frontmatter_updates"
        assert result == expected_path
        assert expected_path.exists()

    def test_create_subsystem_creates_directory_if_not_exists(self, temp_project):
        """Creates docs/subsystems/ directory if it doesn't exist."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        # Ensure subsystems directory doesn't exist
        subsystems_dir = temp_project / "docs" / "subsystems"
        assert not subsystems_dir.exists()

        subsystems.create_subsystem("validation")

        assert subsystems_dir.exists()

    def test_create_subsystem_overview_has_correct_frontmatter(self, temp_project):
        """Created OVERVIEW.md has correct frontmatter with DISCOVERING status."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        result = subsystems.create_subsystem("validation")

        overview_path = result / "OVERVIEW.md"
        frontmatter = subsystems.parse_subsystem_frontmatter("validation")

        assert frontmatter is not None
        assert frontmatter.status == SubsystemStatus.DISCOVERING
        assert frontmatter.chunks == []
        assert frontmatter.code_references == []


class TestSubsystemsFindByShortname:
    """Tests for Subsystems.find_by_shortname() method."""

    def test_find_by_shortname_returns_directory_name(self, temp_project):
        """Returns subsystem directory name if shortname exists."""
        from subsystems import Subsystems

        # Create a subsystem directory
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystems_dir.mkdir(parents=True)
        (subsystems_dir / "0001-validation").mkdir()
        (subsystems_dir / "0001-validation" / "OVERVIEW.md").touch()

        subsystems = Subsystems(temp_project)
        result = subsystems.find_by_shortname("validation")

        assert result == "0001-validation"

    def test_find_by_shortname_returns_none_if_not_found(self, temp_project):
        """Returns None if shortname doesn't exist."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        result = subsystems.find_by_shortname("nonexistent")

        assert result is None

    def test_find_by_shortname_handles_multiple_subsystems(self, temp_project):
        """Handles multiple subsystems correctly."""
        from subsystems import Subsystems

        # Create multiple subsystem directories
        subsystems_dir = temp_project / "docs" / "subsystems"
        subsystems_dir.mkdir(parents=True)
        (subsystems_dir / "0001-validation").mkdir()
        (subsystems_dir / "0002-chunk_management").mkdir()
        (subsystems_dir / "0003-frontmatter").mkdir()

        subsystems = Subsystems(temp_project)

        assert subsystems.find_by_shortname("validation") == "0001-validation"
        assert subsystems.find_by_shortname("chunk_management") == "0002-chunk_management"
        assert subsystems.find_by_shortname("frontmatter") == "0003-frontmatter"
        assert subsystems.find_by_shortname("nonexistent") is None


class TestValidateChunkRefs:
    """Tests for Subsystems.validate_chunk_refs() method."""

    def _write_subsystem_with_chunks(self, temp_project, subsystem_name, chunks):
        """Helper to write subsystem OVERVIEW.md with chunks frontmatter."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)
        overview_path = subsystem_path / "OVERVIEW.md"

        if chunks:
            chunks_yaml = "chunks:\n"
            for chunk in chunks:
                chunks_yaml += f"  - chunk_id: {chunk['chunk_id']}\n"
                chunks_yaml += f"    relationship: {chunk['relationship']}\n"
        else:
            chunks_yaml = "chunks: []"

        overview_path.write_text(f"""---
status: DOCUMENTED
{chunks_yaml}
code_references: []
---

# Subsystem
""")

    def _create_chunk(self, temp_project, chunk_name):
        """Helper to create a chunk directory with GOAL.md."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)
        (chunk_path / "GOAL.md").write_text("""---
status: IMPLEMENTING
code_references: []
---

# Chunk Goal
""")

    def test_empty_chunks_list_returns_no_errors(self, temp_project):
        """Empty chunks list returns no errors."""
        from subsystems import Subsystems

        self._write_subsystem_with_chunks(temp_project, "0001-validation", [])

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert errors == []

    def test_valid_chunk_reference_returns_no_errors(self, temp_project):
        """Valid chunk reference returns no errors."""
        from subsystems import Subsystems

        self._create_chunk(temp_project, "0001-feature")
        self._write_subsystem_with_chunks(temp_project, "0001-validation", [
            {"chunk_id": "0001-feature", "relationship": "implements"}
        ])

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert errors == []

    def test_nonexistent_chunk_reference_returns_error(self, temp_project):
        """Non-existent chunk reference returns error message."""
        from subsystems import Subsystems

        self._write_subsystem_with_chunks(temp_project, "0001-validation", [
            {"chunk_id": "0001-nonexistent", "relationship": "implements"}
        ])

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert len(errors) == 1
        assert "0001-nonexistent" in errors[0]
        assert "not found" in errors[0].lower() or "does not exist" in errors[0].lower()

    def test_multiple_valid_references_returns_no_errors(self, temp_project):
        """Multiple valid chunk references returns no errors."""
        from subsystems import Subsystems

        self._create_chunk(temp_project, "0001-feature")
        self._create_chunk(temp_project, "0002-enhancement")
        self._write_subsystem_with_chunks(temp_project, "0001-validation", [
            {"chunk_id": "0001-feature", "relationship": "implements"},
            {"chunk_id": "0002-enhancement", "relationship": "uses"},
        ])

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert errors == []

    def test_multiple_errors_collected(self, temp_project):
        """Multiple invalid references return multiple errors."""
        from subsystems import Subsystems

        self._write_subsystem_with_chunks(temp_project, "0001-validation", [
            {"chunk_id": "0001-nonexistent1", "relationship": "implements"},
            {"chunk_id": "0002-nonexistent2", "relationship": "uses"},
        ])

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert len(errors) == 2

    def test_subsystem_not_found_returns_empty(self, temp_project):
        """Non-existent subsystem returns empty list gracefully."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("9999-nonexistent")
        assert errors == []

    def test_subsystem_without_chunks_field_returns_no_errors(self, temp_project):
        """Subsystem without chunks field returns no errors (backward compat)."""
        from subsystems import Subsystems

        subsystem_path = temp_project / "docs" / "subsystems" / "0001-validation"
        subsystem_path.mkdir(parents=True, exist_ok=True)
        (subsystem_path / "OVERVIEW.md").write_text("""---
status: DOCUMENTED
code_references: []
---

# Subsystem
""")

        subsystems = Subsystems(temp_project)
        errors = subsystems.validate_chunk_refs("0001-validation")
        assert errors == []
