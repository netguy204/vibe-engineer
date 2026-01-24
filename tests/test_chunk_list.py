"""Tests for the 'chunk list' CLI command."""

from ve import cli


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
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
        """Single chunk: outputs docs/chunks path, exit code 0."""
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
        # In-repo path is docs/chunks/
        assert "docs/chunks/feature" in result.output

    def test_multiple_chunks_shows_all(self, runner, temp_project):
        """Multiple chunks: outputs all chunks (IMPLEMENTING + FUTURE)."""
        # Create one IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "first", "VE-001", "--project-dir", str(temp_project)]
        )
        # Create a FUTURE chunk (allowed alongside IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "second", "VE-002", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        # Both chunks should appear
        assert any("first" in line for line in lines)
        assert any("second" in line for line in lines)

    def test_latest_flag_outputs_implementing_chunk(self, runner, temp_project):
        """--latest outputs the current IMPLEMENTING chunk."""
        # Create first chunk (IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "current", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "current" in lines[0]

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
        assert "chunks/feature" in result.output


class TestListStatusDisplay:
    """Tests for status display in 've chunk list' output."""

    def test_list_shows_status_for_each_chunk(self, runner, temp_project):
        """Output includes status in brackets for each chunk."""
        # Create one IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "first", "--project-dir", str(temp_project)]
        )
        # Create a FUTURE chunk (allowed alongside IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "second", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # One should be IMPLEMENTING, one should be FUTURE
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
        # Format should include [IMPLEMENTING]
        assert "[IMPLEMENTING]" in result.output
        assert "feature" in result.output


class TestLatestFlagWithStatus:
    """Tests for --latest flag using in-repo storage."""

    def test_latest_returns_implementing_chunk(self, runner, temp_project):
        """--latest returns an IMPLEMENTING chunk."""
        # Create an IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "implementing" in result.output

    def test_latest_fails_when_no_chunks(self, runner, temp_project):
        """--latest fails when no chunks exist."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No implementing chunk found" in result.output or "No chunks found" in result.output

    def test_latest_ignores_future_chunks(self, runner, temp_project):
        """--latest returns IMPLEMENTING, not FUTURE chunks."""
        # Create IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should return the IMPLEMENTING one
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "implementing" in lines[0]


# Chunk: docs/chunks/chunk_last_active - Last active chunk lookup
class TestLastActiveFlag:
    """Tests for --last-active flag in 've chunk list'."""

    def test_help_shows_last_active_flag(self, runner):
        """--help shows the --last-active flag."""
        result = runner.invoke(cli, ["chunk", "list", "--help"])
        assert result.exit_code == 0
        assert "--last-active" in result.output

    def test_last_active_returns_active_tip(self, runner, temp_project):
        """--last-active returns an ACTIVE tip chunk."""
        # Create and complete a chunk (IMPLEMENTING -> ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "feature" in result.output
        assert "docs/chunks/" in result.output

    def test_last_active_fails_when_no_active_tips(self, runner, temp_project):
        """--last-active fails when no ACTIVE tip chunks exist."""
        # Create only IMPLEMENTING and FUTURE chunks
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "active" in result.output.lower() or "found" in result.output.lower()

    def test_last_active_fails_when_empty_project(self, runner, temp_project):
        """--last-active fails when no chunks exist."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1

    def test_last_active_and_latest_mutually_exclusive(self, runner, temp_project):
        """--last-active and --latest cannot be used together."""
        # Create a chunk for valid state
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Error message should mention mutual exclusivity or that both can't be used
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_last_active_ignores_implementing_chunks(self, runner, temp_project):
        """--last-active returns ACTIVE, not IMPLEMENTING chunks."""
        # Create IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        # --last-active should fail because no ACTIVE chunks exist
        result = runner.invoke(
            cli,
            ["chunk", "list", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1

    def test_last_active_outputs_docs_chunks_path(self, runner, temp_project):
        """--last-active outputs path in docs/chunks/ format."""
        # Create and complete a chunk
        runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/my_feature" in result.output
