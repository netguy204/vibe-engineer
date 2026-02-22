# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose_methods - Extracted from scheduler.py
"""Review routing logic for the orchestrator scheduler.

This module handles routing work units based on review decisions:
- Three-priority fallback chain for decision parsing (tool → file → log)
- Nudge logic when ReviewDecision tool wasn't called
- Loop detection (max iterations)
- APPROVE/FEEDBACK/ESCALATE routing

Extracted from scheduler.py to keep the scheduler focused on dispatch logic.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

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
from orchestrator.review_parsing import (
    create_review_feedback_file,
    parse_review_decision,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewRoutingConfig:
    """Configuration for review routing.

    Contains settings that control review behavior like max iterations
    and max nudges.
    """

    max_iterations: int
    max_nudges: int = 3


class ReviewRoutingCallbacks(Protocol):
    """Protocol defining callbacks needed for review routing.

    These callbacks allow the review routing logic to interact with
    the scheduler without direct coupling.
    """

    async def advance_phase(self, work_unit: WorkUnit) -> None:
        """Advance work unit to the next phase (COMPLETE)."""
        ...

    async def mark_needs_attention(self, work_unit: WorkUnit, reason: str) -> None:
        """Mark work unit as needing operator attention."""
        ...

    def update_work_unit(self, work_unit: WorkUnit) -> None:
        """Persist work unit changes to the store."""
        ...

    async def broadcast_work_unit_update(
        self, chunk: str, status: str, phase: str
    ) -> None:
        """Broadcast work unit status change via WebSocket."""
        ...


def convert_tool_decision_to_result(
    tool_decision: ReviewToolDecision,
    current_iteration: int,
) -> Optional[ReviewResult]:
    """Convert a ReviewToolDecision to a ReviewResult.

    Args:
        tool_decision: The decision captured from the ReviewDecision tool call
        current_iteration: Current review iteration count

    Returns:
        ReviewResult if the decision is valid, None otherwise
    """
    decision_str = tool_decision.decision.upper()
    if decision_str not in [d.value for d in ReviewDecision]:
        logger.warning(f"Invalid decision value from tool call: {decision_str}")
        return None

    # Convert issues from tool format to ReviewIssue format
    issues = []
    if tool_decision.issues:
        for issue_dict in tool_decision.issues:
            if isinstance(issue_dict, dict):
                issues.append(
                    ReviewIssue(
                        location=issue_dict.get("location", "unknown"),
                        concern=issue_dict.get("concern", ""),
                        suggestion=issue_dict.get("suggestion"),
                    )
                )

    return ReviewResult(
        decision=ReviewDecision(decision_str),
        summary=tool_decision.summary,
        issues=issues,
        reason=tool_decision.reason,
        iteration=current_iteration,
    )


def try_parse_from_file(
    worktree_path: Path,
    chunk: str,
) -> Optional[ReviewResult]:
    """Try to parse review decision from REVIEW_DECISION.yaml file.

    Args:
        worktree_path: Path to the worktree
        chunk: Chunk directory name

    Returns:
        ReviewResult if file exists and parses successfully, None otherwise
    """
    decision_file = worktree_path / "docs" / "chunks" / chunk / "REVIEW_DECISION.yaml"
    if not decision_file.exists():
        return None

    try:
        content = decision_file.read_text()
        return parse_review_decision(f"```yaml\n{content}\n```")
    except Exception as e:
        logger.warning(f"Error reading decision file: {e}")
        return None


def try_parse_from_log(
    log_dir: Path,
) -> Optional[ReviewResult]:
    """Try to parse review decision from agent log file.

    Args:
        log_dir: Directory containing agent logs

    Returns:
        ReviewResult if log exists and parses successfully, None otherwise
    """
    review_log = log_dir / "review.txt"
    if not review_log.exists():
        return None

    try:
        log_content = review_log.read_text()
        return parse_review_decision(log_content)
    except Exception as e:
        logger.warning(f"Error parsing review log: {e}")
        return None


async def route_review_decision(
    work_unit: WorkUnit,
    worktree_path: Path,
    result: AgentResult,
    config: ReviewRoutingConfig,
    callbacks: ReviewRoutingCallbacks,
    log_dir: Path,
) -> None:
    """Route work unit based on review decision.

    Handles the three-priority fallback chain for decision parsing:
    1. ReviewDecision tool call captured in AgentResult.review_decision
    2. REVIEW_DECISION.yaml file (fallback for backward compatibility)
    3. Agent log parsing (final fallback)

    Also implements nudge logic when the tool wasn't called and
    loop detection for max iterations.

    Args:
        work_unit: The work unit in REVIEW phase
        worktree_path: Path to the worktree
        result: AgentResult from the review phase
        config: Review routing configuration
        callbacks: Callbacks for scheduler interaction
        log_dir: Directory containing agent logs
    """
    chunk = work_unit.chunk

    # Calculate current iteration (max iterations check is now in _apply_review_decision
    # for the FEEDBACK case only - APPROVE should always succeed regardless of iteration count)
    current_iteration = work_unit.review_iterations + 1

    review_result = None

    # Priority 1: Check if review decision was captured from tool call
    if result.review_decision is not None:
        logger.info(
            f"Review decision captured from tool call for {chunk}: "
            f"{result.review_decision.decision}"
        )
        review_result = convert_tool_decision_to_result(
            result.review_decision, current_iteration
        )
        if review_result is not None:
            # Reset nudge count since tool was called successfully
            work_unit.review_nudge_count = 0

    # If no tool decision and agent completed, implement nudging
    if review_result is None and result.completed:
        # No tool call - increment nudge count and decide whether to nudge or escalate
        work_unit.review_nudge_count += 1
        work_unit.updated_at = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
        callbacks.update_work_unit(work_unit)

        if work_unit.review_nudge_count < config.max_nudges:
            # Continue the session with a nudge prompt
            logger.info(
                f"Reviewer for {chunk} did not call ReviewDecision tool, "
                f"nudging (attempt {work_unit.review_nudge_count}/{config.max_nudges})"
            )
            # Mark as needing to resume with nudge
            # The nudge will be handled in the next dispatch cycle
            work_unit.pending_answer = (
                "You completed the review but did not call the ReviewDecision tool. "
                "Please call the ReviewDecision tool now to submit your final decision. "
                "The tool accepts: decision (APPROVE, FEEDBACK, or ESCALATE), "
                "summary (brief explanation), and optional issues or reason."
            )
            work_unit.session_id = result.session_id  # Keep session for resume
            work_unit.status = WorkUnitStatus.READY  # Ready to resume
            work_unit.updated_at = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            )
            callbacks.update_work_unit(work_unit)

            await callbacks.broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )
            return  # Will resume in next dispatch cycle

        # Max nudges reached - fall back to file/log parsing
        logger.warning(
            f"Reviewer for {chunk} did not call ReviewDecision tool after "
            f"{config.max_nudges} nudges, falling back to file/log parsing"
        )

    # Priority 2 (fallback): Try to read from REVIEW_DECISION.yaml file
    if review_result is None:
        review_result = try_parse_from_file(worktree_path, chunk)

    # Priority 3 (fallback): Try parsing from agent logs
    if review_result is None:
        review_result = try_parse_from_log(log_dir)

    # If still no decision after all fallbacks, escalate to NEEDS_ATTENTION
    if review_result is None:
        logger.error(
            f"Could not determine review decision for {chunk} after "
            f"{work_unit.review_nudge_count} nudges and file/log fallback"
        )
        await callbacks.mark_needs_attention(
            work_unit,
            f"Review completed but could not determine decision. "
            f"Reviewer did not call ReviewDecision tool after {work_unit.review_nudge_count} "
            f"nudges and no decision found in files/logs.",
        )
        return

    # Route based on decision
    await _apply_review_decision(
        work_unit,
        worktree_path,
        review_result,
        current_iteration,
        result.session_id,
        callbacks,
        config,
    )


async def _apply_review_decision(
    work_unit: WorkUnit,
    worktree_path: Path,
    review_result: ReviewResult,
    current_iteration: int,
    session_id: Optional[str],
    callbacks: ReviewRoutingCallbacks,
    config: ReviewRoutingConfig,
) -> None:
    """Apply the parsed review decision to route the work unit.

    Args:
        work_unit: The work unit to route
        worktree_path: Path to the worktree
        review_result: The parsed review result
        current_iteration: Current iteration count
        session_id: Agent session ID (for preserving on ESCALATE)
        callbacks: Callbacks for scheduler interaction
        config: Review routing configuration (for max_iterations check)
    """
    chunk = work_unit.chunk
    from datetime import datetime, timezone

    if review_result.decision == ReviewDecision.APPROVE:
        logger.info(f"Review APPROVED for {chunk}: {review_result.summary}")
        # Reset nudge count and proceed to COMPLETE phase
        work_unit.review_nudge_count = 0
        work_unit.updated_at = datetime.now(timezone.utc)
        callbacks.update_work_unit(work_unit)
        await callbacks.advance_phase(work_unit)

    elif review_result.decision == ReviewDecision.FEEDBACK:
        logger.info(
            f"Review FEEDBACK for {chunk} (iteration {current_iteration}): "
            f"{review_result.summary}"
        )

        # Check iteration limit BEFORE cycling back to implement
        # We can't start another implementation cycle if we've hit the max
        if current_iteration >= config.max_iterations:
            logger.warning(
                f"Chunk {chunk} exceeded max review iterations ({config.max_iterations}) "
                f"with FEEDBACK - escalating"
            )
            await callbacks.mark_needs_attention(
                work_unit,
                f"Auto-escalated: exceeded maximum review iterations ({config.max_iterations}). "
                f"The implementation may need significant rework or the requirements "
                f"may be unclear. Last feedback: {review_result.summary}",
            )
            return

        # Create the feedback file for the implementer
        create_review_feedback_file(
            worktree_path,
            chunk,
            review_result,
            current_iteration,
        )

        # Increment iteration counter and return to IMPLEMENT phase
        work_unit.review_iterations = current_iteration
        work_unit.review_nudge_count = 0  # Reset nudge count
        work_unit.phase = WorkUnitPhase.IMPLEMENT
        work_unit.status = WorkUnitStatus.READY
        work_unit.session_id = None  # Fresh session for re-implementation
        work_unit.attention_reason = None
        work_unit.updated_at = datetime.now(timezone.utc)
        callbacks.update_work_unit(work_unit)

        # Broadcast via WebSocket
        await callbacks.broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

    elif review_result.decision == ReviewDecision.ESCALATE:
        logger.warning(
            f"Review ESCALATED for {chunk}: {review_result.reason or review_result.summary}"
        )
        work_unit.review_nudge_count = 0  # Reset nudge count
        work_unit.session_id = session_id  # Preserve session for resume with operator answer
        work_unit.updated_at = datetime.now(timezone.utc)
        callbacks.update_work_unit(work_unit)
        await callbacks.mark_needs_attention(
            work_unit,
            f"Review escalated: {review_result.reason or review_result.summary}",
        )
