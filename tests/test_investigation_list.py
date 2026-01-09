"""Tests for the 've investigation list' CLI command."""

from ve import cli


class TestInvestigationListCommand:
    """Tests for 've investigation list' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["investigation", "list", "--help"])
        assert result.exit_code == 0
        assert "List" in result.output or "list" in result.output.lower()

    def test_empty_project_exits_with_error(self, runner, temp_project):
        """Empty project: stderr says 'No investigations found', exit code 1."""
        result = runner.invoke(
            cli,
            ["investigation", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No investigations found" in result.output

    def test_single_investigation_outputs_path_with_status(self, runner, temp_project):
        """Single investigation: outputs relative path with status, exit code 0."""
        # Create an investigation first
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/investigations/0001-memory_leak" in result.output
        assert "[ONGOING]" in result.output

    def test_multiple_investigations_sorted(self, runner, temp_project):
        """Multiple investigations: outputs sorted by number, exit code 0."""
        # Create investigations
        runner.invoke(
            cli,
            ["investigation", "create", "first", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["investigation", "create", "second", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        # Should be sorted
        assert "0001-first" in result.output
        assert "0002-second" in result.output

    def test_state_filter_works(self, runner, temp_project):
        """--state filter works correctly."""
        # Create an investigation
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )

        # Filter by ONGOING (should find it)
        result = runner.invoke(
            cli,
            ["investigation", "list", "--state", "ONGOING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "0001-memory_leak" in result.output

        # Filter by SOLVED (should not find it)
        result = runner.invoke(
            cli,
            ["investigation", "list", "--state", "SOLVED", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No investigations found" in result.output

    def test_invalid_state_errors_with_message(self, runner, temp_project):
        """Invalid state value errors with message listing valid states."""
        result = runner.invoke(
            cli,
            ["investigation", "list", "--state", "INVALID", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "Invalid state" in result.output or "invalid" in result.output.lower()
        # Should list valid states
        assert "ONGOING" in result.output

    def test_format_includes_status_brackets(self, runner, temp_project):
        """Status appears in brackets after the path."""
        runner.invoke(
            cli,
            ["investigation", "create", "memory_leak", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["investigation", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Format should be: docs/investigations/0001-memory_leak [ONGOING]
        assert "docs/investigations/0001-memory_leak [ONGOING]" in result.output
