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
    activate_chunk_in_worktree,
    restore_displaced_chunk,
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


# Chunk: docs/chunks/orch_attention_reason - Attention reason tracking tests
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


# Chunk: docs/chunks/orch_activate_on_inject - Chunk activation and displacement tests
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


# Chunk: docs/chunks/deferred_worktree_creation - Deferred worktree creation tests
class TestDeferredWorktreeCreation:
    """Tests for deferred worktree creation.

    These tests verify that worktrees are created at dispatch time (when
    _run_work_unit is called), not at inject time. This ensures:
    1. Injected work units don't consume resources until they run
    2. Blocked work sees the current repository state when it starts
    3. Worktrees reflect HEAD at dispatch time, not inject time
    """

    def test_inject_does_not_create_worktree(
        self, state_store, mock_worktree_manager, tmp_path
    ):
        """Inject creates a work unit but does NOT create a worktree.

        This verifies the deferred worktree creation behavior: when work is
        injected via the API, only a WorkUnit record is created. The worktree
        is NOT created until the scheduler dispatches the work.
        """
        # Create work unit directly (simulating inject behavior)
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify work unit exists
        stored = state_store.get_work_unit("test_chunk")
        assert stored is not None
        assert stored.status == WorkUnitStatus.READY

        # Verify worktree does NOT exist (worktree field is None on the work unit)
        assert stored.worktree is None

        # Also verify worktree_manager.create_worktree was NOT called
        mock_worktree_manager.create_worktree.assert_not_called()

    @pytest.mark.asyncio
    async def test_worktree_created_at_dispatch_time(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Worktree is created when _run_work_unit is called (dispatch time).

        This verifies that the scheduler creates the worktree at the beginning
        of _run_work_unit, transitioning the work unit from READY to RUNNING.
        """
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

        # Configure mock
        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        # Create READY work unit
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify worktree_manager.create_worktree NOT called yet
        mock_worktree_manager.create_worktree.assert_not_called()

        # Run the work unit (this is what the scheduler does when dispatching)
        await scheduler._run_work_unit(work_unit)

        # NOW worktree should have been created
        mock_worktree_manager.create_worktree.assert_called_once_with("test_chunk")

        # Work unit should be RUNNING with worktree path set
        updated = state_store.get_work_unit("test_chunk")
        assert updated.worktree == str(tmp_path)

    @pytest.mark.asyncio
    async def test_ready_work_unit_has_no_worktree_until_dispatched(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Work units in READY status waiting for slots do not have worktrees.

        This test verifies that work units can sit in the READY queue without
        consuming worktree resources.
        """
        # Create multiple READY work units
        now = datetime.now(timezone.utc)
        for i in range(5):
            work_unit = WorkUnit(
                chunk=f"chunk_{i}",
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.READY,
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(work_unit)

        # Verify all work units exist and are READY
        for i in range(5):
            unit = state_store.get_work_unit(f"chunk_{i}")
            assert unit is not None
            assert unit.status == WorkUnitStatus.READY
            # No worktree assigned yet
            assert unit.worktree is None

        # No worktrees should have been created
        mock_worktree_manager.create_worktree.assert_not_called()


class TestBlockedWorkDeferredWorktree:
    """Tests for blocked work units and deferred worktree creation.

    When work has dependencies (blocked_by list), it should not get a worktree
    until:
    1. Dependencies complete
    2. The work unit transitions to READY
    3. The scheduler dispatches it (READY → RUNNING)

    This ensures blocked work sees the repository state AFTER its dependencies
    have been merged.
    """

    def test_blocked_work_unit_has_no_worktree(
        self, state_store, mock_worktree_manager
    ):
        """BLOCKED work units do not have worktrees.

        Work blocked on dependencies should not consume worktree resources
        until those dependencies complete.
        """
        now = datetime.now(timezone.utc)

        # Create chunk_a as READY (the dependency)
        chunk_a = WorkUnit(
            chunk="chunk_a",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_a)

        # Create chunk_b as BLOCKED (depends on chunk_a)
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
        stored = state_store.get_work_unit("chunk_b")
        assert stored.status == WorkUnitStatus.BLOCKED
        assert stored.blocked_by == ["chunk_a"]

        # BLOCKED work unit should have no worktree
        assert stored.worktree is None

        # No worktrees created for blocked work
        mock_worktree_manager.create_worktree.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocked_work_gets_worktree_only_when_running(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Blocked work gets worktree only when it starts running.

        This tests the full flow:
        1. Work is BLOCKED (no worktree)
        2. Dependencies complete (still no worktree - work is now READY)
        3. Scheduler dispatches the work (NOW worktree is created)
        """
        # Set up chunk for activation
        chunk_dir = tmp_path / "docs" / "chunks" / "chunk_b"
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

        mock_worktree_manager.create_worktree.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)

        # Create work unit that was previously BLOCKED, now READY
        # (simulating after dependency completion)
        chunk_b = WorkUnit(
            chunk="chunk_b",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            blocked_by=["chunk_a"],  # Still has blocked_by info for traceability
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(chunk_b)

        # Verify no worktree yet (work is READY, not RUNNING)
        stored = state_store.get_work_unit("chunk_b")
        assert stored.worktree is None
        mock_worktree_manager.create_worktree.assert_not_called()

        # Now dispatch the work (scheduler runs it)
        await scheduler._run_work_unit(chunk_b)

        # Worktree should now be created
        mock_worktree_manager.create_worktree.assert_called_once_with("chunk_b")

        # Work unit should have worktree assigned
        updated = state_store.get_work_unit("chunk_b")
        assert updated.worktree == str(tmp_path)

    def test_blocked_to_ready_transition_no_worktree(
        self, state_store, mock_worktree_manager
    ):
        """Transitioning BLOCKED → READY does not create worktree.

        When dependencies complete and work moves to READY, it should still
        NOT have a worktree. The worktree is only created at dispatch time.
        """
        now = datetime.now(timezone.utc)

        # Create BLOCKED work unit
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["dependency_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Verify BLOCKED state
        stored = state_store.get_work_unit("test_chunk")
        assert stored.status == WorkUnitStatus.BLOCKED
        assert stored.worktree is None

        # Simulate dependency completion - transition to READY
        stored.status = WorkUnitStatus.READY
        stored.blocked_by = []  # Clear blocking dependencies
        stored.updated_at = datetime.now(timezone.utc)
        state_store.update_work_unit(stored)

        # Work unit is now READY but still NO worktree
        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.worktree is None

        # worktree_manager.create_worktree should NOT have been called
        mock_worktree_manager.create_worktree.assert_not_called()


# Chunk: docs/chunks/deferred_worktree_creation - Integration tests with real git
class TestDeferredWorktreeCreationIntegration:
    """Integration tests for deferred worktree creation with real git repos.

    These tests verify the full behavior using actual git worktrees, ensuring
    that the worktree reflects the repository state at dispatch time.
    """

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a git repository for testing."""
        import subprocess

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit so HEAD exists
        (tmp_path / "README.md").write_text("# Test\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        return tmp_path

    def test_worktree_reflects_current_head_at_dispatch_time(self, git_repo):
        """Worktree is created from current HEAD at dispatch time.

        This verifies that if commits are made after work is injected but before
        it runs, the worktree sees those commits.
        """
        import subprocess
        from orchestrator.worktree import WorktreeManager

        manager = WorktreeManager(git_repo)

        # Simulate: work is "injected" - at this point HEAD is at initial commit
        # We just note that no worktree exists yet
        assert not manager.worktree_exists("test_chunk")

        # Simulate: other work happens and commits are made
        (git_repo / "new_file.txt").write_text("new content after inject")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new file after inject"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Now simulate: work is dispatched - worktree is created NOW
        worktree_path = manager.create_worktree("test_chunk")

        # The worktree should have the new file (HEAD at dispatch time)
        assert (worktree_path / "new_file.txt").exists()
        assert (worktree_path / "new_file.txt").read_text() == "new content after inject"

        # Clean up
        manager.remove_worktree("test_chunk", remove_branch=True)

    def test_blocked_work_sees_dependency_changes_when_dispatched(self, git_repo):
        """Blocked work sees changes from completed dependencies.

        This is the key scenario: chunk_b depends on chunk_a. When chunk_a
        completes and merges, and chunk_b is later dispatched, chunk_b's
        worktree should contain chunk_a's changes.
        """
        import subprocess
        from orchestrator.worktree import WorktreeManager

        manager = WorktreeManager(git_repo)

        # Simulate chunk_a completing: create its worktree, make changes, merge
        chunk_a_worktree = manager.create_worktree("chunk_a")

        # chunk_a makes changes
        (chunk_a_worktree / "chunk_a_file.txt").write_text("content from chunk_a")
        subprocess.run(
            ["git", "add", "."], cwd=chunk_a_worktree, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "chunk_a implementation"],
            cwd=chunk_a_worktree,
            check=True,
            capture_output=True,
        )

        # chunk_a completes - worktree is removed and branch is merged
        manager.remove_worktree("chunk_a", remove_branch=False)
        manager.merge_to_base("chunk_a", delete_branch=True)

        # Verify chunk_a's changes are now on the base branch
        assert (git_repo / "chunk_a_file.txt").exists()

        # Now chunk_b (which was blocked on chunk_a) is dispatched
        # Its worktree is created NOW, from current HEAD
        chunk_b_worktree = manager.create_worktree("chunk_b")

        # chunk_b's worktree should see chunk_a's file
        assert (chunk_b_worktree / "chunk_a_file.txt").exists()
        assert (
            (chunk_b_worktree / "chunk_a_file.txt").read_text()
            == "content from chunk_a"
        )

        # Clean up
        manager.remove_worktree("chunk_b", remove_branch=True)


# Chunk: docs/chunks/orch_attention_queue - Answer injection tests
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


# Chunk: docs/chunks/orch_conflict_oracle - Conflict integration tests
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
