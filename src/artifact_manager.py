"""ArtifactManager abstract base class for workflow artifacts.

# Chunk: docs/chunks/artifact_manager_base - Base class for artifact lifecycle management
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle

This module provides a generic base class that captures the shared pattern across
all four workflow artifact types (chunks, narratives, investigations, subsystems).
It eliminates duplicated code for:
- Artifact directory enumeration
- Frontmatter parsing
- Status access and updates
- Status transition validation

Each concrete manager (Chunks, Narratives, Investigations, Subsystems) subclasses
this base and specifies only artifact-specific configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from state_machine import StateMachine


# Type variables for frontmatter models and status enums
FrontmatterT = TypeVar("FrontmatterT", bound=BaseModel)
StatusT = TypeVar("StatusT", bound=StrEnum)


class ArtifactManager(ABC, Generic[FrontmatterT, StatusT]):
    """Abstract base class for workflow artifact managers.

    Provides common functionality for managing workflow artifacts including:
    - Directory enumeration
    - Frontmatter parsing
    - Status access and updates with transition validation

    Concrete implementations must define:
    - artifact_dir_name: str (e.g., "chunks", "narratives")
    - main_filename: str (e.g., "GOAL.md", "OVERVIEW.md")
    - frontmatter_model_class: type (Pydantic model for frontmatter)
    - status_enum: type (StrEnum for status values)
    - transition_map: dict (valid status transitions)
    """

    def __init__(self, project_dir: Path) -> None:
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        self._project_dir = Path(project_dir)
        self._state_machine: StateMachine | None = None

    @property
    def project_dir(self) -> Path:
        """Return the project root directory."""
        return self._project_dir

    @property
    @abstractmethod
    def artifact_dir_name(self) -> str:
        """Return the directory name for this artifact type (e.g., 'chunks')."""
        ...

    @property
    def artifact_type_name(self) -> str:
        """Return human-readable singular name for error messages.

        Defaults to capitalized singular form derived from artifact_dir_name.
        Override in subclasses if needed (e.g., for 'Chunk' vs 'chunks').
        """
        # Convert 'subsystems' -> 'Subsystem', 'chunks' -> 'Chunk', etc.
        name = self.artifact_dir_name.rstrip("s")  # Remove trailing 's'
        return name.capitalize()

    @property
    @abstractmethod
    def main_filename(self) -> str:
        """Return the main markdown filename (e.g., 'GOAL.md', 'OVERVIEW.md')."""
        ...

    @property
    @abstractmethod
    def frontmatter_model_class(self) -> type[FrontmatterT]:
        """Return the Pydantic model class for frontmatter validation."""
        ...

    @property
    @abstractmethod
    def status_enum(self) -> type[StatusT]:
        """Return the StrEnum class for status values."""
        ...

    @property
    @abstractmethod
    def transition_map(self) -> dict[StatusT, set[StatusT]]:
        """Return the valid status transitions dict."""
        ...

    @property
    def artifact_dir(self) -> Path:
        """Return the path to the artifacts directory."""
        return self._project_dir / "docs" / self.artifact_dir_name

    def _get_state_machine(self) -> StateMachine:
        """Get or create the StateMachine for transition validation."""
        if self._state_machine is None:
            self._state_machine = StateMachine(self.transition_map, self.status_enum)
        return self._state_machine

    def enumerate_artifacts(self) -> list[str]:
        """List artifact directory names.

        Returns:
            List of artifact directory names, or empty list if none exist.
        """
        if not self.artifact_dir.exists():
            return []
        return [f.name for f in self.artifact_dir.iterdir() if f.is_dir()]

    def get_artifact_path(self, artifact_id: str) -> Path:
        """Get the path to an artifact's directory.

        Args:
            artifact_id: The artifact directory name.

        Returns:
            Path to the artifact directory.
        """
        return self.artifact_dir / artifact_id

    def get_main_file_path(self, artifact_id: str) -> Path:
        """Get the path to an artifact's main markdown file.

        Args:
            artifact_id: The artifact directory name.

        Returns:
            Path to the main markdown file (GOAL.md or OVERVIEW.md).
        """
        return self.artifact_dir / artifact_id / self.main_filename

    def parse_frontmatter(self, artifact_id: str) -> FrontmatterT | None:
        """Parse and validate frontmatter for an artifact.

        Args:
            artifact_id: The artifact directory name.

        Returns:
            Validated frontmatter model if successful, None if:
            - Artifact directory doesn't exist
            - Main file doesn't exist
            - Frontmatter is malformed or fails validation
        """
        from frontmatter import parse_frontmatter

        main_path = self.get_main_file_path(artifact_id)
        if not main_path.exists():
            return None

        return parse_frontmatter(main_path, self.frontmatter_model_class)

    def get_status(self, artifact_id: str) -> StatusT:
        """Get the current status of an artifact.

        Args:
            artifact_id: The artifact directory name.

        Returns:
            The current status value.

        Raises:
            ValueError: If artifact not found or has invalid frontmatter.
        """
        frontmatter = self.parse_frontmatter(artifact_id)
        if frontmatter is None:
            raise ValueError(
                f"{self.artifact_type_name} '{artifact_id}' not found in docs/{self.artifact_dir_name}/"
            )
        return frontmatter.status

    def update_status(
        self, artifact_id: str, new_status: StatusT
    ) -> tuple[StatusT, StatusT]:
        """Update artifact status with transition validation.

        Args:
            artifact_id: The artifact directory name.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If artifact not found, invalid status, or invalid transition.
        """
        # Get current status
        current_status = self.get_status(artifact_id)

        # Validate the transition using StateMachine
        sm = self._get_state_machine()
        sm.validate_transition(current_status, new_status)

        # Update the frontmatter
        self._update_frontmatter(artifact_id, "status", new_status.value)

        return (current_status, new_status)

    def _update_frontmatter(
        self, artifact_id: str, field: str, value: Any
    ) -> None:
        """Update a single field in the artifact's frontmatter.

        Args:
            artifact_id: The artifact directory name.
            field: The frontmatter field name to update.
            value: The new value for the field.

        Raises:
            FileNotFoundError: If the main file doesn't exist.
            ValueError: If the file has no frontmatter.
        """
        from frontmatter import update_frontmatter_field

        main_path = self.get_main_file_path(artifact_id)
        update_frontmatter_field(main_path, field, value)
