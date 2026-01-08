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
