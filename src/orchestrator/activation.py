# Subsystem: docs/subsystems/orchestrator - Parallel agent orchestration
# Chunk: docs/chunks/scheduler_decompose - Extracted from scheduler.py for single-responsibility
# Chunk: docs/chunks/orch_verify_active - VerificationStatus, VerificationResult, verify_chunk_active_status
"""Chunk activation lifecycle management.

This module handles the activation of chunks in worktrees, including:
- Verifying chunk ACTIVE status before commit/merge
- Activating target chunks by setting status to IMPLEMENTING
- Displacing and restoring chunks that were temporarily demoted

Extracted from scheduler.py to keep the scheduler focused on dispatch logic.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional

from chunks import Chunks
from frontmatter import update_frontmatter_field
from models import ChunkStatus
from models.chunk import VALID_CHUNK_TRANSITIONS

logger = logging.getLogger(__name__)


class VerificationStatus(StrEnum):
    """Result of verifying chunk completion status."""

    COMPLETED = "COMPLETED"  # Post-IMPLEMENTING status, proceed with commit/merge
    IMPLEMENTING = "IMPLEMENTING"  # Still IMPLEMENTING, needs retry
    ERROR = "ERROR"  # Error parsing or reading GOAL.md


@dataclass
class VerificationResult:
    """Result from verifying chunk's GOAL.md status."""

    status: VerificationStatus
    error: Optional[str] = None


def _is_post_implementing(status: ChunkStatus) -> bool:
    """Check if a chunk status is reachable from IMPLEMENTING in the state machine.

    Returns True for ACTIVE, SUPERSEDED, and HISTORICAL — any status that
    indicates the chunk has moved past the IMPLEMENTING phase.
    """
    reachable: set[ChunkStatus] = set()
    frontier = set(VALID_CHUNK_TRANSITIONS.get(ChunkStatus.IMPLEMENTING, set()))
    while frontier - reachable:
        reachable |= frontier
        frontier = {t for s in frontier for t in VALID_CHUNK_TRANSITIONS.get(s, set())}
    return status in reachable


# Chunk: docs/chunks/orch_activate_on_inject - Refactored to use Chunks class for frontmatter parsing
def verify_chunk_active_status(worktree_path: Path, chunk: str) -> VerificationResult:
    """Verify that a chunk's GOAL.md has moved past IMPLEMENTING.

    Checks whether the chunk status is reachable from IMPLEMENTING in
    the chunk state machine (ACTIVE, SUPERSEDED, HISTORICAL). IMPLEMENTING
    means the agent hasn't finished yet; FUTURE is unexpected at this point.

    Args:
        worktree_path: Path to the worktree containing the chunk
        chunk: The chunk directory name

    Returns:
        VerificationResult indicating COMPLETED, IMPLEMENTING, or ERROR
    """
    chunks = Chunks(worktree_path)

    try:
        frontmatter = chunks.parse_chunk_frontmatter(chunk)

        if frontmatter is None:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error=f"Chunk '{chunk}' not found or GOAL.md missing",
            )

        if _is_post_implementing(frontmatter.status):
            return VerificationResult(status=VerificationStatus.COMPLETED)
        elif frontmatter.status == ChunkStatus.IMPLEMENTING:
            return VerificationResult(status=VerificationStatus.IMPLEMENTING)
        else:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error=(
                    f"Unexpected status '{frontmatter.status.value}' in GOAL.md"
                    f" (expected post-IMPLEMENTING status)"
                ),
            )

    except Exception as e:
        return VerificationResult(
            status=VerificationStatus.ERROR,
            error=f"Error reading GOAL.md: {e}",
        )


# Chunk: docs/chunks/orch_activate_on_inject - Activate target chunk in worktree, displacing any existing IMPLEMENTING chunk
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


# Chunk: docs/chunks/orch_activate_on_inject - Restore a displaced chunk back to IMPLEMENTING before merge
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
