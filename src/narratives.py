"""Narratives module - business logic for narrative management."""

import jinja2

from constants import template_dir


def render_template(template_name, **kwargs):
    template_path = template_dir / template_name
    with open(template_path, "r") as template_file:
        template = jinja2.Template(template_file.read())
        return template.render(**kwargs)


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
        narrative_path.mkdir(parents=True, exist_ok=True)

        # Copy and expand templates
        for template_file in (template_dir / "narrative").glob("*.md"):
            rendered = render_template(
                template_file.relative_to(template_dir),
                short_name=short_name,
                next_id=next_id_str,
            )
            with open(narrative_path / template_file.name, "w") as dest_file:
                dest_file.write(rendered)

        return narrative_path
