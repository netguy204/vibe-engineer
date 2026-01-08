"""Tests for the Narratives class."""

from narratives import Narratives


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
