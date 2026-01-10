"""Narratives module - business logic for narrative management."""
# Chunk: docs/chunks/0006-narrative_cli_commands - Narrative creation and management
# Chunk: docs/chunks/0026-template_system_consolidation - Template system integration
# Subsystem: docs/subsystems/0001-template_system - Uses template rendering

from template_system import ActiveNarrative, TemplateContext, render_to_directory


# Chunk: docs/chunks/0006-narrative_cli_commands - Core narrative class
# Subsystem: docs/subsystems/0001-template_system - Uses template rendering
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

    # Chunk: docs/chunks/0006-narrative_cli_commands - Create narrative directory
    # Chunk: docs/chunks/0026-template_system_consolidation - Template system integration
    # Subsystem: docs/subsystems/0001-template_system - Uses render_to_directory
    def create_narrative(self, short_name: str):
        """Create a new narrative directory with templates.

        Args:
            short_name: The short name for the narrative (already validated).

        Returns:
            Path to the created narrative directory.
        """
        # Ensure narratives directory exists (fallback for pre-existing projects)
        self.narratives_dir.mkdir(parents=True, exist_ok=True)

        # Calculate next sequence number (4-digit zero-padded)
        next_id = self.num_narratives + 1
        next_id_str = f"{next_id:04d}"

        # Create narrative directory
        narrative_path = self.narratives_dir / f"{next_id_str}-{short_name}"

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
            next_id=next_id_str,
        )

        return narrative_path
