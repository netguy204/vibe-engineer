"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from models import (
    SymbolicReference,
    SubsystemRelationship,
    InvestigationFrontmatter,
    InvestigationStatus,
    ChunkFrontmatter,
    ChunkStatus,
    NarrativeFrontmatter,
    NarrativeStatus,
    SubsystemFrontmatter,
    SubsystemStatus,
)


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


# Chunk: docs/chunks/chunk_frontmatter_model - Test suite for ChunkFrontmatter
class TestChunkFrontmatter:
    """Tests for ChunkFrontmatter model validation."""

    def test_invalid_status_value_rejected(self):
        """Invalid status value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkFrontmatter(status="INVALID_STATUS")
        assert "status" in str(exc_info.value).lower()

    def test_missing_status_rejected(self):
        """Missing status field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkFrontmatter()
        assert "status" in str(exc_info.value).lower()

    def test_valid_frontmatter_parses_successfully(self):
        """Valid frontmatter with all fields parses correctly."""
        # Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            ticket="VE-123",
            parent_chunk="0001-previous_chunk",
            code_paths=["src/foo.py", "src/bar.py"],
            code_references=[
                {"ref": "src/foo.py#Foo", "implements": "Main logic"}
            ],
            narrative="0001-my_narrative",
            subsystems=[
                {"subsystem_id": "0001-validation", "relationship": "implements"}
            ],
            proposed_chunks=[
                {"prompt": "Fix the bug", "chunk_directory": None}
            ],
            dependents=[
                {"artifact_type": "chunk", "artifact_id": "integration", "repo": "acme/service-a"}
            ]
        )
        assert frontmatter.status == ChunkStatus.IMPLEMENTING
        assert frontmatter.ticket == "VE-123"
        assert frontmatter.parent_chunk == "0001-previous_chunk"
        assert len(frontmatter.code_paths) == 2
        assert len(frontmatter.code_references) == 1
        assert frontmatter.narrative == "0001-my_narrative"
        assert len(frontmatter.subsystems) == 1
        assert len(frontmatter.proposed_chunks) == 1
        assert len(frontmatter.dependents) == 1

    def test_optional_fields_default_correctly(self):
        """Optional fields default to None or empty lists."""
        frontmatter = ChunkFrontmatter(status=ChunkStatus.ACTIVE)
        assert frontmatter.ticket is None
        assert frontmatter.parent_chunk is None
        assert frontmatter.code_paths == []
        assert frontmatter.code_references == []
        assert frontmatter.narrative is None
        assert frontmatter.subsystems == []
        assert frontmatter.proposed_chunks == []
        assert frontmatter.dependents == []

    def test_all_status_values_accepted(self):
        """All valid status values are accepted."""
        for status in ChunkStatus:
            frontmatter = ChunkFrontmatter(status=status)
            assert frontmatter.status == status

    def test_lowercase_status_rejected(self):
        """Lowercase status values are rejected (case-sensitive enum)."""
        with pytest.raises(ValidationError):
            ChunkFrontmatter(status="implementing")

    def test_created_after_defaults_to_empty_list(self):
        """created_after defaults to empty list when not provided."""
        frontmatter = ChunkFrontmatter(status=ChunkStatus.ACTIVE)
        assert frontmatter.created_after == []

    def test_created_after_accepts_list_of_strings(self):
        """created_after accepts a list of short name strings."""
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            created_after=["chunk_frontmatter_model", "proposed_chunks_frontmatter"]
        )
        assert frontmatter.created_after == ["chunk_frontmatter_model", "proposed_chunks_frontmatter"]


class TestNarrativeFrontmatterCreatedAfter:
    """Tests for created_after field in NarrativeFrontmatter."""

    def test_created_after_defaults_to_empty_list(self):
        """created_after defaults to empty list when not provided."""
        frontmatter = NarrativeFrontmatter(status=NarrativeStatus.ACTIVE)
        assert frontmatter.created_after == []

    def test_created_after_accepts_list_of_strings(self):
        """created_after accepts a list of short name strings."""
        frontmatter = NarrativeFrontmatter(
            status=NarrativeStatus.DRAFTING,
            created_after=["some_artifact", "another_artifact"]
        )
        assert frontmatter.created_after == ["some_artifact", "another_artifact"]


class TestInvestigationFrontmatterCreatedAfter:
    """Tests for created_after field in InvestigationFrontmatter."""

    def test_created_after_defaults_to_empty_list(self):
        """created_after defaults to empty list when not provided."""
        frontmatter = InvestigationFrontmatter(status=InvestigationStatus.ONGOING)
        assert frontmatter.created_after == []

    def test_created_after_accepts_list_of_strings(self):
        """created_after accepts a list of short name strings."""
        frontmatter = InvestigationFrontmatter(
            status=InvestigationStatus.SOLVED,
            created_after=["memory_leak_investigation", "another_one"]
        )
        assert frontmatter.created_after == ["memory_leak_investigation", "another_one"]


class TestSubsystemFrontmatterCreatedAfter:
    """Tests for created_after field in SubsystemFrontmatter."""

    def test_created_after_defaults_to_empty_list(self):
        """created_after defaults to empty list when not provided."""
        frontmatter = SubsystemFrontmatter(status=SubsystemStatus.DOCUMENTED)
        assert frontmatter.created_after == []

    def test_created_after_accepts_list_of_strings(self):
        """created_after accepts a list of short name strings."""
        frontmatter = SubsystemFrontmatter(
            status=SubsystemStatus.STABLE,
            created_after=["template_system", "frontmatter_parsing"]
        )
        assert frontmatter.created_after == ["template_system", "frontmatter_parsing"]


# Chunk: docs/chunks/project_qualified_refs - Project-qualified SymbolicReference tests
class TestSymbolicReferenceWithProjectQualification:
    """Tests for SymbolicReference with project-qualified paths."""

    def test_valid_project_qualified_with_class(self):
        """Project-qualified class reference validates successfully."""
        ref = SymbolicReference(ref="acme/proj::src/foo.py#Bar", implements="Something")
        assert ref.ref == "acme/proj::src/foo.py#Bar"

    def test_valid_project_qualified_file_only(self):
        """Project-qualified file-only reference validates successfully."""
        ref = SymbolicReference(ref="acme/proj::src/foo.py", implements="Something")
        assert ref.ref == "acme/proj::src/foo.py"

    def test_valid_project_qualified_with_nested_symbol(self):
        """Project-qualified nested symbol reference validates successfully."""
        ref = SymbolicReference(ref="acme/proj::src/foo.py#Bar::baz", implements="Something")
        assert ref.ref == "acme/proj::src/foo.py#Bar::baz"

    def test_backward_compatible_local_reference(self):
        """Non-qualified local reference still validates."""
        ref = SymbolicReference(ref="src/foo.py#Bar", implements="Something")
        assert ref.ref == "src/foo.py#Bar"

    def test_invalid_empty_project_qualifier(self):
        """Reference with empty project qualifier (::path) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="::src/foo.py", implements="Something")
        assert "project qualifier cannot be empty" in str(exc_info.value).lower()

    def test_invalid_project_format_no_slash(self):
        """Project qualifier without org/repo format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="justproject::src/foo.py", implements="Something")
        assert "org/repo" in str(exc_info.value).lower()

    def test_invalid_project_format_multiple_slashes(self):
        """Project qualifier with multiple slashes is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="org/repo/extra::src/foo.py", implements="Something")
        assert "slash" in str(exc_info.value).lower() or "org/repo" in str(exc_info.value).lower()

    def test_invalid_project_empty_org(self):
        """Project qualifier with empty org (/repo) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="/repo::src/foo.py", implements="Something")
        assert "org" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_invalid_project_empty_repo(self):
        """Project qualifier with empty repo (org/) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="org/::src/foo.py", implements="Something")
        assert "repo" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_invalid_multiple_double_colon(self):
        """Reference with multiple :: before # is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="acme/a::b/c::src/foo.py", implements="Something")
        # The second :: would be treated as part of the file path which is fine,
        # but actually this creates ambiguity. Let me rethink...
        # Actually per the plan: "Multiple :: delimiters should be invalid"
        assert "multiple" in str(exc_info.value).lower() or "::" in str(exc_info.value)

    def test_valid_complex_project_names(self):
        """Project with dots and hyphens in names validates."""
        ref = SymbolicReference(ref="my-org/my.project::src/foo.py#Bar", implements="Something")
        assert ref.ref == "my-org/my.project::src/foo.py#Bar"
