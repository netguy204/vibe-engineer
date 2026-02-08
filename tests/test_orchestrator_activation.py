# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Tests for extracted activation module
"""Tests for the orchestrator activation module.

These tests verify chunk activation lifecycle functions that manage
chunk status transitions during orchestrator dispatch.
"""

import pytest
from pathlib import Path

from orchestrator.activation import (
    VerificationStatus,
    VerificationResult,
    verify_chunk_active_status,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)


class TestVerificationStatus:
    """Tests for the VerificationStatus enum."""

    def test_enum_values(self):
        """All expected status values exist."""
        assert VerificationStatus.COMPLETED == "COMPLETED"
        assert VerificationStatus.IMPLEMENTING == "IMPLEMENTING"
        assert VerificationStatus.ERROR == "ERROR"


class TestVerificationResult:
    """Tests for the VerificationResult dataclass."""

    def test_result_with_status_only(self):
        """Result can be created with status only."""
        result = VerificationResult(status=VerificationStatus.COMPLETED)
        assert result.status == VerificationStatus.COMPLETED
        assert result.error is None

    def test_result_with_error(self):
        """Result can include an error message."""
        result = VerificationResult(
            status=VerificationStatus.ERROR,
            error="Chunk not found"
        )
        assert result.status == VerificationStatus.ERROR
        assert result.error == "Chunk not found"


class TestVerifyChunkActiveStatus:
    """Tests for verify_chunk_active_status function."""

    def test_active_status(self, tmp_path):
        """Returns COMPLETED when chunk has status: ACTIVE."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: ACTIVE
---

# Chunk Goal
""")

        result = verify_chunk_active_status(tmp_path, "test_chunk")
        assert result.status == VerificationStatus.COMPLETED
        assert result.error is None

    def test_historical_status(self, tmp_path):
        """Returns COMPLETED when chunk has status: HISTORICAL."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: HISTORICAL
---

# Chunk Goal
""")

        result = verify_chunk_active_status(tmp_path, "test_chunk")
        assert result.status == VerificationStatus.COMPLETED
        assert result.error is None

    def test_implementing_status(self, tmp_path):
        """Returns IMPLEMENTING when chunk has status: IMPLEMENTING."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: IMPLEMENTING
---

# Chunk Goal
""")

        result = verify_chunk_active_status(tmp_path, "test_chunk")
        assert result.status == VerificationStatus.IMPLEMENTING
        assert result.error is None

    def test_missing_chunk(self, tmp_path):
        """Returns ERROR when chunk does not exist."""
        result = verify_chunk_active_status(tmp_path, "nonexistent_chunk")
        assert result.status == VerificationStatus.ERROR
        assert "not found" in result.error.lower()

    def test_unexpected_status(self, tmp_path):
        """Returns ERROR for non-completed, non-implementing status."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: FUTURE
---

# Chunk Goal
""")

        result = verify_chunk_active_status(tmp_path, "test_chunk")
        assert result.status == VerificationStatus.ERROR
        assert "post-IMPLEMENTING" in result.error


class TestActivateChunkInWorktree:
    """Tests for activate_chunk_in_worktree function."""

    def test_activate_future_chunk(self, tmp_path):
        """Activates a FUTURE chunk to IMPLEMENTING."""
        chunk_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: FUTURE
---

# Chunk Goal
""")

        displaced = activate_chunk_in_worktree(tmp_path, "target_chunk")

        assert displaced is None
        # Verify status was updated
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_already_implementing(self, tmp_path):
        """Returns None if chunk is already IMPLEMENTING."""
        chunk_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: IMPLEMENTING
---

# Chunk Goal
""")

        displaced = activate_chunk_in_worktree(tmp_path, "target_chunk")

        assert displaced is None
        # Status should remain IMPLEMENTING
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_displaces_existing_implementing(self, tmp_path):
        """Displaces existing IMPLEMENTING chunk when activating new one."""
        # Create existing IMPLEMENTING chunk
        existing_dir = tmp_path / "docs" / "chunks" / "existing_chunk"
        existing_dir.mkdir(parents=True)
        existing_goal = existing_dir / "GOAL.md"
        existing_goal.write_text("""---
status: IMPLEMENTING
---

# Existing Chunk
""")

        # Create target chunk to activate
        target_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        target_dir.mkdir(parents=True)
        target_goal = target_dir / "GOAL.md"
        target_goal.write_text("""---
status: FUTURE
---

# Target Chunk
""")

        displaced = activate_chunk_in_worktree(tmp_path, "target_chunk")

        assert displaced == "existing_chunk"
        # Existing chunk should now be FUTURE
        assert "status: FUTURE" in existing_goal.read_text()
        # Target chunk should now be IMPLEMENTING
        assert "status: IMPLEMENTING" in target_goal.read_text()

    def test_nonexistent_chunk_raises(self, tmp_path):
        """Raises ValueError for nonexistent chunk."""
        with pytest.raises(ValueError, match="not found"):
            activate_chunk_in_worktree(tmp_path, "nonexistent_chunk")

    def test_non_future_status_raises(self, tmp_path):
        """Raises ValueError when chunk is not FUTURE."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: ACTIVE
---

# Chunk Goal
""")

        with pytest.raises(ValueError, match="expected 'FUTURE'"):
            activate_chunk_in_worktree(tmp_path, "test_chunk")


class TestRestoreDisplacedChunk:
    """Tests for restore_displaced_chunk function."""

    def test_restore_future_to_implementing(self, tmp_path):
        """Restores a FUTURE chunk back to IMPLEMENTING."""
        chunk_dir = tmp_path / "docs" / "chunks" / "displaced_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: FUTURE
---

# Chunk Goal
""")

        restore_displaced_chunk(tmp_path, "displaced_chunk")

        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_nonexistent_chunk_warns(self, tmp_path, caplog):
        """Logs warning for nonexistent chunk."""
        restore_displaced_chunk(tmp_path, "nonexistent_chunk")

        assert "not found" in caplog.text.lower()

    def test_non_future_status_warns(self, tmp_path, caplog):
        """Logs warning when chunk is not FUTURE."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("""---
status: ACTIVE
---

# Chunk Goal
""")

        restore_displaced_chunk(tmp_path, "test_chunk")

        assert "expected 'FUTURE'" in caplog.text
        # Status should not have changed
        assert "status: ACTIVE" in goal_md.read_text()
