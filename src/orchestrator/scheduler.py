# Chunk: docs/chunks/orch_scheduling - Orchestrator scheduling layer
# Chunk: docs/chunks/orch_verify_active - ACTIVE status verification
# Chunk: docs/chunks/orch_activate_on_inject - Chunk activation on inject
# Chunk: docs/chunks/orch_attention_queue - Answer injection on resume
# Chunk: docs/chunks/orch_question_forward - AskUserQuestion forwarding
# Chunk: docs/chunks/orch_conflict_oracle - Conflict oracle integration
"""Scheduler for dispatching work units to agents.

The scheduler runs a background loop that:
1. Checks for READY work units
2. Checks for conflicts with running/ready work units
3. Spawns agents up to max_agents slots
4. Updates work unit status based on agent outcomes
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Optional

import yaml

from chunks import Chunks
from models import ChunkStatus
from task_utils import update_frontmatter_field
from orchestrator.agent import AgentRunner, create_log_callback
from orchestrator.models import (
    AgentResult,
    ConflictVerdict,
    OrchestratorConfig,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore
from orchestrator.worktree import WorktreeManager, WorktreeError


logger = logging.getLogger(__name__)


class VerificationStatus(StrEnum):
    """Result of verifying chunk ACTIVE status."""

    ACTIVE = "ACTIVE"  # Status is ACTIVE, proceed with commit/merge
    IMPLEMENTING = "IMPLEMENTING"  # Still IMPLEMENTING, needs retry
    ERROR = "ERROR"  # Error parsing or reading GOAL.md


@dataclass
class VerificationResult:
    """Result from verifying chunk's GOAL.md status."""

    status: VerificationStatus
    error: Optional[str] = None


# Chunk: docs/chunks/orch_activate_on_inject - Refactored to use Chunks class
def verify_chunk_active_status(worktree_path: Path, chunk: str) -> VerificationResult:
    """Verify that a chunk's GOAL.md has status: ACTIVE.

    Uses the Chunks class to parse frontmatter and check the status field.

    Args:
        worktree_path: Path to the worktree containing the chunk
        chunk: The chunk directory name

    Returns:
        VerificationResult indicating ACTIVE, IMPLEMENTING, or ERROR
    """
    chunks = Chunks(worktree_path)

    try:
        frontmatter = chunks.parse_chunk_frontmatter(chunk)

        if frontmatter is None:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error=f"Chunk '{chunk}' not found or GOAL.md missing",
            )

        if frontmatter.status == ChunkStatus.ACTIVE:
            return VerificationResult(status=VerificationStatus.ACTIVE)
        elif frontmatter.status == ChunkStatus.IMPLEMENTING:
            return VerificationResult(status=VerificationStatus.IMPLEMENTING)
        else:
            # Other statuses like FUTURE, SUPERSEDED, etc. are unexpected here
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error=f"Unexpected status '{frontmatter.status.value}' in GOAL.md (expected ACTIVE)",
            )

    except Exception as e:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            error=f"Error reading GOAL.md: {e}",
        )


class SchedulerError(Exception):
    """Exception raised for scheduler-related errors."""

    pass


# Chunk: docs/chunks/orch_activate_on_inject - Chunk activation helper
def activate_chunk_in_worktree(
    worktree_path: Path,
    target_chunk: str,
) -> Optional[str]:
    """Activate target chunk in worktree, displacing any existing IMPLEMENTING chunk.

    This function ensures exactly one chunk is IMPLEMENTING in the worktree by:
    1. Finding any existing IMPLEMENTING chunk
    2. If found and different from target, demoting it to FUTURE
    3. Activating the target chunk (FUTURE -> IMPLEMENTING)

    Args:
        worktree_path: Path to the worktree
        target_chunk: The chunk to activate

    Returns:
        The name of the displaced chunk (if any), or None.

    Raises:
        ValueError: If target chunk doesn't exist or can't be activated
    """
    chunks = Chunks(worktree_path)

    # Check if target is already IMPLEMENTING
    frontmatter = chunks.parse_chunk_frontmatter(target_chunk)
    if frontmatter is None:
        raise ValueError(f"Chunk '{target_chunk}' not found in worktree")

    if frontmatter.status == ChunkStatus.IMPLEMENTING:
        logger.info(f"Chunk {target_chunk} is already IMPLEMENTING, no activation needed")
        return None

    if frontmatter.status != ChunkStatus.FUTURE:
        raise ValueError(
            f"Chunk '{target_chunk}' has status '{frontmatter.status.value}', "
            f"expected 'FUTURE' for activation"
        )

    # Find any existing IMPLEMENTING chunk
    current_implementing = chunks.get_current_chunk()
    displaced_chunk = None

    if current_implementing is not None and current_implementing != target_chunk:
        # Demote the existing IMPLEMENTING chunk to FUTURE
        logger.info(
            f"Displacing existing IMPLEMENTING chunk '{current_implementing}' to FUTURE"
        )
        goal_path = chunks.get_chunk_goal_path(current_implementing)
        update_frontmatter_field(goal_path, "status", ChunkStatus.FUTURE.value)
        displaced_chunk = current_implementing

    # Now activate the target chunk
    logger.info(f"Activating chunk '{target_chunk}' (FUTURE -> IMPLEMENTING)")
    goal_path = chunks.get_chunk_goal_path(target_chunk)
    update_frontmatter_field(goal_path, "status", ChunkStatus.IMPLEMENTING.value)

    return displaced_chunk


# Chunk: docs/chunks/orch_activate_on_inject - Restore displaced chunk helper
def restore_displaced_chunk(worktree_path: Path, displaced_chunk: str) -> None:
    """Restore a displaced chunk back to IMPLEMENTING status.

    This is called before merge to ensure the user's manually-active chunk
    retains its IMPLEMENTING status after the merge.

    Args:
        worktree_path: Path to the worktree
        displaced_chunk: The chunk to restore to IMPLEMENTING
    """
    chunks = Chunks(worktree_path)

    # Verify the chunk exists and is currently FUTURE
    frontmatter = chunks.parse_chunk_frontmatter(displaced_chunk)
    if frontmatter is None:
        logger.warning(f"Cannot restore displaced chunk '{displaced_chunk}': not found")
        return

    if frontmatter.status != ChunkStatus.FUTURE:
        logger.warning(
            f"Cannot restore displaced chunk '{displaced_chunk}': "
            f"status is '{frontmatter.status.value}', expected 'FUTURE'"
        )
        return

    # Restore to IMPLEMENTING
    logger.info(f"Restoring displaced chunk '{displaced_chunk}' to IMPLEMENTING")
    goal_path = chunks.get_chunk_goal_path(displaced_chunk)
    update_frontmatter_field(goal_path, "status", ChunkStatus.IMPLEMENTING.value)


class Scheduler:
    """Manages work unit scheduling and agent dispatch.

    The scheduler maintains a pool of running agents and dispatches
    work units from the ready queue when slots are available.
    """

    def __init__(
        self,
        store: StateStore,
        worktree_manager: WorktreeManager,
        agent_runner: AgentRunner,
        config: OrchestratorConfig,
        project_dir: Path,
    ):
        """Initialize the scheduler.

        Args:
            store: State store for work units
            worktree_manager: Worktree manager for isolation
            agent_runner: Agent runner for phase execution
            config: Scheduler configuration
            project_dir: Root project directory
        """
        self.store = store
        self.worktree_manager = worktree_manager
        self.agent_runner = agent_runner
        self.config = config
        self.project_dir = project_dir

        self._running_agents: dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()

    @property
    def running_count(self) -> int:
        """Get the number of currently running agents."""
        return len(self._running_agents)

    @property
    def available_slots(self) -> int:
        """Get the number of available agent slots."""
        return max(0, self.config.max_agents - self.running_count)

    async def start(self) -> None:
        """Start the dispatch loop.

        Runs until stop() is called.
        """
        logger.info(
            f"Scheduler started (max_agents={self.config.max_agents}, "
            f"interval={self.config.dispatch_interval_seconds}s)"
        )

        # Clean up any orphaned worktrees from previous runs
        await self._recover_from_crash()

        while not self._stop_event.is_set():
            try:
                await self._dispatch_tick()
            except Exception as e:
                logger.error(f"Error in dispatch tick: {e}")

            # Wait for next tick or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.dispatch_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

        logger.info("Scheduler stopped")

    async def stop(self, timeout: float = 30.0) -> None:
        """Stop the dispatch loop gracefully.

        Args:
            timeout: Maximum time to wait for running agents
        """
        logger.info("Stopping scheduler...")
        self._stop_event.set()

        # Wait for running agents to complete
        if self._running_agents:
            logger.info(f"Waiting for {len(self._running_agents)} running agents...")
            tasks = list(self._running_agents.values())

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for agents, cancelling...")
                for task in tasks:
                    task.cancel()

    async def _recover_from_crash(self) -> None:
        """Recover from a previous daemon crash.

        - Mark RUNNING work units as READY
        - Clean up orphaned worktrees
        """
        logger.info("Checking for recovery from previous crash...")

        # Get all RUNNING work units
        running_units = self.store.list_work_units(status=WorkUnitStatus.RUNNING)

        for unit in running_units:
            logger.warning(f"Found orphaned RUNNING work unit: {unit.chunk}")
            # Mark as READY to retry
            unit.status = WorkUnitStatus.READY
            unit.worktree = None
            unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(unit)

        # Clean up orphaned worktrees
        orphaned = self.worktree_manager.cleanup_orphaned_worktrees()
        for chunk in orphaned:
            unit = self.store.get_work_unit(chunk)
            if unit is None or unit.status != WorkUnitStatus.RUNNING:
                logger.info(f"Removing orphaned worktree for {chunk}")
                try:
                    self.worktree_manager.remove_worktree(chunk, remove_branch=False)
                except WorktreeError as e:
                    logger.warning(f"Failed to remove orphaned worktree: {e}")

    async def _dispatch_tick(self) -> None:
        """Execute one dispatch cycle.

        Checks for available slots and spawns agents for READY work units.
        Includes conflict checking to ensure safe parallelization.
        """
        async with self._lock:
            # Clean up completed tasks
            completed = [
                chunk
                for chunk, task in self._running_agents.items()
                if task.done()
            ]
            for chunk in completed:
                del self._running_agents[chunk]

            # Check available slots
            slots = self.available_slots
            if slots <= 0:
                return

            # Get ready queue
            ready_units = self.store.get_ready_queue(limit=slots)

            for unit in ready_units:
                if unit.chunk in self._running_agents:
                    continue  # Already running

                # Chunk: docs/chunks/orch_conflict_oracle - Check for conflicts before dispatch
                blocking_chunks = await self._check_conflicts(unit)
                if blocking_chunks:
                    logger.info(
                        f"Work unit {unit.chunk} blocked by conflicts: {blocking_chunks}"
                    )
                    continue  # Skip this unit, try next

                # Spawn agent task
                task = asyncio.create_task(
                    self._run_work_unit(unit),
                    name=f"agent-{unit.chunk}",
                )
                self._running_agents[unit.chunk] = task

                logger.info(
                    f"Dispatched agent for {unit.chunk} "
                    f"(phase={unit.phase.value}, priority={unit.priority})"
                )

    async def _run_work_unit(self, work_unit: WorkUnit) -> None:
        """Execute a single work unit.

        Args:
            work_unit: The work unit to execute
        """
        chunk = work_unit.chunk
        phase = work_unit.phase

        try:
            # Create worktree
            logger.info(f"Creating worktree for {chunk}")
            worktree_path = self.worktree_manager.create_worktree(chunk)

            # Chunk: docs/chunks/orch_activate_on_inject - Activate chunk in worktree
            # Activate the target chunk, displacing any existing IMPLEMENTING chunk
            try:
                displaced = activate_chunk_in_worktree(worktree_path, chunk)
                if displaced:
                    work_unit.displaced_chunk = displaced
                    logger.info(f"Stored displaced chunk '{displaced}' for later restoration")
            except ValueError as e:
                logger.error(f"Failed to activate chunk {chunk}: {e}")
                await self._mark_needs_attention(work_unit, f"Chunk activation failed: {e}")
                return

            # Update work unit to RUNNING
            work_unit.status = WorkUnitStatus.RUNNING
            work_unit.worktree = str(worktree_path)
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Set up logging
            log_dir = self.worktree_manager.get_log_path(chunk)
            log_callback = create_log_callback(chunk, phase, log_dir)

            # Chunk: docs/chunks/orch_attention_queue - Pass pending answer on resume
            # Check if there's a pending answer to inject
            pending_answer = work_unit.pending_answer
            if pending_answer:
                logger.info(f"Injecting pending answer for {chunk}")

            # Chunk: docs/chunks/orch_question_forward - Question callback for attention queue
            # Create callback to log when question is captured (actual handling in AgentResult)
            def question_callback(question_data: dict) -> None:
                question_text = question_data.get("question", "Unknown question")
                logger.info(f"Agent {chunk} asked question: {question_text[:100]}")

            # Run the agent
            logger.info(f"Running agent for {chunk} phase {phase.value}")
            result = await self.agent_runner.run_phase(
                chunk=chunk,
                phase=phase,
                worktree_path=worktree_path,
                resume_session_id=work_unit.session_id,
                answer=pending_answer,
                log_callback=log_callback,
                question_callback=question_callback,
            )

            # Clear pending_answer after successful dispatch
            if pending_answer:
                work_unit.pending_answer = None
                work_unit.updated_at = datetime.now(timezone.utc)
                self.store.update_work_unit(work_unit)

            # Handle result
            await self._handle_agent_result(work_unit, result)

        except WorktreeError as e:
            logger.error(f"Worktree error for {chunk}: {e}")
            await self._mark_needs_attention(work_unit, str(e))

        except Exception as e:
            logger.error(f"Unexpected error running {chunk}: {e}")
            await self._mark_needs_attention(work_unit, str(e))

        finally:
            # Remove from running agents
            async with self._lock:
                if chunk in self._running_agents:
                    del self._running_agents[chunk]

    async def _handle_agent_result(
        self,
        work_unit: WorkUnit,
        result: AgentResult,
    ) -> None:
        """Handle the result of an agent execution.

        Args:
            work_unit: The work unit that was executed
            result: Result from the agent
        """
        chunk = work_unit.chunk
        phase = work_unit.phase

        if result.suspended:
            # Agent asked a question - needs operator attention
            logger.info(f"Agent for {chunk} suspended (question queued)")
            work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
            work_unit.session_id = result.session_id
            # Chunk: docs/chunks/orch_attention_reason - Capture question as attention reason
            # Extract question text for attention_reason
            if result.question:
                question_text = result.question.get("question", "Agent asked a question")
            else:
                question_text = "Agent asked a question"
            work_unit.attention_reason = f"Question: {question_text}"
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

        elif result.error:
            # Agent failed
            logger.error(f"Agent for {chunk} failed: {result.error}")
            await self._mark_needs_attention(work_unit, result.error)

        elif result.completed:
            # Phase completed - advance to next phase or mark done
            logger.info(f"Agent for {chunk} completed phase {phase.value}")
            await self._advance_phase(work_unit)

        else:
            # Unknown state - mark needs attention
            logger.warning(f"Agent for {chunk} ended in unknown state")
            await self._mark_needs_attention(
                work_unit, "Agent ended in unknown state"
            )

    async def _advance_phase(self, work_unit: WorkUnit) -> None:
        """Advance a work unit to the next phase.

        Args:
            work_unit: The work unit to advance
        """
        chunk = work_unit.chunk
        current_phase = work_unit.phase

        # Phase progression
        next_phase_map = {
            WorkUnitPhase.GOAL: WorkUnitPhase.PLAN,
            WorkUnitPhase.PLAN: WorkUnitPhase.IMPLEMENT,
            WorkUnitPhase.IMPLEMENT: WorkUnitPhase.COMPLETE,
            WorkUnitPhase.COMPLETE: None,  # Done
        }

        next_phase = next_phase_map.get(current_phase)

        if next_phase is None:
            # Work unit complete - verify ACTIVE status before commit/merge
            logger.info(f"Work unit {chunk} completed all phases")

            # Get worktree path for verification
            worktree_path = self.worktree_manager.get_worktree_path(chunk)

            # Verify the chunk's GOAL.md has status: ACTIVE
            verification = verify_chunk_active_status(worktree_path, chunk)
            logger.info(
                f"Verification result for {chunk}: {verification.status.value}"
            )

            if verification.status == VerificationStatus.IMPLEMENTING:
                # Agent didn't finish marking ACTIVE - check retry count
                if work_unit.completion_retries >= self.config.max_completion_retries:
                    logger.warning(
                        f"Chunk {chunk} still IMPLEMENTING after "
                        f"{work_unit.completion_retries} retries"
                    )
                    await self._mark_needs_attention(
                        work_unit,
                        f"Chunk status still IMPLEMENTING after "
                        f"{work_unit.completion_retries} retries",
                    )
                    return

                # Resume the agent to finish marking ACTIVE
                work_unit.completion_retries += 1
                work_unit.updated_at = datetime.now(timezone.utc)
                self.store.update_work_unit(work_unit)

                logger.info(
                    f"Resuming agent for {chunk} to mark ACTIVE "
                    f"(attempt {work_unit.completion_retries})"
                )

                log_dir = self.worktree_manager.get_log_path(chunk)
                log_callback = create_log_callback(
                    chunk, WorkUnitPhase.COMPLETE, log_dir
                )

                try:
                    result = await self.agent_runner.resume_for_active_status(
                        chunk=chunk,
                        worktree_path=worktree_path,
                        session_id=work_unit.session_id,
                        log_callback=log_callback,
                    )

                    # Update session_id if it changed
                    if result.session_id:
                        work_unit.session_id = result.session_id
                        self.store.update_work_unit(work_unit)

                    # Re-handle the result (will call _advance_phase again if completed)
                    await self._handle_agent_result(work_unit, result)
                except Exception as e:
                    logger.error(f"Error resuming agent for {chunk}: {e}")
                    await self._mark_needs_attention(
                        work_unit, f"Resume for ACTIVE status failed: {e}"
                    )
                return

            elif verification.status == VerificationStatus.ERROR:
                logger.error(
                    f"Verification error for {chunk}: {verification.error}"
                )
                await self._mark_needs_attention(work_unit, verification.error)
                return

            # Status is ACTIVE - proceed with commit/merge
            logger.info(f"Chunk {chunk} verified ACTIVE, proceeding to commit/merge")

            # Chunk: docs/chunks/orch_mechanical_commit - Mechanical commit
            # Check for uncommitted changes that need to be committed
            if self.worktree_manager.has_uncommitted_changes(chunk):
                logger.info(f"Uncommitted changes detected for {chunk}, committing")
                try:
                    committed = self.worktree_manager.commit_changes(chunk)
                    if committed:
                        logger.info(f"Committed changes for {chunk}")
                    else:
                        logger.info(f"No changes to commit for {chunk}")
                except WorktreeError as e:
                    logger.error(f"Error committing changes for {chunk}: {e}")
                    await self._mark_needs_attention(work_unit, f"Commit error: {e}")
                    return

            # Chunk: docs/chunks/orch_activate_on_inject - Restore displaced chunk before merge
            # Restore any displaced chunk to IMPLEMENTING before the merge
            if work_unit.displaced_chunk:
                logger.info(
                    f"Restoring displaced chunk '{work_unit.displaced_chunk}' "
                    f"to IMPLEMENTING before merge"
                )
                restore_displaced_chunk(worktree_path, work_unit.displaced_chunk)

            # Remove the worktree (must be done before merge)
            try:
                self.worktree_manager.remove_worktree(chunk, remove_branch=False)
            except WorktreeError as e:
                logger.warning(f"Failed to remove worktree for {chunk}: {e}")

            # Merge the branch back to base if it has changes
            try:
                if self.worktree_manager.has_changes(chunk):
                    logger.info(
                        f"Merging {chunk} branch back to "
                        f"{self.worktree_manager.base_branch}"
                    )
                    self.worktree_manager.merge_to_base(chunk, delete_branch=True)
                else:
                    logger.info(f"No changes in {chunk}, skipping merge")
                    # Clean up the empty branch
                    branch = self.worktree_manager.get_branch_name(chunk)
                    if self.worktree_manager._branch_exists(branch):
                        import subprocess
                        subprocess.run(
                            ["git", "branch", "-d", branch],
                            cwd=self.project_dir,
                            capture_output=True,
                        )
            except WorktreeError as e:
                logger.error(f"Failed to merge {chunk} to base: {e}")
                # Mark as needs attention instead of done
                work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
                work_unit.updated_at = datetime.now(timezone.utc)
                self.store.update_work_unit(work_unit)
                return

            work_unit.status = WorkUnitStatus.DONE
            work_unit.session_id = None
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Chunk: docs/chunks/orch_blocked_lifecycle - Unblock dependents after completion
            self._unblock_dependents(chunk)

        else:
            # Advance to next phase
            logger.info(f"Work unit {chunk} advancing to phase {next_phase.value}")
            work_unit.phase = next_phase
            work_unit.status = WorkUnitStatus.READY
            work_unit.session_id = None
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Chunk: docs/chunks/orch_conflict_oracle - Re-analyze conflicts on phase advance
            # Phase advancement may provide more precise information for conflict analysis
            # (e.g., PLAN.md now exists with Location: lines)
            await self._reanalyze_conflicts(chunk)

    # Chunk: docs/chunks/orch_conflict_oracle - Conflict checking for dispatch
    async def _check_conflicts(self, work_unit: WorkUnit) -> list[str]:
        """Check for conflicts with active work units and return blocking chunks.

        Analyzes the work unit against all RUNNING and READY work units to
        detect potential conflicts. Returns immediately if any SERIALIZE
        verdict is found with an active blocker.

        For ASK_OPERATOR verdicts without an override, the work unit is marked
        as needing attention.

        Args:
            work_unit: The work unit to check

        Returns:
            List of chunk names that are blocking this work unit
        """
        from orchestrator.oracle import create_oracle

        chunk = work_unit.chunk
        blocking_chunks = []

        # Get all RUNNING and READY work units (except self)
        running_units = self.store.list_work_units(status=WorkUnitStatus.RUNNING)
        ready_units = self.store.list_work_units(status=WorkUnitStatus.READY)

        active_chunks = [
            u.chunk for u in running_units + ready_units
            if u.chunk != chunk
        ]

        if not active_chunks:
            return []

        # Create oracle for conflict analysis
        oracle = create_oracle(self.project_dir, self.store)

        for other_chunk in active_chunks:
            # Check cached verdict first
            verdict = work_unit.conflict_verdicts.get(other_chunk)

            if verdict is None:
                # No cached verdict - analyze conflict
                try:
                    analysis = oracle.analyze_conflict(chunk, other_chunk)
                    verdict = analysis.verdict.value

                    # Cache the verdict on both work units
                    work_unit.conflict_verdicts[other_chunk] = verdict
                    work_unit.updated_at = datetime.now(timezone.utc)
                    self.store.update_work_unit(work_unit)

                    # Also update the other work unit if it exists
                    other_unit = self.store.get_work_unit(other_chunk)
                    if other_unit:
                        other_unit.conflict_verdicts[chunk] = verdict
                        other_unit.updated_at = datetime.now(timezone.utc)
                        self.store.update_work_unit(other_unit)

                except Exception as e:
                    logger.error(f"Error analyzing conflict {chunk} vs {other_chunk}: {e}")
                    continue

            # Handle verdict - only block if the other chunk is RUNNING
            # READY vs READY conflicts don't block; we just need to resolve
            # before both try to run simultaneously
            is_other_running = other_chunk in [u.chunk for u in running_units]

            if verdict == ConflictVerdict.SERIALIZE.value:
                # Must serialize - only block if other is currently running
                if is_other_running:
                    blocking_chunks.append(other_chunk)
                    logger.info(f"Conflict: {chunk} blocked by running {other_chunk}")

            elif verdict == ConflictVerdict.ASK_OPERATOR.value:
                # Check if there's an override
                if work_unit.conflict_override:
                    # Override exists - use it
                    if work_unit.conflict_override == ConflictVerdict.SERIALIZE.value:
                        if is_other_running:
                            blocking_chunks.append(other_chunk)
                    # INDEPENDENT override means no blocking
                elif is_other_running:
                    # Other chunk is running and we don't know if it's safe
                    # Mark as needing attention so operator can decide
                    await self._mark_needs_attention(
                        work_unit,
                        f"Unresolved conflict with running {other_chunk}. "
                        f"Use 've orch resolve' to parallelize or serialize.",
                    )
                    blocking_chunks.append(other_chunk)
                # If other is just READY, log a warning but allow dispatch
                # The operator should resolve this but we don't block progress
                else:
                    logger.warning(
                        f"Unresolved conflict between {chunk} and {other_chunk}. "
                        f"Consider running 've orch resolve' before both start."
                    )

            # ConflictVerdict.INDEPENDENT - no blocking needed

        # Update blocked_by field if there are blockers
        if blocking_chunks and set(blocking_chunks) != set(work_unit.blocked_by):
            work_unit.blocked_by = list(set(work_unit.blocked_by + blocking_chunks))
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

        return blocking_chunks

    async def _reanalyze_conflicts(self, chunk: str) -> None:
        """Re-analyze conflicts for a chunk with updated information.

        Called when a chunk advances stages and more precise analysis is possible.
        Clears existing conflict analyses and triggers fresh analysis.

        Args:
            chunk: The chunk that advanced
        """
        # Clear existing conflicts for this chunk
        deleted = self.store.clear_conflicts_for_chunk(chunk)
        if deleted:
            logger.info(f"Cleared {deleted} stale conflict analyses for {chunk}")

        # Get the work unit
        work_unit = self.store.get_work_unit(chunk)
        if work_unit is None:
            return

        # Clear cached verdicts
        work_unit.conflict_verdicts = {}
        work_unit.updated_at = datetime.now(timezone.utc)
        self.store.update_work_unit(work_unit)

        # The next dispatch tick will trigger fresh analysis

    # Chunk: docs/chunks/orch_blocked_lifecycle - Automatic unblock when blockers complete
    def _unblock_dependents(self, completed_chunk: str) -> None:
        """Unblock work units that were blocked by a now-completed chunk.

        Called when a work unit transitions to DONE. For each work unit that
        has the completed chunk in its blocked_by list:
        1. Remove the completed chunk from blocked_by
        2. If blocked_by becomes empty and status is BLOCKED, transition to READY

        Args:
            completed_chunk: The chunk name that just completed
        """
        # Find all work units that have completed_chunk in their blocked_by
        blocked_units = self.store.list_blocked_by_chunk(completed_chunk)

        for unit in blocked_units:
            # Remove the completed chunk from blocked_by
            if completed_chunk in unit.blocked_by:
                unit.blocked_by.remove(completed_chunk)
                unit.updated_at = datetime.now(timezone.utc)

                # If no more blockers and status is BLOCKED, transition to READY
                if not unit.blocked_by and unit.status == WorkUnitStatus.BLOCKED:
                    logger.info(
                        f"Unblocking {unit.chunk} - blocker {completed_chunk} completed"
                    )
                    unit.status = WorkUnitStatus.READY
                else:
                    logger.info(
                        f"Removed {completed_chunk} from {unit.chunk}'s blocked_by "
                        f"(remaining: {unit.blocked_by})"
                    )

                self.store.update_work_unit(unit)

    # Chunk: docs/chunks/orch_attention_reason - Attention reason tracking for work units
    async def _mark_needs_attention(
        self,
        work_unit: WorkUnit,
        reason: str,
    ) -> None:
        """Mark a work unit as needing operator attention.

        Args:
            work_unit: The work unit
            reason: Reason for needing attention (stored in attention_reason field)
        """
        logger.warning(f"Work unit {work_unit.chunk} needs attention: {reason}")
        work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
        work_unit.attention_reason = reason
        work_unit.updated_at = datetime.now(timezone.utc)
        self.store.update_work_unit(work_unit)

    def get_running_chunks(self) -> list[str]:
        """Get list of currently running chunk names."""
        return list(self._running_agents.keys())


def create_scheduler(
    store: StateStore,
    project_dir: Path,
    config: Optional[OrchestratorConfig] = None,
    base_branch: Optional[str] = None,
) -> Scheduler:
    """Create a configured scheduler instance.

    Args:
        store: State store
        project_dir: Project directory
        config: Optional config (uses defaults if not provided)
        base_branch: Git branch to use as base for worktrees (uses current if None)

    Returns:
        Configured Scheduler instance
    """
    if config is None:
        config = OrchestratorConfig()

    worktree_manager = WorktreeManager(project_dir, base_branch=base_branch)
    agent_runner = AgentRunner(project_dir)

    return Scheduler(
        store=store,
        worktree_manager=worktree_manager,
        agent_runner=agent_runner,
        config=config,
        project_dir=project_dir,
    )
