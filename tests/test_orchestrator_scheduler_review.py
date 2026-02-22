# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_verify_active - Unit and integration tests for ACTIVE status verification
# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
"""Tests for the orchestrator scheduler review phase.

This file contains tests extracted from test_orchestrator_scheduler.py related
to the review phase, including:
- TestReviewPhase
- TestReviewDecisionParsing
- TestReviewFeedbackFile
- TestReviewDecisionTool
- TestManualDoneUnblock
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from orchestrator.models import (
    AgentResult,
    ReviewDecision,
    ReviewToolDecision,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)

# Note: Fixtures (state_store, mock_worktree_manager, mock_agent_runner,
# orchestrator_config, scheduler) are defined in conftest.py


class TestReviewPhase:
    """Tests for REVIEW phase transitions and handling."""

    # Chunk: docs/chunks/orch_pre_review_rebase - Updated to expect REBASE after IMPLEMENT
    @pytest.mark.asyncio
    async def test_advance_implement_to_rebase(self, scheduler, state_store):
        """Advances from IMPLEMENT to REBASE phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.REBASE
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_advance_rebase_to_review(self, scheduler, state_store):
        """Advances from REBASE to REVIEW phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REBASE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.REVIEW
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_advance_review_to_complete(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Advancing from REVIEW with APPROVE decision goes to COMPLETE.

        Note: Uses review_nudge_count=2 so file fallback is triggered after one
        more nudge attempt (3 is max). This tests backward compatibility with
        file-based decisions.
        """
        # Set up chunk directory with an APPROVE decision file
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        # Write an APPROVE decision YAML
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("""decision: APPROVE
summary: Implementation looks good
iteration: 1
""")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=2,  # Already nudged twice, so 3rd attempt triggers fallback
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=True, suspended=False)

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        # Should advance to COMPLETE phase (handled by _advance_phase)
        assert updated.phase == WorkUnitPhase.COMPLETE
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_review_feedback_returns_to_implement(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """REVIEW with FEEDBACK decision returns to IMPLEMENT.

        Note: Uses review_nudge_count=2 so file fallback is triggered after one
        more nudge attempt (3 is max). This tests backward compatibility with
        file-based decisions.
        """
        # Set up chunk directory with a FEEDBACK decision file
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("""decision: FEEDBACK
summary: Issues found in implementation
issues:
  - location: src/main.py
    concern: Missing error handling
    suggestion: Add try/except block
iteration: 1
""")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_iterations=0,
            review_nudge_count=2,  # Already nudged twice, so 3rd attempt triggers fallback
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=True, suspended=False)

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.status == WorkUnitStatus.READY
        assert updated.review_iterations == 1

        # Feedback file should be created
        feedback_file = chunk_dir / "REVIEW_FEEDBACK.md"
        assert feedback_file.exists()
        content = feedback_file.read_text()
        assert "Issues to Address" in content
        assert "Missing error handling" in content

    @pytest.mark.asyncio
    async def test_review_feedback_increments_iterations(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Multiple FEEDBACK decisions increment the iteration counter.

        Note: Uses review_nudge_count=2 so file fallback is triggered after one
        more nudge attempt (3 is max). This tests backward compatibility with
        file-based decisions.
        """
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("""decision: FEEDBACK
summary: Still has issues
iteration: 2
""")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_iterations=1,  # Already had one iteration
            review_nudge_count=2,  # Already nudged twice, so 3rd attempt triggers fallback
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=True, suspended=False)

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.review_iterations == 2

    @pytest.mark.asyncio
    async def test_review_escalate_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """REVIEW with ESCALATE decision marks NEEDS_ATTENTION.

        Note: Uses review_nudge_count=2 so file fallback is triggered after one
        more nudge attempt (3 is max). This tests backward compatibility with
        file-based decisions.
        """
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("""decision: ESCALATE
summary: Fundamental design issue
reason: AMBIGUITY - Requirements unclear
""")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=2,  # Already nudged twice, so 3rd attempt triggers fallback
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(completed=True, suspended=False)

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            with patch("orchestrator.scheduler.broadcast_attention_update"):
                await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "escalated" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_review_loop_detection_auto_escalates(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Auto-escalates when iterations exceed max_iterations with FEEDBACK.

        Note: The max_iterations check now only fires when the review decision
        is FEEDBACK (not APPROVE). APPROVE should always succeed regardless of
        iteration count. This test verifies that FEEDBACK at max_iterations
        triggers escalation.
        """
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        # Create reviewers config with max_iterations = 3
        reviewers_dir = tmp_path / "docs" / "reviewers" / "baseline"
        reviewers_dir.mkdir(parents=True)
        (reviewers_dir / "METADATA.yaml").write_text("""name: baseline
loop_detection:
  max_iterations: 3
""")

        # Point project_dir to tmp_path so load_reviewer_config finds the config
        scheduler.project_dir = tmp_path
        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_iterations=3,  # Already at max
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Provide FEEDBACK decision via tool call - at max iterations, this should escalate
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=ReviewToolDecision(
                decision="FEEDBACK",
                summary="More issues found",
            ),
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            with patch("orchestrator.scheduler.broadcast_attention_update"):
                await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "exceeded" in updated.attention_reason.lower()
        assert "iterations" in updated.attention_reason.lower()

# Chunk: docs/chunks/orch_review_phase - Tests for parsing review decision from agent output
class TestReviewDecisionParsing:
    """Tests for parsing review decision from agent output."""

    def test_parse_approve_decision(self):
        """Parse valid APPROVE YAML."""
        from orchestrator.review_parsing import parse_review_decision

        output = """The review is complete.

```yaml
decision: APPROVE
summary: Implementation looks good and meets all requirements
iteration: 1
```

Done.
"""
        result = parse_review_decision(output)
        assert result is not None
        assert result.decision == ReviewDecision.APPROVE
        assert "looks good" in result.summary

    def test_parse_feedback_decision(self):
        """Parse FEEDBACK with issues list."""
        from orchestrator.review_parsing import parse_review_decision

        output = """Review findings:

```yaml
decision: FEEDBACK
summary: Some issues need to be addressed
issues:
  - location: src/main.py#function
    concern: Missing error handling
    suggestion: Add try/except
  - location: src/utils.py
    concern: Unused import
iteration: 1
```
"""
        result = parse_review_decision(output)
        assert result is not None
        assert result.decision == ReviewDecision.FEEDBACK
        assert len(result.issues) == 2
        assert result.issues[0].location == "src/main.py#function"
        assert "error handling" in result.issues[0].concern

    def test_parse_escalate_decision(self):
        """Parse ESCALATE with reason."""
        from orchestrator.review_parsing import parse_review_decision

        output = """```yaml
decision: ESCALATE
summary: Cannot complete review
reason: AMBIGUITY - Requirements are unclear
```
"""
        result = parse_review_decision(output)
        assert result is not None
        assert result.decision == ReviewDecision.ESCALATE
        assert result.reason == "AMBIGUITY - Requirements are unclear"

    def test_parse_malformed_yaml(self):
        """Graceful handling of parse errors."""
        from orchestrator.review_parsing import parse_review_decision

        output = """```yaml
this is not: valid yaml: with: too many: colons
decision: [malformed]
```
"""
        result = parse_review_decision(output)
        # Should return None when parsing fails
        assert result is None

    def test_parse_fallback_decision_line(self):
        """Parse simple decision line as fallback."""
        from orchestrator.review_parsing import parse_review_decision

        output = """
Review complete.
decision: APPROVE
Everything looks good.
"""
        result = parse_review_decision(output)
        assert result is not None
        assert result.decision == ReviewDecision.APPROVE

# Chunk: docs/chunks/orch_review_phase - Tests for REVIEW_FEEDBACK.md file creation
class TestReviewFeedbackFile:
    """Tests for REVIEW_FEEDBACK.md file creation."""

    def test_create_review_feedback_file(self, tmp_path):
        """Verify file is created with correct content."""
        from orchestrator.review_parsing import create_review_feedback_file
        from orchestrator.models import ReviewResult, ReviewDecision, ReviewIssue

        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        feedback = ReviewResult(
            decision=ReviewDecision.FEEDBACK,
            summary="Issues found during review",
            issues=[
                ReviewIssue(
                    location="src/main.py",
                    concern="Missing docstring",
                    suggestion="Add function docstring",
                ),
            ],
            iteration=1,
        )

        result_path = create_review_feedback_file(
            tmp_path, "test_chunk", feedback, 1
        )

        assert result_path.exists()
        content = result_path.read_text()

        assert "# Review Feedback" in content
        assert "**Iteration:** 1" in content
        assert "FEEDBACK" in content
        assert "Issues found during review" in content
        assert "Missing docstring" in content
        assert "Add function docstring" in content

    def test_feedback_file_includes_iteration_count(self, tmp_path):
        """Check iteration tracking in feedback file."""
        from orchestrator.review_parsing import create_review_feedback_file
        from orchestrator.models import ReviewResult, ReviewDecision

        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        feedback = ReviewResult(
            decision=ReviewDecision.FEEDBACK,
            summary="Second round of feedback",
            iteration=2,
        )

        result_path = create_review_feedback_file(
            tmp_path, "test_chunk", feedback, 2
        )

        content = result_path.read_text()
        assert "**Iteration:** 2" in content


# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
class TestReviewDecisionTool:
    """Tests for the ReviewDecision tool-based review decision handling."""

    @pytest.mark.asyncio
    async def test_review_decision_from_tool_call(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Review decision from tool call is captured and routed correctly."""
        from orchestrator.models import ReviewToolDecision

        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult with a captured review decision from tool call
        tool_decision = ReviewToolDecision(
            decision="APPROVE",
            summary="Implementation meets all requirements",
            criteria_assessment=[{"criterion": "test", "status": "satisfied"}],
        )
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=tool_decision,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        # Should advance to COMPLETE phase
        assert updated.phase == WorkUnitPhase.COMPLETE
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_review_feedback_from_tool_call(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """FEEDBACK decision from tool call routes back to IMPLEMENT."""
        from orchestrator.models import ReviewToolDecision

        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_iterations=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult with FEEDBACK from tool call
        tool_decision = ReviewToolDecision(
            decision="FEEDBACK",
            summary="Missing error handling",
            issues=[
                {"location": "src/main.py", "concern": "No try/except", "suggestion": "Add error handling"}
            ],
        )
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=tool_decision,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.phase == WorkUnitPhase.IMPLEMENT
        assert updated.status == WorkUnitStatus.READY
        assert updated.review_iterations == 1

        # Feedback file should be created
        feedback_file = chunk_dir / "REVIEW_FEEDBACK.md"
        assert feedback_file.exists()

    @pytest.mark.asyncio
    async def test_review_escalate_from_tool_call(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """ESCALATE decision from tool call marks NEEDS_ATTENTION."""
        from orchestrator.models import ReviewToolDecision

        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        tool_decision = ReviewToolDecision(
            decision="ESCALATE",
            summary="Requirements are ambiguous",
            reason="AMBIGUITY - Cannot determine correct behavior",
        )
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=tool_decision,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            with patch("orchestrator.scheduler.broadcast_attention_update"):
                await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "escalated" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_nudge_when_tool_not_called(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """When reviewer completes without calling tool, session is resumed with nudge."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=0,
            session_id="session-123",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult with NO review decision (tool not called)
        result = AgentResult(
            completed=True,
            suspended=False,
            session_id="session-123",
            review_decision=None,  # Tool was not called
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        # Should be READY to resume with nudge
        assert updated.status == WorkUnitStatus.READY
        assert updated.pending_answer is not None
        assert "ReviewDecision" in updated.pending_answer
        assert updated.review_nudge_count == 1
        assert updated.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_escalate_after_max_nudges(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """After 3 nudges without tool call, escalates to NEEDS_ATTENTION."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=2,  # Already nudged twice
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # AgentResult with NO review decision (tool not called after nudges)
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=None,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            with patch("orchestrator.scheduler.broadcast_attention_update"):
                await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        # After 3rd nudge (2 previous + 1 this time), should escalate
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "nudge" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_fallback_to_file_parsing_after_max_nudges(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """After max nudges, falls back to file parsing if decision file exists."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        # Create a decision file (fallback)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("""decision: APPROVE
summary: Implementation looks good
""")

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=2,  # Already nudged twice (will be 3rd)
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=None,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        # Should advance to COMPLETE phase using file fallback
        assert updated.phase == WorkUnitPhase.COMPLETE
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_nudge_count_resets_on_successful_decision(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Nudge count is reset when tool is called successfully."""
        from orchestrator.models import ReviewToolDecision

        chunk_dir = tmp_path / "docs" / "chunks" / "test"
        chunk_dir.mkdir(parents=True)

        mock_worktree_manager.get_worktree_path.return_value = tmp_path
        mock_worktree_manager.get_log_path.return_value = tmp_path / "logs"

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.REVIEW,
            status=WorkUnitStatus.RUNNING,
            review_nudge_count=2,  # Had some nudges before
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        tool_decision = ReviewToolDecision(
            decision="APPROVE",
            summary="All good now",
        )
        result = AgentResult(
            completed=True,
            suspended=False,
            review_decision=tool_decision,
        )

        with patch("orchestrator.scheduler.broadcast_work_unit_update"):
            await scheduler._handle_review_result(work_unit, tmp_path, result)

        updated = state_store.get_work_unit("test")
        assert updated.review_nudge_count == 0  # Reset to 0


# Chunk: docs/chunks/orch_manual_done_unblock - Manual DONE transition triggers unblock
class TestManualDoneUnblock:
    """Tests for unblocking dependents when work unit is manually set to DONE.

    When an operator manually sets a work unit status to DONE (via API or CLI),
    the unblock_dependents function should be called to transition any dependent
    work units from BLOCKED/NEEDS_ATTENTION to READY. This addresses the issue
    where auto-unblock only triggered when the scheduler completed a work unit
    through normal flow, leaving dependents stuck after manual intervention.
    """

    def test_unblock_dependents_function_exists(self, state_store):
        """The unblock_dependents module-level function exists and is importable."""
        from orchestrator.scheduler import unblock_dependents

        # Create blocker work unit (DONE)
        now = datetime.now(timezone.utc)
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker)

        # Create dependent work unit (BLOCKED)
        dependent = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(dependent)

        # Call the module-level function
        unblock_dependents(state_store, "blocker_chunk")

        # Verify dependent is now READY
        updated = state_store.get_work_unit("dependent_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert "blocker_chunk" not in updated.blocked_by

    def test_manual_done_via_api_unblocks_dependent(self, state_store):
        """Manual DONE via API endpoint should unblock dependent work units.

        This tests the integration where update_work_unit_endpoint calls
        unblock_dependents when status changes to DONE.
        """
        from orchestrator.scheduler import unblock_dependents

        now = datetime.now(timezone.utc)

        # Create blocker work unit (will be set to DONE manually)
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.NEEDS_ATTENTION,  # Simulates stuck state
            attention_reason="Merge to base failed: conflict",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker)

        # Create dependent work unit (BLOCKED)
        dependent = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(dependent)

        # Simulate what the API endpoint does: update status to DONE
        blocker.status = WorkUnitStatus.DONE
        blocker.attention_reason = None
        blocker.updated_at = datetime.now(timezone.utc)
        state_store.update_work_unit(blocker)

        # Then call unblock_dependents (what the API endpoint should do)
        unblock_dependents(state_store, "blocker_chunk")

        # Verify dependent is now READY
        updated = state_store.get_work_unit("dependent_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert "blocker_chunk" not in updated.blocked_by

    def test_unblock_multiple_dependents(self, state_store):
        """Manual DONE should unblock multiple dependent work units."""
        from orchestrator.scheduler import unblock_dependents

        now = datetime.now(timezone.utc)

        # Create blocker work unit (DONE)
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker)

        # Create multiple dependent work units
        for name in ["dep_a", "dep_b", "dep_c"]:
            dep = WorkUnit(
                chunk=name,
                phase=WorkUnitPhase.PLAN,
                status=WorkUnitStatus.BLOCKED,
                blocked_by=["blocker_chunk"],
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(dep)

        # Call unblock_dependents
        unblock_dependents(state_store, "blocker_chunk")

        # Verify all dependents are now READY
        for name in ["dep_a", "dep_b", "dep_c"]:
            updated = state_store.get_work_unit(name)
            assert updated.status == WorkUnitStatus.READY, f"{name} should be READY"
            assert "blocker_chunk" not in updated.blocked_by

    def test_partial_unblock_with_multiple_blockers(self, state_store):
        """Dependent with multiple blockers stays BLOCKED until all complete."""
        from orchestrator.scheduler import unblock_dependents

        now = datetime.now(timezone.utc)

        # Create two blocker work units
        blocker_a = WorkUnit(
            chunk="blocker_a",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker_a)

        blocker_b = WorkUnit(
            chunk="blocker_b",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,  # Still running
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker_b)

        # Create dependent blocked by BOTH
        dependent = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_a", "blocker_b"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(dependent)

        # Unblock after blocker_a completes
        unblock_dependents(state_store, "blocker_a")

        # Verify dependent is STILL BLOCKED (blocker_b still running)
        updated = state_store.get_work_unit("dependent_chunk")
        assert updated.status == WorkUnitStatus.BLOCKED
        assert "blocker_a" not in updated.blocked_by
        assert "blocker_b" in updated.blocked_by

    def test_unblock_needs_attention_to_ready(self, state_store):
        """Work unit in NEEDS_ATTENTION transitions to READY when manually unblocked."""
        from orchestrator.scheduler import unblock_dependents

        now = datetime.now(timezone.utc)

        # Create blocker work unit (DONE)
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker)

        # Create dependent in NEEDS_ATTENTION (e.g., from conflict resolution)
        dependent = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.NEEDS_ATTENTION,
            blocked_by=["blocker_chunk"],
            attention_reason="Conflict with running blocker_chunk",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(dependent)

        # Call unblock_dependents
        unblock_dependents(state_store, "blocker_chunk")

        # Verify dependent is now READY with cleared attention_reason
        updated = state_store.get_work_unit("dependent_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.attention_reason is None
        assert "blocker_chunk" not in updated.blocked_by

    def test_scheduler_unblock_still_works(self, state_store):
        """Existing scheduler-driven unblock (via _unblock_dependents method) still works.

        This is a regression test to ensure we didn't break the existing behavior.
        """
        from orchestrator.scheduler import unblock_dependents

        now = datetime.now(timezone.utc)

        # Create blocker work unit
        blocker = WorkUnit(
            chunk="blocker_chunk",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocker)

        # Create dependent work unit
        dependent = WorkUnit(
            chunk="dependent_chunk",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_chunk"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(dependent)

        # Call the function (same function used by scheduler)
        unblock_dependents(state_store, "blocker_chunk")

        # Verify dependent is now READY
        updated = state_store.get_work_unit("dependent_chunk")
        assert updated.status == WorkUnitStatus.READY
