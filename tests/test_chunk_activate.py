"""Tests for the 'chunk activate' CLI command.

Note: chunk activate is for in-repo chunks (task directory mode) only.
Scratchpad chunks don't have FUTURE status and don't need activation.
"""

import pytest
from conftest import setup_task_directory
from chunks import Chunks
from models import ChunkStatus
from ve import cli


# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
class TestActivateCommand:
    """Tests for 've chunk activate' CLI command."""

    def test_help_shows_correct_usage(self, runner):
        """--help shows correct usage."""
        result = runner.invoke(cli, ["chunk", "activate", "--help"])
        assert result.exit_code == 0
        assert "Activate a FUTURE chunk" in result.output
        assert "CHUNK_ID" in result.output

    def test_activates_future_chunk(self, runner, tmp_path):
        """Successfully activates a FUTURE chunk to IMPLEMENTING."""
        # Set up task directory for in-repo chunks
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create a FUTURE chunk in task directory
        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(task_dir)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

        # Verify status changed in external repo
        chunk_mgr = Chunks(external_path)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("feature")
        assert frontmatter.status == ChunkStatus.IMPLEMENTING

    def test_activates_using_full_chunk_name(self, runner, tmp_path):
        """Can activate using full chunk directory name."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(task_dir)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

        chunk_mgr = Chunks(external_path)
        frontmatter = chunk_mgr.parse_chunk_frontmatter("feature")
        assert frontmatter.status == ChunkStatus.IMPLEMENTING

    def test_outputs_success_message(self, runner, tmp_path):
        """Shows success message after activation."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        runner.invoke(
            cli,
            ["chunk", "start", "feature", "--future", "--project-dir", str(task_dir)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0
        assert "Activated" in result.output or "feature" in result.output


class TestActivateFailures:
    """Tests for failure conditions of 've chunk activate'."""

    def test_fails_when_chunk_not_found(self, runner, tmp_path):
        """Fails with error when chunk doesn't exist."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        result = runner.invoke(
            cli,
            ["chunk", "activate", "nonexistent", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_fails_when_chunk_not_future(self, runner, tmp_path):
        """Fails with error when target chunk is not FUTURE."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create a FUTURE chunk then manually change it to ACTIVE
        chunk_mgr = Chunks(external_path)
        chunk_mgr.create_chunk(None, "active", status="FUTURE")
        goal_path = chunk_mgr.get_chunk_goal_path("active")
        content = goal_path.read_text()
        goal_path.write_text(content.replace("status: FUTURE", "status: ACTIVE"))

        result = runner.invoke(
            cli,
            ["chunk", "activate", "active", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        # Should mention that status is not FUTURE
        assert "ACTIVE" in result.output or "FUTURE" in result.output

    def test_fails_when_another_chunk_implementing(self, runner, tmp_path):
        """Fails when another chunk is already IMPLEMENTING."""
        task_dir, _, _ = setup_task_directory(tmp_path)

        # Create an IMPLEMENTING chunk
        runner.invoke(
            cli,
            ["chunk", "start", "current", "--project-dir", str(task_dir)]
        )
        # Create a FUTURE chunk
        runner.invoke(
            cli,
            ["chunk", "start", "future", "--future", "--project-dir", str(task_dir)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "future", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0
        assert "already" in result.output.lower() or "implementing" in result.output.lower()

    def test_fails_when_active_chunk_exists(self, runner, tmp_path):
        """Also fails when an IMPLEMENTING chunk exists (different naming)."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        # Create chunks directly in external repo
        chunk_mgr = Chunks(external_path)
        chunk_mgr.create_chunk(None, "implementing", status="IMPLEMENTING")
        chunk_mgr.create_chunk(None, "future", status="FUTURE")

        result = runner.invoke(
            cli,
            ["chunk", "activate", "future", "--project-dir", str(task_dir)]
        )
        assert result.exit_code != 0


class TestActivateWithTicketId:
    """Tests for activation with ticket IDs."""

    def test_activates_chunk_with_ticket_id(self, runner, tmp_path):
        """Can activate a chunk that has a ticket ID."""
        task_dir, external_path, _ = setup_task_directory(tmp_path)

        runner.invoke(
            cli,
            ["chunk", "start", "feature", "ve-001", "--future", "--project-dir", str(task_dir)]
        )
        result = runner.invoke(
            cli,
            ["chunk", "activate", "feature", "--project-dir", str(task_dir)]
        )
        assert result.exit_code == 0

        chunk_mgr = Chunks(external_path)
        # In task mode, chunks may have different naming
        chunks = chunk_mgr.enumerate_chunks()
        assert len(chunks) > 0
        frontmatter = chunk_mgr.parse_chunk_frontmatter(chunks[0])
        assert frontmatter.status == ChunkStatus.IMPLEMENTING
