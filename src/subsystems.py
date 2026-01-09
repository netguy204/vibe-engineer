"""Subsystems module - business logic for subsystem documentation management."""

import pathlib
import re

import jinja2
from pydantic import ValidationError
import yaml

from constants import template_dir
from models import SubsystemFrontmatter


# Regex for validating subsystem directory name pattern: {NNNN}-{short_name}
SUBSYSTEM_DIR_PATTERN = re.compile(r"^\d{4}-.+$")


def render_template(template_name, **kwargs):
    """Render a Jinja2 template with the given context."""
    template_path = template_dir / template_name
    with open(template_path, "r") as template_file:
        template = jinja2.Template(template_file.read())
        return template.render(**kwargs)


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

    def find_by_shortname(self, shortname: str) -> str | None:
        """Find subsystem directory by shortname.

        Args:
            shortname: The short name of the subsystem to find.

        Returns:
            Directory name (e.g., "0001-validation") if found, None otherwise.
        """
        for dirname in self.enumerate_subsystems():
            if self.is_subsystem_dir(dirname):
                # Extract the shortname part after the prefix
                parts = dirname.split("-", 1)
                if len(parts) == 2 and parts[1] == shortname:
                    return dirname
        return None

    @property
    def num_subsystems(self):
        """Return the number of subsystems."""
        return len(self.enumerate_subsystems())

    def create_subsystem(self, shortname: str) -> pathlib.Path:
        """Create a new subsystem directory with OVERVIEW.md template.

        Args:
            shortname: The short name for the subsystem (already validated).

        Returns:
            Path to created subsystem directory.
        """
        # Ensure subsystems directory exists
        self.subsystems_dir.mkdir(parents=True, exist_ok=True)

        # Calculate next sequence number (4-digit zero-padded)
        next_id = self.num_subsystems + 1
        next_id_str = f"{next_id:04d}"

        # Create subsystem directory
        subsystem_path = self.subsystems_dir / f"{next_id_str}-{shortname}"
        subsystem_path.mkdir(parents=True, exist_ok=True)

        # Render and write template
        for template_file in (template_dir / "subsystem").glob("*.md"):
            rendered = render_template(
                template_file.relative_to(template_dir),
                short_name=shortname,
                next_id=next_id_str,
            )
            with open(subsystem_path / template_file.name, "w") as dest_file:
                dest_file.write(rendered)

        return subsystem_path

    def validate_chunk_refs(self, subsystem_id: str) -> list[str]:
        """Validate chunk references in a subsystem's frontmatter.

        Checks that each chunk_id referenced in the subsystem's `chunks` field
        exists as a directory in docs/chunks/.

        Args:
            subsystem_id: The subsystem directory name to validate.

        Returns:
            List of error messages (empty if all refs valid or no refs).
        """
        errors: list[str] = []

        # Get subsystem frontmatter
        frontmatter = self.parse_subsystem_frontmatter(subsystem_id)
        if frontmatter is None:
            return []  # Subsystem doesn't exist or invalid, nothing to validate

        # Get chunks from validated frontmatter
        chunks = frontmatter.chunks
        if not chunks:
            return []

        # Chunks directory path
        chunks_dir = self.project_dir / "docs" / "chunks"

        for chunk_rel in chunks:
            chunk_id = chunk_rel.chunk_id

            # Check if chunk directory exists
            chunk_path = chunks_dir / chunk_id
            if not chunk_path.exists():
                errors.append(
                    f"Chunk '{chunk_id}' does not exist in docs/chunks/"
                )

        return errors
