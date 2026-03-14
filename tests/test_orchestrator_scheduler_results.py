# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_verify_active - Unit and integration tests for ACTIVE status verification
# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
"""Tests for orchestrator scheduler agent result handling.

This module contains tests for:
- Mechanical commit behavior
- Agent result handling (suspended, error, completed)
- Verbose success output handling
- Crash recovery
- Worktree retention
"""

import pytest
from datetime import datetime, timezone

from orchestrator.models import (
    AgentResult,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)


# Chunk: docs/chunks/orch_mechanical_commit - Unit tests for mechanical commit in scheduler
class TestMechanicalCommit:
    """Tests for mechanical commit in scheduler."""

    @pytest.mark.asyncio
    async def test_mechanical_commit_delegated_to_finalize_work_unit(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Commit is delegated to finalize_work_unit, not called directly by scheduler.

        Chunk: docs/chunks/finalize_double_commit - The scheduler no longer calls
        commit_changes directly for non-retained worktrees. Instead,
        finalize_work_unit owns the full commit→remove→merge sequence.
        """
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
        mock_worktree_manager.has_uncommitted_changes.return_value = True
        mock_worktree_manager.commit_changes.return_value = True
        mock_worktree_manager.has_changes.return_value = True

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

        # commit_changes should NOT be called directly by the scheduler
        mock_worktree_manager.commit_changes.assert_not_called()
        # finalize_work_unit should be called (it handles commit internally)
        mock_worktree_manager.finalize_work_unit.assert_called_once_with("test_chunk")

    @pytest.mark.asyncio
    async def test_mechanical_commit_not_called_when_no_changes(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Mechanical commit is not called when no uncommitted changes."""
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

        # Should NOT have called commit_changes
        mock_worktree_manager.commit_changes.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalization_error_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Finalization error (including commit errors) marks work unit as NEEDS_ATTENTION.

        Chunk: docs/chunks/finalize_double_commit - Commit errors now surface through
        finalize_work_unit, not through direct scheduler commit_changes calls.
        """
        from orchestrator.worktree import WorktreeError

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
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError("git commit failed")

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

        # Should be marked NEEDS_ATTENTION
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "Finalization failed" in updated.attention_reason

    @pytest.mark.asyncio
    async def test_mechanical_commit_proceeds_after_nothing_to_commit(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Proceeds to merge even when commit returns False (nothing to commit)."""
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
        mock_worktree_manager.has_uncommitted_changes.return_value = True
        mock_worktree_manager.commit_changes.return_value = False  # Nothing to commit
        mock_worktree_manager.has_changes.return_value = False

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

        # Should have proceeded to DONE (merge phase completes)
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.DONE


class TestAgentResultHandling:
    """Tests for agent result handling."""

    @pytest.mark.asyncio
    async def test_handle_suspended_result(self, scheduler, state_store):
        """Suspended result marks unit NEEDS_ATTENTION."""
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
            question={"question": "What color?", "options": []},
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.session_id == "session123"

    @pytest.mark.asyncio
    async def test_handle_error_result(self, scheduler, state_store):
        """Error result marks unit NEEDS_ATTENTION."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=False, error="Something went wrong")

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION

    @pytest.mark.asyncio
    async def test_handle_completed_result(self, scheduler, state_store):
        """Completed result advances phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=True, suspended=False)

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.status == WorkUnitStatus.READY


class TestVerboseSuccessNotMisinterpreted:
    """Tests that verbose success summaries don't trigger NEEDS_ATTENTION.

    These integration tests verify the end-to-end flow: when an agent completes
    successfully (is_error=False) but with verbose output containing phrases like
    "Failed to" or "Error:", the work unit should advance phases, NOT enter
    NEEDS_ATTENTION status.
    """

    @pytest.mark.asyncio
    async def test_verbose_success_advances_phase(self, scheduler, state_store):
        """Agent completing with verbose text advances phase, not NEEDS_ATTENTION.

        This simulates the coderef_format_prompting scenario where an agent
        outputs a detailed success summary that happens to contain phrases that
        look like errors (e.g., "Failed to find optional X", "Error: 0 found").
        """
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_verbose",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult indicating successful completion
        # The actual result text is not stored in AgentResult, but completed=True
        # is what matters when is_error=False from the SDK
        result = AgentResult(
            completed=True,
            suspended=False,
            session_id="session123",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test_verbose")
        # Should advance to next phase, NOT enter NEEDS_ATTENTION
        assert updated.status == WorkUnitStatus.READY
        assert updated.phase == WorkUnitPhase.IMPLEMENT

    @pytest.mark.asyncio
    async def test_sdk_error_flag_triggers_attention(self, scheduler, state_store):
        """SDK is_error=True correctly triggers NEEDS_ATTENTION.

        When the SDK indicates an error via the is_error flag, the work unit
        should enter NEEDS_ATTENTION. This is the authoritative error signal.
        """
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_sdk_error",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult with error (completed=False, error set)
        result = AgentResult(
            completed=False,
            suspended=False,
            error="SDK reported an error condition",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test_sdk_error")
        # Should enter NEEDS_ATTENTION for genuine errors
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION

    @pytest.mark.asyncio
    async def test_question_detection_still_triggers_attention(
        self, scheduler, state_store
    ):
        """Question detection via hook still correctly triggers NEEDS_ATTENTION.

        The question interception mechanism (via AskUserQuestion hook) should
        still correctly suspend agents and enter NEEDS_ATTENTION. This verifies
        that removing text-based error detection doesn't break question handling.
        """
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_question",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult from question interception (suspended=True)
        result = AgentResult(
            completed=False,
            suspended=True,
            session_id="session123",
            question={"question": "Which approach?", "options": [{"label": "A"}]},
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("test_question")
        # Should enter NEEDS_ATTENTION for questions
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        # Session should be preserved for resumption
        assert updated.session_id == "session123"


class TestCrashRecovery:
    """Tests for crash recovery."""

    @pytest.mark.asyncio
    async def test_recover_running_units(self, scheduler, state_store):
        """Recovers RUNNING units to READY on startup."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="orphan",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._recover_from_crash()

        updated = state_store.get_work_unit("orphan")
        assert updated.status == WorkUnitStatus.READY
        assert updated.worktree is None


# Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
class TestRetainWorktree:
    """Tests for retain_worktree flag."""

    @pytest.mark.asyncio
    async def test_retain_worktree_skips_cleanup_in_recovery(self, scheduler, state_store):
        """Crash recovery respects retain_worktree and doesn't remove worktree."""
        now = datetime.now(timezone.utc)
        # A DONE work unit with retain_worktree should keep its worktree
        work_unit = WorkUnit(
            chunk="retained_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            worktree="/some/worktree/path",
            retain_worktree=True,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Recovery should not try to remove worktrees for units with retain_worktree
        await scheduler._recover_from_crash()

        # Work unit should still have retain_worktree set
        updated = state_store.get_work_unit("retained_chunk")
        assert updated.retain_worktree is True
        # Status should be unchanged (still DONE)
        assert updated.status == WorkUnitStatus.DONE

    def test_work_unit_has_retain_worktree_field(self):
        """WorkUnit model has retain_worktree field."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        # Default should be False
        assert unit.retain_worktree is False

        # Can be set to True
        unit.retain_worktree = True
        assert unit.retain_worktree is True

    def test_retain_worktree_in_json_serializable(self):
        """retain_worktree is included in JSON serialization."""
        now = datetime.now(timezone.utc)
        unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            retain_worktree=True,
            created_at=now,
            updated_at=now,
        )
        serialized = unit.model_dump_json_serializable()
        assert "retain_worktree" in serialized
        assert serialized["retain_worktree"] is True
