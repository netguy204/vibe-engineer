# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_merge_rebase_retry - Merge conflict retry during finalization
"""Tests for orchestrator scheduler merge conflict retry handling.

This module contains tests for:
- Merge conflict detection during finalization
- Automatic retry via REBASE phase
- Retry limit enforcement (escalate to NEEDS_ATTENTION after 2 retries)
- Non-merge-conflict errors still escalate immediately
- is_merge_conflict_error helper function
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.models import (
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.merge import is_merge_conflict_error
from orchestrator.worktree import WorktreeError


class TestIsMergeConflictError:
    """Tests for the is_merge_conflict_error helper function."""

    def test_detects_merge_conflict_in_error_message(self):
        """Detects 'Merge conflict' in error message string."""
        error = WorktreeError("Merge conflict between orch/test and main")
        assert is_merge_conflict_error(error) is True

    def test_detects_conflict_keyword_in_error_message(self):
        """Detects 'CONFLICT' in error message string."""
        error = WorktreeError("CONFLICT (content): Merge conflict in file.py")
        assert is_merge_conflict_error(error) is True

    def test_accepts_string_input(self):
        """Accepts plain string input (not just WorktreeError)."""
        assert is_merge_conflict_error("Merge conflict detected") is True
        assert is_merge_conflict_error("CONFLICT in file.txt") is True

    def test_returns_false_for_non_conflict_errors(self):
        """Returns False for errors that are not merge conflicts."""
        error = WorktreeError("Failed to remove worktree: permission denied")
        assert is_merge_conflict_error(error) is False

        assert is_merge_conflict_error("Branch not found") is False
        assert is_merge_conflict_error("Git command failed") is False


class TestMergeConflictRetryFlow:
    """Tests for the merge conflict retry flow in scheduler."""

    @pytest.mark.asyncio
    async def test_merge_conflict_triggers_rebase_retry(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Merge conflict during finalization triggers REBASE retry."""
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
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.recreate_worktree_from_branch.return_value = tmp_path

        # Make finalize_work_unit raise a merge conflict error
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError(
            "Merge conflict between orch/test_chunk and main"
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            merge_conflict_retries=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Verify work unit transitioned to REBASE phase
        updated = state_store.get_work_unit("test_chunk")
        assert updated.phase == WorkUnitPhase.REBASE
        assert updated.status == WorkUnitStatus.READY
        assert updated.merge_conflict_retries == 1

        # Verify worktree recreation was called
        mock_worktree_manager.recreate_worktree_from_branch.assert_called_once_with(
            "test_chunk"
        )

    @pytest.mark.asyncio
    async def test_successful_retry_completes_normally(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """After a retry, successful finalization transitions to DONE."""
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
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        # Successful finalization this time
        mock_worktree_manager.finalize_work_unit.return_value = None

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            merge_conflict_retries=1,  # Already had one retry
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Verify work unit transitioned to DONE
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.DONE
        # Verify merge_conflict_retries was reset
        assert updated.merge_conflict_retries == 0

    @pytest.mark.asyncio
    async def test_third_conflict_escalates_to_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Third merge conflict escalates to NEEDS_ATTENTION."""
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
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = True

        # Make finalize_work_unit raise a merge conflict error
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError(
            "Merge conflict between orch/test_chunk and main"
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            merge_conflict_retries=2,  # Already had 2 retries (max)
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Verify work unit transitioned to NEEDS_ATTENTION
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "retries" in updated.attention_reason.lower()
        assert "merge conflict" in updated.attention_reason.lower()

        # Verify worktree recreation was NOT called (no retry attempted)
        mock_worktree_manager.recreate_worktree_from_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_conflict_error_escalates_immediately(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Non-merge-conflict errors escalate to NEEDS_ATTENTION immediately."""
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
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = True

        # Make finalize_work_unit raise a non-conflict error
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError(
            "Failed to remove worktree: permission denied"
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            merge_conflict_retries=0,  # Fresh work unit
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Verify work unit transitioned to NEEDS_ATTENTION
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "permission denied" in updated.attention_reason.lower()

        # Verify merge_conflict_retries was NOT incremented
        assert updated.merge_conflict_retries == 0

        # Verify worktree recreation was NOT called
        mock_worktree_manager.recreate_worktree_from_branch.assert_not_called()

    @pytest.mark.asyncio
    async def test_worktree_recreation_failure_escalates(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """If worktree recreation fails, escalate to NEEDS_ATTENTION."""
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
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = True

        # Make finalize_work_unit raise a merge conflict
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError(
            "Merge conflict between orch/test_chunk and main"
        )
        # Make worktree recreation fail
        mock_worktree_manager.recreate_worktree_from_branch.side_effect = WorktreeError(
            "Branch orch/test_chunk does not exist"
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            merge_conflict_retries=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        # Verify work unit transitioned to NEEDS_ATTENTION
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "recreate worktree" in updated.attention_reason.lower()


class TestMergeConflictRetriesField:
    """Tests for merge_conflict_retries field persistence."""

    def test_merge_conflict_retries_defaults_to_zero(self, state_store):
        """merge_conflict_retries defaults to 0 for new work units."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        retrieved = state_store.get_work_unit("test_chunk")
        assert retrieved.merge_conflict_retries == 0

    def test_merge_conflict_retries_persists_on_update(self, state_store):
        """merge_conflict_retries value persists through update."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            merge_conflict_retries=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Update the value
        work_unit.merge_conflict_retries = 2
        state_store.update_work_unit(work_unit)

        retrieved = state_store.get_work_unit("test_chunk")
        assert retrieved.merge_conflict_retries == 2

    def test_merge_conflict_retries_in_json_serializable(self):
        """merge_conflict_retries appears in model_dump_json_serializable."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            merge_conflict_retries=1,
            created_at=now,
            updated_at=now,
        )

        json_dict = work_unit.model_dump_json_serializable()
        assert "merge_conflict_retries" in json_dict
        assert json_dict["merge_conflict_retries"] == 1
