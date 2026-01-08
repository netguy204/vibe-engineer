"""Tests for the 'chunk activate' CLI command."""

from chunks import Chunks
from ve import cli


class TestActivateCommand:
    """Tests for 've chunk activate' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "activate", "--help"])
        assert result.exit_code == 0
        assert "Activate a FUTURE chunk" in result.output
        assert "CHUNK_ID" in result.output

    def test_activates_future_chunk(self, runner, temp_project):
        """Successfully activates a FUTURE chunk to IMPLEMENTING."""
        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        # Verify status changed
        chunk_mgr = Chunks(temp_project)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("0001")
        assert frontmatter["status"] == "IMPLEMENTING"

    def test_activates_using_full_chunk_name(self, runner, temp_project):
        """Can activate using full chunk directory name."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0001-feature", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_mgr = Chunks(temp_project)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("0001")
        assert frontmatter["status"] == "IMPLEMENTING"

    def test_outputs_success_message(self, runner, temp_project):
        """Shows success message after activation."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0
        assert "Activated" in result.output or "0001-feature" in result.output


class TestActivateFailures:
    """Tests for failure conditions of 've chunk activate'."""

    def test_fails_when_chunk_not_found(self, runner, temp_project):
        """Fails with error when chunk doesn't exist."""
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0999", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_fails_when_chunk_not_future(self, runner, temp_project):
        """Fails with error when target chunk is not FUTURE."""
        # Create a FUTURE chunk then activate to make it IMPLEMENTING
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "active", status="FUTURE")
        # Manually change it to ACTIVE (non-FUTURE, non-IMPLEMENTING)
        goal_path = chunk_mgr.get_chunk_goal_path("0001")
        content = goal_path.read_text()
        goal_path.write_text(content.replace("status: FUTURE", "status: ACTIVE"))

        result = runner.invoke(
            cli,
            ["chunk", "activate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        # Should mention that status is not FUTURE
        assert "ACTIVE" in result.output or "FUTURE" in result.output

    def test_fails_when_another_chunk_implementing(self, runner, temp_project):
        """Fails when another chunk is already IMPLEMENTING."""
        # Create an IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "current", "--project-dir", str(temp_project)]
        )
        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0
        assert "already" in result.output.lower() or "implementing" in result.output.lower()

    def test_fails_when_active_chunk_exists(self, runner, temp_project):
        """Also fails when an IMPLEMENTING chunk exists (different naming)."""
        # Create chunks
        chunk_mgr = Chunks(temp_project)
        chunk_mgr.create_chunk(None, "implementing", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "future", status="FUTURE")

        result = runner.invoke(
            cli,
            ["chunk", "activate", "0002", "--project-dir", str(temp_project)]
        )
        assert result.exit_code != 0


class TestActivateWithTicketId:
    """Tests for activation with ticket IDs."""

    def test_activates_chunk_with_ticket_id(self, runner, temp_project):
        """Can activate a chunk that has a ticket ID."""
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--future", "--project-dir", str(temp_project)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "0001", "--project-dir", str(temp_project)]
        )
        assert result.exit_code == 0

        chunk_mgr = Chunks(temp_project)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("0001")
        assert frontmatter["status"] == "IMPLEMENTING"
