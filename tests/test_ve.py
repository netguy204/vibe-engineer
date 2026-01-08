"""Tests for ve.py CLI"""

import pathlib
import tempfile

import pytest
from click.testing import CliRunner

# Import the module under test
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from ve import cli
from chunks import Chunks


@pytest.fixture
def temp_project():
    """Create a temporary project directory for chunk output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield pathlib.Path(tmpdir)


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestChunksClass:
    """Tests for the Chunks class."""

    def test_create_chunk_creates_directory(self, temp_project):
        """Verify chunk creation creates the expected directory structure."""
        chunk_mgr = Chunks(temp_project)
        result_path = chunk_mgr.create_chunk("VE-001", "my_feature")

        assert result_path.exists()
        assert result_path.is_dir()
        assert "0001-my_feature-VE-001" in result_path.name

    def test_enumerate_chunks_empty(self, temp_project):
        """Verify enumerate_chunks returns empty list for new project."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.enumerate_chunks() == []

    def test_num_chunks_increments(self, temp_project):
        """Verify chunk numbering increments correctly."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.num_chunks == 0

        chunk_mgr.create_chunk("VE-001", "first")
        assert chunk_mgr.num_chunks == 1

        chunk_mgr.create_chunk("VE-002", "second")
        assert chunk_mgr.num_chunks == 2


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
        assert "spaces" in result.output.lower()

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
        assert "space" in output_lower
        assert "character" in output_lower
        assert "32" in result.output or "length" in output_lower


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
        assert "space" in result.output.lower()

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
    """Tests for duplicate chunk detection."""

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
        """Duplicate creation proceeds when user confirms."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Create duplicate - answer 'y' to proceed
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)],
            input="y\n"
        )
        assert result2.exit_code == 0

        # Should have 2 chunks now
        chunk_dir = temp_project / "docs" / "chunks"
        assert len(list(chunk_dir.iterdir())) == 2

    def test_yes_flag_skips_prompt(self, runner, temp_project):
        """--yes flag bypasses duplicate confirmation prompt."""
        # Create first chunk
        result1 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--project-dir", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Create duplicate with --yes - no prompt needed
        result2 = runner.invoke(
            cli,
            ["chunk", "start", "feature", "VE-001", "--yes", "--project-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Should have 2 chunks now
        chunk_dir = temp_project / "docs" / "chunks"
        assert len(list(chunk_dir.iterdir())) == 2


class TestPathFormat:
    """Tests for chunk path format."""

    def test_path_format_with_ticket_id(self, runner, temp_project):
        """Path format is {NNNN}-{short_name}-{ticket_id} when ticket_id provided."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        assert created_dirs[0].name == "0001-feature-ve-001"

    def test_path_format_without_ticket_id(self, runner, temp_project):
        """Path format is {NNNN}-{short_name} when ticket_id omitted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_dir = temp_project / "docs" / "chunks"
        created_dirs = list(chunk_dir.iterdir())
        assert len(created_dirs) == 1
        # Should NOT have -None at the end
        assert created_dirs[0].name == "0001-feature"
        assert "None" not in created_dirs[0].name


class TestListChunks:
    """Tests for Chunks.list_chunks() method."""

    def test_empty_project_returns_empty_list(self, temp_project):
        """Empty project returns empty list."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.list_chunks() == []

    def test_single_chunk_returns_list_with_one_item(self, temp_project):
        """Single chunk returns list with one item."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "feature")
        result = chunk_mgr.list_chunks()
        assert len(result) == 1
        assert result[0] == (1, "0001-feature-VE-001")

    def test_multiple_chunks_descending_order(self, temp_project):
        """Multiple chunks returned in descending numeric order."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.create_chunk("VE-003", "third")
        result = chunk_mgr.list_chunks()
        assert len(result) == 3
        assert result[0][0] == 3  # highest first
        assert result[1][0] == 2
        assert result[2][0] == 1

    def test_chunks_with_and_without_ticket_id(self, temp_project):
        """Chunks with different name formats all parsed correctly."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "with_ticket")
        chunk_mgr.create_chunk(None, "without_ticket")
        result = chunk_mgr.list_chunks()
        assert len(result) == 2
        assert result[0] == (2, "0002-without_ticket")
        assert result[1] == (1, "0001-with_ticket-VE-001")


class TestGetLatestChunk:
    """Tests for Chunks.get_latest_chunk() method."""

    def test_empty_project_returns_none(self, temp_project):
        """Empty project returns None."""
        chunk_mgr = Chunks(temp_project)
        assert chunk_mgr.get_latest_chunk() is None

    def test_single_chunk_returns_that_chunk(self, temp_project):
        """Single chunk returns that chunk's name."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "feature")
        assert chunk_mgr.get_latest_chunk() == "0001-feature-VE-001"

    def test_multiple_chunks_returns_highest(self, temp_project):
        """Multiple chunks returns highest-numbered chunk."""
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk("VE-001", "first")
        chunk_mgr.create_chunk("VE-002", "second")
        chunk_mgr.create_chunk("VE-003", "third")
        assert chunk_mgr.get_latest_chunk() == "0003-third-VE-003"


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
        assert "docs/chunks/0001-feature-ve-001" in result.output

    def test_prints_created_path_without_ticket_id(self, runner, temp_project):
        """Success message shows the created path when ticket_id omitted."""
        result = runner.invoke(
            cli,
            ["chunk", "start", "feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Created" in result.output
        assert "docs/chunks/0001-feature" in result.output
