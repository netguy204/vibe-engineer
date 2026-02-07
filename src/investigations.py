"""Investigations module - business logic for investigation management."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/artifact_manager_base - Refactored to inherit from ArtifactManager
# Chunk: docs/chunks/investigation_commands - Investigation management business logic
# Chunk: docs/chunks/populate_created_after - Automatic created_after population on investigation creation
# Chunk: docs/chunks/ordering_remove_seqno - Short name directory format for investigations

import pathlib
from pathlib import Path

from artifact_manager import ArtifactManager
from artifact_ordering import ArtifactIndex, ArtifactType
from models import InvestigationFrontmatter, InvestigationStatus, VALID_INVESTIGATION_TRANSITIONS
from template_system import ActiveInvestigation, TemplateContext, render_to_directory


# Subsystem: docs/subsystems/template_system - Uses template rendering
class Investigations(ArtifactManager[InvestigationFrontmatter, InvestigationStatus]):
    """Utility class for managing investigation documentation."""

    def __init__(self, project_dir: Path | pathlib.Path) -> None:
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        super().__init__(Path(project_dir))

    # Abstract property implementations from ArtifactManager
    @property
    def artifact_dir_name(self) -> str:
        return "investigations"

    @property
    def main_filename(self) -> str:
        return "OVERVIEW.md"

    @property
    def frontmatter_model_class(self) -> type[InvestigationFrontmatter]:
        return InvestigationFrontmatter

    @property
    def status_enum(self) -> type[InvestigationStatus]:
        return InvestigationStatus

    @property
    def transition_map(self) -> dict[InvestigationStatus, set[InvestigationStatus]]:
        return VALID_INVESTIGATION_TRANSITIONS

    # Backward compatibility aliases
    @property
    def project_dir(self) -> Path:
        """Return the project root directory (alias for backward compatibility)."""
        return self._project_dir

    @property
    def investigations_dir(self) -> Path:
        """Return the path to the investigations directory (alias for artifact_dir)."""
        return self.artifact_dir

    def enumerate_investigations(self) -> list[str]:
        """List investigation directory names (alias for enumerate_artifacts)."""
        return self.enumerate_artifacts()

    @property
    def num_investigations(self) -> int:
        """Return the number of investigations."""
        return len(self.enumerate_investigations())

    # Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
    def parse_investigation_frontmatter(self, investigation_id: str) -> InvestigationFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for an investigation.

        This is an alias for parse_frontmatter() that maintains the original
        method name for backward compatibility.

        Args:
            investigation_id: The investigation directory name.

        Returns:
            Validated InvestigationFrontmatter if successful, None if:
            - Investigation directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        return self.parse_frontmatter(investigation_id)

    # Chunk: docs/chunks/validation_error_surface - Error surfacing for frontmatter parsing
    def parse_investigation_frontmatter_with_errors(
        self, investigation_id: str
    ) -> tuple[InvestigationFrontmatter | None, list[str]]:
        """Parse OVERVIEW.md frontmatter with error details.

        This is an alias for parse_frontmatter_with_errors() that maintains the
        original method name for backward compatibility and consistency with
        parse_investigation_frontmatter().

        Use this method when callers need to report errors to users (e.g., validation
        commands, CLI feedback). For silent failure scenarios where None is acceptable,
        use parse_investigation_frontmatter() instead.

        Args:
            investigation_id: The investigation directory name.

        Returns:
            Tuple of (frontmatter, errors) where:
            - frontmatter is the validated model if successful, None otherwise
            - errors is a list of error messages (empty if parsing succeeded)
        """
        return self.parse_frontmatter_with_errors(investigation_id)

    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    def create_investigation(self, short_name: str) -> pathlib.Path:
        """Create a new investigation directory with OVERVIEW.md template.

        Args:
            short_name: The short name for the investigation (already validated).

        Returns:
            Path to created investigation directory.

        Raises:
            ValueError: If an investigation with the same short_name already exists.
        """
        # Check for collisions before creating
        duplicates = self.find_duplicates(short_name)
        if duplicates:
            raise ValueError(
                f"Investigation with short_name '{short_name}' already exists: {duplicates[0]}"
            )

        # Get current investigation tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.INVESTIGATION)

        # Ensure investigations directory exists
        self.investigations_dir.mkdir(parents=True, exist_ok=True)

        # Create investigation directory using short_name only (no sequence prefix)
        investigation_path = self.investigations_dir / short_name

        # Create investigation context
        investigation = ActiveInvestigation(
            short_name=short_name,
            id=investigation_path.name,
            _project_dir=self.project_dir,
        )
        context = TemplateContext(active_investigation=investigation)

        # Render templates to directory
        render_to_directory(
            "investigation",
            investigation_path,
            context=context,
            short_name=short_name,
            created_after=tips,
        )

        return investigation_path

    def find_duplicates(self, short_name: str) -> list[str]:
        """Find existing investigations with the same short_name.

        Args:
            short_name: The short name to check for collisions.

        Returns:
            List of existing investigation directory names that would collide.
        """
        duplicates = []
        for name in self.enumerate_investigations():
            # Directory name is the short name
            if name == short_name:
                duplicates.append(name)
        return duplicates
