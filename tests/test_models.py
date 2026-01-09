"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from models import SymbolicReference, SubsystemRelationship, InvestigationFrontmatter, InvestigationStatus


class TestSymbolicReference:
    """Tests for SymbolicReference model."""

    def test_invalid_empty_ref(self):
        """Empty ref string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="", implements="Something")
        assert "ref cannot be empty" in str(exc_info.value)

    def test_invalid_missing_file_path(self):
        """Reference starting with # (missing file path) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="#SomeClass", implements="Something")
        assert "must start with a file path" in str(exc_info.value)

    def test_invalid_empty_symbol_after_hash(self):
        """Reference with empty symbol after # is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#", implements="Something")
        assert "symbol path cannot be empty" in str(exc_info.value)

    def test_invalid_empty_implements(self):
        """Empty implements field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py", implements="")
        assert "implements" in str(exc_info.value).lower()

    def test_invalid_missing_implements(self):
        """Missing implements field is rejected."""
        with pytest.raises(ValidationError):
            SymbolicReference(ref="src/foo.py")

    def test_multiple_hashes_rejected(self):
        """Reference with multiple # characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#Bar#baz", implements="Something")
        assert "cannot contain multiple #" in str(exc_info.value)

    def test_symbol_with_empty_part_rejected(self):
        """Symbol path with empty part (::Foo or Foo::) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#::Foo", implements="Something")
        assert "empty component" in str(exc_info.value).lower()

        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="src/foo.py#Foo::", implements="Something")
        assert "empty component" in str(exc_info.value).lower()


class TestSubsystemRelationship:
    """Tests for SubsystemRelationship model (inverse of ChunkRelationship)."""

    def test_invalid_relationship_type(self):
        """Invalid relationship type (not 'implements' or 'uses') fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemRelationship(subsystem_id="0001-validation", relationship="extends")
        assert "relationship" in str(exc_info.value).lower()

    def test_empty_subsystem_id_fails(self):
        """Empty subsystem_id fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemRelationship(subsystem_id="", relationship="implements")
        assert "subsystem_id" in str(exc_info.value).lower()

    def test_invalid_subsystem_id_format_no_hyphen(self):
        """Invalid subsystem_id format (missing hyphen) fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemRelationship(subsystem_id="0001validation", relationship="implements")
        assert "subsystem_id" in str(exc_info.value).lower()

    def test_invalid_subsystem_id_format_short_number(self):
        """Invalid subsystem_id format (less than 4 digits) fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemRelationship(subsystem_id="001-validation", relationship="implements")
        assert "subsystem_id" in str(exc_info.value).lower()

    def test_invalid_subsystem_id_format_no_name(self):
        """Invalid subsystem_id format (missing short name after hyphen) fails."""
        with pytest.raises(ValidationError) as exc_info:
            SubsystemRelationship(subsystem_id="0001-", relationship="implements")
        assert "subsystem_id" in str(exc_info.value).lower()


class TestInvestigationFrontmatter:
    """Tests for InvestigationFrontmatter model validation."""

    def test_invalid_status_value_rejected(self):
        """Invalid status value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvestigationFrontmatter(status="INVALID_STATUS")
        assert "status" in str(exc_info.value).lower()

    def test_missing_status_rejected(self):
        """Missing status field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InvestigationFrontmatter()
        assert "status" in str(exc_info.value).lower()

    def test_valid_frontmatter_parses_successfully(self):
        """Valid frontmatter with all fields parses correctly."""
        frontmatter = InvestigationFrontmatter(
            status=InvestigationStatus.ONGOING,
            trigger="Test failures after upgrade",
            proposed_chunks=[
                {"prompt": "Fix the memory leak", "chunk_directory": None}
            ]
        )
        assert frontmatter.status == InvestigationStatus.ONGOING
        assert frontmatter.trigger == "Test failures after upgrade"
        assert len(frontmatter.proposed_chunks) == 1

    def test_proposed_chunks_defaults_to_empty_list(self):
        """proposed_chunks defaults to empty list when not provided."""
        frontmatter = InvestigationFrontmatter(status=InvestigationStatus.SOLVED)
        assert frontmatter.proposed_chunks == []

    def test_trigger_defaults_to_none(self):
        """trigger defaults to None when not provided."""
        frontmatter = InvestigationFrontmatter(status=InvestigationStatus.NOTED)
        assert frontmatter.trigger is None
