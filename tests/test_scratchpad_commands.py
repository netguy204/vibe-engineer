"""Tests for scratchpad_commands module."""
# Chunk: docs/chunks/scratchpad_chunk_commands - Unit tests for scratchpad command functions

from pathlib import Path
import pytest

from models import ScratchpadChunkStatus
from scratchpad import Scratchpad, ScratchpadChunks
from scratchpad_commands import (
    detect_scratchpad_context,
    scratchpad_create_chunk,
    scratchpad_list_chunks,
    scratchpad_complete_chunk,
    get_current_scratchpad_chunk,
)


# ============================================================================
# detect_scratchpad_context Tests
# ============================================================================


class TestDetectScratchpadContext:
    """Tests for detect_scratchpad_context function."""

    def test_project_context(self, tmp_path: Path):
        """Detects project context from regular directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        project_path, task_name = detect_scratchpad_context(project_dir)

        assert project_path == project_dir
        assert task_name is None

    def test_task_context(self, tmp_path: Path):
        """Detects task context from directory with .ve-task.yaml."""
        task_dir = tmp_path / "my-task"
        task_dir.mkdir()
        (task_dir / ".ve-task.yaml").write_text("name: my-task\n")

        project_path, task_name = detect_scratchpad_context(task_dir)

        assert project_path is None
        assert task_name == "my-task"


# ============================================================================
# scratchpad_create_chunk Tests
# ============================================================================


class TestScratchpadCreateChunk:
    """Tests for scratchpad_create_chunk function."""

    def test_creates_chunk_in_project_context(self, tmp_path: Path):
        """Creates chunk in project-scoped scratchpad."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        chunk_path = scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        assert chunk_path.exists()
        assert chunk_path.name == "my-chunk"
        assert (chunk_path / "GOAL.md").exists()
        assert chunk_path.parent.name == "chunks"
        assert chunk_path.parent.parent.name == "my-project"

    def test_creates_chunk_in_task_context(self, tmp_path: Path):
        """Creates chunk in task-scoped scratchpad."""
        scratchpad_root = tmp_path / "scratchpad"

        chunk_path = scratchpad_create_chunk(
            project_path=None,
            task_name="my-task",
            short_name="task-chunk",
            scratchpad_root=scratchpad_root,
        )

        assert chunk_path.exists()
        assert chunk_path.name == "task-chunk"
        assert (chunk_path / "GOAL.md").exists()
        assert chunk_path.parent.name == "chunks"
        assert chunk_path.parent.parent.name == "task:my-task"

    def test_creates_chunk_with_ticket(self, tmp_path: Path):
        """Creates chunk with ticket reference."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        chunk_path = scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            ticket="LIN-123",
            scratchpad_root=scratchpad_root,
        )

        goal_content = (chunk_path / "GOAL.md").read_text()
        assert "ticket: LIN-123" in goal_content

    def test_rejects_duplicate_names(self, tmp_path: Path):
        """Raises error for duplicate chunk names."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        with pytest.raises(ValueError, match="already exists"):
            scratchpad_create_chunk(
                project_path=project_dir,
                task_name=None,
                short_name="my-chunk",
                scratchpad_root=scratchpad_root,
            )

    def test_validates_short_name(self, tmp_path: Path):
        """Validates short_name format."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        with pytest.raises(ValueError, match="Invalid short_name"):
            scratchpad_create_chunk(
                project_path=project_dir,
                task_name=None,
                short_name="123-invalid",
                scratchpad_root=scratchpad_root,
            )

    def test_requires_context(self, tmp_path: Path):
        """Raises error if no context provided."""
        scratchpad_root = tmp_path / "scratchpad"

        with pytest.raises(ValueError, match="Either project_path or task_name"):
            scratchpad_create_chunk(
                project_path=None,
                task_name=None,
                short_name="my-chunk",
                scratchpad_root=scratchpad_root,
            )


# ============================================================================
# scratchpad_list_chunks Tests
# ============================================================================


class TestScratchpadListChunks:
    """Tests for scratchpad_list_chunks function."""

    def test_lists_chunks_in_project_context(self, tmp_path: Path):
        """Lists chunks from project-scoped scratchpad."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        # Create some chunks
        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="chunk-a",
            scratchpad_root=scratchpad_root,
        )
        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="chunk-b",
            scratchpad_root=scratchpad_root,
        )

        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert isinstance(result, list)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "chunk-a" in names
        assert "chunk-b" in names

    def test_lists_chunks_in_task_context(self, tmp_path: Path):
        """Lists chunks from task-scoped scratchpad."""
        scratchpad_root = tmp_path / "scratchpad"

        scratchpad_create_chunk(
            project_path=None,
            task_name="my-task",
            short_name="task-chunk",
            scratchpad_root=scratchpad_root,
        )

        result = scratchpad_list_chunks(
            project_path=None,
            task_name="my-task",
            scratchpad_root=scratchpad_root,
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "task-chunk"

    def test_returns_empty_list_when_no_chunks(self, tmp_path: Path):
        """Returns empty list when no chunks exist."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert result == []

    def test_latest_returns_implementing_chunk(self, tmp_path: Path):
        """Returns current IMPLEMENTING chunk with latest=True."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        chunk_path = scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            latest=True,
            scratchpad_root=scratchpad_root,
        )

        assert result is not None
        assert result == str(chunk_path)

    def test_latest_returns_none_when_no_implementing_chunk(self, tmp_path: Path):
        """Returns None with latest=True when no IMPLEMENTING chunk."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        # Create a chunk and archive it
        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )
        scratchpad_complete_chunk(
            project_path=project_dir,
            task_name=None,
            chunk_id="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            latest=True,
            scratchpad_root=scratchpad_root,
        )

        assert result is None

    def test_list_includes_status(self, tmp_path: Path):
        """List result includes status information."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert len(result) == 1
        assert result[0]["status"] == "IMPLEMENTING"


# ============================================================================
# scratchpad_complete_chunk Tests
# ============================================================================


class TestScratchpadCompleteChunk:
    """Tests for scratchpad_complete_chunk function."""

    def test_archives_chunk_by_id(self, tmp_path: Path):
        """Archives chunk by explicit ID."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        completed_id = scratchpad_complete_chunk(
            project_path=project_dir,
            task_name=None,
            chunk_id="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        assert completed_id == "my-chunk"

        # Verify status changed
        result = scratchpad_list_chunks(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )
        assert result[0]["status"] == "ARCHIVED"

    def test_archives_current_implementing_chunk(self, tmp_path: Path):
        """Archives current IMPLEMENTING chunk when no ID provided."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        completed_id = scratchpad_complete_chunk(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert completed_id == "my-chunk"

    def test_raises_for_nonexistent_chunk(self, tmp_path: Path):
        """Raises error for non-existent chunk."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        # Create context directory structure
        Scratchpad(scratchpad_root=scratchpad_root).ensure_initialized()
        context_path = scratchpad_root / "my-project"
        context_path.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError, match="not found"):
            scratchpad_complete_chunk(
                project_path=project_dir,
                task_name=None,
                chunk_id="nonexistent",
                scratchpad_root=scratchpad_root,
            )

    def test_raises_when_no_implementing_chunk(self, tmp_path: Path):
        """Raises error when no IMPLEMENTING chunk exists."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        # Create context but no chunks
        Scratchpad(scratchpad_root=scratchpad_root).ensure_initialized()
        context_path = scratchpad_root / "my-project"
        context_path.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError, match="No IMPLEMENTING chunk found"):
            scratchpad_complete_chunk(
                project_path=project_dir,
                task_name=None,
                scratchpad_root=scratchpad_root,
            )


# ============================================================================
# get_current_scratchpad_chunk Tests
# ============================================================================


class TestGetCurrentScratchpadChunk:
    """Tests for get_current_scratchpad_chunk function."""

    def test_returns_current_implementing_chunk(self, tmp_path: Path):
        """Returns current IMPLEMENTING chunk ID and path."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        chunk_path = scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="my-chunk",
            scratchpad_root=scratchpad_root,
        )

        chunk_id, path = get_current_scratchpad_chunk(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert chunk_id == "my-chunk"
        assert path == chunk_path

    def test_returns_none_when_no_implementing_chunk(self, tmp_path: Path):
        """Returns (None, None) when no IMPLEMENTING chunk exists."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        chunk_id, path = get_current_scratchpad_chunk(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert chunk_id is None
        assert path is None

    def test_skips_archived_chunks(self, tmp_path: Path):
        """Skips ARCHIVED chunks when looking for current."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        scratchpad_root = tmp_path / "scratchpad"

        # Create and archive a chunk
        scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="old-chunk",
            scratchpad_root=scratchpad_root,
        )
        scratchpad_complete_chunk(
            project_path=project_dir,
            task_name=None,
            chunk_id="old-chunk",
            scratchpad_root=scratchpad_root,
        )

        # Create a new implementing chunk
        new_chunk_path = scratchpad_create_chunk(
            project_path=project_dir,
            task_name=None,
            short_name="new-chunk",
            scratchpad_root=scratchpad_root,
        )

        chunk_id, path = get_current_scratchpad_chunk(
            project_path=project_dir,
            task_name=None,
            scratchpad_root=scratchpad_root,
        )

        assert chunk_id == "new-chunk"
        assert path == new_chunk_path
