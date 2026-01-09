"""Subsystems module - business logic for subsystem documentation management."""

from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING

import jinja2
from pydantic import ValidationError
import yaml

from constants import template_dir
from models import SubsystemFrontmatter, SubsystemStatus, VALID_STATUS_TRANSITIONS
from symbols import is_parent_of, parse_reference

if TYPE_CHECKING:
    from chunks import Chunks


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

    def get_status(self, subsystem_id: str) -> SubsystemStatus:
        """Get the current status of a subsystem.

        Args:
            subsystem_id: The subsystem directory name.

        Returns:
            The current SubsystemStatus.

        Raises:
            ValueError: If subsystem not found or has invalid frontmatter.
        """
        frontmatter = self.parse_subsystem_frontmatter(subsystem_id)
        if frontmatter is None:
            raise ValueError(f"Subsystem '{subsystem_id}' not found in docs/subsystems/")
        return frontmatter.status

    def update_status(
        self, subsystem_id: str, new_status: SubsystemStatus
    ) -> tuple[SubsystemStatus, SubsystemStatus]:
        """Update subsystem status with transition validation.

        Args:
            subsystem_id: The subsystem directory name.
            new_status: The new status to transition to.

        Returns:
            Tuple of (old_status, new_status) on success.

        Raises:
            ValueError: If subsystem not found, invalid status, or invalid transition.
        """
        # Get current status
        current_status = self.get_status(subsystem_id)

        # Validate the transition
        valid_transitions = VALID_STATUS_TRANSITIONS.get(current_status, set())
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
        self._update_overview_frontmatter(subsystem_id, "status", new_status.value)

        return (current_status, new_status)

    def _update_overview_frontmatter(
        self, subsystem_id: str, field: str, value
    ) -> None:
        """Update a single field in OVERVIEW.md frontmatter.

        Args:
            subsystem_id: The subsystem directory name.
            field: The frontmatter field name to update.
            value: The new value for the field.

        Raises:
            ValueError: If the file has no frontmatter.
        """
        overview_path = self.subsystems_dir / subsystem_id / "OVERVIEW.md"

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

    def find_overlapping_subsystems(
        self, chunk_id: str, chunks: Chunks
    ) -> list[dict]:
        """Find subsystems with code_references overlapping a chunk's changes.

        A subsystem overlaps if any of its code_references are in a parent-child
        or equal relationship with any of the chunk's code_references (or code_paths
        as a fallback).

        Args:
            chunk_id: The chunk ID to check.
            chunks: Chunks instance for parsing chunk frontmatter.

        Returns:
            List of dicts with keys: subsystem_id, status, overlapping_refs

        Raises:
            ValueError: If chunk_id doesn't exist.
        """
        # Resolve and validate chunk exists
        chunk_name = chunks.resolve_chunk_id(chunk_id)
        if chunk_name is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Get chunk frontmatter
        frontmatter = chunks.parse_chunk_frontmatter(chunk_id)
        if frontmatter is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        # Get chunk's code references (symbolic format)
        code_refs = frontmatter.get("code_references", [])
        chunk_refs: list[str] = []

        if code_refs and chunks._is_symbolic_format(code_refs):
            chunk_refs = chunks._extract_symbolic_refs(code_refs)

        # Fall back to code_paths if no symbolic code_references
        if not chunk_refs:
            code_paths = frontmatter.get("code_paths", [])
            # code_paths are file-only references
            chunk_refs = code_paths if code_paths else []

        # No references to check against
        if not chunk_refs:
            return []

        # Check each subsystem for overlap
        results: list[dict] = []

        for subsystem_id in self.enumerate_subsystems():
            if not self.is_subsystem_dir(subsystem_id):
                continue

            subsystem_fm = self.parse_subsystem_frontmatter(subsystem_id)
            if subsystem_fm is None:
                continue

            # Get subsystem's code_references
            subsystem_refs = [ref.ref for ref in subsystem_fm.code_references]
            if not subsystem_refs:
                continue

            # Find overlapping references
            overlapping = self._find_overlapping_refs(chunk_refs, subsystem_refs)

            if overlapping:
                results.append({
                    "subsystem_id": subsystem_id,
                    "status": subsystem_fm.status.value,
                    "overlapping_refs": overlapping,
                })

        return results

    def _find_overlapping_refs(
        self, chunk_refs: list[str], subsystem_refs: list[str]
    ) -> list[str]:
        """Find subsystem references that overlap with chunk references.

        Args:
            chunk_refs: List of chunk reference strings.
            subsystem_refs: List of subsystem reference strings.

        Returns:
            List of subsystem reference strings that overlap.
        """
        overlapping: list[str] = []

        for subsystem_ref in subsystem_refs:
            for chunk_ref in chunk_refs:
                # Check both directions: chunk->subsystem and subsystem->chunk
                if is_parent_of(chunk_ref, subsystem_ref) or is_parent_of(subsystem_ref, chunk_ref):
                    overlapping.append(subsystem_ref)
                    break  # Don't add the same ref multiple times

        return overlapping
