"""StateMachine for workflow artifact status transitions.

# Chunk: docs/chunks/artifact_manager_base - Reusable state machine for artifact lifecycle
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

This module provides a reusable StateMachine class that validates status transitions
for workflow artifacts (chunks, narratives, investigations, subsystems). It eliminates
duplicated transition validation logic across the four artifact managers.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar


# Type variable for status enums
StatusT = TypeVar("StatusT", bound=StrEnum)


class StateMachine:
    """Validates status transitions for workflow artifacts.

    Encapsulates transition validation logic that was previously duplicated
    across Chunks, Narratives, Investigations, and Subsystems managers.

    Usage:
        from models import ChunkStatus, VALID_CHUNK_TRANSITIONS
        sm = StateMachine(VALID_CHUNK_TRANSITIONS, ChunkStatus)
        sm.validate_transition(current_status, new_status)  # Raises on invalid
    """

    def __init__(
        self,
        transition_map: dict[StatusT, set[StatusT]],
        status_enum: type[StatusT],
    ) -> None:
        """Initialize with transition rules.

        Args:
            transition_map: Dict mapping each status to the set of valid next statuses.
                           Empty set indicates a terminal state.
            status_enum: The StrEnum type for status values (for error messages).
        """
        self._transition_map = transition_map
        self._status_enum = status_enum

    def validate_transition(self, current: StatusT, new: StatusT) -> None:
        """Validate a status transition.

        Args:
            current: The current status.
            new: The new status to transition to.

        Raises:
            ValueError: If the transition is not valid, with a descriptive message
                       that includes either the list of valid transitions or
                       indicates that the current state is terminal.
        """
        valid_transitions = self._transition_map.get(current, set())

        if new in valid_transitions:
            return  # Valid transition

        # Build error message
        if not valid_transitions:
            # Terminal state
            raise ValueError(
                f"Cannot transition from {current.value} to {new.value}. "
                f"{current.value} is a terminal state with no valid transitions"
            )
        else:
            # Non-terminal state with valid transitions that don't include new
            valid_names = sorted(s.value for s in valid_transitions)
            valid_str = ", ".join(valid_names)
            raise ValueError(
                f"Cannot transition from {current.value} to {new.value}. "
                f"Valid transitions: {valid_str}"
            )
