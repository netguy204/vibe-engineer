"""Subsystems module - business logic for subsystem documentation management."""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Subsystem: docs/subsystems/template_system - Template rendering system
# Subsystem: docs/subsystems/template_system - Uses template rendering
# Chunk: docs/chunks/artifact_manager_base - Refactored to inherit from ArtifactManager
# Chunk: docs/chunks/ordering_remove_seqno - Short name directory format for subsystems
# Chunk: docs/chunks/populate_created_after - Automatic created_after population on subsystem creation

from __future__ import annotations

import pathlib
import re
from pathlib import Path
from typing import TYPE_CHECKING


from artifact_manager import ArtifactManager
from artifact_ordering import ArtifactIndex, ArtifactType
from models import SubsystemFrontmatter, SubsystemStatus, VALID_STATUS_TRANSITIONS, extract_short_name
from symbols import is_parent_of, parse_reference, qualify_ref
from template_system import ActiveSubsystem, TemplateContext, render_to_directory

if TYPE_CHECKING:
    from chunks import Chunks


# Regex for validating subsystem directory name pattern
# Legacy: {NNNN}-{short_name}, New: {short_name} (lowercase, starting with letter)
SUBSYSTEM_DIR_PATTERN = re.compile(r"^(\d{4}-.+|[a-z][a-z0-9_-]*)$")


# Subsystem: docs/subsystems/template_system - Uses template rendering
class Subsystems(ArtifactManager[SubsystemFrontmatter, SubsystemStatus]):
    """Utility class for managing subsystem documentation.

    Provides methods for enumerating subsystems, validating directory names,
    and parsing subsystem frontmatter.
    """

    def __init__(self, project_dir: Path | pathlib.Path) -> None:
        """Initialize with project directory.

        Args:
            project_dir: Path to the project root directory.
        """
        super().__init__(Path(project_dir))

    # Abstract property implementations from ArtifactManager
    @property
    def artifact_dir_name(self) -> str:
        return "subsystems"

    @property
    def main_filename(self) -> str:
        return "OVERVIEW.md"

    @property
    def frontmatter_model_class(self) -> type[SubsystemFrontmatter]:
        return SubsystemFrontmatter

    @property
    def status_enum(self) -> type[SubsystemStatus]:
        return SubsystemStatus

    @property
    def transition_map(self) -> dict[SubsystemStatus, set[SubsystemStatus]]:
        return VALID_STATUS_TRANSITIONS

    # Backward compatibility aliases
    @property
    def project_dir(self) -> Path:
        """Return the project root directory (alias for backward compatibility)."""
        return self._project_dir

    @property
    def subsystems_dir(self) -> Path:
        """Return the path to the subsystems directory (alias for artifact_dir)."""
        return self.artifact_dir

    def enumerate_subsystems(self) -> list[str]:
        """List subsystem directory names (alias for enumerate_artifacts)."""
        return self.enumerate_artifacts()

    # Chunk: docs/chunks/frontmatter_io - Migrated to use shared frontmatter utilities
    def parse_subsystem_frontmatter(self, subsystem_id: str) -> SubsystemFrontmatter | None:
        """Parse and validate OVERVIEW.md frontmatter for a subsystem.

        This is an alias for parse_frontmatter() that maintains the original
        method name for backward compatibility.

        Args:
            subsystem_id: The subsystem directory name.

        Returns:
            Validated SubsystemFrontmatter if successful, None if:
            - Subsystem directory doesn't exist
            - OVERVIEW.md doesn't exist
            - Frontmatter is malformed or fails validation
        """
        return self.parse_frontmatter(subsystem_id)

    def is_subsystem_dir(self, name: str) -> bool:
        """Check if a directory name matches the subsystem pattern.

        Args:
            name: Directory name to check.

        Returns:
            True if name matches valid artifact ID pattern, False otherwise.
        """
        if not SUBSYSTEM_DIR_PATTERN.match(name):
            return False
        # For legacy format, ensure there's content after the prefix
        if re.match(r"^\d{4}-", name):
            parts = name.split("-", 1)
            return len(parts) == 2 and bool(parts[1])
        return True

    # Chunk: docs/chunks/subsystem_cli_scaffolding - Lookup subsystem directory by shortname
    def find_by_shortname(self, shortname: str) -> str | None:
        """Find subsystem directory by shortname.

        Args:
            shortname: The short name of the subsystem to find.

        Returns:
            Directory name if found, None otherwise.
        """
        for dirname in self.enumerate_subsystems():
            if self.is_subsystem_dir(dirname):
                # Extract short_name (handles both patterns)
                existing_short = extract_short_name(dirname)
                if existing_short == shortname:
                    return dirname
        return None

    @property
    def num_subsystems(self) -> int:
        """Return the number of subsystems."""
        return len(self.enumerate_subsystems())

    # Subsystem: docs/subsystems/template_system - Uses render_to_directory
    # Chunk: docs/chunks/subsystem_cli_scaffolding - Create subsystem directory with template
    def create_subsystem(self, shortname: str) -> pathlib.Path:
        """Create a new subsystem directory with OVERVIEW.md template.

        Args:
            shortname: The short name for the subsystem (already validated).

        Returns:
            Path to created subsystem directory.

        Raises:
            ValueError: If a subsystem with the same short_name already exists.
        """
        # Check for collisions before creating
        duplicates = self.find_duplicates(shortname)
        if duplicates:
            raise ValueError(
                f"Subsystem with short_name '{shortname}' already exists: {duplicates[0]}"
            )

        # Get current subsystem tips for created_after field
        artifact_index = ArtifactIndex(self.project_dir)
        tips = artifact_index.find_tips(ArtifactType.SUBSYSTEM)

        # Ensure subsystems directory exists
        self.subsystems_dir.mkdir(parents=True, exist_ok=True)

        # Create subsystem directory using short_name only (no sequence prefix)
        subsystem_path = self.subsystems_dir / shortname

        # Create subsystem context
        subsystem = ActiveSubsystem(
            short_name=shortname,
            id=subsystem_path.name,
            _project_dir=self.project_dir,
        )
        context = TemplateContext(active_subsystem=subsystem)

        # Render templates to directory
        render_to_directory(
            "subsystem",
            subsystem_path,
            context=context,
            short_name=shortname,
            created_after=tips,
        )

        return subsystem_path

    def find_duplicates(self, shortname: str) -> list[str]:
        """Find existing subsystems with the same short_name.

        Args:
            shortname: The short name to check for collisions.

        Returns:
            List of existing subsystem directory names that would collide.
        """
        duplicates = []
        for name in self.enumerate_subsystems():
            existing_short = extract_short_name(name)
            if existing_short == shortname:
                duplicates.append(name)
        return duplicates

    # Chunk: docs/chunks/bidirectional_refs - Validates chunk references in subsystem frontmatter exist
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

    # Chunk: docs/chunks/subsystem_impact_resolution - Find subsystems with overlapping code refs
    # Chunk: docs/chunks/chunk_frontmatter_model - Uses typed frontmatter.code_references and code_paths
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
        chunk_refs: list[str] = [ref.ref for ref in frontmatter.code_references]

        # Fall back to code_paths if no symbolic code_references
        if not chunk_refs:
            # code_paths are file-only references
            chunk_refs = frontmatter.code_paths if frontmatter.code_paths else []

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

    # Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
    # Chunk: docs/chunks/subsystem_impact_resolution - Helper for hierarchical reference comparison
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
        local_project = "."

        for subsystem_ref in subsystem_refs:
            qualified_subsystem = qualify_ref(subsystem_ref, local_project)
            for chunk_ref in chunk_refs:
                qualified_chunk = qualify_ref(chunk_ref, local_project)
                # Check both directions: chunk->subsystem and subsystem->chunk
                if is_parent_of(qualified_chunk, qualified_subsystem) or is_parent_of(qualified_subsystem, qualified_chunk):
                    overlapping.append(subsystem_ref)
                    break  # Don't add the same ref multiple times

        return overlapping
