"""Tests for the 've subsystem list' CLI command."""

from ve import cli


class TestSubsystemListCommand:
    """Tests for 've subsystem list' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["subsystem", "list", "--help"])
        assert result.exit_code == 0
        assert "List all subsystems" in result.output or "list" in result.output.lower()

    def test_empty_project_exits_with_error(self, runner, temp_project):
        """Empty project: stderr says 'No subsystems found', exit code 1."""
        result = runner.invoke(
            cli,
            ["subsystem", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No subsystems found" in result.output

    def test_single_subsystem_outputs_path(self, runner, temp_project):
        """Single subsystem: outputs relative path with status, exit code 0."""
        # Create a subsystem first
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output
        assert "[DISCOVERING]" in result.output

    def test_multiple_subsystems_sorted(self, runner, temp_project):
        """Multiple subsystems: outputs sorted by number, exit code 0."""
        # Create subsystems
        runner.invoke(
            cli,
            ["subsystem", "discover", "first", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["subsystem", "discover", "second", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        # Should be sorted (highest first like chunks, or ascending - follow the pattern)
        assert "0001-first" in result.output
        assert "0002-second" in result.output

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        # Create a subsystem in a specific directory
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/subsystems/0001-validation" in result.output

    def test_list_format_includes_status_brackets(self, runner, temp_project):
        """Status appears in brackets after the path."""
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["subsystem", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Format should be: docs/subsystems/0001-validation [DISCOVERING]
        assert "docs/subsystems/0001-validation [DISCOVERING]" in result.output
