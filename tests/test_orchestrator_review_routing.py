# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose_methods - Tests for extracted review_routing module
"""Tests for the orchestrator review_routing module.

These tests verify review decision routing logic including:
- Decision routing (APPROVE/FEEDBACK/ESCALATE)
- Fallback chain (tool → file → log)
- Nudge logic
- Loop detection (max iterations)
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.models import (
    AgentResult,
    ReviewDecision,
    ReviewIssue,
    ReviewResult,
    ReviewToolDecision,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.review_routing import (
    ReviewRoutingConfig,
    convert_tool_decision_to_result,
    route_review_decision,
    try_parse_from_file,
    try_parse_from_log,
)


class MockReviewRoutingCallbacks:
    """Mock implementation of ReviewRoutingCallbacks for testing."""

    def __init__(self):
        self.advance_phase_calls = []
        self.mark_needs_attention_calls = []
        self.update_work_unit_calls = []
        self.broadcast_calls = []

    async def advance_phase(self, work_unit: WorkUnit) -> None:
        self.advance_phase_calls.append(work_unit)

    async def mark_needs_attention(self, work_unit: WorkUnit, reason: str) -> None:
        self.mark_needs_attention_calls.append((work_unit, reason))

    def update_work_unit(self, work_unit: WorkUnit) -> None:
        self.update_work_unit_calls.append(work_unit)

    async def broadcast_work_unit_update(
        self, chunk: str, status: str, phase: str
    ) -> None:
        self.broadcast_calls.append((chunk, status, phase))


def create_test_work_unit(
    chunk: str = "test_chunk",
    review_iterations: int = 0,
    review_nudge_count: int = 0,
) -> WorkUnit:
    """Create a test work unit in REVIEW phase."""
    return WorkUnit(
        chunk=chunk,
        phase=WorkUnitPhase.REVIEW,
        status=WorkUnitStatus.RUNNING,
        priority=100,
        review_iterations=review_iterations,
        review_nudge_count=review_nudge_count,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestConvertToolDecisionToResult:
    """Tests for convert_tool_decision_to_result function."""

    def test_converts_approve_decision(self):
        """Converts APPROVE decision from tool call."""
        tool_decision = ReviewToolDecision(
            decision="APPROVE",
            summary="Code looks good",
        )

        result = convert_tool_decision_to_result(tool_decision, current_iteration=1)

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE
        assert result.summary == "Code looks good"
        assert result.iteration == 1

    def test_converts_feedback_with_issues(self):
        """Converts FEEDBACK decision with issues."""
        tool_decision = ReviewToolDecision(
            decision="FEEDBACK",
            summary="Needs improvements",
            issues=[
                {"location": "src/main.py:42", "concern": "Missing error handling"},
                {"location": "tests/", "concern": "Low coverage", "suggestion": "Add more tests"},
            ],
        )

        result = convert_tool_decision_to_result(tool_decision, current_iteration=2)

        assert result is not None
        assert result.decision == ReviewDecision.FEEDBACK
        assert len(result.issues) == 2
        assert result.issues[0].location == "src/main.py:42"
        assert result.issues[0].concern == "Missing error handling"
        assert result.issues[1].suggestion == "Add more tests"

    def test_converts_escalate_with_reason(self):
        """Converts ESCALATE decision with reason."""
        tool_decision = ReviewToolDecision(
            decision="ESCALATE",
            summary="Cannot proceed",
            reason="Requirements are unclear",
        )

        result = convert_tool_decision_to_result(tool_decision, current_iteration=1)

        assert result is not None
        assert result.decision == ReviewDecision.ESCALATE
        assert result.reason == "Requirements are unclear"

    def test_returns_none_for_invalid_decision(self):
        """Returns None for invalid decision value."""
        tool_decision = ReviewToolDecision(
            decision="MAYBE",  # Invalid
            summary="Not sure",
        )

        result = convert_tool_decision_to_result(tool_decision, current_iteration=1)

        assert result is None

    def test_case_insensitive_decision(self):
        """Decision conversion is case-insensitive."""
        tool_decision = ReviewToolDecision(
            decision="approve",  # lowercase
            summary="LGTM",
        )

        result = convert_tool_decision_to_result(tool_decision, current_iteration=1)

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE


class TestTryParseFromFile:
    """Tests for try_parse_from_file function."""

    def test_parses_decision_file(self, tmp_path):
        """Parses decision from REVIEW_DECISION.yaml file."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("decision: APPROVE\nsummary: Looks good")

        result = try_parse_from_file(tmp_path, "test_chunk")

        assert result is not None
        assert result.decision == ReviewDecision.APPROVE

    def test_returns_none_if_file_missing(self, tmp_path):
        """Returns None if decision file doesn't exist."""
        result = try_parse_from_file(tmp_path, "nonexistent_chunk")

        assert result is None

    def test_returns_none_on_parse_error(self, tmp_path):
        """Returns None if file content can't be parsed."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("not: valid: yaml: content: here")

        result = try_parse_from_file(tmp_path, "test_chunk")

        # Should return None when parsing fails
        assert result is None


class TestTryParseFromLog:
    """Tests for try_parse_from_log function."""

    def test_parses_review_log(self, tmp_path):
        """Parses decision from review.txt log file."""
        review_log = tmp_path / "review.txt"
        review_log.write_text("""
Some agent output...

```yaml
decision: FEEDBACK
summary: Needs work
```

More output...
""")

        result = try_parse_from_log(tmp_path)

        assert result is not None
        assert result.decision == ReviewDecision.FEEDBACK

    def test_returns_none_if_log_missing(self, tmp_path):
        """Returns None if review.txt doesn't exist."""
        result = try_parse_from_log(tmp_path)

        assert result is None


class TestRouteReviewDecision:
    """Tests for route_review_decision function."""

    @pytest.mark.asyncio
    async def test_approve_calls_advance_phase(self, tmp_path):
        """APPROVE decision calls advance_phase callback."""
        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="APPROVE",
                summary="All good",
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert len(callbacks.advance_phase_calls) == 1
        assert callbacks.advance_phase_calls[0] == work_unit

    @pytest.mark.asyncio
    async def test_feedback_returns_to_implement(self, tmp_path):
        """FEEDBACK decision returns work unit to IMPLEMENT phase."""
        # Create chunk directory for feedback file
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="FEEDBACK",
                summary="Needs improvements",
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert work_unit.phase == WorkUnitPhase.IMPLEMENT
        assert work_unit.status == WorkUnitStatus.READY
        assert work_unit.review_iterations == 1
        assert len(callbacks.broadcast_calls) == 1

    @pytest.mark.asyncio
    async def test_escalate_calls_mark_needs_attention(self, tmp_path):
        """ESCALATE decision calls mark_needs_attention callback."""
        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="ESCALATE",
                summary="Cannot proceed",
                reason="Requirements unclear",
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert len(callbacks.mark_needs_attention_calls) == 1
        work_unit, reason = callbacks.mark_needs_attention_calls[0]
        assert "escalated" in reason.lower()
        assert "Requirements unclear" in reason

    @pytest.mark.asyncio
    async def test_max_iterations_triggers_escalation(self, tmp_path):
        """Exceeding max iterations triggers auto-escalation."""
        work_unit = create_test_work_unit(review_iterations=3)  # Already at max
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(completed=True)

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert len(callbacks.mark_needs_attention_calls) == 1
        _, reason = callbacks.mark_needs_attention_calls[0]
        assert "exceeded maximum review iterations" in reason

    @pytest.mark.asyncio
    async def test_nudge_when_tool_not_called(self, tmp_path):
        """Nudges reviewer when tool wasn't called."""
        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3, max_nudges=3)
        result = AgentResult(
            completed=True,
            session_id="session123",
            # No review_decision
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        # Should set up nudge
        assert work_unit.review_nudge_count == 1
        assert work_unit.pending_answer is not None
        assert "ReviewDecision tool" in work_unit.pending_answer
        assert work_unit.status == WorkUnitStatus.READY
        assert len(callbacks.broadcast_calls) == 1

    @pytest.mark.asyncio
    async def test_max_nudges_triggers_fallback(self, tmp_path):
        """Max nudges reached triggers file/log fallback parsing."""
        # Create decision file for fallback
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("decision: APPROVE\nsummary: Fallback approval")

        work_unit = create_test_work_unit(review_nudge_count=2)  # At max nudges - 1
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3, max_nudges=3)
        result = AgentResult(completed=True)  # No tool decision

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        # Should fall back to file and find APPROVE
        assert len(callbacks.advance_phase_calls) == 1

    @pytest.mark.asyncio
    async def test_no_decision_after_all_fallbacks_escalates(self, tmp_path):
        """No decision after all fallbacks triggers escalation."""
        work_unit = create_test_work_unit(review_nudge_count=2)  # At max nudges - 1
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3, max_nudges=3)
        result = AgentResult(completed=True)  # No tool decision, no file, no log

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert len(callbacks.mark_needs_attention_calls) == 1
        _, reason = callbacks.mark_needs_attention_calls[0]
        assert "could not determine decision" in reason.lower()

    @pytest.mark.asyncio
    async def test_file_fallback_priority_2(self, tmp_path):
        """File fallback is used when tool decision is missing."""
        # Create decision file
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("decision: APPROVE\nsummary: From file")

        work_unit = create_test_work_unit(review_nudge_count=2)  # Skip nudging
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3, max_nudges=3)
        result = AgentResult(completed=True)  # No tool decision

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        # Should use file fallback
        assert len(callbacks.advance_phase_calls) == 1

    @pytest.mark.asyncio
    async def test_log_fallback_priority_3(self, tmp_path):
        """Log fallback is used when tool and file are missing."""
        # Create log file
        review_log = tmp_path / "review.txt"
        review_log.write_text("```yaml\ndecision: APPROVE\nsummary: From log\n```")

        work_unit = create_test_work_unit(review_nudge_count=2)  # Skip nudging
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3, max_nudges=3)
        result = AgentResult(completed=True)  # No tool decision

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        # Should use log fallback
        assert len(callbacks.advance_phase_calls) == 1

    @pytest.mark.asyncio
    async def test_tool_decision_has_priority_1(self, tmp_path):
        """Tool decision takes priority over file and log."""
        # Create both file and log with different decisions
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)
        decision_file = chunk_dir / "REVIEW_DECISION.yaml"
        decision_file.write_text("decision: FEEDBACK\nsummary: From file")

        review_log = tmp_path / "review.txt"
        review_log.write_text("```yaml\ndecision: ESCALATE\nsummary: From log\n```")

        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="APPROVE",  # Tool says APPROVE
                summary="From tool",
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        # Should use tool decision (APPROVE), not file (FEEDBACK) or log (ESCALATE)
        assert len(callbacks.advance_phase_calls) == 1

    @pytest.mark.asyncio
    async def test_nudge_count_reset_on_successful_tool_call(self, tmp_path):
        """Nudge count is reset when tool is called successfully."""
        work_unit = create_test_work_unit(review_nudge_count=2)  # Had previous nudges
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="APPROVE",
                summary="All good",
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        assert work_unit.review_nudge_count == 0

    @pytest.mark.asyncio
    async def test_feedback_creates_feedback_file(self, tmp_path):
        """FEEDBACK decision creates REVIEW_FEEDBACK.md file."""
        chunk_dir = tmp_path / "docs" / "chunks" / "test_chunk"
        chunk_dir.mkdir(parents=True)

        work_unit = create_test_work_unit()
        callbacks = MockReviewRoutingCallbacks()
        config = ReviewRoutingConfig(max_iterations=3)
        result = AgentResult(
            completed=True,
            review_decision=ReviewToolDecision(
                decision="FEEDBACK",
                summary="Needs work",
                issues=[{"location": "src/main.py", "concern": "Missing tests"}],
            ),
        )

        await route_review_decision(
            work_unit=work_unit,
            worktree_path=tmp_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=tmp_path,
        )

        feedback_file = chunk_dir / "REVIEW_FEEDBACK.md"
        assert feedback_file.exists()
        content = feedback_file.read_text()
        assert "Needs work" in content
        assert "Missing tests" in content
