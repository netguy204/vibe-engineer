"""Tests for the 'chunk start' CLI command."""

from ve import cli
from chunks import Chunks


class TestStartCommand:
    """Tests for the 'chunk start' command."""

    def test_start_command_exists(self, runner):
        """Verify the start command is registered (as alias for create)."""
        result = runner.invoke(cli, ["chunk", "start", "--help"])
        assert result.exit_code == 0
        assert "Create a new chunk" in result.output

    def test_start_accepts_short_name_only(self, runner, temp_project):
        """Command accepts short_name without ticket_id."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"

    def test_start_accepts_short_name_and_ticket_id(self, runner, temp_project):
        """Command accepts short_name followed by ticket_id."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"


class TestShortNameValidation:
    """Tests for short_name validation."""

    def test_rejects_spaces(self, runner, temp_project):
        """short_name with spaces is rejected."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "invalid characters" in result.output.lower()

    def test_rejects_invalid_characters(self, runner, temp_project):
        """short_name with invalid characters is rejected."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my@feature!", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "character" in result.output.lower()

    def test_rejects_length_32_or_more(self, runner, temp_project):
        """short_name with 32+ characters is rejected."""
        long_name = "a" * 32
        result = runner.invoke(
            cli,
            ["chunk", "start", long_name, "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "32" in result.output or "length" in result.output.lower()

    def test_accepts_valid_short_name(self, runner, temp_project):
        """Valid short_name with alphanumeric, underscore, hyphen is accepted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature-v2", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"

    def test_collects_all_errors(self, runner, temp_project):
        """Multiple validation errors are collected and shown together."""
        # 33 chars with a space and invalid char
        bad_name = "a" * 30 + " @!"
        result = runner.invoke(
            cli,
            ["chunk", "start", bad_name, "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should mention multiple issues
        output_lower = result.output.lower()
        assert "invalid characters" in output_lower
        assert "32" in result.output or "less than" in output_lower


class TestTicketIdValidation:
    """Tests for ticket_id validation."""

    def test_rejects_invalid_characters(self, runner, temp_project):
        """ticket_id with invalid characters is rejected."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "VE@001!", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "character" in result.output.lower()

    def test_rejects_spaces(self, runner, temp_project):
        """ticket_id with spaces is rejected."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "VE 001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "invalid characters" in result.output.lower()

    def test_accepts_valid_ticket_id(self, runner, temp_project):
        """Valid ticket_id with alphanumeric, underscore, hyphen is accepted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "my_feature", "VE-001_a", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"


class TestLowercaseNormalization:
    """Tests for lowercase normalization of inputs."""

    def test_short_name_normalized_to_lowercase(self, runner, temp_project):
        """short_name is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "My_Feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"
        # Check the created chunk uses lowercase
        chunks = Chunks(temp_project)
        chunk_list = chunks.enumerate_chunks()
        assert len(chunk_list) == 1
        assert "my_feature" in chunk_list[0]
        assert "My_Feature" not in chunk_list[0]

    def test_ticket_id_normalized_to_lowercase(self, runner, temp_project):
        """ticket_id is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"
        # Check the output shows lowercase - in-repo chunks include ticket in directory name
        assert "feature" in result.output
        chunks = Chunks(temp_project)
        chunk_list = chunks.enumerate_chunks()
        assert len(chunk_list) == 1
        # In-repo format: short_name-ticket_id
        assert "feature-ve-001" in chunk_list[0]


class TestDuplicateDetection:
    """Tests for duplicate chunk detection.

    # Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
    Note: With short_name only format, duplicate detection is now stricter.
    Creating a chunk with the same short_name will error by default.
    """

    def test_detects_duplicate_and_rejects(self, runner, temp_project):
        """Duplicate chunk detected and rejected."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Complete it first so we can create another
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        # Try to create duplicate with same name
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code != 0
        assert "already exists" in result2.output.lower()

    def test_allows_different_short_name(self, runner, temp_project):
        """Different short_name is allowed after completing previous chunk."""
        # Create first chunk (IMPLEMENTING)
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Complete it
        runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)]
        )

        # Create with different short_name - should work
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature2", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Should have 2 chunks now
        chunks = Chunks(temp_project)
        assert len(chunks.enumerate_chunks()) == 2


class TestPathFormat:
    """Tests for chunk path format.

    In-repo chunks use short_name-ticket_id format in directory name.
    """

    def test_path_format_with_ticket_id(self, runner, temp_project):
        """In-repo chunk uses short_name-ticket_id for directory."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunks = Chunks(temp_project)
        chunk_list = chunks.enumerate_chunks()
        assert len(chunk_list) == 1
        assert chunk_list[0] == "feature-ve-001"
        # Ticket should also be in frontmatter
        fm = chunks.parse_chunk_frontmatter("feature-ve-001")
        assert fm.ticket == "ve-001"

    def test_path_format_without_ticket_id(self, runner, temp_project):
        """Path format is {short_name} when ticket_id omitted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunks = Chunks(temp_project)
        chunk_list = chunks.enumerate_chunks()
        assert len(chunk_list) == 1
        assert chunk_list[0] == "feature"


class TestSuccessOutput:
    """Tests for success output."""

    def test_prints_created_path(self, runner, temp_project):
        """Success message shows the created path."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        # In-repo path is docs/chunks/
        assert "docs/chunks/feature-ve-001" in result.output

    def test_prints_created_path_without_ticket_id(self, runner, temp_project):
        """Success message shows the created path when ticket_id omitted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "docs/chunks/feature" in result.output


class TestFutureFlag:
    """Tests for --future flag on 've chunk start'.

    In-repo chunks support FUTURE status for work that isn't immediately started.
    """

    def test_future_flag_creates_future_chunk(self, runner, temp_project):
        """--future flag creates chunk with FUTURE status."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"

        chunks = Chunks(temp_project)
        fm = chunks.parse_chunk_frontmatter("feature")
        assert fm.status.value == "FUTURE"

    def test_future_flag_outputs_created_path(self, runner, temp_project):
        """--future flag still outputs the created path."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "docs/chunks/feature" in result.output

    def test_without_future_flag_creates_implementing(self, runner, temp_project):
        """Without --future, chunk has status IMPLEMENTING."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunks = Chunks(temp_project)
        fm = chunks.parse_chunk_frontmatter("feature")
        assert fm.status.value == "IMPLEMENTING"

    def test_future_flag_with_ticket_id(self, runner, temp_project):
        """--future flag works with ticket_id argument."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunks = Chunks(temp_project)
        fm = chunks.parse_chunk_frontmatter("feature-ve-001")
        assert fm.status.value == "FUTURE"
        assert fm.ticket == "ve-001"

    def test_help_shows_future_flag(self, runner):
        """--help includes documentation for --future flag."""
        result = runner.invoke(cli, ["chunk", "start", "--help"])
        assert result.exit_code == 0
        assert "--future" in result.output


class TestImplementingGuard:
    """Tests for guard preventing multiple IMPLEMENTING chunks.

    In-repo storage only allows one IMPLEMENTING chunk at a time.
    FUTURE chunks can be created alongside an IMPLEMENTING chunk.
    """

    def test_rejects_second_implementing_chunk(self, runner, temp_project):
        """Cannot create second IMPLEMENTING chunk."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "first_chunk", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Try to create second IMPLEMENTING chunk - should fail
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "second_chunk", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code != 0
        assert "already IMPLEMENTING" in result2.output

    def test_allows_future_alongside_implementing(self, runner, temp_project):
        """Can create FUTURE chunk alongside IMPLEMENTING chunk."""
        # Create first chunk (IMPLEMENTING)
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "first_chunk", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Create second chunk as FUTURE - should succeed
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "second_chunk", "--future", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Both chunks should exist
        chunks = Chunks(temp_project)
        chunk_list = chunks.enumerate_chunks()
        assert len(chunk_list) == 2
        assert "first_chunk" in chunk_list
        assert "second_chunk" in chunk_list
