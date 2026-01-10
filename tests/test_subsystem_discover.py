"""Tests for the 've subsystem discover' CLI command."""

from ve import cli


# Chunk: docs/chunks/0044-remove_sequence_prefix - Updated for short_name only format
class TestSubsystemDiscoverCommand:
    """Tests for 've subsystem discover' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["subsystem", "discover", "--help"])
        assert result.exit_code == 0
        assert "SHORTNAME" in result.output or "shortname" in result.output.lower()

    def test_valid_shortname_creates_directory(self, runner, temp_project):
        """Valid shortname creates directory and outputs path."""
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/subsystems/validation" in result.output

        # Verify directory was created
        subsystem_dir = temp_project / "docs" / "subsystems" / "validation"
        assert subsystem_dir.exists()
        assert (subsystem_dir / "OVERVIEW.md").exists()

    def test_invalid_shortname_errors(self, runner, temp_project):
        """Invalid shortname (via validate_identifier) errors with message."""
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "Invalid-Name!", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_shortname_with_spaces_errors(self, runner, temp_project):
        """Shortname with spaces errors."""
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "invalid name", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_shortname_normalized_to_lowercase(self, runner, temp_project):
        """Shortname is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "VALIDATION", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "validation" in result.output
        assert "VALIDATION" not in result.output  # Should be lowercased

    def test_duplicate_shortname_errors(self, runner, temp_project):
        """Duplicate shortname errors with 'already exists' message."""
        # Create first subsystem
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        # Try to create duplicate
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "validation" in result.output
        assert "validation" in result.output

    def test_duplicate_shortname_case_insensitive(self, runner, temp_project):
        """Duplicate check is case-insensitive."""
        # Create subsystem with lowercase
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        # Try to create with uppercase - should fail
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "VALIDATION", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/subsystems/validation" in result.output

        # Verify in correct location
        subsystem_dir = temp_project / "docs" / "subsystems" / "validation"
        assert subsystem_dir.exists()

    def test_multiple_subsystems(self, runner, temp_project):
        """Multiple subsystems can be created."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "first", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "second", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "second" in result.output

        # Create third
        result = runner.invoke(
            cli,
            ["subsystem", "discover", "third", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "third" in result.output
