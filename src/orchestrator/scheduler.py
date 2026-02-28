# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/orch_scheduling - Dispatch loop and work unit scheduling
# Chunk: docs/chunks/deferred_worktree_creation - Worktree creation at dispatch time
# Chunk: docs/chunks/explicit_deps_skip_oracle - Oracle bypass for explicit dependencies
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition on unblock
# Chunk: docs/chunks/orch_verify_active - ACTIVE status verification before commit/merge
# Chunk: docs/chunks/orch_task_detection - Scheduler factory with task_info parameter
# Chunk: docs/chunks/orch_attention_reason - Store and display reason for NEEDS_ATTENTION status
# Chunk: docs/chunks/orch_conflict_oracle - Conflict checking and re-analysis during dispatch
# Chunk: docs/chunks/orch_broadcast_invariant - WebSocket broadcasting invariant documentation
# Chunk: docs/chunks/scheduler_decompose - Decomposed into focused modules
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
# Chunk: docs/chunks/finalization_recovery - Crash recovery for incomplete finalization
"""Scheduler for dispatching work units to agents.

The scheduler runs a background loop that:
1. Checks for READY work units
2. Checks for conflicts with running/ready work units
3. Spawns agents up to max_agents slots
4. Updates work unit status based on agent outcomes
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
from orchestrator.agent import AgentRunner, create_log_callback, create_review_decision_hook
from orchestrator.models import (
    AgentResult,
    ConflictVerdict,
    OrchestratorConfig,
    ReviewToolDecision,
    TaskContextInfo,
    WorkUnit,
    WorkUnitPhase,
    WorkUnitStatus,
)
from orchestrator.state import StateStore, StaleWriteError
from orchestrator.websocket import broadcast_attention_update, broadcast_work_unit_update
# Chunk: docs/chunks/orch_merge_rebase_retry - Import is_merge_conflict_error for merge conflict detection
from orchestrator.worktree import WorktreeManager, WorktreeError, is_merge_conflict_error

# Chunk: docs/chunks/scheduler_decompose - Imports from extracted modules
from orchestrator.activation import (
    VerificationStatus,
    VerificationResult,
    verify_chunk_active_status,
    activate_chunk_in_worktree,
    restore_displaced_chunk,
)
from orchestrator.review_parsing import (
    load_reviewer_config,
)
from orchestrator.review_routing import (
    ReviewRoutingConfig,
    route_review_decision,
)
from orchestrator.retry import (
    is_retryable_api_error,
    is_session_limit_error,
    parse_reset_time,
)


logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """Exception raised for scheduler-related errors."""

    pass


# Chunk: docs/chunks/orch_manual_done_unblock - Module-level function for unblocking dependents
# Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition when blockers complete
# Chunk: docs/chunks/optimistic_locking - Optimistic locking for stale write detection
def unblock_dependents(store: StateStore, completed_chunk: str) -> None:
    """Unblock work units that were blocked by a now-completed chunk.

    This module-level function is called when a work unit transitions to DONE,
    either through the scheduler's normal flow or via manual API intervention.
    For each work unit that has the completed chunk in its blocked_by list:
    1. Remove the completed chunk from blocked_by
    2. If blocked_by becomes empty and status is BLOCKED or NEEDS_ATTENTION,
       transition to READY and clear attention_reason

    Uses optimistic locking to avoid overwriting concurrent API updates.
    On stale write, re-reads the work unit and retries.

    Args:
        store: The StateStore instance to use for querying and updating work units
        completed_chunk: The chunk name that just completed
    """
    # Find all work units that have completed_chunk in their blocked_by
    blocked_units = store.list_blocked_by_chunk(completed_chunk)

    for unit in blocked_units:
        # Retry loop for optimistic locking
        max_retries = 3
        for attempt in range(max_retries):
            # Capture expected timestamp before modification
            expected_updated_at = unit.updated_at

            # Remove the completed chunk from blocked_by
            if completed_chunk in unit.blocked_by:
                unit.blocked_by.remove(completed_chunk)
                unit.updated_at = datetime.now(timezone.utc)

                # If no more blockers and status is BLOCKED or NEEDS_ATTENTION,
                # transition to READY. Work units can be in NEEDS_ATTENTION when
                # they encountered a conflict that required serialization - once
                # the blocker completes, they should automatically become READY.
                if not unit.blocked_by and unit.status in (
                    WorkUnitStatus.BLOCKED,
                    WorkUnitStatus.NEEDS_ATTENTION,
                ):
                    logger.info(
                        f"Unblocking {unit.chunk} - blocker {completed_chunk} completed"
                    )
                    unit.status = WorkUnitStatus.READY
                    unit.attention_reason = None  # Clear stale reason
                else:
                    logger.info(
                        f"Removed {completed_chunk} from {unit.chunk}'s blocked_by "
                        f"(remaining: {unit.blocked_by})"
                    )

                try:
                    store.update_work_unit(unit, expected_updated_at=expected_updated_at)
                    break  # Success - exit retry loop
                except StaleWriteError:
                    if attempt == max_retries - 1:
                        logger.warning(
                            f"Failed to unblock {unit.chunk} after {max_retries} attempts "
                            f"due to concurrent modifications"
                        )
                    else:
                        logger.info(
                            f"Stale write unblocking {unit.chunk}, retrying "
                            f"(attempt {attempt + 2}/{max_retries})"
                        )
                        # Re-read the work unit for retry
                        fresh = store.get_work_unit(unit.chunk)
                        if fresh is None:
                            # Work unit was deleted - nothing to do
                            break
                        if completed_chunk not in fresh.blocked_by:
                            # Already unblocked by another process
                            break
                        unit = fresh
            else:
                # completed_chunk not in blocked_by - nothing to do
                break


# Chunk: docs/chunks/scheduler_decompose_methods - Adapter for ReviewRoutingCallbacks protocol
class _SchedulerReviewCallbacks:
    """Adapter implementing ReviewRoutingCallbacks for the Scheduler.

    This class adapts the Scheduler's methods to the ReviewRoutingCallbacks
    protocol, allowing the review_routing module to interact with the
    scheduler without direct coupling.
    """

    def __init__(self, scheduler: "Scheduler"):
        """Initialize with a reference to the scheduler.

        Args:
            scheduler: The Scheduler instance to delegate to
        """
        self._scheduler = scheduler

    async def advance_phase(self, work_unit: WorkUnit) -> None:
        """Advance work unit to the next phase."""
        await self._scheduler._advance_phase(work_unit)

    async def mark_needs_attention(self, work_unit: WorkUnit, reason: str) -> None:
        """Mark work unit as needing operator attention."""
        await self._scheduler._mark_needs_attention(work_unit, reason)

    def update_work_unit(self, work_unit: WorkUnit) -> None:
        """Persist work unit changes to the store."""
        self._scheduler.store.update_work_unit(work_unit)

    async def broadcast_work_unit_update(
        self, chunk: str, status: str, phase: str
    ) -> None:
        """Broadcast work unit status change via WebSocket."""
        await broadcast_work_unit_update(chunk=chunk, status=status, phase=phase)


# Chunk: docs/chunks/orch_broadcast_invariant - WebSocket broadcasting invariant documentation
class Scheduler:
    """Manages work unit scheduling and agent dispatch.

    The scheduler maintains a pool of running agents and dispatches
    work units from the ready queue when slots are available.

    INVARIANT - WebSocket Broadcasting:
        Every work unit state change MUST call broadcast_work_unit_update()
        after updating the database. This ensures the dashboard receives
        real-time notifications. State changes include:
        - READY → RUNNING (dispatch)
        - Phase advancement (READY with new phase)
        - RUNNING → NEEDS_ATTENTION (error/question)
        - Completion (DONE)

        Pattern:
            work_unit.status = WorkUnitStatus.RUNNING
            self.store.update_work_unit(work_unit)
            await broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )

        See also: src/orchestrator/api/work_units.py which follows this invariant.
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

    # Chunk: docs/chunks/persist_retry_state - Preserve retry backoff across daemon restarts
    async def _recover_from_crash(self) -> None:
        """Recover from a previous daemon crash.

        Recovery steps:
        1. Mark RUNNING work units as READY (for retry)
        2. Preserve retry backoff for units that were mid-retry
        3. Detect orphaned worktrees (respecting retain_worktree flag)
        4. Recover incomplete finalizations (Chunk: finalization_recovery)
           - Detect work units whose worktree was removed but merge wasn't completed
           - Auto-merge if possible, or escalate to NEEDS_ATTENTION on conflict
        """
        logger.info("Checking for recovery from previous crash...")

        # Get all RUNNING work units
        running_units = self.store.list_work_units(status=WorkUnitStatus.RUNNING)

        for unit in running_units:
            logger.warning(f"Found orphaned RUNNING work unit: {unit.chunk}")
            # Mark as READY to retry
            unit.status = WorkUnitStatus.READY
            unit.updated_at = datetime.now(timezone.utc)

            # Chunk: docs/chunks/phase_aware_recovery - Preserve worktree if still exists
            # Only clear the worktree reference if the worktree no longer exists.
            # This enables recovery to resume from the existing worktree rather than
            # recreating it and potentially hitting activation failures for post-PLAN phases.
            if unit.worktree and self.worktree_manager.worktree_exists(unit.chunk):
                logger.info(f"Preserving existing worktree for {unit.chunk}")
            else:
                unit.worktree = None

            # Preserve retry backoff across daemon restart
            if unit.api_retry_count > 0:
                backoff = self._compute_retry_backoff(unit.api_retry_count)
                unit.next_retry_at = datetime.now(timezone.utc) + backoff
                logger.info(
                    f"Preserving retry backoff for {unit.chunk} "
                    f"(attempt {unit.api_retry_count}, backoff {backoff.total_seconds():.1f}s)"
                )

            self.store.update_work_unit(unit)

        # Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
        # Detect orphaned worktrees but do NOT remove them automatically.
        # This preserves uncommitted work that would otherwise be lost.
        worktrees = self.worktree_manager.list_worktrees()
        retained_count = 0
        orphaned_count = 0

        for chunk in worktrees:
            unit = self.store.get_work_unit(chunk)
            if unit is not None and unit.status == WorkUnitStatus.RUNNING:
                # Active agent - skip counting
                continue
            if unit is not None and unit.retain_worktree:
                retained_count += 1
                logger.info(f"Found retained worktree for {chunk}")
            else:
                # No work unit, or work unit without retain_worktree
                orphaned_count += 1
                logger.info(f"Found orphaned worktree for {chunk}")

        total_retained = retained_count + orphaned_count
        if total_retained > 0:
            logger.warning(
                f"Found {total_retained} retained worktrees ({retained_count} retained, "
                f"{orphaned_count} orphaned). Use 've orch worktree list' to view and "
                f"'ve orch worktree prune' to clean up."
            )

        # Check warning threshold
        if total_retained > self.config.worktree_warning_threshold:
            logger.warning(
                f"Worktree count ({total_retained}) exceeds threshold "
                f"({self.config.worktree_warning_threshold}). Consider running "
                f"'ve orch worktree prune' to free up disk space."
            )

        # Chunk: docs/chunks/finalization_recovery - Recover incomplete finalizations
        # After handling RUNNING work units, check for work units that crashed during
        # finalization (worktree removed but merge not completed)
        incomplete_finalizations = self._find_incomplete_finalizations()
        for chunk in incomplete_finalizations:
            self._recover_incomplete_finalization(chunk)

    # Chunk: docs/chunks/finalization_recovery - Detect work units that crashed during finalization
    def _find_incomplete_finalizations(self) -> list[str]:
        """Find work units that crashed during finalization.

        Looks for work units where:
        - Status is DONE or phase is COMPLETE
        - The orch/<chunk> branch still exists
        - The worktree has been removed
        - The branch has commits ahead of base (merge wasn't completed)

        Returns:
            List of chunk names needing finalization recovery
        """
        incomplete = []

        # Get work units in terminal state that might have incomplete finalization
        # Check COMPLETE phase (normal finalization crash) or DONE status (rare case)
        complete_phase_units = [
            u for u in self.store.list_work_units()
            if u.phase == WorkUnitPhase.COMPLETE
        ]
        done_units = self.store.list_work_units(status=WorkUnitStatus.DONE)

        # Deduplicate by chunk name (a DONE unit in COMPLETE phase appears in both lists)
        seen_chunks: set[str] = set()
        candidates = []
        for unit in complete_phase_units + done_units:
            if unit.chunk not in seen_chunks:
                seen_chunks.add(unit.chunk)
                candidates.append(unit)

        for unit in candidates:
            chunk = unit.chunk
            branch = self.worktree_manager.get_branch_name(chunk)

            # Check if branch exists
            if not self.worktree_manager._branch_exists(branch):
                continue

            # Check if worktree has been removed (crash was after worktree removal)
            if self.worktree_manager.worktree_exists(chunk):
                continue  # Worktree still exists, not an incomplete finalization

            # Check if branch has changes ahead of base (merge wasn't completed)
            # If no changes, just need branch cleanup
            has_changes = self.worktree_manager.has_changes(chunk)
            if has_changes:
                logger.warning(
                    f"Found incomplete finalization for {chunk}: branch {branch} exists "
                    f"but merge not completed"
                )
                incomplete.append(chunk)
            else:
                # Branch exists but no changes - just clean up the branch
                logger.info(
                    f"Found dangling branch for {chunk} with no changes, cleaning up"
                )
                self.worktree_manager.delete_branch(chunk)

        return incomplete

    # Chunk: docs/chunks/finalization_recovery - Recover a single incomplete finalization
    def _recover_incomplete_finalization(self, chunk: str) -> None:
        """Recover a work unit that crashed during finalization.

        Attempts to complete the merge to base. On conflict, escalates
        to NEEDS_ATTENTION with a descriptive message.

        Args:
            chunk: The chunk name to recover
        """
        branch = self.worktree_manager.get_branch_name(chunk)

        try:
            # Attempt to complete the merge
            self.worktree_manager.merge_to_base(chunk, delete_branch=True)

            logger.warning(
                f"Auto-recovered incomplete finalization for {chunk}: merged to base"
            )

            # Get the work unit to update status and unblock dependents
            unit = self.store.get_work_unit(chunk)
            if unit is not None:
                # If still in COMPLETE phase, transition to DONE
                if unit.phase == WorkUnitPhase.COMPLETE and unit.status != WorkUnitStatus.DONE:
                    unit.status = WorkUnitStatus.DONE
                    unit.session_id = None
                    unit.api_retry_count = 0
                    unit.next_retry_at = None
                    unit.updated_at = datetime.now(timezone.utc)
                    self.store.update_work_unit(unit)

                    # Unblock any dependents that were waiting on this chunk
                    unblock_dependents(self.store, chunk)

        except WorktreeError as e:
            # Merge conflict - escalate to NEEDS_ATTENTION
            logger.warning(
                f"Incomplete finalization for {chunk} has merge conflict: "
                f"escalating to NEEDS_ATTENTION"
            )

            unit = self.store.get_work_unit(chunk)
            if unit is not None:
                reason = (
                    f"Crash during finalization left unmerged branch '{branch}'. "
                    f"Merge conflict: {e}. Manually complete the merge and run "
                    f"'git branch -d {branch}' to clean up."
                )
                unit.status = WorkUnitStatus.NEEDS_ATTENTION
                unit.attention_reason = reason
                unit.updated_at = datetime.now(timezone.utc)
                self.store.update_work_unit(unit)

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

                # Chunk: docs/chunks/orch_api_retry - Respect retry backoff timing
                if unit.next_retry_at is not None:
                    if datetime.now(timezone.utc) < unit.next_retry_at:
                        # Not ready yet - still in backoff period
                        continue
                    # Backoff period elapsed - clear the retry timestamp
                    unit.next_retry_at = None
                    unit.updated_at = datetime.now(timezone.utc)
                    self.store.update_work_unit(unit)

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

    # Chunk: docs/chunks/orch_question_forward - Provides question_callback to run_phase for forwarding
    # Chunk: docs/chunks/reviewer_decision_tool - Sets up review_decision_callback for REVIEW phase
    # Chunk: docs/chunks/orch_broadcast_invariant - Broadcast RUNNING status when work unit is dispatched
    # Chunk: docs/chunks/orch_activate_on_inject - Integration of chunk activation after worktree creation
    # Chunk: docs/chunks/orch_unblock_transition - Clear attention_reason and blocked_by when transitioning to RUNNING
    # Chunk: docs/chunks/orch_attention_queue - Pass pending_answer to agent runner on resume
    # Chunk: docs/chunks/optimistic_locking - Optimistic locking for dispatch transition
    # Chunk: docs/chunks/dispatch_toctou_guard - TOCTOU guard for status verification before worktree creation
    async def _run_work_unit(self, work_unit: WorkUnit) -> None:
        """Execute a single work unit.

        Args:
            work_unit: The work unit to execute
        """
        chunk = work_unit.chunk
        phase = work_unit.phase

        # TOCTOU Guard: Re-read the work unit from the store to verify it is still
        # in READY status. Between _dispatch_tick() reading the ready queue and this
        # method executing, an API-driven status change could have modified the work
        # unit (e.g., PATCH /work-units/{chunk} to NEEDS_ATTENTION). This guard
        # prevents wasted work (worktree creation, activation) when the work unit
        # is no longer eligible for dispatch.
        fresh_unit = self.store.get_work_unit(chunk)
        if fresh_unit is None:
            logger.warning(
                f"Skipping dispatch for {chunk}: work unit was deleted"
            )
            return
        if fresh_unit.status != WorkUnitStatus.READY:
            logger.warning(
                f"Skipping dispatch for {chunk}: status changed from READY to "
                f"{fresh_unit.status.value} before worktree creation"
            )
            return

        # Use the fresh work unit for the rest of the method
        work_unit = fresh_unit
        # Capture expected timestamp for optimistic locking
        expected_updated_at = work_unit.updated_at

        try:
            # Create worktree
            logger.info(f"Creating worktree for {chunk}")
            worktree_path = self.worktree_manager.create_worktree(chunk)
            # Chunk: docs/chunks/orch_worktree_cleanup - Worktree cleanup on activation failure
            worktree_created = True

            # Chunk: docs/chunks/phase_aware_recovery - Phase-aware activation check
            # Only activate during PLAN phase. Later phases already have the chunk
            # in the correct status on the branch (IMPLEMENTING, ACTIVE, HISTORICAL).
            # Calling activation on post-PLAN phases would fail because activation
            # expects FUTURE status.
            if phase == WorkUnitPhase.PLAN:
                try:
                    displaced = activate_chunk_in_worktree(worktree_path, chunk)
                    if displaced:
                        work_unit.displaced_chunk = displaced
                        logger.info(f"Stored displaced chunk '{displaced}' for later restoration")
                except ValueError as e:
                    logger.error(f"Failed to activate chunk {chunk}: {e}")
                    # Chunk: docs/chunks/orch_worktree_cleanup - Worktree cleanup on activation failure
                    # Clean up the worktree since we're returning early after creation
                    if worktree_created:
                        try:
                            self.worktree_manager.remove_worktree(chunk, remove_branch=False)
                            logger.info(f"Cleaned up worktree for {chunk} after activation failure")
                        except WorktreeError as cleanup_error:
                            logger.warning(
                                f"Failed to clean up worktree for {chunk}: {cleanup_error}"
                            )
                    await self._mark_needs_attention(work_unit, f"Chunk activation failed: {e}")
                    return

                # Chunk: docs/chunks/orch_rename_propagation - Capture baseline IMPLEMENTING chunks
                # After activation succeeds, snapshot the current IMPLEMENTING chunks
                # in the worktree. This enables detecting renames during the phase.
                from chunks import Chunks
                chunks_manager = Chunks(worktree_path)
                work_unit.baseline_implementing = chunks_manager.list_implementing_chunks()
                logger.info(
                    f"Captured baseline IMPLEMENTING chunks for {chunk}: "
                    f"{work_unit.baseline_implementing}"
                )

            # Update work unit to RUNNING with optimistic locking
            # If someone else (e.g., API) updated the work unit since we read it,
            # we should detect that and skip dispatch rather than overwrite their change.
            work_unit.status = WorkUnitStatus.RUNNING
            work_unit.worktree = str(worktree_path)
            work_unit.attention_reason = None  # Clear any stale reason
            work_unit.blocked_by = []  # Clear stale blockers
            work_unit.updated_at = datetime.now(timezone.utc)
            try:
                self.store.update_work_unit(
                    work_unit, expected_updated_at=expected_updated_at
                )
            except StaleWriteError as e:
                logger.warning(
                    f"Skipping dispatch for {chunk}: {e}. "
                    f"Work unit was modified by another process."
                )
                # Clean up the worktree we just created
                try:
                    self.worktree_manager.remove_worktree(chunk, remove_branch=False)
                except WorktreeError:
                    pass
                return

            # Broadcast via WebSocket so dashboard updates
            await broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )

            # Set up logging
            log_dir = self.worktree_manager.get_log_path(chunk)
            log_callback = create_log_callback(chunk, phase, log_dir)

            # Check if there's a pending answer to inject
            pending_answer = work_unit.pending_answer
            if pending_answer:
                logger.info(f"Injecting pending answer for {chunk}")

            # Create callback to log when question is captured (actual handling in AgentResult)
            def question_callback(question_data: dict) -> None:
                question_text = question_data.get("question", "Unknown question")
                logger.info(f"Agent {chunk} asked question: {question_text[:100]}")

            # Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
            # Create callback for review decision capture during REVIEW phase
            review_decision_callback = None
            if phase == WorkUnitPhase.REVIEW:
                def review_decision_callback(decision_data: ReviewToolDecision) -> None:
                    logger.info(
                        f"Agent {chunk} submitted review decision: {decision_data.decision}"
                    )

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
                review_decision_callback=review_decision_callback,
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

    # Chunk: docs/chunks/orch_question_forward - Transitions work unit to NEEDS_ATTENTION with question as attention_reason
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
            # Extract question text for attention_reason
            if result.question:
                question_text = result.question.get("question", "Agent asked a question")
            else:
                question_text = "Agent asked a question"
            work_unit.attention_reason = f"Question: {question_text}"
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Broadcast via WebSocket so dashboard updates
            await broadcast_attention_update(
                "added", work_unit.chunk, work_unit.attention_reason
            )
            await broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )

        elif result.error:
            # Agent failed - check error type in priority order:
            # 1. Session limit with parseable reset time -> schedule at reset time
            # 2. 5xx API error -> exponential backoff retry
            # 3. Other errors -> NEEDS_ATTENTION

            # Chunk: docs/chunks/orch_session_auto_resume - Session limit auto-retry
            if is_session_limit_error(result.error):
                reset_time = parse_reset_time(result.error)
                if reset_time is not None:
                    # Schedule retry at the reset time
                    await self._schedule_session_retry(work_unit, result, reset_time)
                    return
                # Fall through to NEEDS_ATTENTION if reset time not parseable

            # Chunk: docs/chunks/orch_api_retry - Automatic retry for 5xx API errors
            if (
                is_retryable_api_error(result.error)
                and work_unit.api_retry_count < self.config.api_retry_max_attempts
            ):
                # Schedule retry with exponential backoff
                await self._schedule_api_retry(work_unit, result)
            else:
                # Non-retryable error or retries exhausted
                if work_unit.api_retry_count >= self.config.api_retry_max_attempts:
                    logger.warning(
                        f"Exhausted {self.config.api_retry_max_attempts} API retries "
                        f"for {chunk}, marking NEEDS_ATTENTION"
                    )
                    reason = (
                        f"API error after {work_unit.api_retry_count} retries: "
                        f"{result.error[:200]}"
                    )
                else:
                    logger.error(f"Agent for {chunk} failed: {result.error}")
                    reason = result.error
                await self._mark_needs_attention(work_unit, reason)

        elif result.completed:
            # Phase completed - advance to next phase or mark done
            logger.info(f"Agent for {chunk} completed phase {phase.value}")

            # Chunk: docs/chunks/orch_rename_propagation - Check for rename before advancing phase
            # This must happen before _advance_phase so the work unit has the correct name
            worktree_path = self.worktree_manager.get_worktree_path(chunk)
            rename_result = self._detect_rename(work_unit, worktree_path)

            if rename_result is not None:
                old_name, new_name = rename_result
                try:
                    work_unit = await self._propagate_rename(work_unit, old_name, new_name)
                    # Update local variables to reflect the rename
                    chunk = work_unit.chunk
                    worktree_path = self.worktree_manager.get_worktree_path(chunk)
                    logger.info(f"Successfully propagated rename to {chunk}")
                except (WorktreeError, ValueError) as e:
                    logger.error(f"Failed to propagate rename {old_name} -> {new_name}: {e}")
                    await self._mark_needs_attention(
                        work_unit,
                        f"Rename propagation failed ({old_name} -> {new_name}): {e}"
                    )
                    return
            # Chunk: docs/chunks/rename_rebase_guard - Phase-aware ambiguity handling
            # Only check for "chunk disappeared" errors during GOAL/PLAN phases.
            # For post-PLAN phases, the work unit's chunk being absent from IMPLEMENTING
            # is expected (it's now ACTIVE after COMPLETE) — don't treat it as an error.
            elif (
                work_unit.phase in (WorkUnitPhase.GOAL, WorkUnitPhase.PLAN)
                and work_unit.baseline_implementing
                and chunk not in work_unit.baseline_implementing
            ):
                # Chunk disappeared but no clear rename detected - ambiguous situation
                # Check if it's because there are multiple new chunks
                from chunks import Chunks
                chunks_manager = Chunks(worktree_path)
                current_implementing = set(chunks_manager.list_implementing_chunks())
                baseline_set = set(work_unit.baseline_implementing)
                new_chunks = current_implementing - baseline_set

                if len(new_chunks) > 1:
                    await self._mark_needs_attention(
                        work_unit,
                        f"Ambiguous rename detected: chunk {chunk} disappeared but "
                        f"multiple new chunks found: {new_chunks}"
                    )
                    return
                elif len(new_chunks) == 0:
                    await self._mark_needs_attention(
                        work_unit,
                        f"Chunk {chunk} disappeared from worktree with no replacement"
                    )
                    return

            # Chunk: docs/chunks/orch_review_phase - Special handling for REVIEW phase to route to _handle_review_result
            # Chunk: docs/chunks/orch_pre_review_rebase - Special handling for REBASE phase outcomes
            if phase == WorkUnitPhase.REVIEW:
                # REVIEW phase needs special handling to parse the decision
                await self._handle_review_result(work_unit, worktree_path, result)
            elif phase == WorkUnitPhase.REBASE:
                # REBASE phase completed successfully - merge clean, tests pass
                # Advance to REVIEW
                await self._advance_phase(work_unit)
            else:
                await self._advance_phase(work_unit)

        else:
            # Unknown state - mark needs attention
            logger.warning(f"Agent for {chunk} ended in unknown state")
            await self._mark_needs_attention(
                work_unit, "Agent ended in unknown state"
            )

    # Chunk: docs/chunks/orch_review_phase - Updated phase progression map to include REVIEW between IMPLEMENT and COMPLETE
    # Chunk: docs/chunks/orch_blocked_lifecycle - Calls _unblock_dependents after work unit transitions to DONE
    # Chunk: docs/chunks/orch_activate_on_inject - Restore displaced chunk before merge when work unit completes
    # Chunk: docs/chunks/orch_broadcast_invariant - Broadcast READY status on phase advancement and DONE status on completion
    # Chunk: docs/chunks/orch_unblock_transition - Clear attention_reason when transitioning to READY on phase advancement
    # Chunk: docs/chunks/orch_pre_review_rebase - REBASE phase inserted between IMPLEMENT and REVIEW
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
            WorkUnitPhase.IMPLEMENT: WorkUnitPhase.REBASE,  # IMPLEMENT → REBASE
            WorkUnitPhase.REBASE: WorkUnitPhase.REVIEW,     # REBASE → REVIEW
            WorkUnitPhase.REVIEW: WorkUnitPhase.COMPLETE,   # REVIEW → COMPLETE (on APPROVE)
            WorkUnitPhase.COMPLETE: None,  # Done
        }

        next_phase = next_phase_map.get(current_phase)

        if next_phase is None:
            # Chunk: docs/chunks/scheduler_decompose_methods - Extracted completion logic
            await self._finalize_completed_work_unit(work_unit)
        else:
            # Advance to next phase
            logger.info(f"Work unit {chunk} advancing to phase {next_phase.value}")
            work_unit.phase = next_phase
            work_unit.status = WorkUnitStatus.READY
            work_unit.session_id = None
            work_unit.attention_reason = None  # Clear any stale reason
            # Chunk: docs/chunks/orch_api_retry - Reset retry state on successful phase advancement
            work_unit.api_retry_count = 0
            work_unit.next_retry_at = None
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Broadcast via WebSocket so dashboard updates
            await broadcast_work_unit_update(
                chunk=work_unit.chunk,
                status=work_unit.status.value,
                phase=work_unit.phase.value,
            )

            # Phase advancement may provide more precise information for conflict analysis
            # (e.g., PLAN.md now exists with Location: lines)
            await self._reanalyze_conflicts(chunk)

    # Chunk: docs/chunks/scheduler_decompose_methods - Extracted from _advance_phase
    async def _finalize_completed_work_unit(self, work_unit: WorkUnit) -> None:
        """Finalize a work unit that has completed all phases.

        This method handles the completion/cleanup logic:
        - Verify chunk ACTIVE status
        - Handle IMPLEMENTING status retries
        - Commit uncommitted changes
        - Restore displaced chunks
        - Handle retained worktrees vs finalization
        - Transition to DONE and unblock dependents

        Args:
            work_unit: The work unit to finalize
        """
        chunk = work_unit.chunk
        logger.info(f"Work unit {chunk} completed all phases")

        # Get worktree path for verification
        worktree_path = self.worktree_manager.get_worktree_path(chunk)

        # Verify the chunk's GOAL.md has reached a completed status
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

        # Status is post-IMPLEMENTING - proceed with commit/merge
        logger.info(f"Chunk {chunk} verified completed, proceeding to commit/merge")

        # Check for uncommitted changes that need to be committed
        # Chunk: docs/chunks/orch_mechanical_commit - Mechanical commit after COMPLETE phase
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

        # Restore any displaced chunk to IMPLEMENTING before the merge
        if work_unit.displaced_chunk:
            logger.info(
                f"Restoring displaced chunk '{work_unit.displaced_chunk}' "
                f"to IMPLEMENTING before merge"
            )
            restore_displaced_chunk(worktree_path, work_unit.displaced_chunk)

        # Chunk: docs/chunks/orch_worktree_retain - Retain worktrees after completion
        # If retain_worktree is set, skip worktree removal and merge.
        # The worktree stays on its branch for debugging/inspection.
        # Use `ve orch prune` to clean up retained worktrees later.
        if work_unit.retain_worktree:
            logger.info(
                f"Retaining worktree for {chunk} at {worktree_path} "
                f"(branch: {self.worktree_manager.get_branch_name(chunk)})"
            )
            # Skip worktree removal and merge - leave everything in place
        else:
            # Chunk: docs/chunks/orch_prune_consolidate - Use consolidated finalize_work_unit
            # Chunk: docs/chunks/orch_merge_rebase_retry - Detect and handle merge conflicts
            # Commit changes, remove worktree, merge to base, cleanup branch
            try:
                logger.info(f"Finalizing worktree for {chunk}")
                self.worktree_manager.finalize_work_unit(chunk)
            except WorktreeError as e:
                logger.error(f"Failed to finalize {chunk}: {e}")

                # Check if this is a merge conflict (vs other finalization errors)
                if is_merge_conflict_error(e):
                    # Attempt automatic retry via REBASE phase
                    logger.info(f"Detected merge conflict for {chunk}, attempting retry")
                    retry_initiated = await self._handle_merge_conflict_retry(work_unit, e)
                    if retry_initiated:
                        # Work unit is now in REBASE phase, don't mark as DONE
                        return
                    # If retry wasn't initiated (limit exceeded), fall through to return
                    # since _handle_merge_conflict_retry already marked NEEDS_ATTENTION
                    return

                # Non-merge-conflict error - mark as needs attention
                reason = f"Finalization failed: {e}"
                work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
                work_unit.attention_reason = reason
                work_unit.updated_at = datetime.now(timezone.utc)
                self.store.update_work_unit(work_unit)

                # Broadcast via WebSocket so dashboard updates
                await broadcast_attention_update("added", work_unit.chunk, reason)
                await broadcast_work_unit_update(
                    chunk=work_unit.chunk,
                    status=work_unit.status.value,
                    phase=work_unit.phase.value,
                )
                return

        work_unit.status = WorkUnitStatus.DONE
        work_unit.session_id = None
        # Chunk: docs/chunks/orch_api_retry - Reset retry state on successful completion
        work_unit.api_retry_count = 0
        work_unit.next_retry_at = None
        # Chunk: docs/chunks/orch_merge_rebase_retry - Reset merge conflict retry counter
        work_unit.merge_conflict_retries = 0
        work_unit.updated_at = datetime.now(timezone.utc)
        self.store.update_work_unit(work_unit)

        # Broadcast via WebSocket so dashboard updates
        await broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

        self._unblock_dependents(chunk)

    # Chunk: docs/chunks/orch_merge_rebase_retry - Handle merge conflict during finalization
    async def _handle_merge_conflict_retry(
        self,
        work_unit: WorkUnit,
        error: WorktreeError,
    ) -> bool:
        """Handle merge conflict during finalization by cycling back to REBASE.

        When a merge conflict occurs during finalization, this method:
        1. Checks if retry limit (2) has been reached
        2. If limit reached, escalates to NEEDS_ATTENTION
        3. Otherwise, recreates the worktree from the surviving branch
        4. Sets phase=REBASE, status=READY for another attempt
        5. Increments merge_conflict_retries counter

        Args:
            work_unit: The work unit that encountered the merge conflict
            error: The WorktreeError containing the merge conflict details

        Returns:
            True if retry was initiated, False if escalated to NEEDS_ATTENTION
        """
        chunk = work_unit.chunk
        max_merge_conflict_retries = 2  # Allow 2 retries (3 total attempts)

        if work_unit.merge_conflict_retries >= max_merge_conflict_retries:
            # Retry limit exceeded - escalate to NEEDS_ATTENTION
            logger.warning(
                f"Merge conflict retry limit exceeded for {chunk} "
                f"({work_unit.merge_conflict_retries} retries)"
            )
            reason = (
                f"Merge conflict during finalization after "
                f"{work_unit.merge_conflict_retries} retries. "
                f"Manual conflict resolution required. Error: {error}"
            )
            await self._mark_needs_attention(work_unit, reason)
            return False

        # Recreate the worktree from the surviving branch
        logger.info(
            f"Merge conflict during finalization for {chunk}, "
            f"recreating worktree for REBASE retry "
            f"(attempt {work_unit.merge_conflict_retries + 1})"
        )

        try:
            worktree_path = self.worktree_manager.recreate_worktree_from_branch(chunk)
        except WorktreeError as e:
            logger.error(f"Failed to recreate worktree for {chunk}: {e}")
            await self._mark_needs_attention(
                work_unit,
                f"Failed to recreate worktree for merge conflict retry: {e}",
            )
            return False

        # Set phase=REBASE, status=READY for another attempt
        work_unit.phase = WorkUnitPhase.REBASE
        work_unit.status = WorkUnitStatus.READY
        work_unit.worktree = str(worktree_path)
        work_unit.session_id = None  # New session for REBASE
        work_unit.merge_conflict_retries += 1
        work_unit.attention_reason = None  # Clear any stale reason
        # Reset API retry state for the new phase
        work_unit.api_retry_count = 0
        work_unit.next_retry_at = None
        work_unit.updated_at = datetime.now(timezone.utc)
        self.store.update_work_unit(work_unit)

        logger.info(
            f"Work unit {chunk} cycling back to REBASE phase "
            f"(merge_conflict_retries={work_unit.merge_conflict_retries})"
        )

        # Broadcast via WebSocket so dashboard updates
        await broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

        return True

    async def _check_conflicts(self, work_unit: WorkUnit) -> list[str]:
        """Check for conflicts with active work units and return blocking chunks.

        For work units with explicit_deps=True, conflict detection uses only the
        blocked_by list that was populated at injection time from declared
        dependencies. The oracle is bypassed entirely, trusting the explicit
        dependency declaration.

        For work units without explicit_deps, analyzes the work unit against all
        RUNNING and READY work units to detect potential conflicts. Returns
        immediately if any SERIALIZE verdict is found with an active blocker.

        For ASK_OPERATOR verdicts without an override, the work unit is marked
        as needing attention.

        Args:
            work_unit: The work unit to check

        Returns:
            List of chunk names that are blocking this work unit
        """
        chunk = work_unit.chunk
        blocking_chunks = []

        # Get all RUNNING and READY work units (except self)
        running_units = self.store.list_work_units(status=WorkUnitStatus.RUNNING)
        ready_units = self.store.list_work_units(status=WorkUnitStatus.READY)

        # When explicit_deps=True, skip oracle analysis entirely. The blocked_by list
        # was populated at injection time from declared dependencies - trust that
        # declaration rather than using heuristic detection.
        if work_unit.explicit_deps:
            # Only check if any chunk in blocked_by is currently RUNNING
            running_chunk_names = {u.chunk for u in running_units}
            for blocked_chunk in work_unit.blocked_by:
                if blocked_chunk in running_chunk_names:
                    blocking_chunks.append(blocked_chunk)
                    logger.info(
                        f"Explicit-deps work unit {chunk} blocked by running {blocked_chunk}"
                    )
            # No oracle analysis, no verdict caching - just blocked_by checks
            return blocking_chunks

        # Non-explicit work units use oracle-based conflict detection
        from orchestrator.oracle import create_oracle

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
    # Chunk: docs/chunks/orch_unblock_transition - Fix NEEDS_ATTENTION to READY transition when blockers complete
    def _unblock_dependents(self, completed_chunk: str) -> None:
        """Unblock work units that were blocked by a now-completed chunk.

        This is a thin wrapper around the module-level unblock_dependents function,
        kept for backward compatibility within the Scheduler class.

        Args:
            completed_chunk: The chunk name that just completed
        """
        unblock_dependents(self.store, completed_chunk)

    # Chunk: docs/chunks/orch_review_phase - Route work unit based on review decision (APPROVE/FEEDBACK/ESCALATE)
    # Chunk: docs/chunks/reviewer_decision_tool - ReviewDecision tool for explicit review decisions
    # Chunk: docs/chunks/scheduler_decompose_methods - Delegated to review_routing module
    async def _handle_review_result(
        self,
        work_unit: WorkUnit,
        worktree_path: Path,
        result: AgentResult,
    ) -> None:
        """Handle the result of a REVIEW phase execution.

        Thin wrapper that delegates to the review_routing module. Routes the
        work unit based on the review decision using a three-priority fallback
        chain for decision parsing.

        Args:
            work_unit: The work unit in REVIEW phase
            worktree_path: Path to the worktree
            result: AgentResult from the review phase
        """
        # Load reviewer config for loop detection settings
        reviewer_config = load_reviewer_config(self.project_dir)
        max_iterations = reviewer_config["loop_detection"]["max_iterations"]

        # Create routing configuration
        config = ReviewRoutingConfig(
            max_iterations=max_iterations,
            max_nudges=3,
        )

        # Create callbacks adapter that binds scheduler methods
        callbacks = _SchedulerReviewCallbacks(self)

        # Get log directory for fallback parsing
        log_dir = self.worktree_manager.get_log_path(work_unit.chunk)

        # Delegate to review_routing module
        await route_review_decision(
            work_unit=work_unit,
            worktree_path=worktree_path,
            result=result,
            config=config,
            callbacks=callbacks,
            log_dir=log_dir,
        )

    def _compute_retry_backoff(self, retry_count: int) -> timedelta:
        """Compute exponential backoff delay for a retry attempt.

        Uses the formula: delay = min(initial * 2^(retry_count-1), max_delay)

        Args:
            retry_count: Current retry attempt number (1-indexed)

        Returns:
            timedelta representing the backoff delay
        """
        delay_ms = min(
            self.config.api_retry_initial_delay_ms * (2 ** (retry_count - 1)),
            self.config.api_retry_max_delay_ms,
        )
        return timedelta(milliseconds=delay_ms)

    # Chunk: docs/chunks/orch_api_retry - Schedule retry with exponential backoff for 5xx API errors
    async def _schedule_api_retry(
        self,
        work_unit: WorkUnit,
        result: AgentResult,
    ) -> None:
        """Schedule a retry for a work unit that encountered a 5xx API error.

        Uses exponential backoff: delay = min(initial * 2^retry_count, max_delay)

        The work unit is transitioned back to READY with:
        - Incremented api_retry_count
        - next_retry_at set to the earliest time the retry should happen
        - pending_answer set to "continue" to resume the session
        - session_id preserved for session resumption

        Args:
            work_unit: The work unit that encountered the error
            result: The AgentResult containing the error and session_id
        """
        chunk = work_unit.chunk

        # Increment retry count
        work_unit.api_retry_count += 1

        # Calculate exponential backoff delay using helper
        backoff = self._compute_retry_backoff(work_unit.api_retry_count)

        # Set next retry time
        work_unit.next_retry_at = datetime.now(timezone.utc) + backoff

        # Set up session resumption with "continue" prompt
        work_unit.pending_answer = "continue"
        work_unit.session_id = result.session_id

        # Transition to READY for dispatch loop to pick up
        work_unit.status = WorkUnitStatus.READY
        work_unit.attention_reason = None  # Clear any stale reason
        work_unit.updated_at = datetime.now(timezone.utc)

        self.store.update_work_unit(work_unit)

        logger.info(
            f"Retrying {chunk} after API error (attempt {work_unit.api_retry_count}/"
            f"{self.config.api_retry_max_attempts}, backoff {backoff.total_seconds() * 1000:.0f}ms): "
            f"{result.error[:100] if result.error else 'unknown error'}"
        )

        # Broadcast status update
        await broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

    # Chunk: docs/chunks/orch_session_auto_resume - Schedule retry at session limit reset time
    async def _schedule_session_retry(
        self,
        work_unit: WorkUnit,
        result: AgentResult,
        reset_time: datetime,
    ) -> None:
        """Schedule a retry for a work unit that hit a session limit.

        Unlike _schedule_api_retry which uses exponential backoff, this method
        schedules the retry at a specific reset time extracted from the error
        message.

        The work unit is transitioned back to READY with:
        - next_retry_at set to the parsed reset time
        - pending_answer set to "continue" to resume the session
        - session_id preserved for session resumption

        Note: api_retry_count is NOT incremented since this is a different
        retry mechanism.

        Args:
            work_unit: The work unit that hit the session limit
            result: The AgentResult containing the error and session_id
            reset_time: The UTC datetime when the session limit resets
        """
        chunk = work_unit.chunk

        # Set retry time to the reset time
        work_unit.next_retry_at = reset_time

        # Set up session resumption with "continue" prompt
        work_unit.pending_answer = "continue"
        work_unit.session_id = result.session_id

        # Transition to READY for dispatch loop to pick up
        work_unit.status = WorkUnitStatus.READY
        work_unit.attention_reason = None  # Clear any stale reason
        work_unit.updated_at = datetime.now(timezone.utc)

        self.store.update_work_unit(work_unit)

        logger.info(
            f"Session limit hit for {chunk}, scheduled retry at {reset_time.isoformat()}"
        )

        # Broadcast status update
        await broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

    # Chunk: docs/chunks/orch_attention_reason - Setting attention_reason when marking work unit as NEEDS_ATTENTION
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

        # Broadcast via WebSocket so dashboard updates
        await broadcast_attention_update("added", work_unit.chunk, reason)
        await broadcast_work_unit_update(
            chunk=work_unit.chunk,
            status=work_unit.status.value,
            phase=work_unit.phase.value,
        )

    def get_running_chunks(self) -> list[str]:
        """Get list of currently running chunk names."""
        return list(self._running_agents.keys())

    # Chunk: docs/chunks/orch_rename_propagation - Propagate chunk rename through all data structures
    async def _propagate_rename(
        self, work_unit: WorkUnit, old_name: str, new_name: str
    ) -> WorkUnit:
        """Propagate a chunk rename through all orchestrator data structures.

        When a chunk is renamed during a phase (e.g., via `ve chunk suggest-prefix`),
        this method atomically updates:
        1. Database work_units table (INSERT + DELETE since chunk is PK)
        2. Filesystem .ve/chunks/{old}/ -> .ve/chunks/{new}/
        3. Git branch orch/{old} -> orch/{new}
        4. Cross-references in other work units (blocked_by, conflict_verdicts)
        5. conflict_analyses table entries
        6. In-memory _running_agents dict key
        7. The baseline_implementing snapshot (for subsequent phases)

        Args:
            work_unit: The work unit being renamed
            old_name: Original chunk name
            new_name: New chunk name

        Returns:
            Updated WorkUnit with new chunk name
        """
        logger.info(f"Propagating rename: {old_name} -> {new_name}")

        # Step 1: Git branch rename (do this first - easier to roll back if it fails)
        try:
            self.worktree_manager.rename_branch(old_name, new_name)
            logger.info(f"Renamed git branch orch/{old_name} -> orch/{new_name}")
        except WorktreeError as e:
            logger.error(f"Failed to rename git branch: {e}")
            raise

        # Step 2: Filesystem rename
        try:
            self.worktree_manager.rename_chunk_directory(old_name, new_name)
            logger.info(f"Renamed chunk directory .ve/chunks/{old_name} -> .ve/chunks/{new_name}")
        except WorktreeError as e:
            # Try to roll back git branch rename
            try:
                self.worktree_manager.rename_branch(new_name, old_name)
            except WorktreeError:
                pass
            logger.error(f"Failed to rename chunk directory: {e}")
            raise

        # Step 3: Database work unit rename
        try:
            renamed_unit = self.store.rename_work_unit(old_name, new_name)

            # Update the worktree path to point to the new location
            if renamed_unit.worktree:
                new_worktree_path = str(self.worktree_manager.get_worktree_path(new_name))
                renamed_unit.worktree = new_worktree_path
                renamed_unit.updated_at = datetime.now(timezone.utc)

            # Update baseline_implementing to use new name
            if old_name in renamed_unit.baseline_implementing:
                renamed_unit.baseline_implementing = [
                    new_name if c == old_name else c
                    for c in renamed_unit.baseline_implementing
                ]

            self.store.update_work_unit(renamed_unit)
            logger.info(f"Renamed work unit in database")
        except ValueError as e:
            # Database rename failed - try to roll back filesystem and git
            try:
                self.worktree_manager.rename_chunk_directory(new_name, old_name)
            except WorktreeError:
                pass
            try:
                self.worktree_manager.rename_branch(new_name, old_name)
            except WorktreeError:
                pass
            logger.error(f"Failed to rename work unit in database: {e}")
            raise

        # Step 4: Update cross-references in other work units
        blocked_by_updated = self.store.update_blocked_by_references(old_name, new_name)
        if blocked_by_updated > 0:
            logger.info(f"Updated blocked_by references in {blocked_by_updated} work units")

        verdicts_updated = self.store.update_conflict_verdicts_references(old_name, new_name)
        if verdicts_updated > 0:
            logger.info(f"Updated conflict_verdicts references in {verdicts_updated} work units")

        # Step 5: Update conflict_analyses table
        analyses_updated = self.store.update_conflict_analyses_references(old_name, new_name)
        if analyses_updated > 0:
            logger.info(f"Updated conflict_analyses references in {analyses_updated} rows")

        # Step 6: Update in-memory _running_agents dict
        async with self._lock:
            if old_name in self._running_agents:
                self._running_agents[new_name] = self._running_agents.pop(old_name)
                logger.info(f"Updated _running_agents dict key")

        # Broadcast via WebSocket
        await broadcast_work_unit_update(
            chunk=new_name,
            status=renamed_unit.status.value,
            phase=renamed_unit.phase.value,
        )

        logger.info(f"Rename propagation complete: {old_name} -> {new_name}")
        return renamed_unit

    # Chunk: docs/chunks/orch_rename_propagation - Detect chunk rename by comparing baseline to current
    # Chunk: docs/chunks/rename_rebase_guard - Phase-aware rename detection guard
    def _detect_rename(
        self, work_unit: WorkUnit, worktree_path: Path
    ) -> tuple[str, str] | None:
        """Detect if the work unit's chunk was renamed during the phase.

        Compares the current IMPLEMENTING chunks in the worktree against the
        baseline snapshot captured at worktree creation time. If the work unit's
        original chunk name is missing but a new IMPLEMENTING chunk exists,
        a rename occurred.

        IMPORTANT: Rename detection is only active during GOAL and PLAN phases.
        Renames only happen via `ve chunk suggest-prefix` during PLAN phase.
        For post-PLAN phases (IMPLEMENT, REBASE, REVIEW, COMPLETE), renames are
        not possible because:
        - The chunk directory has already been renamed (if at all)
        - After COMPLETE, the chunk status is ACTIVE, not IMPLEMENTING

        The work unit's identity (`work_unit.chunk`) is the source of truth for
        which chunk this work unit manages. We don't need to verify it's still
        IMPLEMENTING because we know exactly which chunk we're working with.

        Args:
            work_unit: The work unit to check
            worktree_path: Path to the worktree

        Returns:
            Tuple of (old_name, new_name) if a rename was detected,
            None if no rename or detection is ambiguous.

        The caller should handle ambiguous cases (zero or >1 new chunks)
        by marking the work unit as NEEDS_ATTENTION.
        """
        # Phase guard: renames only possible during GOAL and PLAN phases
        # Post-PLAN phases cannot have renames - skip detection entirely
        if work_unit.phase not in (WorkUnitPhase.GOAL, WorkUnitPhase.PLAN):
            return None

        from chunks import Chunks

        # If no baseline was captured, we can't detect renames
        if not work_unit.baseline_implementing:
            return None

        # Get current IMPLEMENTING chunks in the worktree
        chunks_manager = Chunks(worktree_path)
        current_implementing = set(chunks_manager.list_implementing_chunks())
        baseline_set = set(work_unit.baseline_implementing)

        # Check if the work unit's chunk is still present
        if work_unit.chunk in current_implementing:
            # No rename - chunk is still there
            return None

        # The work unit's chunk is missing. Check for new chunks.
        new_chunks = current_implementing - baseline_set

        if len(new_chunks) == 1:
            # Exactly one new chunk - this is our rename
            new_name = new_chunks.pop()
            logger.info(
                f"Detected rename: {work_unit.chunk} -> {new_name}"
            )
            return (work_unit.chunk, new_name)

        elif len(new_chunks) == 0:
            # Chunk disappeared entirely with no replacement
            logger.warning(
                f"Chunk {work_unit.chunk} disappeared from worktree with no replacement"
            )
            return None

        else:
            # Multiple new chunks - ambiguous, cannot determine which is the rename
            logger.warning(
                f"Ambiguous rename detection for {work_unit.chunk}: "
                f"multiple new chunks {new_chunks}"
            )
            return None


def create_scheduler(
    store: StateStore,
    project_dir: Path,
    config: Optional[OrchestratorConfig] = None,
    base_branch: Optional[str] = None,
    task_info: Optional[TaskContextInfo] = None,
) -> Scheduler:
    """Create a configured scheduler instance.

    Args:
        store: State store
        project_dir: Project directory (or task directory in task context)
        config: Optional config (uses defaults if not provided)
        base_branch: Git branch to use as base for worktrees (uses current if None)
        task_info: Task context information (None for single-repo mode)

    Returns:
        Configured Scheduler instance
    """
    if config is None:
        config = OrchestratorConfig()

    # Pass task_info to WorktreeManager for multi-repo support
    worktree_manager = WorktreeManager(
        project_dir,
        base_branch=base_branch,
        task_info=task_info,
    )
    agent_runner = AgentRunner(project_dir)

    return Scheduler(
        store=store,
        worktree_manager=worktree_manager,
        agent_runner=agent_runner,
        config=config,
        project_dir=project_dir,
    )
