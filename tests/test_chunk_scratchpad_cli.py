"""CLI integration tests for chunk commands."""

from pathlib import Path
import pytest
from click.testing import CliRunner

from ve import cli


class TestChunkCreateCLI:
    """Tests for `ve chunk create` command with in-repo storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self, tmp_path: Path):
        """Set up temporary project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "docs" / "chunks").mkdir(parents=True)
        return project_dir

    def test_creates_chunk_in_docs_chunks(self, cli_runner, temp_project):
        """Creates chunk in docs/chunks/ directory."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0, f"Failed with: {result.output}"
        assert "my-chunk" in result.output
        assert "docs/chunks/my-chunk" in result.output

        # Verify chunk was created in docs/chunks/
        chunk_path = temp_project / "docs" / "chunks" / "my-chunk"
        assert chunk_path.exists()
        assert (chunk_path / "GOAL.md").exists()

    def test_creates_chunk_with_ticket(self, cli_runner, temp_project):
        """Creates chunk with ticket reference (ticket in frontmatter only)."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "lin-123", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0

        # Chunk: docs/chunks/chunknaming_drop_ticket - Directory uses short_name only
        # Verify ticket in frontmatter (directory is my-chunk, not my-chunk-lin-123)
        goal_content = (
            temp_project / "docs" / "chunks" / "my-chunk" / "GOAL.md"
        ).read_text()
        assert "ticket: lin-123" in goal_content

    def test_validates_short_name(self, cli_runner, temp_project):
        """Validates short_name format - rejects names with invalid chars."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "create", "invalid name", "--project-dir", str(temp_project)],
        )

        assert result.exit_code != 0
        assert "Error" in result.output

    def test_rejects_duplicate_names(self, cli_runner, temp_project):
        """Rejects duplicate chunk names."""
        # Create first chunk as FUTURE so we can test duplicate detection
        # (without IMPLEMENTING guard interfering)
        result1 = cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--future", "--project-dir", str(temp_project)],
        )
        assert result1.exit_code == 0

        # Try to create duplicate
        result2 = cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--future", "--project-dir", str(temp_project)],
        )

        assert result2.exit_code != 0
        assert "already exists" in result2.output


class TestChunkListCLI:
    """Tests for `ve chunk list` command with in-repo storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self, tmp_path: Path):
        """Set up temporary project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "docs" / "chunks").mkdir(parents=True)
        return project_dir

    def test_lists_chunks_from_docs_chunks(self, cli_runner, temp_project):
        """Lists chunks from docs/chunks/ directory."""
        # Create a chunk first
        cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )

        # List chunks
        result = cli_runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "my-chunk" in result.output
        assert "IMPLEMENTING" in result.output

    def test_no_chunks_found(self, cli_runner, temp_project):
        """Reports no chunks found."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)],
        )

        assert result.exit_code != 0
        assert "No chunks found" in result.output

    def test_latest_returns_implementing_chunk(self, cli_runner, temp_project):
        """--latest returns current IMPLEMENTING chunk path."""
        # Create a chunk
        cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )

        # Get latest
        result = cli_runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "my-chunk" in result.output
        assert "docs/chunks/" in result.output

    def test_latest_no_implementing_chunk(self, cli_runner, temp_project):
        """--latest reports no implementing chunk when none exists."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "list", "--latest", "--project-dir", str(temp_project)],
        )

        assert result.exit_code != 0
        assert "No implementing chunk found" in result.output


class TestChunkCompleteCLI:
    """Tests for `ve chunk complete` command with in-repo storage."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self, tmp_path: Path):
        """Set up temporary project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "docs" / "chunks").mkdir(parents=True)
        return project_dir

    def test_completes_chunk_by_id(self, cli_runner, temp_project):
        """Completes chunk by explicit ID."""
        # Create a chunk
        cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )

        # Complete it
        result = cli_runner.invoke(
            cli,
            ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "Completed docs/chunks/my-chunk" in result.output

    def test_completes_current_implementing_chunk(self, cli_runner, temp_project):
        """Completes current IMPLEMENTING chunk when no ID provided."""
        # Create a chunk
        cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )

        # Complete without ID
        result = cli_runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "Completed docs/chunks/my-chunk" in result.output

    def test_chunk_status_changes_to_active(self, cli_runner, temp_project):
        """Chunk status changes to ACTIVE after completion."""
        # Create and complete a chunk
        cli_runner.invoke(
            cli,
            ["chunk", "create", "my-chunk", "--project-dir", str(temp_project)],
        )
        cli_runner.invoke(
            cli,
            ["chunk", "complete", "my-chunk", "--project-dir", str(temp_project)],
        )

        # List chunks and verify status
        result = cli_runner.invoke(
            cli,
            ["chunk", "list", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "ACTIVE" in result.output

    def test_error_for_nonexistent_chunk(self, cli_runner, temp_project):
        """Reports error for non-existent chunk."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "complete", "nonexistent", "--project-dir", str(temp_project)],
        )

        assert result.exit_code != 0
        assert "not found" in result.output

    def test_error_when_no_implementing_chunk(self, cli_runner, temp_project):
        """Reports error when no IMPLEMENTING chunk to complete."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "complete", "--project-dir", str(temp_project)],
        )

        assert result.exit_code != 0
        assert "No implementing chunk found" in result.output


class TestChunkStartAlias:
    """Tests for `ve chunk start` alias."""

    @pytest.fixture
    def cli_runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self, tmp_path: Path):
        """Set up temporary project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        (project_dir / "docs" / "chunks").mkdir(parents=True)
        return project_dir

    def test_start_alias_works(self, cli_runner, temp_project):
        """ve chunk start works as alias for ve chunk create."""
        result = cli_runner.invoke(
            cli,
            ["chunk", "start", "my-chunk", "--project-dir", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "my-chunk" in result.output
