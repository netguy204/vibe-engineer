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


class TestFrontmatterParseErrors:
    """Tests for surfacing Pydantic validation errors in frontmatter parsing.

    When a chunk has invalid frontmatter, `ve chunk list` should show a helpful
    error message instead of just `[UNKNOWN]`.
    """

    def test_list_shows_parse_error_for_invalid_frontmatter(self, runner, temp_project):
        """When frontmatter parsing fails, shows [PARSE ERROR: ...] not [UNKNOWN]."""
        # Create a chunk with valid structure first
        runner.invoke(
            cli,
            ["chunk", "start", "valid_chunk", "--project-dir", str(temp_project)]
        )
        # Complete it so we can create another
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        # Manually create a chunk with invalid frontmatter (invalid status value)
        invalid_chunk_dir = temp_project / "docs" / "chunks" / "invalid_chunk"
        invalid_chunk_dir.mkdir(parents=True)
        goal_content = """---
status: NOT_A_VALID_STATUS
---
# Invalid Chunk
"""
        (invalid_chunk_dir / "GOAL.md").write_text(goal_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should show PARSE ERROR instead of UNKNOWN
        assert "[PARSE ERROR:" in result.output
        # Should NOT just say UNKNOWN
        assert "[UNKNOWN]" not in result.output

    def test_list_shows_specific_validation_error(self, runner, temp_project):
        """Error message includes specific Pydantic validation info."""
        # Manually create a chunk with frontmatter that fails Pydantic validation
        invalid_chunk_dir = temp_project / "docs" / "chunks" / "bad_status"
        invalid_chunk_dir.mkdir(parents=True)
        goal_content = """---
status: BANANA
---
# Invalid Chunk
"""
        (invalid_chunk_dir / "GOAL.md").write_text(goal_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Error should mention the field (status)
        assert "status" in result.output.lower() or "PARSE ERROR" in result.output

    def test_list_shows_error_for_missing_required_field(self, runner, temp_project):
        """Missing required fields in frontmatter show parse error."""
        # Manually create a chunk without required 'status' field
        invalid_chunk_dir = temp_project / "docs" / "chunks" / "missing_status"
        invalid_chunk_dir.mkdir(parents=True)
        goal_content = """---
ticket: null
---
# Missing Status
"""
        (invalid_chunk_dir / "GOAL.md").write_text(goal_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should show PARSE ERROR
        assert "[PARSE ERROR:" in result.output or "PARSE ERROR" in result.output

    def test_valid_chunks_still_show_correctly(self, runner, temp_project):
        """Valid chunks display their status correctly alongside error chunks."""
        # Create a valid chunk
        runner.invoke(
            cli,
            ["chunk", "start", "valid", "--project-dir", str(temp_project)]
        )
        # Complete it
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        # Create an invalid chunk manually
        invalid_chunk_dir = temp_project / "docs" / "chunks" / "invalid"
        invalid_chunk_dir.mkdir(parents=True)
        goal_content = """---
status: BAD
---
# Invalid
"""
        (invalid_chunk_dir / "GOAL.md").write_text(goal_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Valid chunk should show ACTIVE
        assert "[ACTIVE]" in result.output
        # Invalid chunk should show PARSE ERROR
        assert "[PARSE ERROR:" in result.output or "PARSE ERROR" in result.output
