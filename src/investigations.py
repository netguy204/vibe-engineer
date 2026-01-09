"""Investigations module - business logic for investigation management."""

import pathlib
import re

from pydantic import ValidationError
import yaml

from models import InvestigationFrontmatter
from template_system import ActiveInvestigation, TemplateContext, render_to_directory


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

    def create_investigation(self, short_name: str) -> pathlib.Path:
        """Create a new investigation directory with OVERVIEW.md template.

        Args:
            short_name: The short name for the investigation (already validated).

        Returns:
            Path to created investigation directory.
        """
        # Ensure investigations directory exists
        self.investigations_dir.mkdir(parents=True, exist_ok=True)

        # Calculate next sequence number (4-digit zero-padded)
        next_id = self.num_investigations + 1
        next_id_str = f"{next_id:04d}"

        # Create investigation directory
        investigation_path = self.investigations_dir / f"{next_id_str}-{short_name}"

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
            next_id=next_id_str,
        )

        return investigation_path

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
