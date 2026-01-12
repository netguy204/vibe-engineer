"""Tests for the 'chunk list' CLI command."""

from chunks import Chunks
from ve import cli


# Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
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
        assert "docs/chunks/feature-ve-001" in result.output

    def test_multiple_chunks_reverse_order(self, runner, temp_project):
        """Multiple chunks: outputs in reverse numeric order, exit code 0."""
        # Create chunks - complete first before creating second (guard prevents multiple IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "first", "VE-001", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "status", "first-ve-001", "ACTIVE", "--project-dir", str(temp_project)]
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
        assert "second-ve-002" in lines[0]  # highest first
        assert "first-ve-001" in lines[1]

    def test_latest_flag_outputs_only_highest(self, runner, temp_project):
        """--latest with multiple chunks: outputs only IMPLEMENTING chunk."""
        # Create chunks - complete first before creating second (guard prevents multiple IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "first", "VE-001", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "status", "first-ve-001", "ACTIVE", "--project-dir", str(temp_project)]
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
        assert "second-ve-002" in lines[0]

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
        assert "docs/chunks/feature" in result.output


class TestListStatusDisplay:
    """Tests for status display in 've chunk list' output."""

    def test_list_shows_status_for_each_chunk(self, runner, temp_project):
        """Output includes status in brackets for each chunk."""
        # Create chunks with different statuses
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "start", "future", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "[IMPLEMENTING]" in result.output
        assert "[FUTURE]" in result.output

    def test_list_format_includes_status_brackets(self, runner, temp_project):
        """Status appears in brackets after the path."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Format should be: docs/chunks/feature [IMPLEMENTING]
        assert "docs/chunks/feature [IMPLEMENTING]" in result.output


class TestLatestFlagWithStatus:
    """Tests for --latest flag using get_current_chunk()."""

    def test_latest_returns_implementing_chunk_not_future(self, runner, temp_project):
        """--latest returns IMPLEMENTING chunk, skipping higher-numbered FUTURE."""
        # Create IMPLEMENTING chunk first
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk (higher number)
        runner.invoke(
            cli,
            ["chunk", "start", "future", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should return the IMPLEMENTING chunk, not the FUTURE one
        assert "implementing" in result.output
        assert "future" not in result.output

    def test_latest_fails_when_no_implementing_chunks(self, runner, temp_project):
        """--latest fails when only FUTURE chunks exist."""
        # Create only FUTURE chunks
        runner.invoke(
            cli,
            ["chunk", "start", "future1", "--future", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "start", "future2", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No implementing chunk found" in result.output or "No chunks found" in result.output

    def test_latest_with_active_and_future_chunks(self, runner, temp_project):
        """--latest returns None when only ACTIVE and FUTURE chunks exist."""
        # Create a chunk and manually set it to ACTIVE
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "active", status="IMPLEMENTING")
        goal_path = chunk_mgr.get_chunk_goal_path("active")
        content = goal_path.read_text()
        goal_path.write_text(content.replace("status: IMPLEMENTING", "status: ACTIVE"))

        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
