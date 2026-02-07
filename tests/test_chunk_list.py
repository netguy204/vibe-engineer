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
        assert "--current" in result.output

    def test_empty_project_exits_with_success(self, runner, temp_project):
        """Empty project: outputs 'No chunks found', exit code 0 (success)."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
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

    def test_current_flag_outputs_implementing_chunk(self, runner, temp_project):
        """--current outputs the current IMPLEMENTING chunk."""
        # Create first chunk (IMPLEMENTING)
        runner.invoke(
            cli,
            ["chunk", "start", "current_chunk", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "current_chunk" in lines[0]

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


# Chunk: docs/chunks/chunk_list_flags - Renamed --latest to --current
class TestCurrentFlag:
    """Tests for --current flag (renamed from --latest)."""

    def test_help_shows_current_flag(self, runner):
        """--help shows the --current flag."""
        result = runner.invoke(cli, ["chunk", "list", "--help"])
        assert result.exit_code == 0
        assert "--current" in result.output
        # --latest should no longer appear
        assert "--latest" not in result.output

    def test_current_returns_implementing_chunk(self, runner, temp_project):
        """--current returns an IMPLEMENTING chunk."""
        # Create an IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "implementing" in result.output

    def test_current_fails_when_no_chunks(self, runner, temp_project):
        """--current fails when no chunks exist."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "No implementing chunk found" in result.output or "No chunks found" in result.output

    def test_current_ignores_future_chunks(self, runner, temp_project):
        """--current returns IMPLEMENTING, not FUTURE chunks."""
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
            ["chunk", "list", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should return the IMPLEMENTING one
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        assert "implementing" in lines[0]

    def test_current_and_last_active_mutually_exclusive(self, runner, temp_project):
        """--current and --last-active cannot be used together."""
        # Create a chunk for valid state
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Error message should mention mutual exclusivity or that both can't be used
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()


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

    def test_last_active_and_current_mutually_exclusive(self, runner, temp_project):
        """--last-active and --current cannot be used together."""
        # Create a chunk for valid state
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--last-active", "--project-dir", str(temp_project)]
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


# Chunk: docs/chunks/chunklist_external_status - External chunk list handling
class TestExternalChunkListing:
    """Tests for listing external chunk references."""

    def test_external_chunk_shows_external_status_not_parse_error(self, runner, temp_project):
        """External chunks show [EXTERNAL: repo] instead of [PARSE ERROR]."""
        # Create an external chunk reference (only external.yaml, no GOAL.md)
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_feature"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_feature
repo: acme/other-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Should show EXTERNAL status, not PARSE ERROR
        assert "[EXTERNAL:" in result.output
        assert "acme/other-repo" in result.output
        # Should NOT show parse error
        assert "[PARSE ERROR:" not in result.output
        assert "not found" not in result.output.lower()

    def test_external_chunk_displays_alongside_local_chunks(self, runner, temp_project):
        """External and local chunks display correctly together."""
        # Create a local IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "local_feature", "--project-dir", str(temp_project)]
        )

        # Create an external chunk reference
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_feature"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_feature
repo: acme/external-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        lines = result.output.strip().split("\n")
        assert len(lines) == 2

        # Local chunk should show IMPLEMENTING
        local_line = [l for l in lines if "local_feature" in l][0]
        assert "[IMPLEMENTING]" in local_line

        # External chunk should show EXTERNAL status
        external_line = [l for l in lines if "external_feature" in l][0]
        assert "[EXTERNAL:" in external_line
        assert "acme/external-repo" in external_line

    def test_external_chunk_participates_in_tip_detection(self, runner, temp_project):
        """External chunks can be tip chunks (marked with *)."""
        # Create an external chunk reference with no created_after (should be a tip)
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_tip"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_tip
repo: acme/other-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # External chunk should have tip indicator
        assert "*" in result.output

    def test_current_flag_does_not_return_external_chunks(self, runner, temp_project):
        """--current flag returns IMPLEMENTING chunks, not external ones."""
        # Create an external chunk reference
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_feature"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_feature
repo: acme/other-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--current", "--project-dir", str(temp_project)]
        )
        # Should fail because there's no IMPLEMENTING chunk
        assert result.exit_code == 1
        assert "No implementing chunk found" in result.output


# Chunk: docs/chunks/chunklist_status_filter - Status filtering for chunk list
class TestStatusFiltering:
    """Tests for status filtering in 've chunk list' command."""

    def test_status_filter_future_only(self, runner, temp_project):
        """--status FUTURE shows only FUTURE chunks."""
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
            ["chunk", "list", "--status", "FUTURE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output
        assert "implementing" not in result.output

    def test_status_filter_implementing_only(self, runner, temp_project):
        """--status IMPLEMENTING shows only IMPLEMENTING chunks."""
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
            ["chunk", "list", "--status", "IMPLEMENTING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "implementing" in result.output
        assert "future-work" not in result.output

    def test_status_filter_active_only(self, runner, temp_project):
        """--status ACTIVE shows only ACTIVE chunks."""
        # Create and complete a chunk (IMPLEMENTING -> ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "future-work" not in result.output

    def test_status_filter_case_insensitive(self, runner, temp_project):
        """Status filter is case-insensitive."""
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output

    def test_status_filter_multiple_statuses(self, runner, temp_project):
        """Multiple --status options show chunks matching any status."""
        # Create and complete a chunk (ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )
        # Create IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "FUTURE", "--status", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output
        assert "completed" in result.output
        assert "implementing" not in result.output

    def test_status_filter_comma_separated(self, runner, temp_project):
        """--status FUTURE,ACTIVE shows both statuses."""
        # Create and complete a chunk (ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )
        # Create IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "FUTURE,ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output
        assert "completed" in result.output
        assert "implementing" not in result.output

    def test_status_filter_invalid_status_error(self, runner, temp_project):
        """Invalid status value produces helpful error."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "INVALID", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should list valid options
        assert "FUTURE" in result.output or "Invalid status" in result.output

    def test_status_filter_empty_result(self, runner, temp_project):
        """No chunks match filter shows appropriate message, exits with success."""
        # Create only IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "No chunks found" in result.output or "matching" in result.output.lower()

    def test_status_filter_with_project_dir(self, runner, temp_project):
        """--status composes correctly with --project-dir."""
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "FUTURE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output


class TestStatusConvenienceFlags:
    """Tests for convenience flags --future, --active, --implementing."""

    def test_future_flag_equivalent_to_status_future(self, runner, temp_project):
        """--future is equivalent to --status FUTURE."""
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )
        # Create IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "future-work" in result.output
        assert "implementing" not in result.output

    def test_active_flag_equivalent_to_status_active(self, runner, temp_project):
        """--active is equivalent to --status ACTIVE."""
        # Create and complete a chunk (ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "future-work" not in result.output

    def test_implementing_flag_equivalent_to_status_implementing(self, runner, temp_project):
        """--implementing is equivalent to --status IMPLEMENTING."""
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
            ["chunk", "list", "--implementing", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "implementing" in result.output
        assert "future-work" not in result.output


class TestStatusFilterMutualExclusivity:
    """Tests for mutual exclusivity between status filters and output mode flags."""

    def test_status_and_current_mutually_exclusive(self, runner, temp_project):
        """--status and --current cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "FUTURE", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_status_and_last_active_mutually_exclusive(self, runner, temp_project):
        """--status and --last-active cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "FUTURE", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_future_flag_and_current_mutually_exclusive(self, runner, temp_project):
        """--future and --current cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--future", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0


class TestStatusFilterWithExternalChunks:
    """Tests for status filtering with external chunk references."""

    def test_status_filter_excludes_external_chunks(self, runner, temp_project):
        """Status filtering excludes external chunks (they have no parseable status)."""
        # Create a local IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "local_feature", "--project-dir", str(temp_project)]
        )

        # Create an external chunk reference
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_feature"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_feature
repo: acme/external-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--status", "IMPLEMENTING", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Local IMPLEMENTING chunk should appear
        assert "local_feature" in result.output
        # External chunk should NOT appear (can't filter by status)
        assert "external_feature" not in result.output

    def test_no_status_filter_includes_external_chunks(self, runner, temp_project):
        """Without status filter, external chunks are included."""
        # Create a local IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "local_feature", "--project-dir", str(temp_project)]
        )

        # Create an external chunk reference
        external_chunk_dir = temp_project / "docs" / "chunks" / "external_feature"
        external_chunk_dir.mkdir(parents=True)
        external_yaml_content = """artifact_type: chunk
artifact_id: external_feature
repo: acme/external-repo
track: main
"""
        (external_chunk_dir / "external.yaml").write_text(external_yaml_content)

        result = runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # Both should appear
        assert "local_feature" in result.output
        assert "external_feature" in result.output


# Chunk: docs/chunks/chunk_list_flags - New --recent flag
class TestRecentFlag:
    """Tests for --recent flag in 've chunk list'."""

    def test_help_shows_recent_flag(self, runner):
        """--help shows the --recent flag."""
        result = runner.invoke(cli, ["chunk", "list", "--help"])
        assert result.exit_code == 0
        assert "--recent" in result.output

    def test_recent_returns_active_chunks(self, runner, temp_project):
        """--recent returns ACTIVE chunks."""
        # Create and complete a chunk (IMPLEMENTING -> ACTIVE)
        runner.invoke(
            cli,
            ["chunk", "start", "feature_one", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "feature_one" in result.output
        assert "docs/chunks/" in result.output

    def test_recent_shows_multiple_active_chunks(self, runner, temp_project):
        """--recent shows multiple ACTIVE chunks in creation order."""
        # Create and complete three chunks
        for name in ["first", "second", "third"]:
            runner.invoke(
                cli,
                ["chunk", "start", name, "--project-dir", str(temp_project)]
            )
            runner.invoke(
                cli,
                ["chunk", "complete", "--project-dir", str(temp_project)]
            )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        # All three should appear
        assert "first" in result.output
        assert "second" in result.output
        assert "third" in result.output
        # Should be in newest-first order
        lines = result.output.strip().split("\n")
        assert len(lines) == 3
        assert "third" in lines[0]
        assert "second" in lines[1]
        assert "first" in lines[2]

    def test_recent_fails_when_no_active_chunks(self, runner, temp_project):
        """--recent fails when no ACTIVE chunks exist."""
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
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1
        assert "no active" in result.output.lower() or "not found" in result.output.lower()

    def test_recent_fails_when_empty_project(self, runner, temp_project):
        """--recent fails when no chunks exist."""
        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 1

    def test_recent_ignores_implementing_chunks(self, runner, temp_project):
        """--recent returns only ACTIVE chunks, not IMPLEMENTING."""
        # Create and complete one chunk
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create an IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "implementing", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "implementing" not in result.output

    def test_recent_ignores_future_chunks(self, runner, temp_project):
        """--recent returns only ACTIVE chunks, not FUTURE."""
        # Create and complete one chunk
        runner.invoke(
            cli,
            ["chunk", "start", "completed", "--project-dir", str(temp_project)]
        )
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )
        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future-work", "--future", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "completed" in result.output
        assert "future-work" not in result.output

    def test_recent_limits_to_10_chunks(self, runner, temp_project):
        """--recent limits output to 10 chunks even if more exist."""
        # Create and complete 12 chunks
        for i in range(12):
            runner.invoke(
                cli,
                ["chunk", "start", f"chunk_{i:02d}", "--project-dir", str(temp_project)]
            )
            runner.invoke(
                cli,
                ["chunk", "complete", "--project-dir", str(temp_project)]
            )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 10
        # Should have newest chunks (11, 10, 09, ..., 02) but not 00, 01
        assert "chunk_11" in result.output
        assert "chunk_02" in result.output
        assert "chunk_01" not in result.output
        assert "chunk_00" not in result.output

    def test_recent_outputs_docs_chunks_path(self, runner, temp_project):
        """--recent outputs path in docs/chunks/ format."""
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
            ["chunk", "list", "--recent", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "docs/chunks/my_feature" in result.output


class TestRecentFlagMutualExclusivity:
    """Tests for --recent flag mutual exclusivity."""

    def test_recent_and_current_mutually_exclusive(self, runner, temp_project):
        """--recent and --current cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--current", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_recent_and_last_active_mutually_exclusive(self, runner, temp_project):
        """--recent and --last-active cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--last-active", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()

    def test_recent_and_status_mutually_exclusive(self, runner, temp_project):
        """--recent and --status cannot be used together."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )

        result = runner.invoke(
            cli,
            ["chunk", "list", "--recent", "--status", "ACTIVE", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "cannot" in result.output.lower()
