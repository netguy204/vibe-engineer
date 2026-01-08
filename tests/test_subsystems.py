"""Tests for subsystem-related models and the Subsystems utility class."""

import pytest
from pydantic import ValidationError

from models import (
    SubsystemStatus,
    ChunkRelationship,
    SubsystemFrontmatter,
    SymbolicReference,
)


class TestSubsystemStatus:
    """Tests for SubsystemStatus enum."""

    def test_all_status_values_exist(self):
        """Verify all five status values exist."""
        assert SubsystemStatus.DISCOVERING.value == "DISCOVERING"
        assert SubsystemStatus.DOCUMENTED.value == "DOCUMENTED"
        assert SubsystemStatus.REFACTORING.value == "REFACTORING"
        assert SubsystemStatus.STABLE.value == "STABLE"
        assert SubsystemStatus.DEPRECATED.value == "DEPRECATED"

    def test_enum_is_string_enum(self):
        """Verify the enum is a string enum for YAML serialization."""
        # StrEnum values should be strings
        assert isinstance(SubsystemStatus.DISCOVERING.value, str)
        assert str(SubsystemStatus.DISCOVERING) == "DISCOVERING"


class TestChunkRelationship:
    """Tests for ChunkRelationship model."""

    def test_valid_implements_relationship(self):
        """Valid chunk_id with 'implements' relationship passes."""
        rel = ChunkRelationship(chunk_id="0003-feature_name", relationship="implements")
        assert rel.chunk_id == "0003-feature_name"
        assert rel.relationship == "implements"

    def test_valid_uses_relationship(self):
        """Valid chunk_id with 'uses' relationship passes."""
        rel = ChunkRelationship(chunk_id="0001-initial_setup", relationship="uses")
        assert rel.chunk_id == "0001-initial_setup"
        assert rel.relationship == "uses"

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

    def test_valid_frontmatter_all_fields(self):
        """Valid frontmatter with all fields passes."""
        frontmatter = SubsystemFrontmatter(
            status=SubsystemStatus.DOCUMENTED,
            chunks=[
                ChunkRelationship(chunk_id="0001-setup", relationship="implements"),
                ChunkRelationship(chunk_id="0002-feature", relationship="uses"),
            ],
            code_references=[
                SymbolicReference(ref="src/foo.py#Bar", implements="Bar class"),
            ],
        )
        assert frontmatter.status == SubsystemStatus.DOCUMENTED
        assert len(frontmatter.chunks) == 2
        assert len(frontmatter.code_references) == 1

    def test_valid_frontmatter_empty_chunks(self):
        """Valid frontmatter with empty chunks list passes."""
        frontmatter = SubsystemFrontmatter(
            status=SubsystemStatus.DISCOVERING,
            chunks=[],
            code_references=[],
        )
        assert frontmatter.status == SubsystemStatus.DISCOVERING
        assert frontmatter.chunks == []

    def test_valid_frontmatter_empty_code_references(self):
        """Valid frontmatter with empty code_references list passes."""
        frontmatter = SubsystemFrontmatter(
            status=SubsystemStatus.STABLE,
            chunks=[ChunkRelationship(chunk_id="0001-test", relationship="implements")],
            code_references=[],
        )
        assert frontmatter.code_references == []

    def test_valid_frontmatter_defaults(self):
        """Valid frontmatter with only required field (status) uses defaults."""
        frontmatter = SubsystemFrontmatter(status=SubsystemStatus.DISCOVERING)
        assert frontmatter.chunks == []
        assert frontmatter.code_references == []

    def test_invalid_status_value(self):
        """Invalid status value fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemFrontmatter(status="INVALID_STATUS")
        assert "status" in str(exc_info.value).lower()

    def test_invalid_chunk_relationship_propagates(self):
        """Invalid chunk relationship fails (propagates from ChunkRelationship)."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemFrontmatter(
                status=SubsystemStatus.DOCUMENTED,
                chunks=[{"chunk_id": "invalid", "relationship": "implements"}],
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
        """is_subsystem_dir() returns False for invalid patterns."""
        from subsystems import Subsystems

        subsystems = Subsystems(temp_project)
        assert subsystems.is_subsystem_dir("invalid") is False
        assert subsystems.is_subsystem_dir("001-short") is False  # Only 3 digits
        assert subsystems.is_subsystem_dir("0001_underscore") is False  # Underscore instead of hyphen
        assert subsystems.is_subsystem_dir("0001-") is False  # No name after hyphen

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
