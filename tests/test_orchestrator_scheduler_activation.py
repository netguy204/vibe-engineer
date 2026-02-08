# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_verify_active - Unit and integration tests for ACTIVE status verification
# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
"""Tests for chunk activation in the orchestrator scheduler.

These tests cover:
- verify_chunk_active_status helper
- ACTIVE status verification during completion
- attention_reason tracking
- activate_chunk_in_worktree helper
- restore_displaced_chunk helper
- Chunk activation during work unit execution

Fixtures (state_store, mock_worktree_manager, mock_agent_runner, orchestrator_config,
scheduler) are defined in conftest.py.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from orchestrator.activation import (
    verify_chunk_active_status,
    VerificationStatus,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)
from orchestrator.models import (
    AgentResult,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)


class TestVerifyChunkActiveStatus:
    """Tests for the verify_chunk_active_status helper."""

    def test_returns_active_when_status_active(self, tmp_path):
        """Returns ACTIVE when GOAL.md has status: ACTIVE."""
        # Create chunk directory with GOAL.md
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: ACTIVE
ticket: null
---

# Chunk Goal
"""
        )

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.COMPLETED
        assert result.error is None

    def test_returns_implementing_when_status_implementing(self, tmp_path):
        """Returns IMPLEMENTING when GOAL.md has status: IMPLEMENTING."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
ticket: null
---

# Chunk Goal
"""
        )

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.IMPLEMENTING
        assert result.error is None

    def test_returns_error_when_goal_md_missing(self, tmp_path):
        """Returns ERROR when GOAL.md doesn't exist."""
        # Create chunk directory but no GOAL.md
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.ERROR
        assert "not found" in result.error

    def test_returns_error_when_no_frontmatter(self, tmp_path):
        """Returns ERROR when GOAL.md has no frontmatter."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("# Chunk Goal\n\nNo frontmatter here.")

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.ERROR
        # The Chunks class treats unparseable GOAL.md as "not found"
        assert "not found" in result.error.lower() or "missing" in result.error.lower()

    def test_returns_error_when_status_missing(self, tmp_path):
        """Returns ERROR when frontmatter has no status field."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
ticket: null
---

# Chunk Goal
"""
        )

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.ERROR
        # The Chunks class treats frontmatter without required status as invalid/not found
        assert "not found" in result.error.lower() or "missing" in result.error.lower()

    def test_returns_error_for_unexpected_status(self, tmp_path):
        """Returns ERROR for unexpected status values like FUTURE."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        result = verify_chunk_active_status(tmp_path, "test_chunk")

        assert result.status == VerificationStatus.ERROR
        assert "FUTURE" in result.error


class TestActiveStatusVerification:
    """Tests for ACTIVE status verification in the scheduler."""

    @pytest.mark.asyncio
    async def test_advance_complete_proceeds_when_active(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Completion proceeds when status is ACTIVE."""
        # Set up chunk with ACTIVE status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: ACTIVE
---

# Chunk Goal
"""
        )

        # Configure mock worktree manager to return our tmp_path
        mock_worktree_manager.get_worktree_path.return_value = tmp_path

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.DONE

    @pytest.mark.asyncio
    async def test_advance_complete_retries_when_implementing(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Retries when status is IMPLEMENTING."""
        # Set up chunk with IMPLEMENTING status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
---

# Chunk Goal
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        # Mock resume_for_active_status to return an error (simulating failure)
        mock_agent_runner.resume_for_active_status = AsyncMock(
            return_value=AgentResult(
                completed=False,
                suspended=False,
                error="Failed to update status",
            )
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            session_id="session123",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Should have called resume_for_active_status
        mock_agent_runner.resume_for_active_status.assert_called_once()

        # Should have incremented retry counter
        updated = state_store.get_work_unit("test_chunk")
        assert updated.completion_retries == 1

    @pytest.mark.asyncio
    async def test_advance_complete_marks_needs_attention_after_max_retries(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Marks NEEDS_ATTENTION after max retries exceeded."""
        # Set up chunk with IMPLEMENTING status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
---

# Chunk Goal
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            completion_retries=2,  # Already at max
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION

    @pytest.mark.asyncio
    async def test_advance_complete_marks_needs_attention_on_error(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Marks NEEDS_ATTENTION when verification returns ERROR."""
        # Set up chunk directory but with unparseable GOAL.md
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("No frontmatter here")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION


# Chunk: docs/chunks/orch_attention_reason - Scheduler tests for attention_reason tracking
class TestAttentionReason:
    """Tests for attention_reason tracking."""

    @pytest.mark.asyncio
    async def test_suspended_result_captures_question_as_reason(self, scheduler, state_store):
        """Suspended result stores question text as attention_reason."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=True,
            session_id="session123",
            question={"question": "Which database should I use?", "options": ["PostgreSQL", "MySQL"]},
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.attention_reason == "Question: Which database should I use?"

    @pytest.mark.asyncio
    async def test_suspended_result_without_question_uses_default(self, scheduler, state_store):
        """Suspended result without question data uses default reason."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=True,
            session_id="session123",
            question=None,
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.attention_reason == "Question: Agent asked a question"

    @pytest.mark.asyncio
    async def test_error_result_stores_error_as_reason(self, scheduler, state_store):
        """Error result stores error message as attention_reason."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=False, error="Connection timeout while accessing API")

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.attention_reason == "Connection timeout while accessing API"

    @pytest.mark.asyncio
    async def test_max_retries_stores_reason(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Max retries exceeded stores appropriate attention_reason."""
        # Set up chunk with IMPLEMENTING status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
---

# Chunk Goal
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            completion_retries=2,  # Already at max
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "IMPLEMENTING" in updated.attention_reason
        assert "retries" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_verification_error_stores_reason(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Verification error stores error message as attention_reason."""
        # Set up chunk directory but with unparseable GOAL.md
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text("No frontmatter here")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.attention_reason is not None
        # The Chunks class treats unparseable GOAL.md as "not found"
        assert (
            "frontmatter" in updated.attention_reason.lower()
            or "not found" in updated.attention_reason.lower()
            or "missing" in updated.attention_reason.lower()
        )


class TestActivateChunkInWorktree:
    """Tests for the activate_chunk_in_worktree helper function."""

    def test_activates_future_chunk(self, tmp_path):
        """Activates a FUTURE chunk to IMPLEMENTING."""
        # Create chunk directory with FUTURE status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        result = activate_chunk_in_worktree(tmp_path, "test_chunk")

        # Should return None (no displaced chunk)
        assert result is None

        # Chunk should now be IMPLEMENTING
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_returns_none_for_already_implementing_chunk(self, tmp_path):
        """Returns None if chunk is already IMPLEMENTING."""
        # Create chunk directory with IMPLEMENTING status
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
ticket: null
---

# Chunk Goal
"""
        )

        result = activate_chunk_in_worktree(tmp_path, "test_chunk")

        # Should return None (no displacement, already implementing)
        assert result is None

        # Status should remain unchanged
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_displaces_existing_implementing_chunk(self, tmp_path):
        """Displaces an existing IMPLEMENTING chunk when activating a FUTURE chunk."""
        # Create existing IMPLEMENTING chunk
        existing_dir = tmp_path / "docs" / "chunks" / "existing_chunk"
        existing_dir.mkdir(parents=True)
        existing_goal = existing_dir / "GOAL.md"
        existing_goal.write_text(
            """---
status: IMPLEMENTING
ticket: null
---

# Existing Chunk
"""
        )

        # Create target FUTURE chunk
        target_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        target_dir.mkdir(parents=True)
        target_goal = target_dir / "GOAL.md"
        target_goal.write_text(
            """---
status: FUTURE
ticket: null
---

# Target Chunk
"""
        )

        result = activate_chunk_in_worktree(tmp_path, "target_chunk")

        # Should return the displaced chunk name
        assert result == "existing_chunk"

        # Existing chunk should now be FUTURE
        content = existing_goal.read_text()
        assert "status: FUTURE" in content

        # Target chunk should now be IMPLEMENTING
        content = target_goal.read_text()
        assert "status: IMPLEMENTING" in content

    def test_raises_for_nonexistent_chunk(self, tmp_path):
        """Raises ValueError for non-existent chunk."""
        # Create docs/chunks but no chunk directory
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        with pytest.raises(ValueError) as exc_info:
            activate_chunk_in_worktree(tmp_path, "nonexistent_chunk")

        assert "not found" in str(exc_info.value)

    def test_raises_for_non_future_chunk(self, tmp_path):
        """Raises ValueError for chunk that is not FUTURE or IMPLEMENTING."""
        # Create chunk with ACTIVE status
        chunk_dir = tmp_path / "docs" / "chunks" / "active_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: ACTIVE
ticket: null
---

# Active Chunk
"""
        )

        with pytest.raises(ValueError) as exc_info:
            activate_chunk_in_worktree(tmp_path, "active_chunk")

        assert "ACTIVE" in str(exc_info.value)
        assert "FUTURE" in str(exc_info.value)


class TestRestoreDisplacedChunk:
    """Tests for the restore_displaced_chunk helper function."""

    def test_restores_displaced_chunk_to_implementing(self, tmp_path):
        """Restores a FUTURE chunk back to IMPLEMENTING."""
        # Create chunk with FUTURE status (simulating displaced chunk)
        chunk_dir = tmp_path / "docs" / "chunks" / "displaced_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Displaced Chunk
"""
        )

        restore_displaced_chunk(tmp_path, "displaced_chunk")

        # Chunk should now be IMPLEMENTING
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_does_not_restore_non_future_chunk(self, tmp_path):
        """Does not modify chunk if not in FUTURE status."""
        # Create chunk with IMPLEMENTING status (shouldn't be changed)
        chunk_dir = tmp_path / "docs" / "chunks" / "implementing_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: IMPLEMENTING
ticket: null
---

# Implementing Chunk
"""
        )

        restore_displaced_chunk(tmp_path, "implementing_chunk")

        # Status should remain IMPLEMENTING
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    def test_handles_nonexistent_chunk_gracefully(self, tmp_path):
        """Does not raise for non-existent chunk."""
        # Create docs/chunks but no chunk directory
        (tmp_path / "docs" / "chunks").mkdir(parents=True)

        # Should not raise
        restore_displaced_chunk(tmp_path, "nonexistent_chunk")


class TestChunkActivationInWorkUnit:
    """Tests for chunk activation during work unit execution."""

    @pytest.mark.asyncio
    async def test_run_work_unit_activates_future_chunk(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit activates a FUTURE chunk in the worktree."""
        # Set up FUTURE chunk
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        goal_md = chunk_dir / "GOAL.md"
        goal_md.write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        # Configure mocks
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Chunk should now be IMPLEMENTING
        content = goal_md.read_text()
        assert "status: IMPLEMENTING" in content

    @pytest.mark.asyncio
    async def test_run_work_unit_stores_displaced_chunk(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit stores displaced chunk in work unit."""
        # Create existing IMPLEMENTING chunk
        existing_dir = tmp_path / "docs" / "chunks" / "existing_chunk"
        existing_dir.mkdir(parents=True)
        existing_goal = existing_dir / "GOAL.md"
        existing_goal.write_text(
            """---
status: IMPLEMENTING
ticket: null
---

# Existing Chunk
"""
        )

        # Create target FUTURE chunk
        target_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        target_dir.mkdir(parents=True)
        target_goal = target_dir / "GOAL.md"
        target_goal.write_text(
            """---
status: FUTURE
ticket: null
---

# Target Chunk
"""
        )

        # Configure mocks
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="target_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Work unit should have displaced_chunk recorded
        updated = state_store.get_work_unit("target_chunk")
        assert updated.displaced_chunk == "existing_chunk"

    @pytest.mark.asyncio
    async def test_advance_phase_restores_displaced_chunk(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """_advance_phase restores displaced chunk before merge."""
        # Set up target chunk with ACTIVE status (completed)
        target_dir = tmp_path / "docs" / "chunks" / "target_chunk"
        target_dir.mkdir(parents=True)
        target_goal = target_dir / "GOAL.md"
        target_goal.write_text(
            """---
status: ACTIVE
ticket: null
---

# Target Chunk
"""
        )

        # Set up displaced chunk with FUTURE status
        displaced_dir = tmp_path / "docs" / "chunks" / "displaced_chunk"
        displaced_dir.mkdir(parents=True)
        displaced_goal = displaced_dir / "GOAL.md"
        displaced_goal.write_text(
            """---
status: FUTURE
ticket: null
---

# Displaced Chunk
"""
        )

        # Configure mocks
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="target_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            displaced_chunk="displaced_chunk",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Displaced chunk should be restored to IMPLEMENTING
        content = displaced_goal.read_text()
        assert "status: IMPLEMENTING" in content

    # Chunk: docs/chunks/orch_worktree_cleanup - Worktree cleanup on activation failure
    @pytest.mark.asyncio
    async def test_run_work_unit_cleans_up_worktree_on_activation_failure(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """When activate_chunk_in_worktree raises ValueError, the worktree is cleaned up."""
        # Set up chunk that will fail activation (simulate missing GOAL.md)
        # The worktree gets created successfully, but activation fails

        # Configure mocks - worktree creation succeeds
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="missing_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Patch activate_chunk_in_worktree to raise ValueError
        with patch(
            "orchestrator.scheduler.activate_chunk_in_worktree",
            side_effect=ValueError("Chunk 'missing_chunk' not found"),
        ):
            await scheduler._run_work_unit(work_unit)

        # Worktree should have been cleaned up
        mock_worktree_manager.remove_worktree.assert_called_once_with(
            "missing_chunk", remove_branch=False
        )

        # Work unit should be marked as NEEDS_ATTENTION
        updated = state_store.get_work_unit("missing_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "Chunk activation failed" in updated.attention_reason

    # Chunk: docs/chunks/orch_worktree_cleanup - Worktree cleanup on activation failure
    @pytest.mark.asyncio
    async def test_run_work_unit_logs_cleanup_failure_without_crashing(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """When worktree cleanup fails after activation failure, it logs but doesn't crash."""
        from orchestrator.worktree import WorktreeError

        # Configure mocks - worktree creation succeeds
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        # Make remove_worktree raise an exception
        mock_worktree_manager.remove_worktree.side_effect = WorktreeError(
            "Failed to remove worktree"
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="failing_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Patch activate_chunk_in_worktree to raise ValueError
        with patch(
            "orchestrator.scheduler.activate_chunk_in_worktree",
            side_effect=ValueError("Chunk 'failing_chunk' not found"),
        ):
            # Should not raise - cleanup failure is logged but doesn't crash
            await scheduler._run_work_unit(work_unit)

        # remove_worktree was attempted
        mock_worktree_manager.remove_worktree.assert_called_once()

        # Work unit should still be marked as NEEDS_ATTENTION (original failure)
        updated = state_store.get_work_unit("failing_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "Chunk activation failed" in updated.attention_reason
