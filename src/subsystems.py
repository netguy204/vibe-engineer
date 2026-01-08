"""Subsystems module - business logic for subsystem documentation management."""

import re

from pydantic import ValidationError
import yaml

from models import SubsystemFrontmatter


# Regex for validating subsystem directory name pattern: {NNNN}-{short_name}
SUBSYSTEM_DIR_PATTERN = re.compile(r"^\d{4}-.+$")


class Subsystems:
    """Utility class for managing subsystem documentation.

    Provides methods for enumerating subsystems, validating directory names,
    and parsing subsystem frontmatter.
    """

    def __init__(self, project_dir):
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        self.project_dir = project_dir

    @property
    def subsystems_dir(self):
        """Return the path to the subsystems directory."""
        return self.project_dir / "docs" / "subsystems"

    def enumerate_subsystems(self) -> list[str]:
        """List subsystem directory names.

        Returns:
            List of subsystem directory names, or empty list if none exist.
        """
        if not self.subsystems_dir.exists():
            return []
        return [f.name for f in self.subsystems_dir.iterdir() if f.is_dir()]

    def is_subsystem_dir(self, name: str) -> bool:
        """Check if a directory name matches the subsystem pattern.

        Args:
            name: Directory name to check.

        Returns:
            True if name matches {NNNN}-{short_name} pattern, False otherwise.
        """
        if not SUBSYSTEM_DIR_PATTERN.match(name):
            return False
        # Ensure there's actually content after the hyphen
        parts = name.split("-", 1)
        return len(parts) == 2 and bool(parts[1])

    def parse_subsystem_frontmatter(self, subsystem_id: str) -> SubsystemFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for a subsystem.

        Args:
            subsystem_id: The subsystem directory name.

        Returns:
            Validated SubsystemFrontmatter if successful, None if:
            - Subsystem directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        overview_path = self.subsystems_dir / subsystem_id / "OVERVIEW.md"
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
            return SubsystemFrontmatter.model_validate(frontmatter_data)
        except (yaml.YAMLError, ValidationError):
            return None
