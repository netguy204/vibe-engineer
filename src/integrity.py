"""Referential integrity validation for VE artifacts.

# Chunk: docs/chunks/integrity_validate - Core referential integrity validation module
# Chunk: docs/chunks/validate_external_chunks - External chunk detection and skipping
# Chunk: docs/chunks/chunks_decompose - Standalone validation functions moved from Chunks class

This module provides project-wide validation of artifact references:
- Chunk outbound references (to narratives, investigations, subsystems, friction entries)
- Code backreferences (# Chunk: and # Subsystem: comments pointing to artifacts)
- Proposed chunks in narratives, investigations, and friction log
- Bidirectional consistency checking
- External chunk handling (skip validation, validated in home repo)
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Literal

from backreferences import CHUNK_BACKREF_PATTERN, SUBSYSTEM_BACKREF_PATTERN
from chunks import Chunks
from external_refs import is_external_artifact
from friction import Friction
from investigations import Investigations
from models import ArtifactType
from narratives import Narratives
from subsystems import Subsystems


@dataclass
class IntegrityError:
    """A single referential integrity error."""

    source: str  # File or artifact where the error was found
    target: str  # The invalid reference target
    link_type: str  # Type of link (e.g., "chunk→narrative", "code→chunk")
    message: str  # Human-readable error description


@dataclass
class IntegrityWarning:
    """A single referential integrity warning (non-fatal)."""

    source: str
    target: str
    link_type: str
    message: str


@dataclass
class IntegrityResult:
    """Result of integrity validation."""

    success: bool
    errors: list[IntegrityError] = field(default_factory=list)
    warnings: list[IntegrityWarning] = field(default_factory=list)
    # Statistics for reporting
    chunks_scanned: int = 0
    narratives_scanned: int = 0
    investigations_scanned: int = 0
    subsystems_scanned: int = 0
    files_scanned: int = 0
    chunk_backrefs_found: int = 0
    subsystem_backrefs_found: int = 0
    external_chunks_skipped: int = 0


# Chunk: docs/chunks/integrity_validate - Core integrity validator class
class IntegrityValidator:
    """Validates referential integrity across all VE artifacts.

    Performs the following validations:
    1. Chunk outbound links: narrative, investigation, subsystems, friction entries
    2. Code backreferences: # Chunk: and # Subsystem: comments
    3. Parent artifact → chunk links: proposed_chunks with chunk_directory
    4. Bidirectional consistency (as warnings)
    """

    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = pathlib.Path(project_dir)
        self.chunks = Chunks(self.project_dir)
        self.narratives = Narratives(self.project_dir)
        self.investigations = Investigations(self.project_dir)
        self.subsystems = Subsystems(self.project_dir)
        self.friction = Friction(self.project_dir)

        # Build in-memory index of existing artifacts
        self._chunk_names: set[str] = set()  # Local chunks (with GOAL.md)
        self._external_chunk_names: set[str] = set()  # External chunks (with external.yaml)
        self._narrative_names: set[str] = set()
        self._investigation_names: set[str] = set()
        self._subsystem_names: set[str] = set()
        self._friction_entry_ids: set[str] = set()

        # Bidirectional consistency indexes (populated during validation)
        # Maps narrative_name -> set of chunk directories listed in its proposed_chunks
        self._narrative_chunks: dict[str, set[str]] = {}
        # Maps investigation_name -> set of chunk directories listed in its proposed_chunks
        self._investigation_chunks: dict[str, set[str]] = {}
        # Maps subsystem_name -> set of chunk_ids listed in its `chunks` frontmatter field
        # Chunk: docs/chunks/integrity_subsystem_bidir - Subsystem→chunk reverse index for bidirectional validation
        self._subsystem_chunks: dict[str, set[str]] = {}
        # Maps chunk_name -> set of file paths referenced in its code_references
        self._chunk_code_files: dict[str, set[str]] = {}

    def _build_artifact_index(self) -> None:
        """Build in-memory index of all existing artifacts.

        Separates local chunks (with GOAL.md) from external chunks (with external.yaml).
        External chunks are pointers to canonical artifacts in other repositories and
        are skipped during validation (validated in their home repository).
        """
        # Separate local and external chunks
        all_chunk_names = self.chunks.enumerate_chunks()
        local_chunks: set[str] = set()
        external_chunks: set[str] = set()

        for chunk_name in all_chunk_names:
            chunk_path = self.chunks.chunk_dir / chunk_name
            if is_external_artifact(chunk_path, ArtifactType.CHUNK):
                external_chunks.add(chunk_name)
            else:
                local_chunks.add(chunk_name)

        self._chunk_names = local_chunks
        self._external_chunk_names = external_chunks

        self._narrative_names = set(self.narratives.enumerate_narratives())
        self._investigation_names = set(self.investigations.enumerate_investigations())
        self._subsystem_names = set(self.subsystems.enumerate_subsystems())

        # Build friction entry index
        if self.friction.exists():
            entries = self.friction.parse_entries()
            self._friction_entry_ids = {e.id for e in entries}

    # Chunk: docs/chunks/integrity_bidirectional - Builds reverse index for narrative/investigation→chunk lookups
    # Chunk: docs/chunks/integrity_subsystem_bidir - Extended with subsystem→chunk reverse index
    def _build_parent_chunk_index(self) -> None:
        """Build reverse index of which chunks each parent artifact lists.

        Populates:
        - _narrative_chunks: Maps narrative_name -> set of chunk_directories
        - _investigation_chunks: Maps investigation_name -> set of chunk_directories
        - _subsystem_chunks: Maps subsystem_name -> set of chunk_ids
        """
        # Index narrative → chunks
        for narrative_name in self._narrative_names:
            frontmatter = self.narratives.parse_narrative_frontmatter(narrative_name)
            if frontmatter and frontmatter.proposed_chunks:
                chunk_dirs: set[str] = set()
                for proposed in frontmatter.proposed_chunks:
                    if proposed.chunk_directory:
                        # Normalize by stripping prefix if present
                        chunk_dir = proposed.chunk_directory
                        if chunk_dir.startswith("docs/chunks/"):
                            chunk_dir = chunk_dir[len("docs/chunks/"):]
                        chunk_dirs.add(chunk_dir)
                self._narrative_chunks[narrative_name] = chunk_dirs
            else:
                self._narrative_chunks[narrative_name] = set()

        # Index investigation → chunks
        for investigation_name in self._investigation_names:
            frontmatter = self.investigations.parse_investigation_frontmatter(investigation_name)
            if frontmatter and frontmatter.proposed_chunks:
                chunk_dirs = set()
                for proposed in frontmatter.proposed_chunks:
                    if proposed.chunk_directory:
                        # Normalize by stripping prefix if present
                        chunk_dir = proposed.chunk_directory
                        if chunk_dir.startswith("docs/chunks/"):
                            chunk_dir = chunk_dir[len("docs/chunks/"):]
                        chunk_dirs.add(chunk_dir)
                self._investigation_chunks[investigation_name] = chunk_dirs
            else:
                self._investigation_chunks[investigation_name] = set()

        # Index subsystem → chunks
        # Chunk: docs/chunks/integrity_subsystem_bidir - Build subsystem→chunk index for bidirectional validation
        for subsystem_name in self._subsystem_names:
            frontmatter = self.subsystems.parse_subsystem_frontmatter(subsystem_name)
            if frontmatter and frontmatter.chunks:
                chunk_ids: set[str] = set()
                for chunk_rel in frontmatter.chunks:
                    chunk_ids.add(chunk_rel.chunk_id)
                self._subsystem_chunks[subsystem_name] = chunk_ids
            else:
                self._subsystem_chunks[subsystem_name] = set()

    # Chunk: docs/chunks/integrity_bidirectional - Builds reverse index mapping chunks to referenced file paths
    def _build_chunk_code_index(self) -> None:
        """Build reverse index of which files each chunk references.

        Populates _chunk_code_files: Maps chunk_name -> set of file paths.
        Extracts file path from code_references (format: {file_path}#{symbol}).
        """
        for chunk_name in self._chunk_names:
            frontmatter = self.chunks.parse_chunk_frontmatter(chunk_name)
            if frontmatter and frontmatter.code_references:
                file_paths: set[str] = set()
                for ref in frontmatter.code_references:
                    # Extract file path from ref (format: file_path or file_path#symbol)
                    ref_str = ref.ref
                    if "#" in ref_str:
                        file_path = ref_str.split("#")[0]
                    else:
                        file_path = ref_str
                    file_paths.add(file_path)
                self._chunk_code_files[chunk_name] = file_paths
            else:
                self._chunk_code_files[chunk_name] = set()

    def validate(self) -> IntegrityResult:
        """Run full referential integrity validation.

        Returns:
            IntegrityResult with errors, warnings, and statistics.
        """
        errors: list[IntegrityError] = []
        warnings: list[IntegrityWarning] = []

        # Build index of existing artifacts
        self._build_artifact_index()

        # Build bidirectional consistency indexes
        self._build_parent_chunk_index()
        self._build_chunk_code_index()

        # Statistics
        chunks_scanned = 0
        narratives_scanned = 0
        investigations_scanned = 0
        subsystems_scanned = 0
        files_scanned = 0
        chunk_backrefs_found = 0
        subsystem_backrefs_found = 0

        # 1. Validate chunk outbound references
        for chunk_name in self._chunk_names:
            chunks_scanned += 1
            chunk_errors, chunk_warnings = self._validate_chunk_outbound(chunk_name)
            errors.extend(chunk_errors)
            warnings.extend(chunk_warnings)

        # 2. Validate narrative → chunk references
        for narrative_name in self._narrative_names:
            narratives_scanned += 1
            narrative_errors = self._validate_narrative_chunk_refs(narrative_name)
            errors.extend(narrative_errors)

        # 3. Validate investigation → chunk references
        for investigation_name in self._investigation_names:
            investigations_scanned += 1
            investigation_errors = self._validate_investigation_chunk_refs(investigation_name)
            errors.extend(investigation_errors)

        # 4. Validate subsystem → chunk references
        # Chunk: docs/chunks/integrity_subsystem_bidir - Updated to collect warnings for bidirectional validation
        for subsystem_name in self._subsystem_names:
            subsystems_scanned += 1
            subsystem_errors, subsystem_warnings = self._validate_subsystem_chunk_refs(subsystem_name)
            errors.extend(subsystem_errors)
            warnings.extend(subsystem_warnings)

        # 5. Validate friction → chunk references
        if self.friction.exists():
            friction_errors = self._validate_friction_chunk_refs()
            errors.extend(friction_errors)

        # 6. Validate code backreferences
        backref_errors, backref_warnings, files_count, chunk_refs, subsystem_refs = (
            self._validate_code_backreferences()
        )
        errors.extend(backref_errors)
        warnings.extend(backref_warnings)
        files_scanned = files_count
        chunk_backrefs_found = chunk_refs
        subsystem_backrefs_found = subsystem_refs

        return IntegrityResult(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunks_scanned=chunks_scanned,
            narratives_scanned=narratives_scanned,
            investigations_scanned=investigations_scanned,
            subsystems_scanned=subsystems_scanned,
            files_scanned=files_scanned,
            chunk_backrefs_found=chunk_backrefs_found,
            subsystem_backrefs_found=subsystem_backrefs_found,
            external_chunks_skipped=len(self._external_chunk_names),
        )

    # Chunk: docs/chunks/integrity_bidirectional - Bidirectional checks for chunk↔narrative and chunk↔investigation
    def _validate_chunk_outbound(
        self, chunk_name: str
    ) -> tuple[list[IntegrityError], list[IntegrityWarning]]:
        """Validate a chunk's outbound references."""
        errors: list[IntegrityError] = []
        warnings: list[IntegrityWarning] = []

        frontmatter = self.chunks.parse_chunk_frontmatter(chunk_name)
        if frontmatter is None:
            errors.append(
                IntegrityError(
                    source=f"docs/chunks/{chunk_name}/GOAL.md",
                    target="<frontmatter>",
                    link_type="chunk→frontmatter",
                    message=f"Could not parse frontmatter for chunk '{chunk_name}'",
                )
            )
            return errors, warnings

        # Validate narrative reference
        if frontmatter.narrative:
            if frontmatter.narrative not in self._narrative_names:
                errors.append(
                    IntegrityError(
                        source=f"docs/chunks/{chunk_name}/GOAL.md",
                        target=f"docs/narratives/{frontmatter.narrative}",
                        link_type="chunk→narrative",
                        message=f"Narrative '{frontmatter.narrative}' does not exist",
                    )
                )
            else:
                # Bidirectional check: does narrative's proposed_chunks include this chunk?
                narrative_chunks = self._narrative_chunks.get(frontmatter.narrative, set())
                if chunk_name not in narrative_chunks:
                    warnings.append(
                        IntegrityWarning(
                            source=f"docs/chunks/{chunk_name}/GOAL.md",
                            target=f"docs/narratives/{frontmatter.narrative}/OVERVIEW.md",
                            link_type="chunk↔narrative",
                            message=f"Chunk references narrative '{frontmatter.narrative}' but narrative's proposed_chunks does not list this chunk",
                        )
                    )

        # Validate investigation reference
        if frontmatter.investigation:
            if frontmatter.investigation not in self._investigation_names:
                errors.append(
                    IntegrityError(
                        source=f"docs/chunks/{chunk_name}/GOAL.md",
                        target=f"docs/investigations/{frontmatter.investigation}",
                        link_type="chunk→investigation",
                        message=f"Investigation '{frontmatter.investigation}' does not exist",
                    )
                )
            else:
                # Bidirectional check: does investigation's proposed_chunks include this chunk?
                investigation_chunks = self._investigation_chunks.get(frontmatter.investigation, set())
                if chunk_name not in investigation_chunks:
                    warnings.append(
                        IntegrityWarning(
                            source=f"docs/chunks/{chunk_name}/GOAL.md",
                            target=f"docs/investigations/{frontmatter.investigation}/OVERVIEW.md",
                            link_type="chunk↔investigation",
                            message=f"Chunk references investigation '{frontmatter.investigation}' but investigation's proposed_chunks does not list this chunk",
                        )
                    )

        # Validate subsystem references
        # Chunk: docs/chunks/integrity_subsystem_bidir - Added bidirectional check for chunk→subsystem
        if frontmatter.subsystems:
            for subsystem_rel in frontmatter.subsystems:
                if subsystem_rel.subsystem_id not in self._subsystem_names:
                    errors.append(
                        IntegrityError(
                            source=f"docs/chunks/{chunk_name}/GOAL.md",
                            target=f"docs/subsystems/{subsystem_rel.subsystem_id}",
                            link_type="chunk→subsystem",
                            message=f"Subsystem '{subsystem_rel.subsystem_id}' does not exist",
                        )
                    )
                else:
                    # Bidirectional check: does subsystem's chunks include this chunk?
                    subsystem_chunks = self._subsystem_chunks.get(subsystem_rel.subsystem_id, set())
                    if chunk_name not in subsystem_chunks:
                        warnings.append(
                            IntegrityWarning(
                                source=f"docs/chunks/{chunk_name}/GOAL.md",
                                target=f"docs/subsystems/{subsystem_rel.subsystem_id}/OVERVIEW.md",
                                link_type="chunk↔subsystem",
                                message=f"Chunk references subsystem '{subsystem_rel.subsystem_id}' but subsystem's chunks does not list this chunk",
                            )
                        )

        # Validate friction entry references
        if frontmatter.friction_entries:
            for entry_ref in frontmatter.friction_entries:
                if entry_ref.entry_id not in self._friction_entry_ids:
                    errors.append(
                        IntegrityError(
                            source=f"docs/chunks/{chunk_name}/GOAL.md",
                            target=f"FRICTION.md#{entry_ref.entry_id}",
                            link_type="chunk→friction",
                            message=f"Friction entry '{entry_ref.entry_id}' does not exist",
                        )
                    )

        # Validate depends_on references (if populated)
        if frontmatter.depends_on:
            for dep in frontmatter.depends_on:
                if dep not in self._chunk_names:
                    errors.append(
                        IntegrityError(
                            source=f"docs/chunks/{chunk_name}/GOAL.md",
                            target=f"docs/chunks/{dep}",
                            link_type="chunk→chunk",
                            message=f"Dependency chunk '{dep}' does not exist",
                        )
                    )

        return errors, warnings

    def _validate_narrative_chunk_refs(
        self, narrative_name: str
    ) -> list[IntegrityError]:
        """Validate narrative's proposed_chunks → chunk references."""
        errors: list[IntegrityError] = []

        frontmatter = self.narratives.parse_narrative_frontmatter(narrative_name)
        if frontmatter is None:
            return errors  # Can't validate if we can't parse

        if frontmatter.proposed_chunks:
            for i, proposed in enumerate(frontmatter.proposed_chunks):
                if proposed.chunk_directory:
                    # Strip docs/chunks/ prefix if present (malformed ref)
                    chunk_dir = proposed.chunk_directory
                    if chunk_dir.startswith("docs/chunks/"):
                        errors.append(
                            IntegrityError(
                                source=f"docs/narratives/{narrative_name}/OVERVIEW.md",
                                target=chunk_dir,
                                link_type="narrative→chunk",
                                message=f"Malformed chunk_directory '{chunk_dir}' - should not include 'docs/chunks/' prefix",
                            )
                        )
                        chunk_dir = chunk_dir[len("docs/chunks/"):]

                    if chunk_dir not in self._chunk_names:
                        errors.append(
                            IntegrityError(
                                source=f"docs/narratives/{narrative_name}/OVERVIEW.md",
                                target=f"docs/chunks/{chunk_dir}",
                                link_type="narrative→chunk",
                                message=f"proposed_chunks[{i}].chunk_directory references non-existent chunk '{chunk_dir}'",
                            )
                        )

        return errors

    def _validate_investigation_chunk_refs(
        self, investigation_name: str
    ) -> list[IntegrityError]:
        """Validate investigation's proposed_chunks → chunk references."""
        errors: list[IntegrityError] = []

        frontmatter = self.investigations.parse_investigation_frontmatter(investigation_name)
        if frontmatter is None:
            return errors  # Can't validate if we can't parse

        if frontmatter.proposed_chunks:
            for i, proposed in enumerate(frontmatter.proposed_chunks):
                if proposed.chunk_directory:
                    # Strip docs/chunks/ prefix if present (malformed ref)
                    chunk_dir = proposed.chunk_directory
                    if chunk_dir.startswith("docs/chunks/"):
                        errors.append(
                            IntegrityError(
                                source=f"docs/investigations/{investigation_name}/OVERVIEW.md",
                                target=chunk_dir,
                                link_type="investigation→chunk",
                                message=f"Malformed chunk_directory '{chunk_dir}' - should not include 'docs/chunks/' prefix",
                            )
                        )
                        chunk_dir = chunk_dir[len("docs/chunks/"):]

                    if chunk_dir not in self._chunk_names:
                        errors.append(
                            IntegrityError(
                                source=f"docs/investigations/{investigation_name}/OVERVIEW.md",
                                target=f"docs/chunks/{chunk_dir}",
                                link_type="investigation→chunk",
                                message=f"proposed_chunks[{i}].chunk_directory references non-existent chunk '{chunk_dir}'",
                            )
                        )

        return errors

    # Chunk: docs/chunks/integrity_subsystem_bidir - Extended to return warnings for bidirectional validation
    def _validate_subsystem_chunk_refs(
        self, subsystem_name: str
    ) -> tuple[list[IntegrityError], list[IntegrityWarning]]:
        """Validate subsystem's chunk references and bidirectional consistency."""
        errors: list[IntegrityError] = []
        warnings: list[IntegrityWarning] = []

        frontmatter = self.subsystems.parse_subsystem_frontmatter(subsystem_name)
        if frontmatter is None:
            return errors, warnings  # Can't validate if we can't parse

        if frontmatter.chunks:
            for chunk_rel in frontmatter.chunks:
                chunk_id = chunk_rel.chunk_id
                is_local_chunk = chunk_id in self._chunk_names
                is_external_chunk = chunk_id in self._external_chunk_names

                if not is_local_chunk and not is_external_chunk:
                    errors.append(
                        IntegrityError(
                            source=f"docs/subsystems/{subsystem_name}/OVERVIEW.md",
                            target=f"docs/chunks/{chunk_id}",
                            link_type="subsystem→chunk",
                            message=f"Chunk '{chunk_id}' does not exist",
                        )
                    )
                elif is_local_chunk:
                    # Bidirectional check only for local chunks
                    # (external chunks don't have GOAL.md with subsystems field)
                    chunk_frontmatter = self.chunks.parse_chunk_frontmatter(chunk_id)
                    if chunk_frontmatter:
                        subsystem_ids = (
                            {s.subsystem_id for s in chunk_frontmatter.subsystems}
                            if chunk_frontmatter.subsystems
                            else set()
                        )
                        if subsystem_name not in subsystem_ids:
                            warnings.append(
                                IntegrityWarning(
                                    source=f"docs/subsystems/{subsystem_name}/OVERVIEW.md",
                                    target=f"docs/chunks/{chunk_id}/GOAL.md",
                                    link_type="subsystem↔chunk",
                                    message=f"Subsystem lists chunk '{chunk_id}' but chunk's subsystems does not reference this subsystem",
                                )
                            )
                # External chunks: no bidirectional check (validated in home repo)

        return errors, warnings

    def _validate_friction_chunk_refs(self) -> list[IntegrityError]:
        """Validate friction log's proposed_chunks → chunk references."""
        errors: list[IntegrityError] = []

        frontmatter = self.friction.parse_frontmatter()
        if frontmatter is None:
            return errors

        if frontmatter.proposed_chunks:
            for i, proposed in enumerate(frontmatter.proposed_chunks):
                if proposed.chunk_directory:
                    # Strip docs/chunks/ prefix if present (malformed ref)
                    chunk_dir = proposed.chunk_directory
                    if chunk_dir.startswith("docs/chunks/"):
                        errors.append(
                            IntegrityError(
                                source="docs/trunk/FRICTION.md",
                                target=chunk_dir,
                                link_type="friction→chunk",
                                message=f"Malformed chunk_directory '{chunk_dir}' - should not include 'docs/chunks/' prefix",
                            )
                        )
                        chunk_dir = chunk_dir[len("docs/chunks/"):]

                    if chunk_dir not in self._chunk_names:
                        errors.append(
                            IntegrityError(
                                source="docs/trunk/FRICTION.md",
                                target=f"docs/chunks/{chunk_dir}",
                                link_type="friction→chunk",
                                message=f"proposed_chunks[{i}].chunk_directory references non-existent chunk '{chunk_dir}'",
                            )
                        )

        return errors

    # Chunk: docs/chunks/integrity_code_backrefs - Line-by-line scanning with line number tracking
    # Chunk: docs/chunks/integrity_bidirectional - Extended with code↔chunk bidirectional warnings
    def _validate_code_backreferences(
        self,
    ) -> tuple[list[IntegrityError], list[IntegrityWarning], int, int, int]:
        """Validate code backreference comments point to existing artifacts.

        Scans source files for # Chunk: and # Subsystem: comments and validates
        that referenced artifacts exist. Reports line numbers for broken references.

        Returns:
            (errors, warnings, files_scanned, chunk_refs_found, subsystem_refs_found)
        """
        errors: list[IntegrityError] = []
        warnings: list[IntegrityWarning] = []
        files_scanned = 0
        chunk_refs_found = 0
        subsystem_refs_found = 0

        # Default source patterns to scan
        src_dir = self.project_dir / "src"
        if not src_dir.exists():
            return errors, warnings, 0, 0, 0

        # Find Python files
        for file_path in src_dir.rglob("*.py"):
            files_scanned += 1
            try:
                content = file_path.read_text()
            except (IOError, UnicodeDecodeError):
                continue

            rel_path = file_path.relative_to(self.project_dir)

            # Iterate line-by-line to track line numbers (1-indexed)
            for line_num, line in enumerate(content.splitlines(), start=1):
                # Check for chunk backreferences
                match = CHUNK_BACKREF_PATTERN.match(line)
                if match:
                    chunk_refs_found += 1
                    chunk_id = match.group(1)
                    # Check both local and external chunks - external chunks are valid
                    # targets for code backreferences (their directory exists locally)
                    is_local_chunk = chunk_id in self._chunk_names
                    is_external_chunk = chunk_id in self._external_chunk_names
                    if not is_local_chunk and not is_external_chunk:
                        errors.append(
                            IntegrityError(
                                source=f"{rel_path}:{line_num}",
                                target=f"docs/chunks/{chunk_id}",
                                link_type="code→chunk",
                                message=f"Code backreference to non-existent chunk '{chunk_id}' at line {line_num}",
                            )
                        )
                    elif is_local_chunk:
                        # Bidirectional check only for local chunks
                        # (external chunks don't have GOAL.md with code_references)
                        chunk_code_files = self._chunk_code_files.get(chunk_id, set())
                        # Match on file path (str(rel_path))
                        if str(rel_path) not in chunk_code_files:
                            warnings.append(
                                IntegrityWarning(
                                    source=f"{rel_path}:{line_num}",
                                    target=f"docs/chunks/{chunk_id}/GOAL.md",
                                    link_type="code↔chunk",
                                    message=f"Code backreference to chunk '{chunk_id}' at line {line_num} but chunk's code_references does not include this file",
                                )
                            )
                    # External chunks: no bidirectional check (validated in home repo)

                # Check for subsystem backreferences
                match = SUBSYSTEM_BACKREF_PATTERN.match(line)
                if match:
                    subsystem_refs_found += 1
                    subsystem_id = match.group(1)
                    if subsystem_id not in self._subsystem_names:
                        errors.append(
                            IntegrityError(
                                source=f"{rel_path}:{line_num}",
                                target=f"docs/subsystems/{subsystem_id}",
                                link_type="code→subsystem",
                                message=f"Code backreference to non-existent subsystem '{subsystem_id}' at line {line_num}",
                            )
                        )

        return errors, warnings, files_scanned, chunk_refs_found, subsystem_refs_found


# Chunk: docs/chunks/chunks_decompose - Standalone validation functions extracted from Chunks class
# Chunk: docs/chunks/bidirectional_refs - Validates subsystem references in chunk frontmatter exist
# Chunk: docs/chunks/chunk_frontmatter_model - Uses typed frontmatter.subsystems access
def validate_chunk_subsystem_refs(project_dir: pathlib.Path, chunk_id: str) -> list[str]:
    """Validate subsystem references in a chunk's frontmatter.

    Checks that each referenced subsystem directory exists in docs/subsystems/.

    Args:
        project_dir: Path to the project directory.
        chunk_id: The chunk ID to validate.

    Returns:
        List of error messages (empty if all refs valid or no refs).
    """
    errors: list[str] = []

    # Use late import to avoid circular dependency
    chunks = Chunks(project_dir)

    # Get chunk frontmatter
    frontmatter = chunks.parse_chunk_frontmatter(chunk_id)
    if frontmatter is None:
        return []  # Chunk doesn't exist, nothing to validate

    # Get subsystems field (already validated by ChunkFrontmatter model)
    if not frontmatter.subsystems:
        return []

    # Subsystems directory path
    subsystems_dir = project_dir / "docs" / "subsystems"

    for entry in frontmatter.subsystems:
        # Check if subsystem directory exists
        subsystem_path = subsystems_dir / entry.subsystem_id
        if not subsystem_path.exists():
            errors.append(
                f"Subsystem '{entry.subsystem_id}' does not exist in docs/subsystems/"
            )

    return errors


# Chunk: docs/chunks/chunks_decompose - Standalone validation functions extracted from Chunks class
# Chunk: docs/chunks/chunk_validate - Validation that referenced investigations exist
# Chunk: docs/chunks/investigation_chunk_refs - Validation that referenced investigations exist
def validate_chunk_investigation_ref(project_dir: pathlib.Path, chunk_id: str) -> list[str]:
    """Validate investigation reference in a chunk's frontmatter.

    Checks:
    1. If investigation field is populated, the referenced investigation
       directory exists in docs/investigations/

    Args:
        project_dir: Path to the project directory.
        chunk_id: The chunk ID to validate.

    Returns:
        List of error messages (empty if valid or no reference).
    """
    errors: list[str] = []

    # Use late import to avoid circular dependency
    chunks = Chunks(project_dir)

    # Get chunk frontmatter
    frontmatter = chunks.parse_chunk_frontmatter(chunk_id)
    if frontmatter is None:
        return []  # Chunk doesn't exist, nothing to validate

    # Get investigation field (already validated by ChunkFrontmatter model)
    if not frontmatter.investigation:
        return []

    # Investigations directory path
    investigations_dir = project_dir / "docs" / "investigations"

    # Check if investigation directory exists
    investigation_path = investigations_dir / frontmatter.investigation
    if not investigation_path.exists():
        errors.append(
            f"Investigation '{frontmatter.investigation}' does not exist in docs/investigations/"
        )

    return errors


# Chunk: docs/chunks/chunks_decompose - Standalone validation functions extracted from Chunks class
# Chunk: docs/chunks/chunk_validate - Validation that referenced narratives exist
def validate_chunk_narrative_ref(project_dir: pathlib.Path, chunk_id: str) -> list[str]:
    """Validate narrative reference in a chunk's frontmatter.

    Checks:
    1. If narrative field is populated, the referenced narrative
       directory exists in docs/narratives/

    Args:
        project_dir: Path to the project directory.
        chunk_id: The chunk ID to validate.

    Returns:
        List of error messages (empty if valid or no reference).
    """
    errors: list[str] = []

    # Use late import to avoid circular dependency
    chunks = Chunks(project_dir)

    # Get chunk frontmatter
    frontmatter = chunks.parse_chunk_frontmatter(chunk_id)
    if frontmatter is None:
        return []  # Chunk doesn't exist, nothing to validate

    # Get narrative field (already validated by ChunkFrontmatter model)
    if not frontmatter.narrative:
        return []

    # Narratives directory path
    narratives_dir = project_dir / "docs" / "narratives"

    # Check if narrative directory exists
    narrative_path = narratives_dir / frontmatter.narrative
    if not narrative_path.exists():
        errors.append(
            f"Narrative '{frontmatter.narrative}' does not exist in docs/narratives/"
        )

    return errors


# Chunk: docs/chunks/chunks_decompose - Standalone validation functions extracted from Chunks class
# Chunk: docs/chunks/friction_chunk_linking - Validation method checking friction entry references exist in FRICTION.md
# Subsystem: docs/subsystems/friction_tracking - Friction log management
def validate_chunk_friction_entries_ref(project_dir: pathlib.Path, chunk_id: str) -> list[str]:
    """Validate friction entry references in a chunk's frontmatter.

    Checks that each referenced friction entry ID exists in FRICTION.md.
    If friction_entries is empty, validation passes (optional field).

    Args:
        project_dir: Path to the project directory.
        chunk_id: The chunk ID to validate.

    Returns:
        List of error messages (empty if valid or no references).
    """
    errors: list[str] = []

    # Use late import to avoid circular dependency
    chunks = Chunks(project_dir)

    # Get chunk frontmatter
    frontmatter = chunks.parse_chunk_frontmatter(chunk_id)
    if frontmatter is None:
        return []  # Chunk doesn't exist, nothing to validate

    # Get friction_entries field (already validated by ChunkFrontmatter model)
    if not frontmatter.friction_entries:
        return []

    # Parse friction log to get existing entry IDs
    friction = Friction(project_dir)
    if not friction.exists():
        errors.append(
            f"Friction log does not exist at docs/trunk/FRICTION.md but chunk "
            f"references friction entries: {[e.entry_id for e in frontmatter.friction_entries]}"
        )
        return errors

    # Get all existing friction entry IDs
    existing_entries = friction.parse_entries()
    existing_entry_ids = {entry.id for entry in existing_entries}

    # Validate each referenced entry exists
    for entry_ref in frontmatter.friction_entries:
        if entry_ref.entry_id not in existing_entry_ids:
            errors.append(
                f"Friction entry '{entry_ref.entry_id}' does not exist in docs/trunk/FRICTION.md"
            )

    return errors


def validate_integrity(project_dir: pathlib.Path) -> IntegrityResult:
    """Convenience function to run integrity validation.

    Args:
        project_dir: Path to the project root.

    Returns:
        IntegrityResult with validation results.
    """
    validator = IntegrityValidator(project_dir)
    return validator.validate()
