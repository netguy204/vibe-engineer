"""Tests for the Narratives class."""
# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - Narrative frontmatter parsing tests

from narratives import Narratives
from models import NarrativeStatus


class TestNarrativesClass:
    """Tests for the Narratives class."""

    def test_enumerate_narratives_empty(self, temp_project):
        """Verify enumerate_narratives returns empty list for new project."""
        narratives = Narratives(temp_project)
        assert narratives.enumerate_narratives() == []

    def test_enumerate_narratives_no_directory(self, temp_project):
        """Verify enumerate_narratives returns empty list when directory doesn't exist."""
        narratives = Narratives(temp_project)
        # Don't create the narratives directory
        assert narratives.enumerate_narratives() == []

    def test_num_narratives_property(self, temp_project):
        """Verify num_narratives returns correct count."""
        narratives = Narratives(temp_project)
        assert narratives.num_narratives == 0

        narratives.create_narrative("first")
        assert narratives.num_narratives == 1

        narratives.create_narrative("second")
        assert narratives.num_narratives == 2

    def test_create_narrative_creates_directory(self, temp_project):
        """Verify narrative creation creates the expected directory structure."""
        narratives = Narratives(temp_project)
        result_path = narratives.create_narrative("my_narrative")

        assert result_path.exists()
        assert result_path.is_dir()
        assert result_path.name == "0001-my_narrative"

    def test_create_narrative_copies_template(self, temp_project):
        """Verify create_narrative copies template files."""
        narratives = Narratives(temp_project)
        result_path = narratives.create_narrative("test_narrative")

        overview_file = result_path / "OVERVIEW.md"
        assert overview_file.exists()
        content = overview_file.read_text()
        assert "status:" in content  # YAML frontmatter exists

    def test_sequence_numbers_increment(self, temp_project):
        """Verify sequence numbers increment correctly."""
        narratives = Narratives(temp_project)

        path1 = narratives.create_narrative("first")
        assert path1.name == "0001-first"

        path2 = narratives.create_narrative("second")
        assert path2.name == "0002-second"

        path3 = narratives.create_narrative("third")
        assert path3.name == "0003-third"

    def test_create_narrative_auto_creates_directory(self, temp_project):
        """Verify docs/narratives/ is auto-created if missing."""
        narratives = Narratives(temp_project)
        # Narratives directory doesn't exist yet
        assert not narratives.narratives_dir.exists()

        narratives.create_narrative("test")
        assert narratives.narratives_dir.exists()

    def test_narratives_dir_property(self, temp_project):
        """Verify narratives_dir returns correct path."""
        narratives = Narratives(temp_project)
        expected = temp_project / "docs" / "narratives"
        assert narratives.narratives_dir == expected


class TestNarrativeCreatedAfterPopulation:
    """Tests for created_after population during narrative creation."""

    def test_first_narrative_has_empty_created_after(self, temp_project):
        """When creating the first narrative, created_after is empty list."""
        narratives = Narratives(temp_project)
        narratives.create_narrative("first_narrative")

        frontmatter = narratives.parse_narrative_frontmatter("0001-first_narrative")
        assert frontmatter is not None
        assert frontmatter.created_after == []

    def test_second_narrative_references_first_as_created_after(self, temp_project):
        """When creating second narrative, created_after contains first narrative's name."""
        narratives = Narratives(temp_project)
        narratives.create_narrative("first_narrative")
        narratives.create_narrative("second_narrative")

        frontmatter = narratives.parse_narrative_frontmatter("0002-second_narrative")
        assert frontmatter is not None
        assert "0001-first_narrative" in frontmatter.created_after


# Chunk: docs/chunks/0032-proposed_chunks_frontmatter - Narrative frontmatter parsing tests
class TestNarrativeFrontmatterParsing:
    """Tests for parse_narrative_frontmatter method."""

    def test_parse_valid_frontmatter_with_proposed_chunks(self, temp_project):
        """Verify valid frontmatter with proposed_chunks parses correctly."""
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: "Some goal"
proposed_chunks:
  - prompt: "First chunk"
    chunk_directory: "0001-first"
  - prompt: "Second chunk"
    chunk_directory: null
---
# Test Narrative
""")

        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-test_narr")

        assert frontmatter is not None
        assert frontmatter.status == NarrativeStatus.ACTIVE
        assert frontmatter.advances_trunk_goal == "Some goal"
        assert len(frontmatter.proposed_chunks) == 2
        assert frontmatter.proposed_chunks[0].prompt == "First chunk"
        assert frontmatter.proposed_chunks[0].chunk_directory == "0001-first"
        assert frontmatter.proposed_chunks[1].prompt == "Second chunk"
        assert frontmatter.proposed_chunks[1].chunk_directory is None

    def test_parse_frontmatter_missing_proposed_chunks_defaults_empty(self, temp_project):
        """Verify missing proposed_chunks field defaults to empty list."""
        narr_dir = temp_project / "docs" / "narratives" / "0001-test_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: DRAFTING
advances_trunk_goal: null
---
# Test Narrative
""")

        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-test_narr")

        assert frontmatter is not None
        assert frontmatter.status == NarrativeStatus.DRAFTING
        assert frontmatter.proposed_chunks == []

    def test_parse_legacy_chunks_field_maps_to_proposed_chunks(self, temp_project):
        """Verify legacy 'chunks' field is mapped to proposed_chunks."""
        narr_dir = temp_project / "docs" / "narratives" / "0001-legacy_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
advances_trunk_goal: null
chunks:
  - prompt: "Legacy prompt"
    chunk_directory: null
---
# Legacy Narrative
""")

        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-legacy_narr")

        assert frontmatter is not None
        assert len(frontmatter.proposed_chunks) == 1
        assert frontmatter.proposed_chunks[0].prompt == "Legacy prompt"

    def test_parse_malformed_frontmatter_returns_none(self, temp_project):
        """Verify malformed YAML frontmatter returns None."""
        narr_dir = temp_project / "docs" / "narratives" / "0001-bad_narr"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""---
status: ACTIVE
  bad_indent: yes
---
# Bad Narrative
""")

        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-bad_narr")

        assert frontmatter is None

    def test_parse_nonexistent_narrative_returns_none(self, temp_project):
        """Verify nonexistent narrative returns None."""
        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-nonexistent")

        assert frontmatter is None

    def test_parse_no_frontmatter_returns_none(self, temp_project):
        """Verify file without frontmatter returns None."""
        narr_dir = temp_project / "docs" / "narratives" / "0001-no_front"
        narr_dir.mkdir(parents=True)

        overview = narr_dir / "OVERVIEW.md"
        overview.write_text("""# No Frontmatter Narrative

Just regular markdown content.
""")

        narratives = Narratives(temp_project)
        frontmatter = narratives.parse_narrative_frontmatter("0001-no_front")

        assert frontmatter is None
