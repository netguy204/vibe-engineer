"""Narratives module - business logic for narrative management."""
# Chunk: docs/chunks/narrative_cli_commands - Narrative creation and management
# Chunk: docs/chunks/template_system_consolidation - Template system integration
# Chunk: docs/chunks/proposed_chunks_frontmatter - Narrative frontmatter parsing
# Chunk: docs/chunks/populate_created_after - Populate created_after from tips
# Chunk: docs/chunks/valid_transitions - State transition validation
# Subsystem: docs/subsystems/template_system - Uses template rendering

import re

from pydantic import ValidationError
import yaml

from artifact_ordering import ArtifactIndex, ArtifactType
from models import NarrativeFrontmatter, NarrativeStatus, VALID_NARRATIVE_TRANSITIONS, extract_short_name
from template_system import ActiveNarrative, TemplateContext, render_to_directory


# Chunk: docs/chunks/narrative_cli_commands - Core narrative class
# Subsystem: docs/subsystems/template_system - Uses template rendering
class Narratives:
    def __init__(self, project_dir):
        self.project_dir = project_dir

    @property
    def narratives_dir(self):
        return self.project_dir / "docs" / "narratives"

    def enumerate_narratives(self):
        """List narrative directory names."""
        if not self.narratives_dir.exists():
            return []
        return [f.name for f in self.narratives_dir.iterdir() if f.is_dir()]

    @property
    def num_narratives(self):
        return len(self.enumerate_narratives())

    # Chunk: docs/chunks/narrative_cli_commands - Create narrative directory
    # Chunk: docs/chunks/template_system_consolidation - Template system integration
    # Chunk: docs/chunks/populate_created_after - Populate created_after from tips
    # Chunk: docs/chunks/remove_sequence_prefix - Use short_name only (no sequence prefix)
    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    def create_narrative(self, short_name: str):
        """Create a new narrative directory with templates.

        Args:
            short_name: The short name for the narrative (already validated).

        Returns:
            Path to the created narrative directory.

        Raises:
            ValueError: If a narrative with the same short_name already exists.
        """
        # Check for collisions before creating
        duplicates = self.find_duplicates(short_name)
        if duplicates:
            raise ValueError(
                f"Narrative with short_name '{short_name}' already exists: {duplicates[0]}"
            )

        # Get current narrative tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.NARRATIVE)

        # Ensure narratives directory exists (fallback for pre-existing projects)
        self.narratives_dir.mkdir(parents=True, exist_ok=True)

        # Create narrative directory using short_name only (no sequence prefix)
        narrative_path = self.narratives_dir / short_name

        # Create narrative context
        narrative = ActiveNarrative(
            short_name=short_name,
            id=narrative_path.name,
            _project_dir=self.project_dir,
        )
        context = TemplateContext(active_narrative=narrative)

        # Render templates to directory
        render_to_directory(
            "narrative",
            narrative_path,
            context=context,
            short_name=short_name,
            created_after=tips,
        )

        return narrative_path

    # Chunk: docs/chunks/remove_sequence_prefix - Collision detection by short_name
    def find_duplicates(self, short_name: str) -> list[str]:
        """Find existing narratives with the same short_name.

        Args:
            short_name: The short name to check for collisions.

        Returns:
            List of existing narrative directory names that would collide.
        """
        duplicates = []
        for name in self.enumerate_narratives():
            existing_short = extract_short_name(name)
            if existing_short == short_name:
                duplicates.append(name)
        return duplicates

    # Chunk: docs/chunks/proposed_chunks_frontmatter - Parse narrative frontmatter
    def parse_narrative_frontmatter(self, narrative_id: str) -> NarrativeFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for a narrative.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Validated NarrativeFrontmatter if successful, None if:
            - Narrative directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
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
            # Handle legacy 'chunks' field by mapping to 'proposed_chunks'
            if "chunks" in frontmatter_data and "proposed_chunks" not in frontmatter_data:
                frontmatter_data["proposed_chunks"] = frontmatter_data.pop("chunks")
            return NarrativeFrontmatter.model_validate(frontmatter_data)
        except (yaml.YAMLError, ValidationError):
            return None

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def get_status(self, narrative_id: str) -> NarrativeStatus:
        """Get the current status of a narrative.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            The current NarrativeStatus.

        Raises:
            ValueError: If narrative not found or has invalid frontmatter.
        """
        frontmatter = self.parse_narrative_frontmatter(narrative_id)
        if frontmatter is None:
            raise ValueError(f"Narrative '{narrative_id}' not found in docs/narratives/")
        return frontmatter.status

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def update_status(
        self, narrative_id: str, new_status: NarrativeStatus
    ) -> tuple[NarrativeStatus, NarrativeStatus]:
        """Update narrative status with transition validation.

        Args:
            narrative_id: The narrative directory name.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If narrative not found, invalid status, or invalid transition.
        """
        # Get current status
        current_status = self.get_status(narrative_id)

        # Validate the transition
        valid_transitions = VALID_NARRATIVE_TRANSITIONS.get(current_status, set())
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
        self._update_overview_frontmatter(narrative_id, "status", new_status.value)

        return (current_status, new_status)

    # Chunk: docs/chunks/valid_transitions - State transition validation
    def _update_overview_frontmatter(
        self, narrative_id: str, field: str, value
    ) -> None:
        """Update a single field in OVERVIEW.md frontmatter.

        Args:
            narrative_id: The narrative directory name.
            field: The frontmatter field name to update.
            value: The new value for the field.

        Raises:
            ValueError: If the file has no frontmatter.
        """
        overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"

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
