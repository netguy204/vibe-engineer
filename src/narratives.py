"""Narratives module - business logic for narrative management."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/narrative_cli_commands - Business logic for narrative management
# Chunk: docs/chunks/artifact_manager_base - Refactored to inherit from ArtifactManager
# Chunk: docs/chunks/populate_created_after - Automatic created_after population on narrative creation
# Chunk: docs/chunks/ordering_remove_seqno - Short name directory format for narratives

import pathlib
from pathlib import Path

from pydantic import ValidationError

from artifact_manager import ArtifactManager
from artifact_ordering import ArtifactIndex, ArtifactType
from models import NarrativeFrontmatter, NarrativeStatus, VALID_NARRATIVE_TRANSITIONS
from template_system import ActiveNarrative, TemplateContext, render_to_directory


# Subsystem: docs/subsystems/template_system - Uses template rendering
class Narratives(ArtifactManager[NarrativeFrontmatter, NarrativeStatus]):
    """Utility class for managing narrative documentation."""

    def __init__(self, project_dir: Path | pathlib.Path) -> None:
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        super().__init__(Path(project_dir))

    # Abstract property implementations from ArtifactManager
    @property
    def artifact_dir_name(self) -> str:
        return "narratives"

    @property
    def main_filename(self) -> str:
        return "OVERVIEW.md"

    @property
    def frontmatter_model_class(self) -> type[NarrativeFrontmatter]:
        return NarrativeFrontmatter

    @property
    def status_enum(self) -> type[NarrativeStatus]:
        return NarrativeStatus

    @property
    def transition_map(self) -> dict[NarrativeStatus, set[NarrativeStatus]]:
        return VALID_NARRATIVE_TRANSITIONS

    # Backward compatibility aliases
    @property
    def project_dir(self) -> Path:
        """Return the project root directory (alias for backward compatibility)."""
        return self._project_dir

    @property
    def narratives_dir(self) -> Path:
        """Return the path to the narratives directory (alias for artifact_dir)."""
        return self.artifact_dir

    def enumerate_narratives(self) -> list[str]:
        """List narrative directory names (alias for enumerate_artifacts)."""
        return self.enumerate_artifacts()

    @property
    def num_narratives(self) -> int:
        """Return the number of narratives."""
        return len(self.enumerate_narratives())

    # Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
    def parse_narrative_frontmatter(self, narrative_id: str) -> NarrativeFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for a narrative.

        Note: This method has special handling for the legacy 'chunks' field
        that maps to 'proposed_chunks'. This is artifact-specific behavior
        that cannot be moved to the base class.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Validated NarrativeFrontmatter if successful, None if:
            - Narrative directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        from frontmatter import extract_frontmatter_dict

        overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
        if not overview_path.exists():
            return None

        # Use extract_frontmatter_dict for raw parsing, then apply legacy field mapping
        frontmatter_data = extract_frontmatter_dict(overview_path)
        if frontmatter_data is None:
            return None

        try:
            # Handle legacy 'chunks' field by mapping to 'proposed_chunks'
            if "chunks" in frontmatter_data and "proposed_chunks" not in frontmatter_data:
                frontmatter_data["proposed_chunks"] = frontmatter_data.pop("chunks")
            return NarrativeFrontmatter.model_validate(frontmatter_data)
        except ValidationError:
            return None

    # Override parse_frontmatter to use the specialized parsing for legacy support
    def parse_frontmatter(self, artifact_id: str) -> NarrativeFrontmatter | None:
        """Parse and validate frontmatter for a narrative.

        Overrides base class to handle legacy 'chunks' field mapping.
        """
        return self.parse_narrative_frontmatter(artifact_id)

    # Chunk: docs/chunks/validation_error_surface - Error surfacing for frontmatter parsing
    def parse_narrative_frontmatter_with_errors(
        self, narrative_id: str
    ) -> tuple[NarrativeFrontmatter | None, list[str]]:
        """Parse OVERVIEW.md frontmatter with error details.

        Handles legacy 'chunks' field mapping to 'proposed_chunks'.

        Use this method when callers need to report errors to users (e.g., validation
        commands, CLI feedback). For silent failure scenarios where None is acceptable,
        use parse_narrative_frontmatter() instead.

        Args:
            narrative_id: The narrative directory name.

        Returns:
            Tuple of (frontmatter, errors) where:
            - frontmatter is the validated model if successful, None otherwise
            - errors is a list of error messages (empty if parsing succeeded)
        """
        from frontmatter import extract_frontmatter_dict

        overview_path = self.narratives_dir / narrative_id / "OVERVIEW.md"
        if not overview_path.exists():
            return None, [f"Narrative '{narrative_id}' not found"]

        frontmatter_data = extract_frontmatter_dict(overview_path)
        if frontmatter_data is None:
            return None, [f"Could not parse frontmatter in {overview_path}"]

        try:
            # Handle legacy 'chunks' field by mapping to 'proposed_chunks'
            if "chunks" in frontmatter_data and "proposed_chunks" not in frontmatter_data:
                frontmatter_data["proposed_chunks"] = frontmatter_data.pop("chunks")
            return NarrativeFrontmatter.model_validate(frontmatter_data), []
        except ValidationError as e:
            errors = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"{loc}: {msg}")
            return None, errors

    # Override parse_frontmatter_with_errors to use the specialized parsing for legacy support
    def parse_frontmatter_with_errors(
        self, artifact_id: str
    ) -> tuple[NarrativeFrontmatter | None, list[str]]:
        """Parse and validate frontmatter with error details.

        Overrides base class to handle legacy 'chunks' field mapping.
        """
        return self.parse_narrative_frontmatter_with_errors(artifact_id)

    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    # Chunk: docs/chunks/narrative_cli_commands - Creates narrative directory with template files
    def create_narrative(self, short_name: str) -> pathlib.Path:
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

    def find_duplicates(self, short_name: str) -> list[str]:
        """Find existing narratives with the same short_name.

        Args:
            short_name: The short name to check for collisions.

        Returns:
            List of existing narrative directory names that would collide.
        """
        duplicates = []
        for name in self.enumerate_narratives():
            # Directory name is the short name
            if name == short_name:
                duplicates.append(name)
        return duplicates
