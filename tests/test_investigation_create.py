"""Tests for the 've investigation create' CLI command."""

from ve import cli


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
class TestInvestigationCreateCommand:
    """Tests for 've investigation create' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["investigation", "create", "--help"])
        assert result.exit_code == 0
        assert "Create a new investigation" in result.output or "create" in result.output.lower()

    def test_valid_shortname_creates_directory(self, runner, temp_project):
        """Valid shortname creates directory and outputs path."""
        result = runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/investigations/memory_leak" in result.output

        # Verify directory was created
        investigation_path = temp_project / "docs" / "investigations" / "memory_leak"
        assert investigation_path.exists()
        assert (investigation_path / "OVERVIEW.md").exists()

    def test_invalid_shortname_errors(self, runner, temp_project):
        """Invalid shortname errors with message."""
        result = runner.invoke(
            cli,
            ["investigation", "create", "invalid name with spaces", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_shortname_normalized_to_lowercase(self, runner, temp_project):
        """Shortname is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["investigation", "create", "MEMORY_LEAK", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "memory_leak" in result.output

        # Verify directory uses lowercase
        investigation_path = temp_project / "docs" / "investigations" / "memory_leak"
        assert investigation_path.exists()

    def test_multiple_investigations_works(self, runner, temp_project):
        """Multiple investigations can be created."""
        # Create first investigation
        runner.invoke(
            cli,
            ["investigation", "create", "first", "--project-dir", str(temp_project)]
        )

        # Create second investigation
        result = runner.invoke(
            cli,
            ["investigation", "create", "second", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "second" in result.output

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        result = runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert temp_project / "docs" / "investigations" / "memory_leak"
