# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/explicit_deps_skip_oracle - Oracle bypass for explicit dependencies
"""Tests for pending answer injection and conflict checking in orchestrator scheduler."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from orchestrator.models import (
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)


class TestPendingAnswerInjection:
    """Tests for pending_answer injection during work unit execution."""

    @pytest.mark.asyncio
    async def test_run_work_unit_passes_pending_answer(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit passes pending_answer to agent runner."""
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
            session_id="session123",
            pending_answer="Use Redis for caching",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Should have called run_phase with the answer
        mock_agent_runner.run_phase.assert_called_once()
        call_kwargs = mock_agent_runner.run_phase.call_args.kwargs
        assert call_kwargs["answer"] == "Use Redis for caching"
        assert call_kwargs["resume_session_id"] == "session123"

    @pytest.mark.asyncio
    async def test_run_work_unit_clears_pending_answer_after_dispatch(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit clears pending_answer after successful dispatch."""
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
            pending_answer="Some answer",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # pending_answer should be cleared after dispatch
        updated = state_store.get_work_unit("test_chunk")
        assert updated.pending_answer is None

    @pytest.mark.asyncio
    async def test_run_work_unit_no_answer_when_none_pending(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """_run_work_unit passes None for answer when no pending_answer."""
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
            pending_answer=None,  # No pending answer
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._run_work_unit(work_unit)

        # Should have called run_phase with no answer
        mock_agent_runner.run_phase.assert_called_once()
        call_kwargs = mock_agent_runner.run_phase.call_args.kwargs
        assert call_kwargs["answer"] is None

    @pytest.mark.asyncio
    async def test_full_flow_needs_attention_answer_resume(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Full flow: NEEDS_ATTENTION → answer → READY → dispatch with answer."""
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

        # 1. Work unit is in NEEDS_ATTENTION state (simulating agent asked question)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            session_id="session_abc",
            attention_reason="Question: What database should I use?",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # 2. Operator provides answer (simulating POST /work-units/{chunk}/answer)
        stored = state_store.get_work_unit("test_chunk")
        stored.pending_answer = "Use PostgreSQL"
        stored.attention_reason = None
        stored.status = WorkUnitStatus.READY
        stored.updated_at = datetime.now(timezone.utc)
        state_store.update_work_unit(stored)

        # 3. Scheduler dispatches the work unit
        ready_unit = state_store.get_work_unit("test_chunk")
        assert ready_unit.status == WorkUnitStatus.READY
        assert ready_unit.pending_answer == "Use PostgreSQL"

        await scheduler._run_work_unit(ready_unit)

        # 4. Verify agent was resumed with the answer
        mock_agent_runner.run_phase.assert_called_once()
        call_kwargs = mock_agent_runner.run_phase.call_args.kwargs
        assert call_kwargs["answer"] == "Use PostgreSQL"
        assert call_kwargs["resume_session_id"] == "session_abc"

        # 5. Verify pending_answer was cleared
        final = state_store.get_work_unit("test_chunk")
        assert final.pending_answer is None


class TestConflictChecking:
    """Tests for conflict oracle integration in scheduler."""

    @pytest.mark.asyncio
    async def test_check_conflicts_empty_when_no_running(
        self, scheduler, state_store
    ):
        """No conflicts when no other work units are running."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        blocking = await scheduler._check_conflicts(work_unit)
        assert blocking == []

    @pytest.mark.asyncio
    async def test_check_conflicts_not_blocked_when_independent(
        self, scheduler, state_store, tmp_path
    ):
        """Work units with INDEPENDENT verdict are not blocked."""
        now = datetime.now(timezone.utc)

        # Create work unit with pre-cached INDEPENDENT verdict
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "INDEPENDENT"},
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a RUNNING work unit
        running_unit = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(running_unit)

        blocking = await scheduler._check_conflicts(work_unit)
        assert blocking == []

    @pytest.mark.asyncio
    async def test_check_conflicts_blocked_when_serialize(
        self, scheduler, state_store
    ):
        """Work units with SERIALIZE verdict are blocked by running units."""
        now = datetime.now(timezone.utc)

        # Create work unit with pre-cached SERIALIZE verdict
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "SERIALIZE"},
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a RUNNING work unit
        running_unit = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(running_unit)

        blocking = await scheduler._check_conflicts(work_unit)
        assert "chunk_b" in blocking

    @pytest.mark.asyncio
    async def test_check_conflicts_serialize_not_blocked_when_ready(
        self, scheduler, state_store
    ):
        """SERIALIZE verdict doesn't block when other chunk is just READY."""
        now = datetime.now(timezone.utc)

        # Create work unit with pre-cached SERIALIZE verdict
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "SERIALIZE"},
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create another READY work unit (not running)
        other_unit = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(other_unit)

        blocking = await scheduler._check_conflicts(work_unit)
        # Not blocked because chunk_b is not RUNNING
        assert blocking == []

    @pytest.mark.asyncio
    async def test_ask_operator_blocks_running_not_ready(
        self, scheduler, state_store
    ):
        """ASK_OPERATOR only blocks when other is RUNNING, not READY."""
        now = datetime.now(timezone.utc)

        # Test with READY: should NOT block
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "ASK_OPERATOR"},
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        other_ready = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(other_ready)

        blocking = await scheduler._check_conflicts(work_unit)
        assert blocking == []

        # Now test with RUNNING: should block and mark needs attention
        state_store.delete_work_unit("chunk_b")
        work_unit2 = state_store.get_work_unit("chunk_a")
        work_unit2.status = WorkUnitStatus.READY  # Reset status

        other_running = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(other_running)

        blocking = await scheduler._check_conflicts(work_unit2)
        assert "chunk_b" in blocking

        # Should be marked needs attention
        updated = state_store.get_work_unit("chunk_a")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION

    @pytest.mark.asyncio
    async def test_conflict_override_independent_allows_dispatch(
        self, scheduler, state_store
    ):
        """Operator override to INDEPENDENT allows dispatch even with ASK_OPERATOR."""
        now = datetime.now(timezone.utc)

        # Work unit with ASK_OPERATOR but INDEPENDENT override
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "ASK_OPERATOR"},
            conflict_override="INDEPENDENT",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        running_unit = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(running_unit)

        blocking = await scheduler._check_conflicts(work_unit)
        assert blocking == []

    @pytest.mark.asyncio
    async def test_reanalyze_conflicts_clears_cached_verdicts(
        self, scheduler, state_store
    ):
        """_reanalyze_conflicts clears cached verdicts for re-analysis."""
        now = datetime.now(timezone.utc)

        # Create work unit with cached verdicts
        work_unit = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            conflict_verdicts={"chunk_b": "SERIALIZE", "chunk_c": "INDEPENDENT"},
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._reanalyze_conflicts("chunk_a")

        # Cached verdicts should be cleared
        updated = state_store.get_work_unit("chunk_a")
        assert updated.conflict_verdicts == {}


# Chunk: docs/chunks/explicit_deps_skip_oracle - Oracle bypass for explicit dependencies
class TestExplicitDepsOracleBypass:
    """Tests for explicit_deps oracle bypass in scheduler.

    When a work unit has explicit_deps=True, the scheduler should skip oracle
    analysis entirely and only check if blocked_by chunks are RUNNING.
    """

    @pytest.mark.asyncio
    async def test_explicit_deps_skips_oracle(self, scheduler, state_store):
        """Explicit-dep work units do not call oracle.analyze_conflict."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit with a blocked_by entry
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a READY blocker (not RUNNING)
        blocker_unit = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker_unit)

        # Mock the oracle to verify it's not called
        with patch("orchestrator.oracle.create_oracle") as mock_create_oracle:
            blocking = await scheduler._check_conflicts(work_unit)

            # Oracle should NOT be created or called
            mock_create_oracle.assert_not_called()

        # Not blocked because blocker is READY, not RUNNING
        assert blocking == []

    @pytest.mark.asyncio
    async def test_explicit_deps_blocked_when_blocker_running(self, scheduler, state_store):
        """Explicit-dep work units block only when blocked_by chunk is RUNNING."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit blocked by another chunk
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a RUNNING blocker
        blocker_unit = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker_unit)

        blocking = await scheduler._check_conflicts(work_unit)

        # Should be blocked because blocker is RUNNING
        assert "blocker_chunk" in blocking

    @pytest.mark.asyncio
    async def test_explicit_deps_unblocked_when_blocker_done(self, scheduler, state_store):
        """Explicit-dep work units unblock when blocked_by chunk is DONE."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit blocked by a DONE chunk
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["done_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a DONE work unit
        done_unit = WorkUnit(
            chunk="done_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(done_unit)

        blocking = await scheduler._check_conflicts(work_unit)

        # Should NOT be blocked - blocker is DONE
        assert blocking == []

    @pytest.mark.asyncio
    async def test_explicit_deps_unblocked_when_blocker_not_exists(self, scheduler, state_store):
        """Explicit-dep work units unblock when blocked_by chunk doesn't exist."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit blocked by a non-existent chunk
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["nonexistent_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        blocking = await scheduler._check_conflicts(work_unit)

        # Should NOT be blocked - blocker doesn't exist (not RUNNING)
        assert blocking == []

    @pytest.mark.asyncio
    async def test_explicit_deps_multiple_blockers_partial_running(self, scheduler, state_store):
        """Explicit-dep work units block on any RUNNING blocker from blocked_by list."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit blocked by multiple chunks
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["blocker_a", "blocker_b", "blocker_c"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # blocker_a is DONE
        done_unit = WorkUnit(
            chunk="blocker_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(done_unit)

        # blocker_b is RUNNING
        running_unit = WorkUnit(
            chunk="blocker_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(running_unit)

        # blocker_c is READY (not running)
        ready_unit = WorkUnit(
            chunk="blocker_c",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(ready_unit)

        blocking = await scheduler._check_conflicts(work_unit)

        # Should be blocked only by the RUNNING chunk
        assert blocking == ["blocker_b"]

    @pytest.mark.asyncio
    async def test_non_explicit_deps_still_uses_oracle(self, scheduler, state_store, tmp_path):
        """Non-explicit work units continue to use oracle analysis."""
        now = datetime.now(timezone.utc)

        # Create a non-explicit work unit (explicit_deps=False is default)
        work_unit = WorkUnit(
            chunk="normal_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=False,  # Default, but explicit for clarity
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create another RUNNING work unit
        running_unit = WorkUnit(
            chunk="other_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(running_unit)

        # Mock the oracle
        mock_analysis = MagicMock()
        mock_analysis.verdict.value = "INDEPENDENT"

        with patch("orchestrator.oracle.create_oracle") as mock_create_oracle:
            mock_oracle = MagicMock()
            mock_oracle.analyze_conflict.return_value = mock_analysis
            mock_create_oracle.return_value = mock_oracle

            blocking = await scheduler._check_conflicts(work_unit)

            # Oracle SHOULD be created and called for non-explicit work units
            mock_create_oracle.assert_called_once()
            mock_oracle.analyze_conflict.assert_called_once_with("normal_chunk", "other_chunk")

        # Independent verdict means no blocking
        assert blocking == []

    @pytest.mark.asyncio
    async def test_explicit_deps_ignores_other_active_chunks(self, scheduler, state_store):
        """Explicit-dep work units ignore chunks not in blocked_by even if RUNNING."""
        now = datetime.now(timezone.utc)

        # Create an explicit-dep work unit with specific blocked_by
        work_unit = WorkUnit(
            chunk="explicit_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            explicit_deps=True,
            blocked_by=["specific_blocker"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a RUNNING chunk that's NOT in blocked_by
        other_running = WorkUnit(
            chunk="unrelated_running_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(other_running)

        # The specific_blocker is READY (not running)
        specific_blocker = WorkUnit(
            chunk="specific_blocker",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(specific_blocker)

        blocking = await scheduler._check_conflicts(work_unit)

        # Should NOT be blocked - unrelated_running_chunk isn't in blocked_by,
        # and specific_blocker is READY not RUNNING
        assert blocking == []
