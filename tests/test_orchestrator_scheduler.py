# Chunk: docs/chunks/orch_scheduling - Scheduler tests
# Chunk: docs/chunks/orch_verify_active - ACTIVE status verification tests
"""Tests for the orchestrator scheduler."""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.scheduler import (
    Scheduler,
    SchedulerError,
    create_scheduler,
    verify_chunk_active_status,
    VerificationStatus,
    VerificationResult,
)
from orchestrator.models import (
    AgentResult,
    OrchestratorConfig,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore


@pytest.fixture
def state_store(tmp_path):
    """Create a state store for testing."""
    db_path = tmp_path / "test.db"
    store = StateStore(db_path)
    store.initialize()
    return store


@pytest.fixture
def mock_worktree_manager():
    """Create a mock worktree manager."""
    manager = MagicMock()
    manager.create_worktree.return_value = Path("/tmp/worktree")
    manager.get_worktree_path.return_value = Path("/tmp/worktree")
    manager.get_log_path.return_value = Path("/tmp/logs")
    manager.worktree_exists.return_value = False
    manager.has_uncommitted_changes.return_value = False
    manager.has_changes.return_value = False
    return manager


@pytest.fixture
def mock_agent_runner():
    """Create a mock agent runner."""
    runner = MagicMock()
    runner.run_phase = AsyncMock(
        return_value=AgentResult(completed=True, suspended=False)
    )
    runner.run_commit = AsyncMock(
        return_value=AgentResult(completed=True, suspended=False)
    )
    return runner


@pytest.fixture
def config():
    """Create test config."""
    return OrchestratorConfig(max_agents=2, dispatch_interval_seconds=0.1)


@pytest.fixture
def scheduler(state_store, mock_worktree_manager, mock_agent_runner, config, tmp_path):
    """Create a scheduler for testing."""
    return Scheduler(
        store=state_store,
        worktree_manager=mock_worktree_manager,
        agent_runner=mock_agent_runner,
        config=config,
        project_dir=tmp_path,
    )


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

        # Should have cleaned up worktree
        mock_worktree_manager.remove_worktree.assert_called_once_with(
            "test", remove_branch=False
        )


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


class TestCreateScheduler:
    """Tests for scheduler factory function."""

    def test_create_scheduler_defaults(self, state_store, tmp_path):
        """Creates scheduler with default config."""
        # Provide explicit base_branch since tmp_path is not a git repo
        scheduler = create_scheduler(state_store, tmp_path, base_branch="main")

        assert scheduler.config.max_agents == 2
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

        assert result.status == VerificationStatus.ACTIVE
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
        assert "frontmatter" in result.error.lower()

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
        assert "status" in result.error.lower()

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
