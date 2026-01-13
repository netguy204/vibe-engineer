"""Investigations module - business logic for investigation management."""
# Chunk: docs/chunks/investigation_commands - Investigation management
# Chunk: docs/chunks/populate_created_after - Populate created_after from tips
# Chunk: docs/chunks/valid_transitions - State transition validation
# Subsystem: docs/subsystems/template_system - Uses template rendering

import pathlib
import re

from pydantic import ValidationError
import yaml

from artifact_ordering import ArtifactIndex, ArtifactType
from models import InvestigationFrontmatter, InvestigationStatus, VALID_INVESTIGATION_TRANSITIONS, extract_short_name
from template_system import ActiveInvestigation, TemplateContext, render_to_directory


# Chunk: docs/chunks/investigation_commands - Core investigation class
# Subsystem: docs/subsystems/template_system - Uses template rendering
class Investigations:
    """Utility class for managing investigation documentation."""

    def __init__(self, project_dir):
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        self.project_dir = project_dir

    @property
    def investigations_dir(self):
        """Return the path to the investigations directory."""
        return self.project_dir / "docs" / "investigations"

    def enumerate_investigations(self):
        """List investigation directory names.

        Returns:
            List of investigation directory names, or empty list if none exist.
        """
        if not self.investigations_dir.exists():
            return []
        return [f.name for f in self.investigations_dir.iterdir() if f.is_dir()]

    @property
    def num_investigations(self):
        """Return the number of investigations."""
        return len(self.enumerate_investigations())

    # Chunk: docs/chunks/investigation_commands - Create investigation directory
    # Chunk: docs/chunks/populate_created_after - Populate created_after from tips
    # Chunk: docs/chunks/ordering_remove_seqno - Use short_name only (no sequence prefix)
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

    # Chunk: docs/chunks/ordering_remove_seqno - Collision detection by short_name
    def find_duplicates(self, short_name: str) -> list[str]:
        """Find existing investigations with the same short_name.

        Args:
            short_name: The short name to check for collisions.

        Returns:
            List of existing investigation directory names that would collide.
        """
        duplicates = []
        for name in self.enumerate_investigations():
            existing_short = extract_short_name(name)
            if existing_short == short_name:
                duplicates.append(name)
        return duplicates

    # Chunk: docs/chunks/investigation_commands - Parse investigation frontmatter
    def parse_investigation_frontmatter(self, investigation_id: str) -> InvestigationFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for an investigation.

        Args:
            investigation_id: The investigation directory name.

        Returns:
            Validated InvestigationFrontmatter if successful, None if:
            - Investigation directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        overview_path = self.investigations_dir / investigation_id / "OVERVIEW.md"
        if not overview_path.exists():
            return None

        content = overview_path.read_text()

        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter_data = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter_data, dict):
                return None
            return InvestigationFrontmatter.model_validate(frontmatter_data)
        except (yaml.YAMLError, ValidationError):
            return None

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def get_status(self, investigation_id: str) -> InvestigationStatus:
        """Get the current status of an investigation.

        Args:
            investigation_id: The investigation directory name.

        Returns:
            The current InvestigationStatus.

        Raises:
            ValueError: If investigation not found or has invalid frontmatter.
        """
        frontmatter = self.parse_investigation_frontmatter(investigation_id)
        if frontmatter is None:
            raise ValueError(f"Investigation '{investigation_id}' not found in docs/investigations/")
        return frontmatter.status

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def update_status(
        self, investigation_id: str, new_status: InvestigationStatus
    ) -> tuple[InvestigationStatus, InvestigationStatus]:
        """Update investigation status with transition validation.

        Args:
            investigation_id: The investigation directory name.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If investigation not found, invalid status, or invalid transition.
        """
        # Get current status
        current_status = self.get_status(investigation_id)

        # Validate the transition
        valid_transitions = VALID_INVESTIGATION_TRANSITIONS.get(current_status, set())
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
        self._update_overview_frontmatter(investigation_id, "status", new_status.value)

        return (current_status, new_status)

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def _update_overview_frontmatter(
        self, investigation_id: str, field: str, value
    ) -> None:
        """Update a single field in OVERVIEW.md frontmatter.

        Args:
            investigation_id: The investigation directory name.
            field: The frontmatter field name to update.
            value: The new value for the field.

        Raises:
            ValueError: If the file has no frontmatter.
        """
        overview_path = self.investigations_dir / investigation_id / "OVERVIEW.md"

        content = overview_path.read_text()

        # Parse frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse frontmatter in {overview_path}")

        frontmatter_text = match.group(1)
        body = match.group(2)

        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_text) or {}

        # Update the field
        frontmatter[field] = value

        # Reconstruct the file
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{new_frontmatter}---\n{body}"

        overview_path.write_text(new_content)
