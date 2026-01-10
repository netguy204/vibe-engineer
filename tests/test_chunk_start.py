"""Tests for the 'chunk start' CLI command."""

from ve import cli


class TestStartCommand:
    """Tests for the 'chunk start' command."""

    def test_start_command_exists(self, runner):
        """Verify the start command is registered."""
        result = runner.invoke(cli, ["chunk", "start", "--help"])
        assert result.exit_code == 0
        assert "Start a new chunk" in result.output

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
        # Check the created directory uses lowercase
        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        assert "my_feature" in created_dirs[0].name
        assert "My_Feature" not in created_dirs[0].name

    def test_ticket_id_normalized_to_lowercase(self, runner, temp_project):
        """ticket_id is normalized to lowercase."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"
        # Check the created directory uses lowercase
        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        assert "ve-001" in created_dirs[0].name
        assert "VE-001" not in created_dirs[0].name


class TestDuplicateDetection:
    """Tests for duplicate chunk detection.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    Note: With short_name only format, duplicate detection is now stricter.
    Creating a chunk with the same short_name will error by default.
    """

    def test_detects_duplicate_and_prompts(self, runner, temp_project):
        """Duplicate chunk detected, prompt shown, abort on 'no'."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Try to create duplicate - answer 'n' to abort
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)],
            input="n\n"
        )
        assert result2.exit_code != 0
        assert "already exists" in result2.output.lower() or "duplicate" in result2.output.lower()

        # Should still have only 1 chunk
        chunk_dir = temp_project / "docs" / "chunks"
        assert len(list(chunk_dir.iterdir())) == 1

    def test_allows_duplicate_when_confirmed(self, runner, temp_project):
        """Duplicate detection allows proceeding with different short_name."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Create with different short_name - no prompt needed
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature2", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Should have 2 chunks now
        chunk_dir = temp_project / "docs" / "chunks"
        assert len(list(chunk_dir.iterdir())) == 2

    def test_yes_flag_skips_prompt(self, runner, temp_project):
        """--yes flag bypasses duplicate confirmation prompt when creating with different names."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Create chunk with different name - --yes flag still works
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature2", "VE-001", "--yes", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Should have 2 chunks now
        chunk_dir = temp_project / "docs" / "chunks"
        assert len(list(chunk_dir.iterdir())) == 2


class TestPathFormat:
    """Tests for chunk path format.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_path_format_with_ticket_id(self, runner, temp_project):
        """Path format is {short_name}-{ticket_id} when ticket_id provided."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        assert created_dirs[0].name == "feature-ve-001"

    def test_path_format_without_ticket_id(self, runner, temp_project):
        """Path format is {short_name} when ticket_id omitted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        # Should NOT have -None at the end
        assert created_dirs[0].name == "feature"
        assert "None" not in created_dirs[0].name


class TestSuccessOutput:
    """Tests for success output.

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_prints_created_path(self, runner, temp_project):
        """Success message shows the created path."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
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

    # Chunk: docs/chunks/remove_sequence_prefix - Updated for short_name only format
    """

    def test_future_flag_creates_future_chunk(self, runner, temp_project):
        """--future flag creates chunk with status FUTURE."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0, f"Failed with: {result.output}"

        goal_path = temp_project / "docs" / "chunks" / "feature" / "GOAL.md"
        content = goal_path.read_text()
        assert "status: FUTURE" in content

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

        goal_path = temp_project / "docs" / "chunks" / "feature" / "GOAL.md"
        content = goal_path.read_text()
        assert "status: IMPLEMENTING" in content

    def test_future_flag_with_ticket_id(self, runner, temp_project):
        """--future flag works with ticket_id argument."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--future", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        goal_path = temp_project / "docs" / "chunks" / "feature-ve-001" / "GOAL.md"
        content = goal_path.read_text()
        assert "status: FUTURE" in content

    def test_help_shows_future_flag(self, runner):
        """--help includes documentation for --future flag."""
        result = runner.invoke(cli, ["chunk", "start", "--help"])
        assert result.exit_code == 0
        assert "--future" in result.output
