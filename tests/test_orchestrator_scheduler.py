# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
# Chunk: docs/chunks/orch_api_retry - Tests for API retry functionality
# Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase tests
"""Tests for orchestrator scheduler - WebSocket broadcasts, API retry, and REBASE phase.

These tests cover:
- WebSocket broadcast invariant (every state change broadcasts)
- API retry logic (is_retryable_api_error, retry scheduling)
- REBASE phase between IMPLEMENT and REVIEW

Other scheduler tests are split into focused modules:
- test_orchestrator_scheduler_dispatch.py - Core dispatch mechanics
- test_orchestrator_scheduler_results.py - Agent result handling
- test_orchestrator_scheduler_activation.py - Chunk activation
- test_orchestrator_scheduler_worktree.py - Deferred worktree creation
- test_orchestrator_scheduler_injection.py - Answer injection and conflicts
- test_orchestrator_scheduler_unblock.py - Unblock flows
- test_orchestrator_scheduler_review.py - Review phase

Fixtures are defined in conftest.py:
- state_store, mock_worktree_manager, mock_agent_runner, orchestrator_config, scheduler
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from orchestrator.retry import is_retryable_api_error
from orchestrator.models import (
    AgentResult,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)


# Chunk: docs/chunks/orch_broadcast_invariant - Test coverage for WebSocket broadcast invariant
class TestWebSocketBroadcasts:
    """Tests for WebSocket broadcast invariant.

    Every work unit state change should broadcast via WebSocket so the
    dashboard receives real-time updates.
    """

    @pytest.mark.asyncio
    async def test_run_work_unit_broadcasts_running_status(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Dispatching a work unit broadcasts RUNNING status via WebSocket."""
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

        with patch("orchestrator.scheduler.broadcast_work_unit_update") as mock_broadcast:
            await scheduler._run_work_unit(work_unit)

            # Verify broadcast was called with RUNNING status
            mock_broadcast.assert_called()
            calls = [
                c
                for c in mock_broadcast.call_args_list
                if c.kwargs.get("status") == "RUNNING"
            ]
            assert len(calls) >= 1, "Expected at least one broadcast with RUNNING status"

    @pytest.mark.asyncio
    async def test_advance_phase_broadcasts_ready_status(self, scheduler, state_store):
        """Advancing phases broadcasts READY status via WebSocket."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test",
            phase=WorkUnitPhase.PLAN,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        with patch("orchestrator.scheduler.broadcast_work_unit_update") as mock_broadcast:
            await scheduler._advance_phase(work_unit)

            # Verify broadcast was called with READY status
            mock_broadcast.assert_called()
            calls = [
                c
                for c in mock_broadcast.call_args_list
                if c.kwargs.get("status") == "READY"
            ]
            assert len(calls) >= 1, "Expected at least one broadcast with READY status"

            # Verify the phase was also advanced
            call_args = calls[0].kwargs
            assert call_args["phase"] == "IMPLEMENT"

    @pytest.mark.asyncio
    async def test_advance_phase_broadcasts_done_status(
        self, scheduler, state_store, mock_worktree_manager, tmp_path
    ):
        """Completing all phases broadcasts DONE status via WebSocket."""
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

        with patch("orchestrator.scheduler.broadcast_work_unit_update") as mock_broadcast:
            await scheduler._advance_phase(work_unit)

            # Verify broadcast was called with DONE status
            mock_broadcast.assert_called()
            calls = [
                c
                for c in mock_broadcast.call_args_list
                if c.kwargs.get("status") == "DONE"
            ]
            assert len(calls) >= 1, "Expected at least one broadcast with DONE status"

    @pytest.mark.asyncio
    async def test_mark_needs_attention_broadcasts_status(self, scheduler, state_store):
        """_mark_needs_attention broadcasts NEEDS_ATTENTION status via WebSocket."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        with patch("orchestrator.scheduler.broadcast_work_unit_update") as mock_broadcast:
            with patch("orchestrator.scheduler.broadcast_attention_update"):
                await scheduler._mark_needs_attention(work_unit, "Something went wrong")

                # Verify broadcast was called with NEEDS_ATTENTION status
                mock_broadcast.assert_called_once()
                call_kwargs = mock_broadcast.call_args.kwargs
                assert call_kwargs["status"] == "NEEDS_ATTENTION"
                assert call_kwargs["chunk"] == "test_chunk"


# Chunk: docs/chunks/orch_api_retry - Tests for API retry functionality
class TestIsRetryableApiError:
    """Tests for the is_retryable_api_error helper function."""

    def test_detects_500_error(self):
        """Detects HTTP 500 Internal Server Error."""
        assert is_retryable_api_error("Error: 500 Internal Server Error")
        assert is_retryable_api_error("status code 500")
        assert is_retryable_api_error("HTTP/1.1 500")

    def test_detects_502_bad_gateway(self):
        """Detects HTTP 502 Bad Gateway."""
        assert is_retryable_api_error("502 Bad Gateway")
        assert is_retryable_api_error("error: 502")

    def test_detects_503_service_unavailable(self):
        """Detects HTTP 503 Service Unavailable."""
        assert is_retryable_api_error("503 Service Unavailable")
        assert is_retryable_api_error("service unavailable")

    def test_detects_504_gateway_timeout(self):
        """Detects HTTP 504 Gateway Timeout."""
        assert is_retryable_api_error("504 Gateway Timeout")
        assert is_retryable_api_error("gateway timeout")

    def test_detects_529_overloaded(self):
        """Detects HTTP 529 Overloaded (Anthropic-specific)."""
        assert is_retryable_api_error("529 Overloaded")
        assert is_retryable_api_error("error code 529")

    def test_detects_overloaded_text(self):
        """Detects 'overloaded' text patterns."""
        assert is_retryable_api_error("API is overloaded, please retry")
        assert is_retryable_api_error("Server overloaded")

    def test_detects_api_error_type(self):
        """Detects Anthropic api_error type."""
        assert is_retryable_api_error("api_error: server error")
        assert is_retryable_api_error("type: api_error")

    def test_detects_rate_limit(self):
        """Detects rate limit errors (often temporary)."""
        assert is_retryable_api_error("rate_limit exceeded")
        assert is_retryable_api_error("rate_limit_error")

    def test_rejects_4xx_errors(self):
        """Does not retry 4xx client errors."""
        assert not is_retryable_api_error("400 Bad Request")
        assert not is_retryable_api_error("401 Unauthorized")
        assert not is_retryable_api_error("403 Forbidden")
        assert not is_retryable_api_error("404 Not Found")
        assert not is_retryable_api_error("429 Too Many Requests")  # 429 is not a 5xx

    def test_rejects_non_api_errors(self):
        """Does not retry non-API errors."""
        assert not is_retryable_api_error("FileNotFoundError: /path/to/file")
        assert not is_retryable_api_error("SyntaxError in code")
        assert not is_retryable_api_error("Permission denied")
        assert not is_retryable_api_error("Invalid argument")

    def test_handles_empty_error(self):
        """Handles empty or None error strings."""
        assert not is_retryable_api_error("")
        assert not is_retryable_api_error(None)

    def test_case_insensitive(self):
        """Pattern matching is case-insensitive."""
        assert is_retryable_api_error("INTERNAL SERVER ERROR")
        assert is_retryable_api_error("Bad Gateway")
        assert is_retryable_api_error("SERVICE UNAVAILABLE")
        assert is_retryable_api_error("Overloaded")


class TestApiRetryScheduling:
    """Tests for API retry scheduling in the scheduler."""

    @pytest.mark.asyncio
    async def test_schedule_api_retry_increments_count(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify retry count increments on each retry."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="retry_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="500 Internal Server Error",
            session_id="session-123",
        )

        await scheduler._schedule_api_retry(work_unit, result)

        updated = state_store.get_work_unit("retry_chunk")
        assert updated.api_retry_count == 1
        assert updated.session_id == "session-123"
        assert updated.pending_answer == "continue"
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_schedule_api_retry_calculates_backoff(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify exponential backoff calculation."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="backoff_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=2,  # 3rd attempt will use 2^2 = 4x initial delay
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            error="503 Service Unavailable",
            session_id="session-456",
        )

        # Default config: initial=100ms, so 3rd attempt = 100 * 2^2 = 400ms
        await scheduler._schedule_api_retry(work_unit, result)

        updated = state_store.get_work_unit("backoff_chunk")
        assert updated.api_retry_count == 3
        assert updated.next_retry_at is not None
        # Should be approximately 400ms in the future
        expected_delay = timedelta(milliseconds=400)
        actual_delay = updated.next_retry_at - now
        # Allow some tolerance for execution time
        assert actual_delay >= expected_delay - timedelta(milliseconds=50)
        assert actual_delay <= expected_delay + timedelta(milliseconds=100)

    @pytest.mark.asyncio
    async def test_schedule_api_retry_caps_at_max_delay(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify backoff caps at max delay."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="max_delay_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=20,  # Very high count, should cap at 5s
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            error="502 Bad Gateway",
            session_id="session-789",
        )

        await scheduler._schedule_api_retry(work_unit, result)

        updated = state_store.get_work_unit("max_delay_chunk")
        # Max delay is 5000ms = 5s by default
        max_delay = timedelta(milliseconds=scheduler.config.api_retry_max_delay_ms)
        actual_delay = updated.next_retry_at - now
        # Should be capped at max delay (with some tolerance)
        assert actual_delay <= max_delay + timedelta(milliseconds=100)

    @pytest.mark.asyncio
    async def test_dispatch_respects_retry_timing(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify dispatch loop skips work units in backoff period."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="waiting_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            next_retry_at=now + timedelta(seconds=10),  # 10 seconds in future
            pending_answer="continue",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Run dispatch tick
        await scheduler._dispatch_tick()

        # Should NOT have dispatched (still in backoff)
        assert "waiting_chunk" not in scheduler._running_agents

    @pytest.mark.asyncio
    async def test_dispatch_clears_retry_timing_when_elapsed(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """Verify dispatch clears next_retry_at when backoff period elapsed."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="ready_retry_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.READY,
            next_retry_at=now - timedelta(seconds=1),  # 1 second in past
            pending_answer="continue",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Run dispatch tick
        await scheduler._dispatch_tick()

        # Should have dispatched (backoff elapsed)
        assert "ready_retry_chunk" in scheduler._running_agents

        # next_retry_at should be cleared
        updated = state_store.get_work_unit("ready_retry_chunk")
        assert updated.next_retry_at is None

    @pytest.mark.asyncio
    async def test_retry_exhaustion_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify NEEDS_ATTENTION after exhausting retries."""
        now = datetime.now(timezone.utc)
        # Set retry count to max - 1
        work_unit = WorkUnit(
            chunk="exhausted_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=scheduler.config.api_retry_max_attempts,  # Already at max
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            error="500 Internal Server Error",
        )

        # Handle the result - should mark needs attention since retries exhausted
        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("exhausted_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "API error after" in updated.attention_reason
        assert str(scheduler.config.api_retry_max_attempts) in updated.attention_reason

    @pytest.mark.asyncio
    async def test_non_retryable_error_immediately_needs_attention(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify non-retryable errors skip retry logic."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="non_retry_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            error="400 Bad Request - invalid parameter",  # 4xx error, not retryable
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("non_retry_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert updated.api_retry_count == 0  # Should not have incremented

    @pytest.mark.asyncio
    async def test_successful_completion_resets_retry_state(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify retry state clears on successful phase completion."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="success_chunk",
            phase=WorkUnitPhase.GOAL,  # Will advance to PLAN
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=5,
            next_retry_at=now + timedelta(seconds=1),
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Advance phase
        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("success_chunk")
        assert updated.phase == WorkUnitPhase.PLAN
        assert updated.status == WorkUnitStatus.READY
        assert updated.api_retry_count == 0
        assert updated.next_retry_at is None


# Chunk: docs/chunks/orch_session_auto_resume - Session limit retry scheduling tests
class TestSessionLimitRetryScheduling:
    """Tests for session limit retry scheduling in the scheduler.

    When an agent hits a session limit with a known reset time, the scheduler
    should automatically schedule a retry at that time instead of marking
    the work unit as NEEDS_ATTENTION.
    """

    @pytest.mark.asyncio
    async def test_session_limit_with_parseable_time_schedules_retry(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Session limit with parseable reset time schedules retry at that time."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="session_limit_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit - resets 10pm",
            session_id="session-abc",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("session_limit_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.next_retry_at is not None
        # Verify it's scheduled for 10pm UTC (or tomorrow if 10pm has passed)
        assert updated.next_retry_at.hour == 22
        assert updated.next_retry_at.minute == 0
        assert updated.session_id == "session-abc"
        assert updated.pending_answer == "continue"

    @pytest.mark.asyncio
    async def test_session_limit_without_parseable_time_needs_attention(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Session limit without parseable reset time marks NEEDS_ATTENTION."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="unparseable_limit_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # No reset time in the error - can't be parsed
        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit - please try again later",
            session_id="session-xyz",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("unparseable_limit_chunk")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "limit" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_session_limit_with_timezone_schedules_utc_retry(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Session limit with timezone correctly converts to UTC for retry."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="tz_limit_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit - resets 10pm (America/New_York)",
            session_id="session-tz",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("tz_limit_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.next_retry_at is not None
        assert updated.next_retry_at.tzinfo == timezone.utc
        # Result should be in UTC (10pm Eastern is 3am or 2am UTC depending on DST)

    @pytest.mark.asyncio
    async def test_session_limit_logs_scheduled_retry_time(
        self, scheduler, state_store, mock_worktree_manager, caplog
    ):
        """Verify scheduler logs 'Session limit hit, scheduled retry at' message."""
        import logging

        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="log_test_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit - resets 10pm",
            session_id="session-log",
        )

        with caplog.at_level(logging.INFO):
            await scheduler._handle_agent_result(work_unit, result)

        assert any("session limit" in record.message.lower() for record in caplog.records)
        assert any("scheduled retry" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_session_limit_checked_before_5xx_retry(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Session limit detection takes priority over 5xx retry logic."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="priority_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Error contains both session limit AND 500-like text
        # Session limit should take priority
        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit (internal error) - resets 10pm",
            session_id="session-priority",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("priority_chunk")
        assert updated.status == WorkUnitStatus.READY
        # Should be scheduled for the reset time, not exponential backoff
        assert updated.next_retry_at.hour == 22

    @pytest.mark.asyncio
    async def test_session_limit_preserves_session_id_for_resumption(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Session ID is preserved for session resumption after reset."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="resume_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="You've hit your limit - resets 10pm",
            session_id="important-session-123",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("resume_chunk")
        assert updated.session_id == "important-session-123"
        assert updated.pending_answer == "continue"

    @pytest.mark.asyncio
    async def test_5xx_error_still_uses_exponential_backoff(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """5xx errors without session limit still use exponential backoff."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="backoff_5xx_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        result = AgentResult(
            completed=False,
            suspended=False,
            error="500 Internal Server Error",
            session_id="session-5xx",
        )

        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("backoff_5xx_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.api_retry_count == 1
        # Should be scheduled with exponential backoff, not at a specific time
        # Initial delay is 100ms
        expected_delay = timedelta(milliseconds=100)
        actual_delay = updated.next_retry_at - now
        assert actual_delay < timedelta(seconds=1)


# Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase tests
class TestRebasePhase:
    """Tests for REBASE phase between IMPLEMENT and REVIEW."""

    @pytest.mark.asyncio
    async def test_implement_advances_to_rebase_not_review(self, scheduler, state_store):
        """Verify IMPLEMENT phase advances to REBASE, not directly to REVIEW."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="rebase_test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        await scheduler._advance_phase(work_unit)

        updated = state_store.get_work_unit("rebase_test")
        assert updated.phase == WorkUnitPhase.REBASE
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_rebase_success_advances_to_review(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """REBASE phase on success advances to REVIEW phase."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="rebase_success",
            phase=WorkUnitPhase.REBASE,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Simulate agent completing successfully (clean merge, tests pass)
        result = AgentResult(completed=True, suspended=False)
        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("rebase_success")
        assert updated.phase == WorkUnitPhase.REVIEW
        assert updated.status == WorkUnitStatus.READY

    @pytest.mark.asyncio
    async def test_rebase_conflict_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """REBASE phase with merge conflict marks work unit NEEDS_ATTENTION."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="rebase_conflict",
            phase=WorkUnitPhase.REBASE,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Simulate agent failing due to unresolvable conflict
        result = AgentResult(
            completed=False,
            error="Merge conflict in src/scheduler.py - cannot resolve automatically",
        )
        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("rebase_conflict")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "conflict" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_rebase_test_failure_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """REBASE phase with test failure marks work unit NEEDS_ATTENTION."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="rebase_test_fail",
            phase=WorkUnitPhase.REBASE,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Simulate agent failing due to test failures after merge
        result = AgentResult(
            completed=False,
            error="Test failures after merge: test_scheduler.py::test_phase_advance FAILED",
        )
        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("rebase_test_fail")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "test" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_rebase_phase_in_full_lifecycle(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner, tmp_path
    ):
        """Verify REBASE phase is in the correct position in the full lifecycle."""
        # Set up chunk with ACTIVE status for final completion
        chunk_dir = tmp_path / "docs" / "chunks" / "lifecycle_test"
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
            chunk="lifecycle_test",
            phase=WorkUnitPhase.GOAL,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Advance through all phases and verify order
        phases_seen = [work_unit.phase]

        # GOAL -> PLAN
        await scheduler._advance_phase(work_unit)
        updated = state_store.get_work_unit("lifecycle_test")
        phases_seen.append(updated.phase)
        assert updated.phase == WorkUnitPhase.PLAN

        # PLAN -> IMPLEMENT
        work_unit = updated
        await scheduler._advance_phase(work_unit)
        updated = state_store.get_work_unit("lifecycle_test")
        phases_seen.append(updated.phase)
        assert updated.phase == WorkUnitPhase.IMPLEMENT

        # IMPLEMENT -> REBASE (this is the key test)
        work_unit = updated
        await scheduler._advance_phase(work_unit)
        updated = state_store.get_work_unit("lifecycle_test")
        phases_seen.append(updated.phase)
        assert updated.phase == WorkUnitPhase.REBASE

        # REBASE -> REVIEW
        work_unit = updated
        await scheduler._advance_phase(work_unit)
        updated = state_store.get_work_unit("lifecycle_test")
        phases_seen.append(updated.phase)
        assert updated.phase == WorkUnitPhase.REVIEW

        # Verify the complete order
        expected_order = [
            WorkUnitPhase.GOAL,
            WorkUnitPhase.PLAN,
            WorkUnitPhase.IMPLEMENT,
            WorkUnitPhase.REBASE,
            WorkUnitPhase.REVIEW,
        ]
        assert phases_seen == expected_order

    @pytest.mark.asyncio
    async def test_rebase_suspended_for_question_marks_needs_attention(
        self, scheduler, state_store, mock_worktree_manager, mock_agent_runner
    ):
        """REBASE phase suspended for question marks work unit NEEDS_ATTENTION."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="rebase_question",
            phase=WorkUnitPhase.REBASE,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Simulate agent asking a question during rebase
        result = AgentResult(
            completed=False,
            suspended=True,
            session_id="session-123",
            question={
                "question": "Both versions modified the same function. Which approach should I use?",
                "options": [{"label": "Keep chunk version"}, {"label": "Keep trunk version"}],
            },
        )
        await scheduler._handle_agent_result(work_unit, result)

        updated = state_store.get_work_unit("rebase_question")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "question" in updated.attention_reason.lower()
        assert updated.session_id == "session-123"


# Chunk: docs/chunks/persist_retry_state - Tests for crash recovery retry preservation
class TestCrashRecoveryRetryPreservation:
    """Tests for preserving retry backoff state across daemon restarts.

    When the orchestrator daemon restarts and finds RUNNING work units,
    it should preserve the retry backoff state for units that were mid-retry.
    """

    @pytest.mark.asyncio
    async def test_recover_from_crash_preserves_retry_backoff(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Crash recovery with api_retry_count > 0 sets next_retry_at appropriately."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="retry_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=3,  # Mid-retry
            next_retry_at=None,  # Cleared when dispatch happened
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Mock worktree manager to return no worktrees
        mock_worktree_manager.list_worktrees.return_value = []

        await scheduler._recover_from_crash()

        updated = state_store.get_work_unit("retry_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.next_retry_at is not None
        # The backoff should be in the future
        assert updated.next_retry_at > now
        # For retry count 3, backoff = min(100ms * 2^(3-1), 5000ms) = 400ms
        expected_delay = timedelta(milliseconds=400)
        actual_delay = updated.next_retry_at - now
        assert actual_delay >= expected_delay - timedelta(milliseconds=50)
        assert actual_delay <= expected_delay + timedelta(milliseconds=100)

    @pytest.mark.asyncio
    async def test_recover_from_crash_no_retry_for_zero_count(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Crash recovery with api_retry_count == 0 does NOT set next_retry_at."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="no_retry_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=0,  # No retries in progress
            next_retry_at=None,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Mock worktree manager to return no worktrees
        mock_worktree_manager.list_worktrees.return_value = []

        await scheduler._recover_from_crash()

        updated = state_store.get_work_unit("no_retry_chunk")
        assert updated.status == WorkUnitStatus.READY
        assert updated.next_retry_at is None

    @pytest.mark.asyncio
    async def test_recovered_unit_respects_backoff_timing(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """After recovery, a work unit with next_retry_at in the future is NOT dispatched."""
        now = datetime.now(timezone.utc)
        work_unit = WorkUnit(
            chunk="backoff_chunk",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            api_retry_count=3,
            next_retry_at=None,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Mock worktree manager to return no worktrees
        mock_worktree_manager.list_worktrees.return_value = []

        # Perform crash recovery
        await scheduler._recover_from_crash()

        # Verify the unit has next_retry_at set
        recovered = state_store.get_work_unit("backoff_chunk")
        assert recovered.status == WorkUnitStatus.READY
        assert recovered.next_retry_at is not None
        assert recovered.next_retry_at > datetime.now(timezone.utc)

        # Now run dispatch tick - should NOT dispatch because of backoff
        await scheduler._dispatch_tick()

        # Should NOT have dispatched (still in backoff)
        assert "backoff_chunk" not in scheduler._running_agents

    @pytest.mark.asyncio
    async def test_recover_from_crash_uses_exponential_backoff_formula(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify recovery uses the same exponential backoff formula as _schedule_api_retry."""
        now = datetime.now(timezone.utc)

        # Test multiple retry counts to verify exponential progression
        test_cases = [
            (1, 100),    # 100ms * 2^0 = 100ms
            (2, 200),    # 100ms * 2^1 = 200ms
            (3, 400),    # 100ms * 2^2 = 400ms
            (4, 800),    # 100ms * 2^3 = 800ms
            (5, 1600),   # 100ms * 2^4 = 1600ms
            (10, 5000),  # Would be 100ms * 2^9 = 51200ms, but capped at 5000ms
        ]

        mock_worktree_manager.list_worktrees.return_value = []

        for retry_count, expected_ms in test_cases:
            work_unit = WorkUnit(
                chunk=f"exp_chunk_{retry_count}",
                phase=WorkUnitPhase.IMPLEMENT,
                status=WorkUnitStatus.RUNNING,
                worktree="/tmp/worktree",
                api_retry_count=retry_count,
                next_retry_at=None,
                created_at=now,
                updated_at=now,
            )
            state_store.create_work_unit(work_unit)

        await scheduler._recover_from_crash()

        for retry_count, expected_ms in test_cases:
            updated = state_store.get_work_unit(f"exp_chunk_{retry_count}")
            assert updated.status == WorkUnitStatus.READY
            assert updated.next_retry_at is not None
            expected_delay = timedelta(milliseconds=expected_ms)
            actual_delay = updated.next_retry_at - now
            # Allow tolerance for execution time
            assert actual_delay >= expected_delay - timedelta(milliseconds=50), \
                f"retry_count={retry_count}: delay too short"
            assert actual_delay <= expected_delay + timedelta(milliseconds=200), \
                f"retry_count={retry_count}: delay too long"


# Chunk: docs/chunks/finalization_recovery - Crash recovery for incomplete finalization
class TestFinalizationRecovery:
    """Tests for recovery from crashes during work unit finalization.

    When a daemon crashes after remove_worktree() but before merge_to_base(),
    the work unit's changes survive only as an unmerged branch. These tests
    verify that the scheduler can detect and recover from this scenario.
    """

    @pytest.mark.asyncio
    async def test_auto_recovery_success_case(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Auto-recover incomplete finalization when merge is clean.

        Simulates a crash after worktree removal but before merge, where
        the merge can be completed automatically (no conflicts).
        """
        now = datetime.now(timezone.utc)

        # Create a work unit in COMPLETE phase (crashed during finalization)
        work_unit = WorkUnit(
            chunk="recovery_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,  # Was running when it crashed
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Configure mocks to simulate crash-during-finalization scenario:
        # - Branch exists (orch/recovery_test)
        # - Worktree does NOT exist (was removed before crash)
        # - Branch has changes ahead of base (merge wasn't completed)
        # - Merge succeeds (no conflicts)
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.merge_to_base.return_value = None  # Success
        mock_worktree_manager.get_branch_name.return_value = "orch/recovery_test"

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Verify merge_to_base was called to complete the merge
        mock_worktree_manager.merge_to_base.assert_called_once_with(
            "recovery_test", delete_branch=True
        )

        # Verify work unit is now DONE
        updated = state_store.get_work_unit("recovery_test")
        assert updated.status == WorkUnitStatus.DONE

    @pytest.mark.asyncio
    async def test_conflict_escalation_case(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Escalate to NEEDS_ATTENTION when merge has conflicts.

        Simulates a crash where the subsequent merge cannot complete
        due to conflicts. The work unit should be marked NEEDS_ATTENTION
        with a descriptive reason including the branch name.
        """
        from orchestrator.worktree import WorktreeError

        now = datetime.now(timezone.utc)

        # Create a work unit in COMPLETE phase
        work_unit = WorkUnit(
            chunk="conflict_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Configure mocks for crash scenario with merge conflict
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.merge_to_base.side_effect = WorktreeError(
            "Merge conflict between orch/conflict_test and main"
        )
        mock_worktree_manager.get_branch_name.return_value = "orch/conflict_test"

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Verify work unit is now NEEDS_ATTENTION with descriptive reason
        updated = state_store.get_work_unit("conflict_test")
        assert updated.status == WorkUnitStatus.NEEDS_ATTENTION
        assert "orch/conflict_test" in updated.attention_reason
        assert "conflict" in updated.attention_reason.lower()

    @pytest.mark.asyncio
    async def test_existing_crash_recovery_preserved(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify existing crash recovery behavior is preserved.

        RUNNING work units should still be reset to READY, which is the
        pre-existing behavior that must not be broken.
        """
        now = datetime.now(timezone.utc)

        # Create a work unit in RUNNING status (orphaned agent)
        work_unit = WorkUnit(
            chunk="orphan_test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # No incomplete finalizations (no matching branches)
        mock_worktree_manager._branch_exists.return_value = False
        mock_worktree_manager.list_worktrees.return_value = []

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Verify work unit was reset to READY (existing behavior)
        updated = state_store.get_work_unit("orphan_test")
        assert updated.status == WorkUnitStatus.READY
        assert updated.worktree is None

    @pytest.mark.asyncio
    async def test_branch_exists_no_changes_cleanup(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Clean up dangling branch when it has no changes ahead of base.

        If a branch exists but has no commits ahead of base, just delete
        the branch without trying to merge.
        """
        now = datetime.now(timezone.utc)

        # Create a work unit in COMPLETE phase
        work_unit = WorkUnit(
            chunk="no_changes_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Configure: branch exists, no worktree, NO changes
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = False
        mock_worktree_manager.get_branch_name.return_value = "orch/no_changes_test"

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Verify branch was deleted (not merged)
        mock_worktree_manager.delete_branch.assert_called_once_with("no_changes_test")
        mock_worktree_manager.merge_to_base.assert_not_called()

    @pytest.mark.asyncio
    async def test_done_status_with_dangling_branch(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Handle DONE work unit with dangling branch.

        Rare case: work unit is DONE but branch still exists with changes.
        This could happen if merge_to_base succeeded but delete_branch failed.
        """
        now = datetime.now(timezone.utc)

        # Create a DONE work unit with dangling branch
        work_unit = WorkUnit(
            chunk="done_dangling_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.DONE,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Configure: branch exists, no worktree, has changes
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.get_branch_name.return_value = "orch/done_dangling_test"

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Should still attempt to merge
        mock_worktree_manager.merge_to_base.assert_called_once()

    @pytest.mark.asyncio
    async def test_worktree_exists_not_incomplete_finalization(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Skip recovery when worktree still exists.

        If the worktree exists, the crash happened before worktree removal,
        which is a different scenario handled by the existing RUNNING→READY logic.
        """
        now = datetime.now(timezone.utc)

        # Create a work unit in COMPLETE phase with worktree
        work_unit = WorkUnit(
            chunk="worktree_exists_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            worktree="/tmp/worktree",
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Configure: branch exists AND worktree exists
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = True
        mock_worktree_manager.list_worktrees.return_value = ["worktree_exists_test"]

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Should NOT attempt merge (worktree exists = not incomplete finalization)
        mock_worktree_manager.merge_to_base.assert_not_called()

    @pytest.mark.asyncio
    async def test_recovery_unblocks_dependents(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Verify that auto-recovery unblocks dependent work units.

        When a work unit is auto-recovered, its dependents should be unblocked.
        """
        now = datetime.now(timezone.utc)

        # Create the work unit that will be recovered
        work_unit = WorkUnit(
            chunk="blocker_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        # Create a work unit blocked by the first one
        blocked_unit = WorkUnit(
            chunk="blocked_test",
            phase=WorkUnitPhase.IMPLEMENT,
            status=WorkUnitStatus.BLOCKED,
            blocked_by=["blocker_test"],
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(blocked_unit)

        # Configure for successful recovery
        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.merge_to_base.return_value = None
        mock_worktree_manager.get_branch_name.return_value = "orch/blocker_test"

        # Run crash recovery
        await scheduler._recover_from_crash()

        # Verify blocked work unit was unblocked
        updated_blocked = state_store.get_work_unit("blocked_test")
        assert updated_blocked.status == WorkUnitStatus.READY
        assert "blocker_test" not in updated_blocked.blocked_by

    @pytest.mark.asyncio
    async def test_recovery_logs_warning_for_detected_incomplete(
        self, scheduler, state_store, mock_worktree_manager, caplog
    ):
        """Verify warnings are logged for detected incomplete finalizations."""
        import logging

        now = datetime.now(timezone.utc)

        work_unit = WorkUnit(
            chunk="log_test",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        state_store.create_work_unit(work_unit)

        mock_worktree_manager._branch_exists.return_value = True
        mock_worktree_manager.worktree_exists.return_value = False
        mock_worktree_manager.has_changes.return_value = True
        mock_worktree_manager.get_branch_name.return_value = "orch/log_test"

        with caplog.at_level(logging.WARNING):
            await scheduler._recover_from_crash()

        # Check that appropriate warnings were logged
        assert any("incomplete finalization" in record.message.lower() for record in caplog.records)


# Chunk: docs/chunks/finalize_double_commit - Tests for double-commit elimination
class TestFinalizeDoubleCommitElimination:
    """Tests that the scheduler does not double-commit during finalization.

    The scheduler should only call commit_changes directly for retained worktrees.
    For normal (non-retained) worktrees, finalize_work_unit owns the full
    commit→remove→merge sequence.
    """

    @pytest.mark.asyncio
    async def test_finalize_completed_does_not_commit_before_finalize(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Scheduler does NOT call commit_changes for non-retained worktrees.

        finalize_work_unit() handles commit internally, so the scheduler
        should not pre-commit.
        """
        now = datetime.now(timezone.utc)

        work_unit = WorkUnit(
            chunk="no_double_commit",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
            retain_worktree=False,
        )
        state_store.create_work_unit(work_unit)

        # Mock verification to return COMPLETED (post-IMPLEMENTING status)
        from orchestrator.activation import VerificationStatus, VerificationResult
        mock_verification = VerificationResult(status=VerificationStatus.COMPLETED)

        with patch("orchestrator.scheduler.verify_chunk_active_status", return_value=mock_verification), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock), \
             patch("orchestrator.scheduler.broadcast_attention_update", new_callable=AsyncMock):
            await scheduler._finalize_completed_work_unit(work_unit)

        # commit_changes should NOT have been called by the scheduler
        mock_worktree_manager.commit_changes.assert_not_called()
        # finalize_work_unit SHOULD have been called
        mock_worktree_manager.finalize_work_unit.assert_called_once_with("no_double_commit")

    @pytest.mark.asyncio
    async def test_finalize_completed_retain_worktree_commits_directly(
        self, scheduler, state_store, mock_worktree_manager
    ):
        """Scheduler DOES call commit_changes for retained worktrees.

        When retain_worktree=True, finalize_work_unit is skipped, so the
        scheduler must commit directly.
        """
        now = datetime.now(timezone.utc)

        work_unit = WorkUnit(
            chunk="retained_commit",
            phase=WorkUnitPhase.COMPLETE,
            status=WorkUnitStatus.RUNNING,
            created_at=now,
            updated_at=now,
            retain_worktree=True,
        )
        state_store.create_work_unit(work_unit)

        # Mock verification to return COMPLETED
        from orchestrator.activation import VerificationStatus, VerificationResult
        mock_verification = VerificationResult(status=VerificationStatus.COMPLETED)

        mock_worktree_manager.has_uncommitted_changes.return_value = True
        mock_worktree_manager.commit_changes.return_value = True

        with patch("orchestrator.scheduler.verify_chunk_active_status", return_value=mock_verification), \
             patch("orchestrator.scheduler.broadcast_work_unit_update", new_callable=AsyncMock), \
             patch("orchestrator.scheduler.broadcast_attention_update", new_callable=AsyncMock):
            await scheduler._finalize_completed_work_unit(work_unit)

        # commit_changes SHOULD have been called by the scheduler
        mock_worktree_manager.commit_changes.assert_called_once_with("retained_commit")
        # finalize_work_unit should NOT have been called (retained worktree)
        mock_worktree_manager.finalize_work_unit.assert_not_called()
