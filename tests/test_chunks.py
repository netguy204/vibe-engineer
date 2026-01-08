"""Tests for the Chunks class."""

from chunks import Chunks


class TestChunksClass:
    """Tests for the Chunks class."""

    def test_create_chunk_creates_directory(self, temp_project):
        """Verify chunk creation creates the expected directory structure."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-001", "my_feature")

        assert result_path.exists()
        assert result_path.is_dir()
        assert "0001-my_feature-VE-001" in result_path.name

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

        chunk_mgr.create_chunk("VE-002", "second")
        assert chunk_mgr.num_chunks == 2


class TestListChunks:
    """Tests for Chunks.list_chunks() method."""

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
        assert result[0] == (1, "0001-feature-VE-001")

    def test_multiple_chunks_descending_order(self, temp_project):
        """Multiple chunks returned in descending numeric order."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.create_chunk("VE-003", "third")
        result = chunk_mgr.list_chunks()
        assert len(result) == 3
        assert result[0][0] == 3  # highest first
        assert result[1][0] == 2
        assert result[2][0] == 1

    def test_chunks_with_and_without_ticket_id(self, temp_project):
        """Chunks with different name formats all parsed correctly."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "with_ticket")
        chunk_mgr.create_chunk(None, "without_ticket")
        result = chunk_mgr.list_chunks()
        assert len(result) == 2
        assert result[0] == (2, "0002-without_ticket")
        assert result[1] == (1, "0001-with_ticket-VE-001")


class TestGetLatestChunk:
    """Tests for Chunks.get_latest_chunk() method."""

    def test_empty_project_returns_none(self, temp_project):
        """Empty project returns None."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.get_latest_chunk() is None

    def test_single_chunk_returns_that_chunk(self, temp_project):
        """Single chunk returns that chunk's name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "feature")
        assert chunk_mgr.get_latest_chunk() == "0001-feature-VE-001"

    def test_multiple_chunks_returns_highest(self, temp_project):
        """Multiple chunks returns highest-numbered chunk."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.create_chunk("VE-003", "third")
        assert chunk_mgr.get_latest_chunk() == "0003-third-VE-003"


class TestGetCurrentChunk:
    """Tests for Chunks.get_current_chunk() method."""

    def test_empty_project_returns_none(self, temp_project):
        """Empty project returns None."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.get_current_chunk() is None

    def test_single_implementing_chunk_returns_that_chunk(self, temp_project):
        """Single IMPLEMENTING chunk returns that chunk's name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature", status="IMPLEMENTING")
        assert chunk_mgr.get_current_chunk() == "0001-feature"

    def test_returns_highest_implementing_chunk(self, temp_project):
        """Multiple IMPLEMENTING chunks returns highest-numbered."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "first", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "second", status="IMPLEMENTING")
        assert chunk_mgr.get_current_chunk() == "0002-second"

    def test_ignores_future_chunks(self, temp_project):
        """FUTURE chunks are ignored, returns IMPLEMENTING chunk."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "implementing", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "future", status="FUTURE")
        # Should return the IMPLEMENTING chunk, not the higher-numbered FUTURE one
        assert chunk_mgr.get_current_chunk() == "0001-implementing"

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
        goal_path = chunk_mgr.get_chunk_goal_path("0001")
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
        chunk_mgr.create_chunk(None, "superseded", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "historical", status="IMPLEMENTING")

        # Manually change statuses
        goal_path1 = chunk_mgr.get_chunk_goal_path("0001")
        content1 = goal_path1.read_text()
        goal_path1.write_text(content1.replace("status: IMPLEMENTING", "status: SUPERSEDED"))

        goal_path2 = chunk_mgr.get_chunk_goal_path("0002")
        content2 = goal_path2.read_text()
        goal_path2.write_text(content2.replace("status: IMPLEMENTING", "status: HISTORICAL"))

        assert chunk_mgr.get_current_chunk() is None


class TestChunkDirectoryInTemplates:
    """Tests for chunk_directory variable in rendered templates."""

    def test_plan_md_contains_chunk_directory(self, temp_project):
        """Rendered PLAN.md contains actual chunk directory name, not placeholder."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk(None, "feature")

        plan_path = result_path / "PLAN.md"
        plan_content = plan_path.read_text()

        # Should contain the actual chunk directory path
        assert "docs/chunks/0001-feature/GOAL.md" in plan_content
        # Should NOT contain the placeholder
        assert "NNNN-name" not in plan_content

    def test_plan_md_contains_chunk_directory_with_ticket(self, temp_project):
        """Rendered PLAN.md includes ticket ID in chunk directory reference."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-001", "feature")

        plan_path = result_path / "PLAN.md"
        plan_content = plan_path.read_text()

        # Should contain the full chunk directory with ticket
        assert "docs/chunks/0001-feature-VE-001/GOAL.md" in plan_content
        assert "NNNN-name" not in plan_content


class TestParseFrontmatterDependents:
    """Tests for parsing dependents from chunk frontmatter."""

    def test_parse_frontmatter_with_dependents(self, temp_project):
        """Existing parse_chunk_frontmatter returns dependents field when present."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature")

        # Write GOAL.md with dependents in frontmatter
        goal_path = chunk_mgr.get_chunk_goal_path("0001-feature")
        goal_path.write_text(
            "---\n"
            "status: active\n"
            "dependents:\n"
            "  - project: other-repo\n"
            "    chunk: 0002-integration\n"
            "---\n"
            "# Goal\n"
        )

        frontmatter = chunk_mgr.parse_chunk_frontmatter("0001-feature")
        assert "dependents" in frontmatter
        assert len(frontmatter["dependents"]) == 1
        assert frontmatter["dependents"][0]["project"] == "other-repo"
        assert frontmatter["dependents"][0]["chunk"] == "0002-integration"

    def test_parse_frontmatter_without_dependents(self, temp_project):
        """Existing chunks without dependents continue to work."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "feature")

        # Write GOAL.md without dependents
        goal_path = chunk_mgr.get_chunk_goal_path("0001-feature")
        goal_path.write_text(
            "---\n"
            "status: active\n"
            "---\n"
            "# Goal\n"
        )

        frontmatter = chunk_mgr.parse_chunk_frontmatter("0001-feature")
        assert frontmatter is not None
        assert "dependents" not in frontmatter
        assert frontmatter.get("status") == "active"


class TestSymbolicOverlap:
    """Tests for compute_symbolic_overlap function."""

    def test_same_file_overlaps(self):
        """Two references to the same file overlap."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py"]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

    def test_parent_contains_child(self):
        """foo.py#Bar and foo.py#Bar::baz overlap (parent contains child)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/foo.py#Bar::baz"]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

    def test_child_overlaps_with_parent(self):
        """Child also overlaps with parent (symmetric)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar::baz"]
        refs_b = ["src/foo.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

    def test_different_symbols_same_file_no_overlap(self):
        """foo.py#Bar and foo.py#Qux do not overlap (different symbols)."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/foo.py#Qux"]
        assert compute_symbolic_overlap(refs_a, refs_b) is False

    def test_file_reference_overlaps_any_symbol(self):
        """foo.py (whole module) overlaps with any symbol in that module."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

        refs_a = ["src/foo.py"]
        refs_b = ["src/foo.py#Bar::baz"]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

    def test_different_files_no_overlap(self):
        """References to different files never overlap."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar"]
        refs_b = ["src/baz.py#Bar"]
        assert compute_symbolic_overlap(refs_a, refs_b) is False

    def test_empty_refs_no_overlap(self):
        """Empty reference lists don't overlap."""
        from chunks import compute_symbolic_overlap
        assert compute_symbolic_overlap([], ["src/foo.py"]) is False
        assert compute_symbolic_overlap(["src/foo.py"], []) is False
        assert compute_symbolic_overlap([], []) is False

    def test_multiple_refs_any_overlap(self):
        """Multiple refs: overlap if any pair overlaps."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar", "src/baz.py#Qux"]
        refs_b = ["src/foo.py#Bar::method"]  # overlaps with refs_a[0]
        assert compute_symbolic_overlap(refs_a, refs_b) is True

    def test_multiple_refs_no_overlap(self):
        """Multiple refs: no overlap if no pair overlaps."""
        from chunks import compute_symbolic_overlap
        refs_a = ["src/foo.py#Bar", "src/baz.py#Qux"]
        refs_b = ["src/foo.py#Other", "src/baz.py#Different"]
        assert compute_symbolic_overlap(refs_a, refs_b) is False
