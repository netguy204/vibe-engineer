"""Tests for the Chunks class."""

from chunks import Chunks
from models import ChunkStatus


class TestChunksClass:
    """Tests for the Chunks class.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_create_chunk_creates_directory(self, temp_project):
        """Verify chunk creation creates the expected directory structure."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-001", "my_feature")

        assert result_path.exists()
        assert result_path.is_dir()
        assert result_path.name == "my_feature-VE-001"

    def test_create_chunk_default_status_implementing(self, temp_project):
        """Default status is IMPLEMENTING when no status param provided."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature")

        goal_path = result_path / "GOAL.md"
        content = goal_path.read_text()
        assert "status: IMPLEMENTING" in content

    def test_create_chunk_with_future_status(self, temp_project):
        """When status='FUTURE', the created GOAL.md has status: FUTURE."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature", status="FUTURE")

        goal_path = result_path / "GOAL.md"
        content = goal_path.read_text()
        assert "status: FUTURE" in content

    def test_create_chunk_with_implementing_status(self, temp_project):
        """Explicit status='IMPLEMENTING' works correctly."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature", status="IMPLEMENTING")

        goal_path = result_path / "GOAL.md"
        content = goal_path.read_text()
        assert "status: IMPLEMENTING" in content

    def test_enumerate_chunks_empty(self, temp_project):
        """Verify enumerate_chunks returns empty list for new project."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.enumerate_chunks() == []

    def test_num_chunks_increments(self, temp_project):
        """Verify chunk numbering increments correctly."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.num_chunks == 0

        chunk_mgr.create_chunk("VE-001", "first")
        assert chunk_mgr.num_chunks == 1

        # Complete first chunk before creating second (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("first-VE-001", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk("VE-002", "second")
        assert chunk_mgr.num_chunks == 2


class TestListChunks:
    """Tests for Chunks.list_chunks() method.

    # Chunk: docs/chunks/artifact_list_ordering - Updated for new return type
    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_empty_project_returns_empty_list(self, temp_project):
        """Empty project returns empty list."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.list_chunks() == []

    def test_single_chunk_returns_list_with_one_item(self, temp_project):
        """Single chunk returns list with one item."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "feature")
        result = chunk_mgr.list_chunks()
        assert len(result) == 1
        assert result[0] == "feature-VE-001"

    def test_multiple_chunks_descending_order(self, temp_project):
        """Multiple chunks returned in causal order (newest first)."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        # Complete each chunk before creating the next (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("first-VE-001", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.update_status("second-VE-002", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk("VE-003", "third")
        result = chunk_mgr.list_chunks()
        assert len(result) == 3
        # Newest first (each depends on previous via created_after)
        assert result[0] == "third-VE-003"
        assert result[1] == "second-VE-002"
        assert result[2] == "first-VE-001"

    def test_chunks_with_and_without_ticket_id(self, temp_project):
        """Chunks with different name formats all parsed correctly."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "with_ticket")
        # Complete first chunk before creating second (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("with_ticket-VE-001", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk(None, "without_ticket")
        result = chunk_mgr.list_chunks()
        assert len(result) == 2
        assert result[0] == "without_ticket"
        assert result[1] == "with_ticket-VE-001"


class TestGetLatestChunk:
    """Tests for Chunks.get_latest_chunk() method.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_empty_project_returns_none(self, temp_project):
        """Empty project returns None."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.get_latest_chunk() is None

    def test_single_chunk_returns_that_chunk(self, temp_project):
        """Single chunk returns that chunk's name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "feature")
        assert chunk_mgr.get_latest_chunk() == "feature-VE-001"

    def test_multiple_chunks_returns_highest(self, temp_project):
        """Multiple chunks returns latest chunk (newest in causal order)."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        # Complete each chunk before creating the next (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("first-VE-001", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.update_status("second-VE-002", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk("VE-003", "third")
        assert chunk_mgr.get_latest_chunk() == "third-VE-003"


class TestGetCurrentChunk:
    """Tests for Chunks.get_current_chunk() method.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_empty_project_returns_none(self, temp_project):
        """Empty project returns None."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.get_current_chunk() is None

    def test_single_implementing_chunk_returns_that_chunk(self, temp_project):
        """Single IMPLEMENTING chunk returns that chunk's name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature", status="IMPLEMENTING")
        assert chunk_mgr.get_current_chunk() == "feature"

    def test_returns_sole_implementing_chunk(self, temp_project):
        """Single IMPLEMENTING chunk is returned as current chunk.

        Note: The guard prevents creating multiple IMPLEMENTING chunks,
        so this test verifies the single-chunk case.
        """
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "first", status="IMPLEMENTING")
        assert chunk_mgr.get_current_chunk() == "first"

        # Creating FUTURE chunks doesn't affect current
        chunk_mgr.create_chunk(None, "second", status="FUTURE")
        assert chunk_mgr.get_current_chunk() == "first"

    def test_ignores_future_chunks(self, temp_project):
        """FUTURE chunks are ignored, returns IMPLEMENTING chunk."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "implementing", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "future", status="FUTURE")
        # Should return the IMPLEMENTING chunk, not the newer FUTURE one
        assert chunk_mgr.get_current_chunk() == "implementing"

    def test_returns_none_when_only_future_chunks(self, temp_project):
        """Returns None when only FUTURE chunks exist."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "future1", status="FUTURE")
        chunk_mgr.create_chunk(None, "future2", status="FUTURE")
        assert chunk_mgr.get_current_chunk() is None

    def test_ignores_active_chunks(self, temp_project):
        """ACTIVE chunks are ignored."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "first", status="IMPLEMENTING")
        # Manually change to ACTIVE status
        goal_path = chunk_mgr.get_chunk_goal_path("first")
        content = goal_path.read_text()
        content = content.replace("status: IMPLEMENTING", "status: ACTIVE")
        goal_path.write_text(content)
        # Create another FUTURE chunk
        chunk_mgr.create_chunk(None, "future", status="FUTURE")
        # Neither should be returned as current
        assert chunk_mgr.get_current_chunk() is None

    def test_ignores_superseded_and_historical(self, temp_project):
        """SUPERSEDED and HISTORICAL chunks are ignored."""
        chunk_mgr = Chunks(temp_project)

        # Create first chunk and mark it SUPERSEDED
        chunk_mgr.create_chunk(None, "superseded", status="IMPLEMENTING")
        goal_path1 = chunk_mgr.get_chunk_goal_path("superseded")
        content1 = goal_path1.read_text()
        goal_path1.write_text(content1.replace("status: IMPLEMENTING", "status: SUPERSEDED"))

        # Create second chunk (no longer blocked) and mark it HISTORICAL
        chunk_mgr.create_chunk(None, "historical", status="IMPLEMENTING")
        goal_path2 = chunk_mgr.get_chunk_goal_path("historical")
        content2 = goal_path2.read_text()
        goal_path2.write_text(content2.replace("status: IMPLEMENTING", "status: HISTORICAL"))

        # Neither SUPERSEDED nor HISTORICAL should be considered current
        assert chunk_mgr.get_current_chunk() is None


class TestCreatedAfterPopulation:
    """Tests for created_after population during chunk creation.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_first_chunk_has_empty_created_after(self, temp_project):
        """When creating the first chunk, created_after is empty list."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "first_chunk")

        # Parse the frontmatter
        frontmatter = chunk_mgr.parse_chunk_frontmatter("first_chunk")
        assert frontmatter is not None
        assert frontmatter.created_after == []

    def test_second_chunk_references_first_as_created_after(self, temp_project):
        """When creating second chunk, created_after contains first chunk's short name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "first_chunk")
        # Complete first chunk before creating second (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("first_chunk", ChunkStatus.ACTIVE)
        chunk_mgr.create_chunk(None, "second_chunk")

        frontmatter = chunk_mgr.parse_chunk_frontmatter("second_chunk")
        assert frontmatter is not None
        # Tips should reference directory names (the format returned by find_tips)
        assert "first_chunk" in frontmatter.created_after

    def test_third_chunk_references_only_current_tip(self, temp_project):
        """Third chunk references only the current tip (second chunk).

        In the causal graph:
        - First chunk has created_after: [] - no parents
        - Second chunk has created_after: [first] - first is its parent
        - After second is created, first is no longer a tip (second references it)
        - Third chunk should only reference second (the current tip)
        """
        chunk_mgr = Chunks(temp_project)

        # Create first chunk (becomes a tip)
        chunk_mgr.create_chunk(None, "first_chunk")
        # Complete first chunk before creating second (guard prevents multiple IMPLEMENTING)
        chunk_mgr.update_status("first_chunk", ChunkStatus.ACTIVE)

        # Create second chunk (references first, making first no longer a tip)
        chunk_mgr.create_chunk(None, "second_chunk")
        # Complete second chunk before creating third
        chunk_mgr.update_status("second_chunk", ChunkStatus.ACTIVE)

        # Create third chunk - only second should be a tip now
        chunk_mgr.create_chunk(None, "third_chunk")

        frontmatter = chunk_mgr.parse_chunk_frontmatter("third_chunk")
        assert frontmatter is not None
        # Second chunk is the only tip (first is referenced by second)
        assert len(frontmatter.created_after) == 1
        assert "second_chunk" in frontmatter.created_after


class TestChunkDirectoryInTemplates:
    """Tests for chunk_directory variable in rendered templates.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_plan_md_contains_chunk_directory(self, temp_project):
        """Rendered PLAN.md contains actual chunk directory name, not placeholder."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature")

        plan_path = result_path / "PLAN.md"
        plan_content = plan_path.read_text()

        # Should contain the actual chunk directory path
        assert "docs/chunks/feature/GOAL.md" in plan_content
        # Should NOT contain the placeholder
        assert "NNNN-name" not in plan_content

    def test_plan_md_contains_chunk_directory_with_ticket(self, temp_project):
        """Rendered PLAN.md includes ticket ID in chunk directory reference."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-001", "feature")

        plan_path = result_path / "PLAN.md"
        plan_content = plan_path.read_text()

        # Should contain the full chunk directory with ticket
        assert "docs/chunks/feature-VE-001/GOAL.md" in plan_content
        assert "NNNN-name" not in plan_content


class TestParseFrontmatterDependents:
    """Tests for parsing dependents from chunk frontmatter.

    # Chunk: docs/chunks/cross_repo_schemas - Frontmatter dependents parsing tests
    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_parse_frontmatter_with_dependents(self, temp_project):
        """Existing parse_chunk_frontmatter returns dependents field when present."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature")

        # Write GOAL.md with dependents in frontmatter (valid ExternalArtifactRef format)
        # Chunk: docs/chunks/consolidate_ext_refs - Updated for ExternalArtifactRef format
        goal_path = chunk_mgr.get_chunk_goal_path("feature")
        goal_path.write_text(
            "---\n"
            "status: ACTIVE\n"
            "dependents:\n"
            "  - artifact_type: chunk\n"
            "    artifact_id: integration\n"
            "    repo: acme/other-repo\n"
            "---\n"
            "# Goal\n"
        )

        frontmatter = chunk_mgr.parse_chunk_frontmatter("feature")
        assert frontmatter is not None
        assert len(frontmatter.dependents) == 1
        assert frontmatter.dependents[0].repo == "acme/other-repo"
        assert frontmatter.dependents[0].artifact_id == "integration"

    def test_parse_frontmatter_without_dependents(self, temp_project):
        """Existing chunks without dependents continue to work."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature")

        # Write GOAL.md without dependents
        goal_path = chunk_mgr.get_chunk_goal_path("feature")
        goal_path.write_text(
            "---\n"
            "status: ACTIVE\n"
            "---\n"
            "# Goal\n"
        )

        frontmatter = chunk_mgr.parse_chunk_frontmatter("feature")
        assert frontmatter is not None
        assert frontmatter.dependents == []
        assert frontmatter.status.value == "ACTIVE"


class TestTicketFrontmatter:
    """Tests for ticket field rendering in GOAL.md frontmatter."""

    def test_ticket_renders_null_when_ticket_id_is_none(self, temp_project):
        """When ticket_id is None, GOAL.md frontmatter has 'ticket: null' (valid YAML)."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature")

        goal_path = result_path / "GOAL.md"
        content = goal_path.read_text()

        # Should render as YAML null, not Python None
        assert "ticket: null" in content
        assert "ticket: None" not in content

    def test_ticket_renders_value_when_ticket_id_provided(self, temp_project):
        """When ticket_id is provided, GOAL.md frontmatter has 'ticket: <value>'."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-123", "feature")

        goal_path = result_path / "GOAL.md"
        content = goal_path.read_text()

        assert "ticket: VE-123" in content


class TestSymbolicOverlap:
    """Tests for compute_symbolic_overlap function."""

    def test_same_file_overlaps(self):
        """Two references to the same file overlap."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

    def test_parent_contains_child(self):
        """foo.py#Bar and foo.py#Bar::baz overlap (parent contains child)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/foo.py#Bar::baz"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

    def test_child_overlaps_with_parent(self):
        """Child also overlaps with parent (symmetric)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar::baz"]
        refs_b = ["src/foo.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

    def test_different_symbols_same_file_no_overlap(self):
        """foo.py#Bar and foo.py#Qux do not overlap (different symbols)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/foo.py#Qux"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is False

    def test_file_reference_overlaps_any_symbol(self):
        """foo.py (whole module) overlaps with any symbol in that module."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py#Bar::baz"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

    def test_different_files_no_overlap(self):
        """References to different files never overlap."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/baz.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is False

    def test_empty_refs_no_overlap(self):
        """Empty reference lists don't overlap."""
        from chunks import compute_symbolic_overlap
        assert compute_symbolic_overlap([], ["src/foo.py"], ".") is False
        assert compute_symbolic_overlap(["src/foo.py"], [], ".") is False
        assert compute_symbolic_overlap([], [], ".") is False

    def test_multiple_refs_any_overlap(self):
        """Multiple refs: overlap if any pair overlaps."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar", "src/baz.py#Qux"]
        refs_b = ["src/foo.py#Bar::method"]  # overlaps with refs_a[0]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is True

    def test_multiple_refs_no_overlap(self):
        """Multiple refs: no overlap if no pair overlaps."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar", "src/baz.py#Qux"]
        refs_b = ["src/foo.py#Other", "src/baz.py#Different"]
        assert compute_symbolic_overlap(refs_a, refs_b, ".") is False


class TestValidateSubsystemRefs:
    """Tests for Chunks.validate_subsystem_refs() method."""

    def _write_chunk_with_subsystems(self, temp_project, chunk_name, subsystems):
        """Helper to write a chunk GOAL.md with subsystems frontmatter."""
        chunk_path = temp_project / "docs" / "chunks" / chunk_name
        chunk_path.mkdir(parents=True, exist_ok=True)
        goal_path = chunk_path / "GOAL.md"

        if subsystems:
            subsystems_yaml = "subsystems:\n"
            for sub in subsystems:
                subsystems_yaml += f"  - subsystem_id: {sub['subsystem_id']}\n"
                subsystems_yaml += f"    relationship: {sub['relationship']}\n"
        else:
            subsystems_yaml = "subsystems: []"

        goal_path.write_text(f"""---
status: IMPLEMENTING
ticket: null
code_paths: []
code_references: []
{subsystems_yaml}
---

# Chunk Goal
""")

    def _create_subsystem(self, temp_project, subsystem_name):
        """Helper to create a subsystem directory with OVERVIEW.md."""
        subsystem_path = temp_project / "docs" / "subsystems" / subsystem_name
        subsystem_path.mkdir(parents=True, exist_ok=True)
        overview_path = subsystem_path / "OVERVIEW.md"
        overview_path.write_text("""---
status: DISCOVERING
chunks: []
code_references: []
---

# Subsystem
""")

    def test_empty_subsystems_returns_no_errors(self, temp_project):
        """Empty subsystems list returns no errors."""
        chunk_mgr = Chunks(temp_project)
        self._write_chunk_with_subsystems(temp_project, "0001-feature", [])

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert errors == []

    def test_missing_subsystems_field_returns_no_errors(self, temp_project):
        """Missing subsystems field returns no errors (backward compat)."""
        chunk_mgr = Chunks(temp_project)
        chunk_path = temp_project / "docs" / "chunks" / "0001-feature"
        chunk_path.mkdir(parents=True, exist_ok=True)
        (chunk_path / "GOAL.md").write_text("""---
status: IMPLEMENTING
code_references: []
---

# Chunk Goal
""")

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert errors == []

    def test_valid_subsystem_reference_returns_no_errors(self, temp_project):
        """Valid subsystem reference returns no errors."""
        chunk_mgr = Chunks(temp_project)
        self._create_subsystem(temp_project, "0001-validation")
        self._write_chunk_with_subsystems(temp_project, "0001-feature", [
            {"subsystem_id": "0001-validation", "relationship": "implements"}
        ])

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert errors == []

    def test_invalid_subsystem_id_format_causes_frontmatter_parse_failure(self, temp_project):
        """Invalid subsystem_id format causes frontmatter parsing to fail."""
        chunk_mgr = Chunks(temp_project)
        # Chunk: docs/chunks/remove_sequence_prefix - Must now use truly invalid format
        # "UPPERCASE" is invalid since new pattern requires lowercase
        self._write_chunk_with_subsystems(temp_project, "feature", [
            {"subsystem_id": "INVALID_UPPERCASE", "relationship": "implements"}
        ])

        # With ChunkFrontmatter validation, invalid subsystem_id format
        # causes parse_chunk_frontmatter to return None (validation fails)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("feature")
        assert frontmatter is None

    def test_nonexistent_subsystem_returns_error(self, temp_project):
        """Non-existent subsystem reference returns error message."""
        chunk_mgr = Chunks(temp_project)
        self._write_chunk_with_subsystems(temp_project, "0001-feature", [
            {"subsystem_id": "0001-nonexistent", "relationship": "implements"}
        ])

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert len(errors) == 1
        assert "0001-nonexistent" in errors[0]
        assert "not found" in errors[0].lower() or "does not exist" in errors[0].lower()

    def test_multiple_valid_references_returns_no_errors(self, temp_project):
        """Multiple valid subsystem references returns no errors."""
        chunk_mgr = Chunks(temp_project)
        self._create_subsystem(temp_project, "0001-validation")
        self._create_subsystem(temp_project, "0002-frontmatter")
        self._write_chunk_with_subsystems(temp_project, "0001-feature", [
            {"subsystem_id": "0001-validation", "relationship": "implements"},
            {"subsystem_id": "0002-frontmatter", "relationship": "uses"},
        ])

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert errors == []

    def test_multiple_nonexistent_subsystems_return_multiple_errors(self, temp_project):
        """Multiple non-existent subsystem references return multiple errors."""
        chunk_mgr = Chunks(temp_project)
        # Use valid subsystem_id format but non-existent directories
        self._write_chunk_with_subsystems(temp_project, "0001-feature", [
            {"subsystem_id": "0001-missing_first", "relationship": "implements"},
            {"subsystem_id": "0002-missing_second", "relationship": "uses"},
        ])

        errors = chunk_mgr.validate_subsystem_refs("0001-feature")
        assert len(errors) == 2
        assert "0001-missing_first" in errors[0]
        assert "0002-missing_second" in errors[1]

    def test_chunk_not_found_returns_none_or_empty(self, temp_project):
        """Non-existent chunk returns empty list or None gracefully."""
        chunk_mgr = Chunks(temp_project)
        errors = chunk_mgr.validate_subsystem_refs("9999-nonexistent")
        # Should return empty list (no errors possible if chunk doesn't exist)
        assert errors == []
