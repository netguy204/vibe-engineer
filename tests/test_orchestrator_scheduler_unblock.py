# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_blocked_lifecycle - Unit tests for automatic unblocking when blockers complete
"""Tests for orchestrator scheduler unblock and question forwarding functionality."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from orchestrator.models import (
    AgentResult,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)


# Fixtures come from conftest.py:
# - state_store
# - mock_worktree_manager
# - mock_agent_runner
# - orchestrator_config
# - scheduler


class TestQuestionForwardingFlow:
    """Tests for the complete question forwarding flow.

    When an agent calls AskUserQuestion, the orchestrator:
    1. Intercepts the call via PreToolUse hook
    2. Captures the question data
    3. Suspends the agent session
    4. Transitions work unit to NEEDS_ATTENTION
    5. Stores question in attention_reason
    """

    @pytest.mark.asyncio
    async def test_run_work_unit_passes_question_callback(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit passes question_callback to run_phase."""
        # Set up chunk for activation
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

        # Verify run_phase was called with question_callback
        mock_agent_runner.run_phase.assert_called_once()
        call_kwargs = mock_agent_runner.run_phase.call_args.kwargs
        assert "question_callback" in call_kwargs
        assert call_kwargs["question_callback"] is not None

    @pytest.mark.asyncio
    async def test_question_forwarding_transitions_to_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Agent asking question transitions work unit to NEEDS_ATTENTION with question data."""
        # Set up chunk for activation
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

        # Configure agent runner to return suspended result with question
        mock_agent_runner.run_phase = AsyncMock(
            return_value=AgentResult(
                completed=False,
                suspended=True,
                session_id="suspended-session-123",
                question={
                    "question": "Which framework should I use?",
                    "options": [
                        {"label": "React", "description": "Frontend library"},
                        {"label": "Vue", "description": "Progressive framework"},
                    ],
                    "header": "Framework",
                    "multiSelect": False,
                },
            )
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Verify work unit transitioned to NEEDS_ATTENTION
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.session_id == "suspended-session-123"
        assert "Which framework should I use?" in updated.attention_reason

    @pytest.mark.asyncio
    async def test_question_answer_resume_flow(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Complete flow: question → NEEDS_ATTENTION → answer → resume → complete."""
        # Set up chunk for activation
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

        # Phase 1: Agent asks a question
        mock_agent_runner.run_phase = AsyncMock(
            return_value=AgentResult(
                completed=False,
                suspended=True,
                session_id="question-session",
                question={"question": "Which database?", "options": []},
            )
        )

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Verify NEEDS_ATTENTION state
        needing_attention = state_store.get_work_unit("test_chunk")
        assert needing_attention.status == WorkUnitStatus.NEEDS_ATTENTION
        assert needing_attention.session_id == "question-session"
        assert "Which database?" in needing_attention.attention_reason

        # Phase 2: Operator provides answer (simulating POST /work-units/{chunk}/answer)
        needing_attention.pending_answer = "Use PostgreSQL"
        needing_attention.attention_reason = None
        needing_attention.status = WorkUnitStatus.READY
        needing_attention.updated_at = datetime.now(timezone.utc)
        state_store.update_work_unit(needing_attention)

        # Phase 3: Agent resumes and completes
        mock_agent_runner.run_phase = AsyncMock(
            return_value=AgentResult(
                completed=True,
                suspended=False,
                session_id="question-session",
            )
        )

        ready_unit = state_store.get_work_unit("test_chunk")
        await scheduler._run_work_unit(ready_unit)

        # Verify run_phase was called with the answer
        call_kwargs = mock_agent_runner.run_phase.call_args.kwargs
        assert call_kwargs["answer"] == "Use PostgreSQL"
        assert call_kwargs["resume_session_id"] == "question-session"

        # Verify pending_answer was cleared
        completed = state_store.get_work_unit("test_chunk")
        assert completed.pending_answer is None


# Chunk: docs/chunks/orch_blocked_lifecycle - Unit tests for automatic unblocking when blockers complete
class TestAutomaticUnblock:
    """Tests for automatic unblocking when blockers complete."""

    @pytest.mark.asyncio
    async def test_advance_phase_done_unblocks_dependents(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Completing a work unit unblocks work units that were blocked by it."""
        # Set up chunk_a with ACTIVE status (will complete)
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        # Set up chunk_b with FUTURE status (just for existence in worktree)
        chunk_b_dir = tmp_path / "docs" / "chunks" / "chunk_b"
        chunk_b_dir.mkdir(parents=True)
        (chunk_b_dir / "GOAL.md").write_text(
            """---
status: FUTURE
---

# Chunk B
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase (about to transition to DONE)
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b in BLOCKED status, blocked by chunk_a
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify chunk_b is BLOCKED
        assert state_store.get_work_unit("chunk_b").status == WorkUnitStatus.BLOCKED
        assert "chunk_a" in state_store.get_work_unit("chunk_b").blocked_by

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify chunk_a is DONE
        updated_a = state_store.get_work_unit("chunk_a")
        assert updated_a.status == WorkUnitStatus.DONE

        # Verify chunk_b is now READY and chunk_a removed from blocked_by
        updated_b = state_store.get_work_unit("chunk_b")
        assert updated_b.status == WorkUnitStatus.READY
        assert "chunk_a" not in updated_b.blocked_by

    @pytest.mark.asyncio
    async def test_advance_phase_done_unblocks_multiple_dependents(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Completing a work unit unblocks multiple work units blocked by it."""
        # Set up chunk_a with ACTIVE status
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b and chunk_c both blocked by chunk_a
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        chunk_c = WorkUnit(
            chunk="chunk_c",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_c)

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify both chunk_b and chunk_c are now READY
        updated_b = state_store.get_work_unit("chunk_b")
        updated_c = state_store.get_work_unit("chunk_c")
        assert updated_b.status == WorkUnitStatus.READY
        assert updated_c.status == WorkUnitStatus.READY
        assert "chunk_a" not in updated_b.blocked_by
        assert "chunk_a" not in updated_c.blocked_by

    @pytest.mark.asyncio
    async def test_advance_phase_done_partial_unblock_with_multiple_blockers(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Work unit with multiple blockers stays BLOCKED until all complete."""
        # Set up chunk_a with ACTIVE status
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_d which is also blocking chunk_b
        chunk_d = WorkUnit(
            chunk="chunk_d",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_d)

        # Create chunk_b blocked by BOTH chunk_a and chunk_d
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["chunk_a", "chunk_d"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify chunk_b is STILL BLOCKED (still blocked by chunk_d)
        updated_b = state_store.get_work_unit("chunk_b")
        assert updated_b.status == WorkUnitStatus.BLOCKED
        assert "chunk_a" not in updated_b.blocked_by
        assert "chunk_d" in updated_b.blocked_by


# Chunk: docs/chunks/orch_unblock_transition - Tests for NEEDS_ATTENTION to READY transition on unblock
class TestNeedsAttentionUnblock:
    """Tests for NEEDS_ATTENTION to READY transition when blockers complete.

    When a work unit is in NEEDS_ATTENTION status (e.g., due to a conflict with
    a running chunk that needed serialization), and its blocker completes, the
    work unit should transition to READY status automatically.

    This addresses the bug where work units remained stuck in NEEDS_ATTENTION
    after their blockers completed because _unblock_dependents only checked for
    BLOCKED status, not NEEDS_ATTENTION status.
    """

    @pytest.mark.asyncio
    async def test_unblock_needs_attention_to_ready(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Work unit in NEEDS_ATTENTION transitions to READY when blocker completes."""
        # Set up chunk_a with ACTIVE status (will complete)
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase (about to transition to DONE)
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b in NEEDS_ATTENTION status, blocked by chunk_a
        # This simulates a scenario where chunk_b encountered a conflict and
        # was marked NEEDS_ATTENTION with chunk_a in its blocked_by list
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            blocked_by=["chunk_a"],
            attention_reason="Conflict with running chunk_a. Use 've orch resolve' to proceed.",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify chunk_b is NEEDS_ATTENTION
        assert state_store.get_work_unit("chunk_b").status == WorkUnitStatus.NEEDS_ATTENTION
        assert "chunk_a" in state_store.get_work_unit("chunk_b").blocked_by

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify chunk_a is DONE
        updated_a = state_store.get_work_unit("chunk_a")
        assert updated_a.status == WorkUnitStatus.DONE

        # Verify chunk_b is now READY (not still stuck in NEEDS_ATTENTION)
        updated_b = state_store.get_work_unit("chunk_b")
        assert updated_b.status == WorkUnitStatus.READY
        assert "chunk_a" not in updated_b.blocked_by

    @pytest.mark.asyncio
    async def test_unblock_clears_attention_reason(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Transitioning from NEEDS_ATTENTION to READY clears attention_reason."""
        # Set up chunk_a with ACTIVE status
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b in NEEDS_ATTENTION with stale attention_reason
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            blocked_by=["chunk_a"],
            attention_reason="Stale reason that should be cleared",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify chunk_b has attention_reason
        assert state_store.get_work_unit("chunk_b").attention_reason is not None

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify chunk_b's attention_reason is cleared
        updated_b = state_store.get_work_unit("chunk_b")
        assert updated_b.status == WorkUnitStatus.READY
        assert updated_b.attention_reason is None

    @pytest.mark.asyncio
    async def test_unblock_multiple_needs_attention_work_units(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Multiple NEEDS_ATTENTION work units transition when blocker completes."""
        # Set up chunk_a with ACTIVE status
        chunk_a_dir = tmp_path / "docs" / "chunks" / "chunk_a"
        chunk_a_dir.mkdir(parents=True)
        (chunk_a_dir / "GOAL.md").write_text(
            """---
status: ACTIVE
---

# Chunk A
"""
        )

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.has_uncommitted_changes.return_value = False
        mock_worktree_manager.has_changes.return_value = False

        now = datetime.now(timezone.utc)

        # Create chunk_a in COMPLETE phase
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create multiple work units in NEEDS_ATTENTION status blocked by chunk_a
        for name, reason in [
            ("chunk_b", "Conflict with chunk_a"),
            ("chunk_c", "Another conflict with chunk_a"),
            ("chunk_d", "Third conflict with chunk_a"),
        ]:
            work_unit = WorkUnit(
                chunk=name,
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.NEEDS_ATTENTION,
                blocked_by=["chunk_a"],
                attention_reason=reason,
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(work_unit)

        # Advance chunk_a to DONE
        await scheduler._advance_phase(chunk_a)

        # Verify all work units are now READY with cleared attention_reason
        for name in ["chunk_b", "chunk_c", "chunk_d"]:
            updated = state_store.get_work_unit(name)
            assert updated.status == WorkUnitStatus.READY, f"{name} should be READY"
            assert updated.attention_reason is None, f"{name} should have cleared reason"
            assert "chunk_a" not in updated.blocked_by, f"{name} should not be blocked"


# Chunk: docs/chunks/orch_unblock_transition - Tests for attention_reason and blocked_by cleanup on status transitions
class TestAttentionReasonCleanup:
    """Tests for attention_reason and blocked_by cleanup on status transitions.

    The attention_reason field should be cleared when work units transition to
    READY or RUNNING states, regardless of how that transition occurs (phase
    advancement, manual status change, unblock, etc.).

    The blocked_by field should be cleared when work units transition to RUNNING.
    """

    @pytest.mark.asyncio
    async def test_advance_phase_clears_attention_reason(self, scheduler, state_store):
        """Phase advancement to READY clears any stale attention_reason."""
        now = datetime.now(timezone.utc)

        # Create a work unit that was previously in NEEDS_ATTENTION but is
        # now advancing phases (simulating manual resolution followed by retry)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            attention_reason="This should be cleared",  # Stale from previous state
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Advance phase (PLAN -> IMPLEMENT)
        await scheduler._advance_phase(work_unit)

        # Verify attention_reason is cleared
        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.READY
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.attention_reason is None

    @pytest.mark.asyncio
    async def test_run_work_unit_clears_attention_reason(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Transitioning to RUNNING clears any stale attention_reason."""
        # Set up chunk for activation
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)

        # Create work unit with stale attention_reason (from previous NEEDS_ATTENTION)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            attention_reason="Stale reason from previous state",  # Should be cleared
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Verify attention_reason is cleared when RUNNING
        # Note: the work unit may have already completed, check intermediate state
        # by checking the mock wasn't called with attention_reason
        updated = state_store.get_work_unit("test_chunk")
        assert updated.attention_reason is None

    @pytest.mark.asyncio
    async def test_run_work_unit_clears_blocked_by(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Transitioning to RUNNING clears any stale blocked_by entries."""
        # Set up chunk for activation
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "GOAL.md").write_text(
            """---
status: FUTURE
ticket: null
---

# Chunk Goal
"""
        )

        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)

        # Create work unit with stale blocked_by (from previous blocking state)
        # This can happen when blockers complete but blocked_by wasn't cleared
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            blocked_by=["stale_blocker_1", "stale_blocker_2"],  # Should be cleared
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Verify blocked_by is cleared when RUNNING
        updated = state_store.get_work_unit("test_chunk")
        assert updated.blocked_by == []
