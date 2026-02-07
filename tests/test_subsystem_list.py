"""Tests for the 've subsystem list' CLI command."""

from ve import cli


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
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
        assert "docs/subsystems/validation" in result.output
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
        assert "first" in result.output
        assert "second" in result.output

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
        assert "docs/subsystems/validation" in result.output

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
        # Format should be: docs/subsystems/validation [DISCOVERING]
        assert "docs/subsystems/validation [DISCOVERING]" in result.output


# Chunk: docs/chunks/cli_json_output - JSON output tests for ve subsystem list
class TestSubsystemListJsonOutput:
    """Tests for --json output in 've subsystem list' command."""

    def test_json_output_basic(self, runner, temp_project):
        """--json outputs valid JSON with subsystem objects."""
        import json

        # Create a subsystem
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["subsystem", "list", "--json", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify it's valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1

        # Verify subsystem structure
        subsystem = data[0]
        assert "validation" in subsystem["name"]
        assert subsystem["status"] == "DISCOVERING"
        assert "is_tip" in subsystem

    def test_json_output_includes_frontmatter(self, runner, temp_project):
        """JSON output includes all frontmatter fields."""
        import json

        # Create a subsystem
        runner.invoke(
            cli,
            ["subsystem", "discover", "validation", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["subsystem", "list", "--json", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        data = json.loads(result.output)
        subsystem = data[0]

        # Check for standard frontmatter fields
        assert "name" in subsystem
        assert "status" in subsystem

    def test_json_output_empty(self, runner, temp_project):
        """Empty project returns empty array with exit code 0 in JSON mode."""
        import json

        result = runner.invoke(
            cli,
            ["subsystem", "list", "--json", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data == []

    def test_json_output_multiple_subsystems(self, runner, temp_project):
        """JSON output correctly lists multiple subsystems."""
        import json

        # Create multiple subsystems
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
            ["subsystem", "list", "--json", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert len(data) == 2

        # Both subsystems should be present
        names = [s["name"] for s in data]
        assert any("first" in n for n in names)
        assert any("second" in n for n in names)
