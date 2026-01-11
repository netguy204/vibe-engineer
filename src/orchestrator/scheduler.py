# Chunk: docs/chunks/orch_scheduling - Orchestrator scheduling layer
# Chunk: docs/chunks/orch_verify_active - ACTIVE status verification
"""Scheduler for dispatching work units to agents.

The scheduler runs a background loop that:
1. Checks for READY work units
2. Spawns agents up to max_agents slots
3. Updates work unit status based on agent outcomes
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

from orchestrator.agent import AgentRunner, create_log_callback
from orchestrator.models import (
    AgentResult,
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


def verify_chunk_active_status(worktree_path: Path, chunk: str) -> VerificationResult:
    """Verify that a chunk's GOAL.md has status: ACTIVE.

    Reads the chunk's GOAL.md from the worktree and parses the frontmatter
    to check the status field.

    Args:
        worktree_path: Path to the worktree containing the chunk
        chunk: The chunk directory name

    Returns:
        VerificationResult indicating ACTIVE, IMPLEMENTING, or ERROR
    """
    goal_path = worktree_path / "docs" / "chunks" / chunk / "GOAL.md"

    if not goal_path.exists():
        return VerificationResult(
            status=VerificationStatus.ERROR,
            error=f"GOAL.md not found at {goal_path}",
        )

    try:
        content = goal_path.read_text()

        # Extract YAML frontmatter (between --- markers)
        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error="No YAML frontmatter found in GOAL.md",
            )

        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        if frontmatter is None:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error="Empty YAML frontmatter in GOAL.md",
            )

        status = frontmatter.get("status")
        if status is None:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error="No 'status' field in GOAL.md frontmatter",
            )

        if status == "ACTIVE":
            return VerificationResult(status=VerificationStatus.ACTIVE)
        elif status == "IMPLEMENTING":
            return VerificationResult(status=VerificationStatus.IMPLEMENTING)
        else:
            # Other statuses like FUTURE, SUPERSEDED, etc. are unexpected here
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error=f"Unexpected status '{status}' in GOAL.md (expected ACTIVE)",
            )

    except yaml.YAMLError as e:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            error=f"Failed to parse YAML frontmatter: {e}",
        )
    except Exception as e:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            error=f"Error reading GOAL.md: {e}",
        )


class SchedulerError(Exception):
    """Exception raised for scheduler-related errors."""

    pass


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

            # Update work unit to RUNNING
            work_unit.status = WorkUnitStatus.RUNNING
            work_unit.worktree = str(worktree_path)
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

            # Set up logging
            log_dir = self.worktree_manager.get_log_path(chunk)
            log_callback = create_log_callback(chunk, phase, log_dir)

            # Run the agent
            logger.info(f"Running agent for {chunk} phase {phase.value}")
            result = await self.agent_runner.run_phase(
                chunk=chunk,
                phase=phase,
                worktree_path=worktree_path,
                resume_session_id=work_unit.session_id,
                log_callback=log_callback,
            )

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

            # Check for uncommitted changes that need to be committed
            if self.worktree_manager.has_uncommitted_changes(chunk):
                logger.info(
                    f"Uncommitted changes detected for {chunk}, running commit phase"
                )
                # Run the /commit skill to properly commit changes
                log_dir = self.worktree_manager.get_log_path(chunk)
                log_callback = create_log_callback(
                    chunk, WorkUnitPhase.COMPLETE, log_dir
                )

                try:
                    result = await self.agent_runner.run_commit(
                        chunk=chunk,
                        worktree_path=worktree_path,
                        log_callback=log_callback,
                    )
                    if not result.completed:
                        logger.warning(f"Commit failed for {chunk}: {result.error}")
                        await self._mark_needs_attention(
                            work_unit, f"Commit failed: {result.error}"
                        )
                        return
                except Exception as e:
                    logger.error(f"Error running commit for {chunk}: {e}")
                    await self._mark_needs_attention(work_unit, f"Commit error: {e}")
                    return

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

        else:
            # Advance to next phase
            logger.info(f"Work unit {chunk} advancing to phase {next_phase.value}")
            work_unit.phase = next_phase
            work_unit.status = WorkUnitStatus.READY
            work_unit.session_id = None
            work_unit.updated_at = datetime.now(timezone.utc)
            self.store.update_work_unit(work_unit)

    async def _mark_needs_attention(
        self,
        work_unit: WorkUnit,
        reason: str,
    ) -> None:
        """Mark a work unit as needing operator attention.

        Args:
            work_unit: The work unit
            reason: Reason for needing attention
        """
        logger.warning(f"Work unit {work_unit.chunk} needs attention: {reason}")
        work_unit.status = WorkUnitStatus.NEEDS_ATTENTION
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
