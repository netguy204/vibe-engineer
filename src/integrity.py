"""Referential integrity validation for VE artifacts.

# Chunk: docs/chunks/integrity_validate - Core referential integrity validation module

This module provides project-wide validation of artifact references:
- Chunk outbound references (to narratives, investigations, subsystems, friction entries)
- Code backreferences (# Chunk: and # Subsystem: comments pointing to artifacts)
- Proposed chunks in narratives, investigations, and friction log
- Bidirectional consistency checking
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Literal

from chunks import Chunks, CHUNK_BACKREF_PATTERN, SUBSYSTEM_BACKREF_PATTERN
from friction import Friction
from investigations import Investigations
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
        self._chunk_names: set[str] = set()
        self._narrative_names: set[str] = set()
        self._investigation_names: set[str] = set()
        self._subsystem_names: set[str] = set()
        self._friction_entry_ids: set[str] = set()

    def _build_artifact_index(self) -> None:
        """Build in-memory index of all existing artifacts."""
        self._chunk_names = set(self.chunks.enumerate_chunks())
        self._narrative_names = set(self.narratives.enumerate_narratives())
        self._investigation_names = set(self.investigations.enumerate_investigations())
        self._subsystem_names = set(self.subsystems.enumerate_subsystems())

        # Build friction entry index
        if self.friction.exists():
            entries = self.friction.parse_entries()
            self._friction_entry_ids = {e.id for e in entries}

    def validate(self) -> IntegrityResult:
        """Run full referential integrity validation.

        Returns:
            IntegrityResult with errors, warnings, and statistics.
        """
        errors: list[IntegrityError] = []
        warnings: list[IntegrityWarning] = []

        # Build index of existing artifacts
        self._build_artifact_index()

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
        for subsystem_name in self._subsystem_names:
            subsystems_scanned += 1
            subsystem_errors = self._validate_subsystem_chunk_refs(subsystem_name)
            errors.extend(subsystem_errors)

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
        )

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

        # Validate subsystem references
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

    def _validate_subsystem_chunk_refs(self, subsystem_name: str) -> list[IntegrityError]:
        """Validate subsystem's chunk references."""
        errors: list[IntegrityError] = []

        frontmatter = self.subsystems.parse_subsystem_frontmatter(subsystem_name)
        if frontmatter is None:
            return errors  # Can't validate if we can't parse

        if frontmatter.chunks:
            for chunk_rel in frontmatter.chunks:
                if chunk_rel.chunk_id not in self._chunk_names:
                    errors.append(
                        IntegrityError(
                            source=f"docs/subsystems/{subsystem_name}/OVERVIEW.md",
                            target=f"docs/chunks/{chunk_rel.chunk_id}",
                            link_type="subsystem→chunk",
                            message=f"Chunk '{chunk_rel.chunk_id}' does not exist",
                        )
                    )

        return errors

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

    def _validate_code_backreferences(
        self,
    ) -> tuple[list[IntegrityError], list[IntegrityWarning], int, int, int]:
        """Validate code backreference comments point to existing artifacts.

        Scans source files for # Chunk: and # Subsystem: comments and validates
        that referenced artifacts exist.

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

            # Find chunk backreferences
            for match in CHUNK_BACKREF_PATTERN.finditer(content):
                chunk_refs_found += 1
                chunk_id = match.group(1)
                if chunk_id not in self._chunk_names:
                    errors.append(
                        IntegrityError(
                            source=str(rel_path),
                            target=f"docs/chunks/{chunk_id}",
                            link_type="code→chunk",
                            message=f"Code backreference to non-existent chunk '{chunk_id}'",
                        )
                    )

            # Find subsystem backreferences
            for match in SUBSYSTEM_BACKREF_PATTERN.finditer(content):
                subsystem_refs_found += 1
                subsystem_id = match.group(1)
                if subsystem_id not in self._subsystem_names:
                    errors.append(
                        IntegrityError(
                            source=str(rel_path),
                            target=f"docs/subsystems/{subsystem_id}",
                            link_type="code→subsystem",
                            message=f"Code backreference to non-existent subsystem '{subsystem_id}'",
                        )
                    )

        return errors, warnings, files_scanned, chunk_refs_found, subsystem_refs_found


def validate_integrity(project_dir: pathlib.Path) -> IntegrityResult:
    """Convenience function to run integrity validation.

    Args:
        project_dir: Path to the project root.

    Returns:
        IntegrityResult with validation results.
    """
    validator = IntegrityValidator(project_dir)
    return validator.validate()
