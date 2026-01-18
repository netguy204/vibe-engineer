"""CLI integration tests for scratchpad-based chunk commands."""

from pathlib import Path
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from ve import cli


class TestChunkCreateCLI:
    """Tests for `ve chunk create` command with scratchpad storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_env(self, tmp_path: Path):
        """Set up temporary project and scratchpad directories."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"
        return project_dir, scratchpad_root

    def test_creates_chunk_in_scratchpad(self, cli_runner, temp_env, tmp_path):
        """Creates chunk in scratchpad storage."""
        project_dir, scratchpad_root = temp_env

        # Patch the scratchpad root to use temp directory
        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "my-chunk" in result.output

        # Verify chunk was created in scratchpad
        chunk_path = scratchpad_root / "my-project" / "chunks" / "my-chunk"
        assert chunk_path.exists()
        assert (chunk_path / "GOAL.md").exists()

    def test_creates_chunk_with_ticket(self, cli_runner, temp_env):
        """Creates chunk with ticket reference."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "lin-123", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0

        # Verify ticket in frontmatter
        goal_content = (
            scratchpad_root / "my-project" / "chunks" / "my-chunk" / "GOAL.md"
        ).read_text()
        assert "ticket: lin-123" in goal_content

    def test_validates_short_name(self, cli_runner, temp_env):
        """Validates short_name format - rejects names with invalid chars."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "create", "invalid name", "--project-dir", str(project_dir)],
            )

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_rejects_duplicate_names(self, cli_runner, temp_env):
        """Rejects duplicate chunk names."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create first chunk
            result1 = cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )
            assert result1.exit_code == 0

            # Try to create duplicate
            result2 = cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

        assert result2.exit_code != 0
        assert "already exists" in result2.output


class TestChunkListCLI:
    """Tests for `ve chunk list` command with scratchpad storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_env(self, tmp_path: Path):
        """Set up temporary project and scratchpad directories."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"
        return project_dir, scratchpad_root

    def test_lists_chunks_from_scratchpad(self, cli_runner, temp_env):
        """Lists chunks from scratchpad storage."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create a chunk first
            cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

            # List chunks
            result = cli_runner.invoke(
                cli,
                ["chunk", "list", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "my-chunk" in result.output
        assert "IMPLEMENTING" in result.output

    def test_no_chunks_found(self, cli_runner, temp_env):
        """Reports no chunks found."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "list", "--project-dir", str(project_dir)],
            )

        assert result.exit_code != 0
        assert "No chunks found" in result.output

    def test_latest_returns_implementing_chunk(self, cli_runner, temp_env):
        """--latest returns current IMPLEMENTING chunk path."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create a chunk
            cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

            # Get latest
            result = cli_runner.invoke(
                cli,
                ["chunk", "list", "--latest", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "my-chunk" in result.output

    def test_latest_no_implementing_chunk(self, cli_runner, temp_env):
        """--latest reports no implementing chunk when none exists."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "list", "--latest", "--project-dir", str(project_dir)],
            )

        assert result.exit_code != 0
        assert "No implementing chunk found" in result.output


class TestChunkCompleteCLI:
    """Tests for `ve chunk complete` command with scratchpad storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_env(self, tmp_path: Path):
        """Set up temporary project and scratchpad directories."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"
        return project_dir, scratchpad_root

    def test_completes_chunk_by_id(self, cli_runner, temp_env):
        """Completes chunk by explicit ID."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create a chunk
            cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

            # Complete it
            result = cli_runner.invoke(
                cli,
                ["chunk", "complete", "my-chunk", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "Completed my-chunk" in result.output

    def test_completes_current_implementing_chunk(self, cli_runner, temp_env):
        """Completes current IMPLEMENTING chunk when no ID provided."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create a chunk
            cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )

            # Complete without ID
            result = cli_runner.invoke(
                cli,
                ["chunk", "complete", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "Completed my-chunk" in result.output

    def test_chunk_status_changes_to_archived(self, cli_runner, temp_env):
        """Chunk status changes to ARCHIVED after completion."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            # Create and complete a chunk
            cli_runner.invoke(
                cli,
                ["chunk", "create", "my-chunk", "--project-dir", str(project_dir)],
            )
            cli_runner.invoke(
                cli,
                ["chunk", "complete", "my-chunk", "--project-dir", str(project_dir)],
            )

            # List chunks and verify status
            result = cli_runner.invoke(
                cli,
                ["chunk", "list", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "ARCHIVED" in result.output

    def test_error_for_nonexistent_chunk(self, cli_runner, temp_env):
        """Reports error for non-existent chunk."""
        project_dir, scratchpad_root = temp_env

        # Create empty scratchpad context
        (scratchpad_root / "my-project").mkdir(parents=True)

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "complete", "nonexistent", "--project-dir", str(project_dir)],
            )

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_error_when_no_implementing_chunk(self, cli_runner, temp_env):
        """Reports error when no IMPLEMENTING chunk to complete."""
        project_dir, scratchpad_root = temp_env

        # Create empty scratchpad context
        (scratchpad_root / "my-project").mkdir(parents=True)

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "complete", "--project-dir", str(project_dir)],
            )

        assert result.exit_code != 0
        assert "Error" in result.output


class TestChunkStartAlias:
    """Tests for `ve chunk start` alias."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_env(self, tmp_path: Path):
        """Set up temporary project and scratchpad directories."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"
        return project_dir, scratchpad_root

    def test_start_alias_works(self, cli_runner, temp_env):
        """ve chunk start works as alias for ve chunk create."""
        project_dir, scratchpad_root = temp_env

        with patch("scratchpad_commands.Scratchpad.DEFAULT_ROOT", scratchpad_root):
            result = cli_runner.invoke(
                cli,
                ["chunk", "start", "my-chunk", "--project-dir", str(project_dir)],
            )

        assert result.exit_code == 0
        assert "my-chunk" in result.output
