"""Migrations module - business logic for repository migration management."""

from __future__ import annotations

import pathlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, BeforeValidator, ValidationError
import yaml


def _coerce_datetime_to_str(v):
    """Coerce datetime to ISO string for frontmatter fields."""
    if isinstance(v, datetime):
        return v.isoformat()
    return v


TimestampStr = Annotated[str, BeforeValidator(_coerce_datetime_to_str)]

from template_system import ActiveMigration, TemplateContext, render_to_directory

if TYPE_CHECKING:
    pass


class MigrationStatus(str, Enum):
    """Valid migration status values."""

    ANALYZING = "ANALYZING"
    REFINING = "REFINING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    ABANDONED = "ABANDONED"


class SourceType(str, Enum):
    """Valid source type values for migrations."""

    CHUNKS = "chunks"
    CODE_ONLY = "code_only"


# Valid status transitions
VALID_MIGRATION_TRANSITIONS: dict[MigrationStatus, set[MigrationStatus]] = {
    MigrationStatus.ANALYZING: {
        MigrationStatus.REFINING,
        MigrationStatus.PAUSED,
        MigrationStatus.ABANDONED,
    },
    MigrationStatus.REFINING: {
        MigrationStatus.EXECUTING,
        MigrationStatus.ANALYZING,  # Can go back if more analysis needed
        MigrationStatus.PAUSED,
        MigrationStatus.ABANDONED,
    },
    MigrationStatus.EXECUTING: {
        MigrationStatus.COMPLETED,
        MigrationStatus.PAUSED,
        MigrationStatus.ABANDONED,
    },
    MigrationStatus.COMPLETED: set(),  # Terminal state
    MigrationStatus.PAUSED: {
        MigrationStatus.ANALYZING,
        MigrationStatus.REFINING,
        MigrationStatus.EXECUTING,
        MigrationStatus.ABANDONED,
    },
    MigrationStatus.ABANDONED: {
        MigrationStatus.ANALYZING,  # Can restart
    },
}


class MigrationFrontmatter(BaseModel):
    """Pydantic model for MIGRATION.md frontmatter validation."""

    status: MigrationStatus
    source_type: SourceType
    current_phase: int
    phases_completed: list[int] = []
    last_activity: TimestampStr
    started: TimestampStr
    completed: TimestampStr | None = None
    chunks_analyzed: int = 0
    subsystems_proposed: int = 0
    subsystems_approved: int = 0
    questions_pending: int = 0
    questions_resolved: int = 0
    pause_reason: str | None = None
    paused_by: str | None = None
    paused_at: TimestampStr | None = None
    resume_instructions: str | None = None


class Migrations:
    """Utility class for managing repository migrations.

    Provides methods for creating, tracking, and managing migrations
    from chunk-based to subsystem-based documentation.
    """

    def __init__(self, project_dir: pathlib.Path):
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        self.project_dir = project_dir

    @property
    def migrations_dir(self) -> pathlib.Path:
        """Return the path to the migrations directory."""
        return self.project_dir / "docs" / "migrations"

    @property
    def chunks_dir(self) -> pathlib.Path:
        """Return the path to the chunks directory."""
        return self.project_dir / "docs" / "chunks"

    @property
    def archive_dir(self) -> pathlib.Path:
        """Return the path to the archive directory."""
        return self.project_dir / "docs" / "archive" / "chunks"

    def enumerate_migrations(self) -> list[str]:
        """List migration directory names.

        Returns:
            List of migration directory names, or empty list if none exist.
        """
        if not self.migrations_dir.exists():
            return []
        return [f.name for f in self.migrations_dir.iterdir() if f.is_dir()]

    def get_migration_dir(self, migration_type: str) -> pathlib.Path:
        """Get path to a specific migration directory.

        Args:
            migration_type: Type of migration (e.g., "chunks_to_subsystems")

        Returns:
            Path to the migration directory.
        """
        return self.migrations_dir / migration_type

    def migration_exists(self, migration_type: str) -> bool:
        """Check if a migration exists.

        Args:
            migration_type: Type of migration

        Returns:
            True if migration directory and MIGRATION.md exist.
        """
        migration_dir = self.get_migration_dir(migration_type)
        return (migration_dir / "MIGRATION.md").exists()

    def detect_source_type(self) -> SourceType:
        """Detect whether repository has chunks or is code-only.

        Returns:
            SourceType.CHUNKS if docs/chunks/ has chunk directories,
            SourceType.CODE_ONLY otherwise.
        """
        if not self.chunks_dir.exists():
            return SourceType.CODE_ONLY

        # Check for actual chunk directories (with GOAL.md)
        for item in self.chunks_dir.iterdir():
            if item.is_dir() and (item / "GOAL.md").exists():
                return SourceType.CHUNKS

        return SourceType.CODE_ONLY

    def parse_migration_frontmatter(
        self, migration_type: str
    ) -> MigrationFrontmatter | None:
        """Parse and validate MIGRATION.md frontmatter.

        Args:
            migration_type: Type of migration

        Returns:
            Validated MigrationFrontmatter if successful, None otherwise.
        """
        migration_path = self.get_migration_dir(migration_type) / "MIGRATION.md"
        if not migration_path.exists():
            return None

        content = migration_path.read_text()

        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter_data = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter_data, dict):
                return None
            return MigrationFrontmatter.model_validate(frontmatter_data)
        except (yaml.YAMLError, ValidationError):
            return None

    def create_migration(
        self,
        migration_type: str = "chunks_to_subsystems",
    ) -> pathlib.Path:
        """Create a new migration directory with MIGRATION.md template.

        Args:
            migration_type: Type of migration (default: chunks_to_subsystems)

        Returns:
            Path to created migration directory.

        Raises:
            ValueError: If a migration of this type already exists.
        """
        if self.migration_exists(migration_type):
            raise ValueError(
                f"Migration '{migration_type}' already exists. "
                "Use 'resume' to continue or 'abandon' to restart."
            )

        # Detect source type
        source_type = self.detect_source_type()

        # Create migration directory structure
        migration_dir = self.get_migration_dir(migration_type)
        migration_dir.mkdir(parents=True, exist_ok=True)
        (migration_dir / "analysis").mkdir(exist_ok=True)
        (migration_dir / "proposals").mkdir(exist_ok=True)
        (migration_dir / "questions").mkdir(exist_ok=True)

        # Create migration context
        migration = ActiveMigration(
            migration_type=migration_type,
            source_type=source_type.value,
            _project_dir=self.project_dir,
        )
        context = TemplateContext(active_migration=migration)

        # Get current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        # Render template to directory (each migration type has its own template)
        render_to_directory(
            f"migrations/{migration_type}",
            migration_dir,
            context=context,
            source_type=source_type.value,
            timestamp=timestamp,
        )

        return migration_dir

    def get_status(self, migration_type: str) -> MigrationStatus:
        """Get the current status of a migration.

        Args:
            migration_type: Type of migration

        Returns:
            The current MigrationStatus.

        Raises:
            ValueError: If migration not found or has invalid frontmatter.
        """
        frontmatter = self.parse_migration_frontmatter(migration_type)
        if frontmatter is None:
            raise ValueError(
                f"Migration '{migration_type}' not found in docs/migrations/"
            )
        return frontmatter.status

    def update_status(
        self,
        migration_type: str,
        new_status: MigrationStatus,
        pause_reason: str | None = None,
        resume_instructions: str | None = None,
    ) -> tuple[MigrationStatus, MigrationStatus]:
        """Update migration status with transition validation.

        Args:
            migration_type: Type of migration
            new_status: The new status to transition to
            pause_reason: Reason for pausing (if transitioning to PAUSED)
            resume_instructions: Instructions for resuming (if transitioning to PAUSED)

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If migration not found, invalid status, or invalid transition.
        """
        current_status = self.get_status(migration_type)

        # Validate the transition
        valid_transitions = VALID_MIGRATION_TRANSITIONS.get(current_status, set())
        if new_status not in valid_transitions:
            valid_names = sorted(s.value for s in valid_transitions)
            if valid_names:
                valid_str = ", ".join(valid_names)
                raise ValueError(
                    f"Cannot transition from {current_status.value} to {new_status.value}. "
                    f"Valid transitions: {valid_str}"
                )
            else:
                raise ValueError(
                    f"Cannot transition from {current_status.value} to {new_status.value}. "
                    f"{current_status.value} is a terminal state with no valid transitions"
                )

        # Update the frontmatter
        updates = {
            "status": new_status.value,
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        if new_status == MigrationStatus.PAUSED:
            updates["pause_reason"] = pause_reason
            updates["paused_by"] = "human"
            updates["paused_at"] = datetime.now(timezone.utc).isoformat()
            updates["resume_instructions"] = resume_instructions
        elif new_status == MigrationStatus.COMPLETED:
            updates["completed"] = datetime.now(timezone.utc).isoformat()

        self._update_migration_frontmatter(migration_type, updates)

        return (current_status, new_status)

    def update_phase(
        self,
        migration_type: str,
        phase: int,
        completed: bool = False,
    ) -> None:
        """Update the current phase of a migration.

        Args:
            migration_type: Type of migration
            phase: The phase number
            completed: Whether the phase is completed
        """
        frontmatter = self.parse_migration_frontmatter(migration_type)
        if frontmatter is None:
            raise ValueError(f"Migration '{migration_type}' not found")

        updates = {
            "current_phase": phase,
            "last_activity": datetime.now(timezone.utc).isoformat(),
        }

        if completed and phase not in frontmatter.phases_completed:
            updates["phases_completed"] = frontmatter.phases_completed + [phase]

        self._update_migration_frontmatter(migration_type, updates)

    def _update_migration_frontmatter(
        self,
        migration_type: str,
        updates: dict,
    ) -> None:
        """Update fields in MIGRATION.md frontmatter.

        Args:
            migration_type: Type of migration
            updates: Dict of field names to new values.

        Raises:
            ValueError: If the file has no frontmatter.
        """
        migration_path = self.get_migration_dir(migration_type) / "MIGRATION.md"

        content = migration_path.read_text()

        # Parse frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse frontmatter in {migration_path}")

        frontmatter_text = match.group(1)
        body = match.group(2)

        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_text) or {}

        # Update fields
        for key, value in updates.items():
            frontmatter[key] = value

        # Reconstruct the file
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{new_frontmatter}---\n{body}"

        migration_path.write_text(new_content)

    def count_chunks(self) -> int:
        """Count the number of chunks in the repository.

        Returns:
            Number of chunk directories with GOAL.md files.
        """
        if not self.chunks_dir.exists():
            return 0

        count = 0
        for item in self.chunks_dir.iterdir():
            if item.is_dir() and (item / "GOAL.md").exists():
                count += 1
        return count
