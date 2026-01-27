"""Tests for Pydantic models."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

import pytest
from pydantic import ValidationError

from models import (
    SymbolicReference,
    SubsystemRelationship,
    InvestigationFrontmatter,
    InvestigationStatus,
    ChunkFrontmatter,
    ChunkStatus,
    BugType,
    NarrativeFrontmatter,
    NarrativeStatus,
    SubsystemFrontmatter,
    SubsystemStatus,
    FrictionTheme,
    FrictionProposedChunk,
    FrictionFrontmatter,
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


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
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
        # Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
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


class TestChunkFrontmatterBugType:
    """Tests for bug_type field in ChunkFrontmatter."""

    def test_valid_bug_type_semantic(self):
        """bug_type: semantic is accepted."""
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            bug_type=BugType.SEMANTIC
        )
        assert frontmatter.bug_type == BugType.SEMANTIC

    def test_valid_bug_type_implementation(self):
        """bug_type: implementation is accepted."""
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.ACTIVE,
            bug_type=BugType.IMPLEMENTATION
        )
        assert frontmatter.bug_type == BugType.IMPLEMENTATION

    def test_bug_type_defaults_to_none(self):
        """bug_type defaults to None when not provided (optional field)."""
        frontmatter = ChunkFrontmatter(status=ChunkStatus.IMPLEMENTING)
        assert frontmatter.bug_type is None

    def test_invalid_bug_type_rejected(self):
        """Invalid bug_type values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkFrontmatter(status=ChunkStatus.IMPLEMENTING, bug_type="invalid")
        assert "bug_type" in str(exc_info.value).lower()

    def test_bug_type_string_values_accepted(self):
        """bug_type accepts string values that match enum values."""
        # Pydantic accepts the string "semantic" and converts to enum
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            bug_type="semantic"
        )
        assert frontmatter.bug_type == BugType.SEMANTIC

        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            bug_type="implementation"
        )
        assert frontmatter.bug_type == BugType.IMPLEMENTATION

    def test_bug_type_uppercase_rejected(self):
        """Uppercase bug_type values are rejected (case-sensitive enum)."""
        with pytest.raises(ValidationError):
            ChunkFrontmatter(status=ChunkStatus.IMPLEMENTING, bug_type="SEMANTIC")

    def test_bug_type_in_full_frontmatter(self):
        """bug_type works correctly in full frontmatter with all fields."""
        frontmatter = ChunkFrontmatter(
            status=ChunkStatus.IMPLEMENTING,
            ticket="BUG-123",
            code_paths=["src/foo.py"],
            bug_type=BugType.SEMANTIC
        )
        assert frontmatter.bug_type == BugType.SEMANTIC
        assert frontmatter.ticket == "BUG-123"


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


class TestSymbolicReferenceOrgRepoErrorMessages:
    """Tests for improved error messages when project qualifier is not in org/repo format."""

    def test_short_project_name_shows_helpful_error(self):
        """Short project name like 'pybusiness' produces error mentioning org/repo format."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="pybusiness::src/foo.py", implements="Something")
        error_str = str(exc_info.value)
        # Should mention org/repo format
        assert "org/repo" in error_str
        # Should include the actual invalid value
        assert "pybusiness" in error_str
        # Should provide an example
        assert "acme/project" in error_str or "e.g." in error_str

    def test_short_project_name_with_symbol_shows_helpful_error(self):
        """Short project name with symbol path produces descriptive error."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="vibe-engineer::src/chunks.py#Chunks", implements="Something")
        error_str = str(exc_info.value)
        # Should mention org/repo format
        assert "org/repo" in error_str
        # Should include the actual invalid value
        assert "vibe-engineer" in error_str

    def test_valid_full_org_repo_format_works(self):
        """Full org/repo format still validates successfully."""
        ref = SymbolicReference(
            ref="cloudcapitalco/pybusiness::src/foo.py#Bar",
            implements="Something"
        )
        assert ref.ref == "cloudcapitalco/pybusiness::src/foo.py#Bar"

    def test_error_message_includes_got_prefix(self):
        """Error message includes 'got' to show what was received."""
        with pytest.raises(ValidationError) as exc_info:
            SymbolicReference(ref="justproject::src/foo.py", implements="Something")
        error_str = str(exc_info.value)
        assert "got" in error_str.lower() or "justproject" in error_str


# Subsystem: docs/subsystems/friction_tracking - Friction log management
class TestFrictionTheme:
    """Tests for FrictionTheme model."""

    def test_valid_theme_parses_successfully(self):
        """Valid FrictionTheme with id and name parses correctly."""
        theme = FrictionTheme(id="code-refs", name="Code Reference Friction")
        assert theme.id == "code-refs"
        assert theme.name == "Code Reference Friction"

    def test_empty_id_rejected(self):
        """Empty id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionTheme(id="", name="Valid Name")
        assert "id cannot be empty" in str(exc_info.value)

    def test_whitespace_id_rejected(self):
        """Whitespace-only id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionTheme(id="   ", name="Valid Name")
        assert "id cannot be empty" in str(exc_info.value)

    def test_empty_name_rejected(self):
        """Empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionTheme(id="valid-id", name="")
        assert "name cannot be empty" in str(exc_info.value)

    def test_whitespace_name_rejected(self):
        """Whitespace-only name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionTheme(id="valid-id", name="   ")
        assert "name cannot be empty" in str(exc_info.value)

    def test_missing_id_rejected(self):
        """Missing id field is rejected."""
        with pytest.raises(ValidationError):
            FrictionTheme(name="Valid Name")

    def test_missing_name_rejected(self):
        """Missing name field is rejected."""
        with pytest.raises(ValidationError):
            FrictionTheme(id="valid-id")


class TestFrictionProposedChunk:
    """Tests for FrictionProposedChunk model."""

    def test_valid_proposed_chunk_parses(self):
        """Valid FrictionProposedChunk parses correctly."""
        chunk = FrictionProposedChunk(
            prompt="Fix the code reference ambiguity issue",
            chunk_directory="symbolic_code_refs",
            addresses=["F001", "F003"],
        )
        assert chunk.prompt == "Fix the code reference ambiguity issue"
        assert chunk.chunk_directory == "symbolic_code_refs"
        assert chunk.addresses == ["F001", "F003"]

    def test_empty_prompt_rejected(self):
        """Empty prompt is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionProposedChunk(prompt="")
        assert "prompt cannot be empty" in str(exc_info.value)

    def test_whitespace_prompt_rejected(self):
        """Whitespace-only prompt is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FrictionProposedChunk(prompt="   ")
        assert "prompt cannot be empty" in str(exc_info.value)

    def test_addresses_defaults_to_empty_list(self):
        """addresses defaults to empty list when not provided."""
        chunk = FrictionProposedChunk(prompt="Do something")
        assert chunk.addresses == []

    def test_chunk_directory_defaults_to_none(self):
        """chunk_directory defaults to None when not provided."""
        chunk = FrictionProposedChunk(prompt="Do something")
        assert chunk.chunk_directory is None

    def test_addresses_is_list_of_strings(self):
        """addresses accepts a list of string IDs."""
        chunk = FrictionProposedChunk(
            prompt="Do something", addresses=["F001", "F002", "F003"]
        )
        assert chunk.addresses == ["F001", "F002", "F003"]


class TestFrictionFrontmatter:
    """Tests for FrictionFrontmatter model."""

    def test_empty_frontmatter_parses(self):
        """FrictionFrontmatter with empty arrays parses correctly."""
        frontmatter = FrictionFrontmatter()
        assert frontmatter.themes == []
        assert frontmatter.proposed_chunks == []

    def test_frontmatter_with_themes(self):
        """FrictionFrontmatter with themes parses correctly."""
        frontmatter = FrictionFrontmatter(
            themes=[
                {"id": "code-refs", "name": "Code Reference Friction"},
                {"id": "templates", "name": "Template System Friction"},
            ]
        )
        assert len(frontmatter.themes) == 2
        assert frontmatter.themes[0].id == "code-refs"
        assert frontmatter.themes[1].name == "Template System Friction"

    def test_frontmatter_with_proposed_chunks(self):
        """FrictionFrontmatter with proposed_chunks parses correctly."""
        frontmatter = FrictionFrontmatter(
            proposed_chunks=[
                {
                    "prompt": "Fix ambiguous refs",
                    "chunk_directory": "symbolic_code_refs",
                    "addresses": ["F001", "F003"],
                },
                {"prompt": "Add pre-commit hook", "chunk_directory": None, "addresses": ["F002"]},
            ]
        )
        assert len(frontmatter.proposed_chunks) == 2
        assert frontmatter.proposed_chunks[0].chunk_directory == "symbolic_code_refs"
        assert frontmatter.proposed_chunks[1].chunk_directory is None

    def test_themes_defaults_to_empty_list(self):
        """themes defaults to empty list when not provided."""
        frontmatter = FrictionFrontmatter(proposed_chunks=[])
        assert frontmatter.themes == []

    def test_proposed_chunks_defaults_to_empty_list(self):
        """proposed_chunks defaults to empty list when not provided."""
        frontmatter = FrictionFrontmatter(themes=[])
        assert frontmatter.proposed_chunks == []


class TestFrictionEntryReference:
    """Tests for FrictionEntryReference model."""

    def test_valid_entry_reference_parses_successfully(self):
        """Valid FrictionEntryReference parses correctly."""
        from models import FrictionEntryReference

        ref = FrictionEntryReference(entry_id="F001", scope="full")
        assert ref.entry_id == "F001"
        assert ref.scope == "full"

    def test_valid_entry_reference_with_partial_scope(self):
        """FrictionEntryReference with partial scope parses correctly."""
        from models import FrictionEntryReference

        ref = FrictionEntryReference(entry_id="F123", scope="partial")
        assert ref.entry_id == "F123"
        assert ref.scope == "partial"

    def test_scope_defaults_to_full(self):
        """scope defaults to 'full' when not provided."""
        from models import FrictionEntryReference

        ref = FrictionEntryReference(entry_id="F001")
        assert ref.scope == "full"

    def test_empty_entry_id_rejected(self):
        """Empty entry_id is rejected."""
        from models import FrictionEntryReference
        import pytest

        with pytest.raises(ValueError, match="entry_id cannot be empty"):
            FrictionEntryReference(entry_id="", scope="full")

    def test_invalid_entry_id_format_rejected(self):
        """entry_id not matching F followed by digits is rejected."""
        from models import FrictionEntryReference
        import pytest

        # Lowercase f
        with pytest.raises(ValueError, match="entry_id must match pattern"):
            FrictionEntryReference(entry_id="f001", scope="full")

        # Missing F prefix
        with pytest.raises(ValueError, match="entry_id must match pattern"):
            FrictionEntryReference(entry_id="001", scope="full")

        # Non-numeric suffix
        with pytest.raises(ValueError, match="entry_id must match pattern"):
            FrictionEntryReference(entry_id="FABC", scope="full")

        # Extra characters
        with pytest.raises(ValueError, match="entry_id must match pattern"):
            FrictionEntryReference(entry_id="F001A", scope="full")

    def test_valid_entry_id_formats_accepted(self):
        """Various valid entry_id formats are accepted."""
        from models import FrictionEntryReference

        # Single digit
        ref1 = FrictionEntryReference(entry_id="F1")
        assert ref1.entry_id == "F1"

        # Two digits
        ref2 = FrictionEntryReference(entry_id="F01")
        assert ref2.entry_id == "F01"

        # Three digits (standard format)
        ref3 = FrictionEntryReference(entry_id="F001")
        assert ref3.entry_id == "F001"

        # Four digits
        ref4 = FrictionEntryReference(entry_id="F9999")
        assert ref4.entry_id == "F9999"

    def test_invalid_scope_rejected(self):
        """Invalid scope value is rejected."""
        from models import FrictionEntryReference
        import pytest

        with pytest.raises(ValueError):
            FrictionEntryReference(entry_id="F001", scope="invalid")
