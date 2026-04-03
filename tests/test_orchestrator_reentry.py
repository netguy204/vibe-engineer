# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_implement_reentry_prompt - Re-entry prompt injection and iteration limit tests
"""Tests for IMPLEMENT re-entry prompt injection and iteration limit enforcement.

Verifies that:
- Implementer receives a contextual prompt on every re-entry to IMPLEMENT phase
- Unaddressed feedback reroute includes context explaining why
- Work unit tracks implement iteration count
- Orchestrator escalates to NEEDS_ATTENTION after max_iterations round-trips
- Re-entry context is injected into the agent prompt
- implement_iterations resets on APPROVE
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.agent import AgentRunner, PHASE_SKILL_FILES
from orchestrator.models import (
    AgentResult,
    ReviewDecision,
    ReviewToolDecision,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.review_routing import (
    ReviewRoutingConfig,
    ReviewRoutingCallbacks,
    _apply_review_decision,
    route_review_decision,
)


# --- Fixtures ---


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


@pytest.fixture
def work_unit(now):
    """Create a basic IMPLEMENT work unit."""
    return WorkUnit(
        chunk="test_chunk",
        phase=WorkUnitPhase.IMPLEMENT,
        status=WorkUnitStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def project_dir(tmp_path):
    """Create a project directory with skill files for testing."""
    # Create .agents/skills directory structure (canonical location)
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    # Create .claude/commands directory for backwards-compat symlinks
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)

    skill_content = """---
description: Test skill
---

## Instructions

This is a test skill for {phase}.
"""
    for phase, skill_name in PHASE_SKILL_FILES.items():
        # Create canonical skill directory and SKILL.md
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            skill_content.format(phase=phase.value)
        )
        # Create backwards-compat symlink in .claude/commands/
        symlink_path = commands_dir / f"{skill_name}.md"
        symlink_path.symlink_to(skill_dir / "SKILL.md")

    return tmp_path


class MockClaudeSDKClient:
    """Mock for ClaudeSDKClient for testing prompt content."""

    last_instance = None

    def __init__(self, options=None):
        self.options = options
        self._query_prompt = None
        MockClaudeSDKClient.last_instance = self

    @classmethod
    def reset(cls):
        cls.last_instance = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def query(self, prompt):
        self._query_prompt = prompt

    async def receive_response(self):
        from claude_agent_sdk.types import ResultMessage

        msg = MagicMock(spec=ResultMessage)
        msg.result = "Success"
        msg.is_error = False
        msg.session_id = None
        yield msg


# --- Tests: Re-entry context injection in agent prompt ---


class TestReentryContextInjection:
    """Tests for re-entry context injection into the implementer prompt."""

    @pytest.mark.asyncio
    async def test_reentry_context_injected_for_implement(self, project_dir, tmp_path):
        """When reentry_context is provided, it's injected into the IMPLEMENT prompt."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
                reentry_context="REVIEW_FEEDBACK.md was not deleted — you must address all feedback items.",
            )

        client = MockClaudeSDKClient.last_instance
        assert client is not None
        prompt = client._query_prompt

        # Verify re-entry context header and content
        assert "## Re-entry Context" in prompt
        assert "re-entering the IMPLEMENT phase" in prompt
        assert "REVIEW_FEEDBACK.md was not deleted" in prompt
        assert "Address the above before doing any other work" in prompt

    @pytest.mark.asyncio
    async def test_no_reentry_context_when_none(self, project_dir, tmp_path):
        """When reentry_context is None, no re-entry section appears."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        assert "Re-entry Context" not in prompt

    @pytest.mark.asyncio
    async def test_reentry_context_not_injected_for_non_implement(self, project_dir, tmp_path):
        """Reentry context injection only happens for IMPLEMENT phase."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.PLAN,
                worktree_path=worktree_path,
                reentry_context="This should not appear for PLAN phase.",
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        assert "Re-entry Context" not in prompt

    @pytest.mark.asyncio
    async def test_reentry_context_appears_before_skill_content(self, project_dir, tmp_path):
        """Re-entry context appears before the skill instructions."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
                reentry_context="Feedback not addressed.",
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        reentry_pos = prompt.find("Re-entry Context")
        skill_pos = prompt.find("Instructions")
        assert reentry_pos < skill_pos, "Re-entry context should appear before skill instructions"

    @pytest.mark.asyncio
    async def test_reentry_context_with_feedback_file(self, project_dir, tmp_path):
        """Both reentry_context and REVIEW_FEEDBACK.md content coexist in prompt."""
        runner = AgentRunner(project_dir)
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        chunk_dir = worktree_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        (chunk_dir / "REVIEW_FEEDBACK.md").write_text("# Feedback\n\nFix the bug.")

        MockClaudeSDKClient.reset()
        with patch("orchestrator.agent.ClaudeSDKClient", MockClaudeSDKClient):
            await runner.run_phase(
                chunk="test_chunk",
                phase=WorkUnitPhase.IMPLEMENT,
                worktree_path=worktree_path,
                reentry_context="Previous implementation did not address review feedback.",
            )

        client = MockClaudeSDKClient.last_instance
        prompt = client._query_prompt

        # Both should be present
        assert "Re-entry Context" in prompt
        assert "Prior Review Feedback" in prompt
        assert "Fix the bug" in prompt
        assert "Previous implementation did not address review feedback" in prompt

        # Re-entry context should be prepended (before feedback content)
        reentry_pos = prompt.find("Re-entry Context")
        feedback_pos = prompt.find("Prior Review Feedback")
        assert reentry_pos < feedback_pos, (
            "Re-entry context should appear before feedback content"
        )


# --- Tests: implement_iterations tracking ---


class TestImplementIterationsModel:
    """Tests for implement_iterations field on WorkUnit."""

    def test_default_implement_iterations_is_zero(self, now):
        """New work units start with implement_iterations=0."""
        wu = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        assert wu.implement_iterations == 0

    def test_implement_iterations_in_json_serializable(self, now):
        """implement_iterations is included in model_dump_json_serializable."""
        wu = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            implement_iterations=3,
            created_at=now,
            updated_at=now,
        )
        data = wu.model_dump_json_serializable()
        assert data["implement_iterations"] == 3

    def test_reentry_context_in_json_serializable(self, now):
        """reentry_context is included in model_dump_json_serializable."""
        wu = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            reentry_context="some context",
            created_at=now,
            updated_at=now,
        )
        data = wu.model_dump_json_serializable()
        assert data["reentry_context"] == "some context"

    def test_reentry_context_default_is_none(self, now):
        """New work units start with reentry_context=None."""
        wu = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        assert wu.reentry_context is None


# --- Tests: Iteration limit enforcement in scheduler ---


class TestIterationLimitEnforcement:
    """Tests for iteration limit enforcement in the scheduler."""

    @pytest.mark.asyncio
    async def test_implement_iterations_incremented_on_dispatch(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """implement_iterations is incremented each time IMPLEMENT is dispatched."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            implement_iterations=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Mock reviewer config
        reviewer_config = {"loop_detection": {"max_iterations": 3}}
        with patch("orchestrator.scheduler.load_reviewer_config", return_value=reviewer_config), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        # Verify counter was incremented
        updated = state_store.get_work_unit("test_chunk")
        assert updated.implement_iterations == 1

    @pytest.mark.asyncio
    async def test_escalates_when_iterations_exceed_limit(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """Work unit escalates to NEEDS_ATTENTION when iterations exceed max."""
        now = datetime.now(timezone.utc)
        # max_iterations=3, so max_iterations+1=4 total runs allowed
        # implement_iterations=4 means we've done 4 runs, trying to start 5th
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            implement_iterations=4,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        reviewer_config = {"loop_detection": {"max_iterations": 3}}
        with patch("orchestrator.scheduler.load_reviewer_config", return_value=reviewer_config), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock), \
             patch("orchestrator.scheduler.broadcast_attention_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "Exceeded maximum implement iterations" in updated.attention_reason
        # Agent should NOT have been called
        mock_agent_runner.run_phase.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_dispatch_at_max_iterations(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """Work unit is allowed to dispatch when at exactly max_iterations (last allowed run)."""
        now = datetime.now(timezone.utc)
        # max_iterations=3, implement_iterations=3 means this is the 4th run (max_iterations+1)
        # which should still be allowed since the check is > max_iterations
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            implement_iterations=3,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        reviewer_config = {"loop_detection": {"max_iterations": 3}}
        with patch("orchestrator.scheduler.load_reviewer_config", return_value=reviewer_config), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        # Agent should have been called (not escalated)
        mock_agent_runner.run_phase.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_implement_phases_not_affected(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """Non-IMPLEMENT phases ignore the iteration counter entirely."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.READY,
            implement_iterations=100,  # High number shouldn't matter for PLAN
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        with patch("orchestrator.scheduler.activate_chunk_in_worktree", return_value=None), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        # Agent should have been called normally
        mock_agent_runner.run_phase.assert_called_once()


# --- Tests: Unaddressed feedback reroute sets reentry_context ---


class TestUnaddressedFeedbackReroute:
    """Tests for reentry_context on unaddressed feedback reroute."""

    @pytest.mark.asyncio
    async def test_reroute_sets_reentry_context(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """When REVIEW_FEEDBACK.md exists at review time, reentry_context is set."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.READY,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Make validate_feedback_addressed return False (file still exists)
        worktree_path = Path("/tmp/worktree")

        with patch("orchestrator.scheduler.validate_feedback_addressed", return_value=False), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        updated = state_store.get_work_unit("test_chunk")
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.status == WorkUnitStatus.READY
        assert updated.reentry_context is not None
        assert "REVIEW_FEEDBACK.md" in updated.reentry_context
        assert "not deleted" in updated.reentry_context

    @pytest.mark.asyncio
    async def test_reentry_context_consumed_on_next_dispatch(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """reentry_context is cleared from work unit after being passed to run_phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            reentry_context="Test context that should be cleared.",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        reviewer_config = {"loop_detection": {"max_iterations": 3}}
        with patch("orchestrator.scheduler.load_reviewer_config", return_value=reviewer_config), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        # Verify run_phase was called with the reentry_context
        call_kwargs = mock_agent_runner.run_phase.call_args
        assert call_kwargs.kwargs.get("reentry_context") == "Test context that should be cleared."

        # Verify reentry_context was cleared from work unit
        updated = state_store.get_work_unit("test_chunk")
        assert updated.reentry_context is None


# --- Tests: APPROVE resets implement_iterations ---


class TestApproveResetsIterations:
    """Tests for implement_iterations reset on APPROVE."""

    @pytest.mark.asyncio
    async def test_approve_resets_implement_iterations(self, now):
        """APPROVE decision resets implement_iterations to 0."""
        from orchestrator.models import ReviewResult

        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            implement_iterations=3,
            review_iterations=2,
            created_at=now,
            updated_at=now,
        )

        review_result = ReviewResult(
            decision=ReviewDecision.APPROVE,
            summary="Looks good",
            iteration=3,
        )

        callbacks = MagicMock(spec=ReviewRoutingCallbacks)
        callbacks.advance_phase = AsyncMock()
        callbacks.update_work_unit = MagicMock()

        config = ReviewRoutingConfig(max_iterations=3)

        await _apply_review_decision(
            work_unit=work_unit,
            worktree_path=Path("/tmp/worktree"),
            review_result=review_result,
            current_iteration=3,
            session_id=None,
            callbacks=callbacks,
            config=config,
        )

        # Verify implement_iterations was reset
        assert work_unit.implement_iterations == 0
        callbacks.advance_phase.assert_called_once()


# --- Tests: Full cycle integration ---


class TestFullCycleIntegration:
    """Integration test simulating multi-cycle implement → review → feedback → implement."""

    @pytest.mark.asyncio
    async def test_feedback_increments_and_reentry_context_not_set_for_review_feedback(self, now):
        """FEEDBACK routing sets phase back to IMPLEMENT but does NOT set reentry_context.
        (Review feedback is conveyed via REVIEW_FEEDBACK.md file, not reentry_context.)"""
        from orchestrator.models import ReviewResult
        from orchestrator.review_parsing import create_review_feedback_file

        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            implement_iterations=2,
            review_iterations=0,
            created_at=now,
            updated_at=now,
        )

        review_result = ReviewResult(
            decision=ReviewDecision.FEEDBACK,
            summary="Needs fixes",
            iteration=1,
        )

        callbacks = MagicMock(spec=ReviewRoutingCallbacks)
        callbacks.advance_phase = AsyncMock()
        callbacks.mark_needs_attention = AsyncMock()
        callbacks.update_work_unit = MagicMock()
        callbacks.broadcast_work_unit_update = AsyncMock()

        config = ReviewRoutingConfig(max_iterations=3)

        with patch("orchestrator.review_routing.create_review_feedback_file"):
            await _apply_review_decision(
                work_unit=work_unit,
                worktree_path=Path("/tmp/worktree"),
                review_result=review_result,
                current_iteration=1,
                session_id=None,
                callbacks=callbacks,
                config=config,
            )

        # Phase should be back to IMPLEMENT
        assert work_unit.phase == WorkUnitPhase.IMPLEMENT
        assert work_unit.status == WorkUnitStatus.READY
        # implement_iterations should NOT be modified by review_routing
        # (it's only incremented by the scheduler on dispatch)
        assert work_unit.implement_iterations == 2
        # reentry_context should NOT be set by review FEEDBACK path
        # (the REVIEW_FEEDBACK.md file itself is the context)
        assert work_unit.reentry_context is None

    @pytest.mark.asyncio
    async def test_iteration_limit_escalates_after_max_plus_one_runs(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """After max_iterations+1 total IMPLEMENT runs, the next dispatch escalates."""
        now = datetime.now(timezone.utc)

        # Simulate: max_iterations=3, so 4 total runs allowed (iterations 0,1,2,3)
        # implement_iterations=4 means 4 runs have completed, trying to start the 5th
        work_unit = WorkUnit(
            chunk="cycle_test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            implement_iterations=4,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        reviewer_config = {"loop_detection": {"max_iterations": 3}}
        with patch("orchestrator.scheduler.load_reviewer_config", return_value=reviewer_config), \
             patch("orchestrator.scheduler.activate_chunk_in_worktree"), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock), \
             patch("orchestrator.scheduler.broadcast_attention_update", new_callable=AsyncMock):
            await scheduler._run_work_unit(work_unit)

        updated = state_store.get_work_unit("cycle_test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "implement iterations" in updated.attention_reason.lower()
        mock_agent_runner.run_phase.assert_not_called()
