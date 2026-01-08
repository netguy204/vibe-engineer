"""Tests for the 'chunk list' CLI command."""

from ve import cli


class TestListCommand:
    """Tests for 've chunk list' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "list", "--help"])
        assert result.exit_code == 0
        assert "List all chunks" in result.output
        assert "--latest" in result.output

    def test_empty_project_exits_with_error(self, runner, temp_project):
        """Empty project: stderr says 'No chunks found', exit code 1."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No chunks found" in result.output

    def test_single_chunk_outputs_path(self, runner, temp_project):
        """Single chunk: outputs relative path, exit code 0."""
        # Create a chunk first
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/0001-feature-ve-001" in result.output

    def test_multiple_chunks_reverse_order(self, runner, temp_project):
        """Multiple chunks: outputs in reverse numeric order, exit code 0."""
        # Create chunks
        runner.invoke(
            cli,
            ["chunk", "start", "first", "VE-001", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "start", "second", "VE-002", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        assert "0002-second-ve-002" in lines[0]  # highest first
        assert "0001-first-ve-001" in lines[1]

    def test_latest_flag_outputs_only_highest(self, runner, temp_project):
        """--latest with multiple chunks: outputs only highest-numbered chunk."""
        # Create chunks
        runner.invoke(
            cli,
            ["chunk", "start", "first", "VE-001", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "start", "second", "VE-002", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "0002-second-ve-002" in lines[0]

    def test_project_dir_option_works(self, runner, temp_project):
        """--project-dir option works correctly."""
        # Create a chunk in a specific directory
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/0001-feature" in result.output
