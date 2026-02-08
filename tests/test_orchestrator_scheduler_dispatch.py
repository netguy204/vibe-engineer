# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_verify_active - Unit and integration tests for ACTIVE status verification
# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
"""Tests for the orchestrator scheduler dispatch mechanics.

Fixtures used in this file come from conftest.py:
- state_store: Creates a test StateStore instance
- mock_worktree_manager: Creates a mock worktree manager
- mock_agent_runner: Creates a mock agent runner
- orchestrator_config: Creates test OrchestratorConfig
- scheduler: Creates a Scheduler instance for testing
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.scheduler import (
    Scheduler,
    SchedulerError,
    create_scheduler,
)
from orchestrator.activation import (
    verify_chunk_active_status,
    VerificationStatus,
    VerificationResult,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)
from orchestrator.retry import (
    is_retryable_api_error,
)
from orchestrator.models import (
    AgentResult,
    OrchestratorConfig,
    ReviewDecision,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore


class TestSchedulerProperties:
    """Tests for scheduler properties."""

    def test_running_count_initial(self, scheduler):
        """Initial running count is zero."""
        assert scheduler.running_count == 0

    def test_available_slots_initial(self, scheduler):
        """Initial available slots equals max_agents."""
        assert scheduler.available_slots == 2


class TestSchedulerDispatch:
    """Tests for dispatch logic."""

    @pytest.mark.asyncio
    async def test_dispatch_tick_empty_queue(self, scheduler, state_store):
        """No work units dispatched when queue is empty."""
        await scheduler._dispatch_tick()

        assert scheduler.running_count == 0

    @pytest.mark.asyncio
    async def test_dispatch_tick_starts_agent(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """Dispatches agent for READY work unit."""
        # Create a READY work unit
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Run dispatch
        await scheduler._dispatch_tick()

        # Should have started an agent
        assert "test_chunk" in scheduler._running_agents

    @pytest.mark.asyncio
    async def test_dispatch_respects_max_agents(
        self, scheduler, state_store
    ):
        """Does not exceed max_agents limit."""
        # Create 4 READY work units
        now = datetime.now(timezone.utc)
        for i in range(4):
            work_unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.READY,
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(work_unit)

        # Run dispatch
        await scheduler._dispatch_tick()

        # Should only start max_agents (2) agents
        assert len(scheduler._running_agents) <= 2

    @pytest.mark.asyncio
    async def test_dispatch_priority_order(self, scheduler, state_store):
        """Higher priority work units dispatched first."""
        now = datetime.now(timezone.utc)

        # Create low priority first
        low_priority = WorkUnit(
            chunk="low_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            priority=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(low_priority)

        # Create high priority second
        high_priority = WorkUnit(
            chunk="high_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            priority=10,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(high_priority)

        # Run dispatch with max_agents=1
        scheduler.config.max_agents = 1
        await scheduler._dispatch_tick()

        # Should have dispatched high priority first
        assert "high_chunk" in scheduler._running_agents
        assert "low_chunk" not in scheduler._running_agents


class TestPhaseAdvancement:
    """Tests for phase advancement logic."""

    @pytest.mark.asyncio
    async def test_advance_goal_to_plan(self, scheduler, state_store):
        """Advances from GOAL to PLAN phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.GOAL,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.PLAN
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_advance_plan_to_implement(self, scheduler, state_store):
        """Advances from PLAN to IMPLEMENT phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_advance_complete_marks_done(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Advancing from COMPLETE marks work unit DONE."""
        # Set up chunk with ACTIVE status (required for completion)
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
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

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.DONE

        # Chunk: docs/chunks/orch_prune_consolidate - Should call finalize_work_unit
        # The finalize_work_unit method handles commit, remove, merge in one call
        mock_worktree_manager.finalize_work_unit.assert_called_once_with("test")

    # Chunk: docs/chunks/orch_prune_consolidate - Finalization failure marks NEEDS_ATTENTION
    @pytest.mark.asyncio
    async def test_advance_finalization_failure_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """When finalization fails, work unit is marked NEEDS_ATTENTION."""
        from orchestrator.worktree import WorktreeError

        # Set up chunk with ACTIVE status (required for completion)
        chunk_dir = tmp_path / "docs" / "chunks" / "test_finalize_fail"
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
        mock_worktree_manager.finalize_work_unit.side_effect = WorktreeError("Merge conflict")

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_finalize_fail",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test_finalize_fail")
        # Work unit should be marked as NEEDS_ATTENTION
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "Finalization failed" in updated.attention_reason


class TestCreateScheduler:
    """Tests for scheduler factory function."""

    def test_create_scheduler_defaults(self, state_store, tmp_path):
        """Creates scheduler with default config."""
        # Provide explicit base_branch since tmp_path is not a git repo
        scheduler = create_scheduler(state_store, tmp_path, base_branch="main")

        assert scheduler.config.max_agents == 4
        assert scheduler.config.dispatch_interval_seconds == 1.0

    def test_create_scheduler_custom_config(self, state_store, tmp_path):
        """Creates scheduler with custom config."""
        config = OrchestratorConfig(max_agents=4, dispatch_interval_seconds=0.5)

        # Provide explicit base_branch since tmp_path is not a git repo
        scheduler = create_scheduler(state_store, tmp_path, config, base_branch="main")

        assert scheduler.config.max_agents == 4
        assert scheduler.config.dispatch_interval_seconds == 0.5


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop."""

    @pytest.mark.asyncio
    async def test_stop_sets_event(self, scheduler):
        """Stop sets the stop event."""
        stop_task = asyncio.create_task(scheduler.stop(timeout=0.1))

        # Give it a moment
        await asyncio.sleep(0.01)

        assert scheduler._stop_event.is_set()
        await stop_task
