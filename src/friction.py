"""Friction module - business logic for friction log management."""
# Chunk: docs/chunks/friction_template_and_cli - Friction log artifact type

import pathlib
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import yaml
from pydantic import ValidationError

from models import FrictionFrontmatter, FrictionTheme, FrictionProposedChunk, ExternalFrictionSource


class FrictionStatus(StrEnum):
    """Derived status for friction entries.

    Status is computed from proposed_chunks, not stored directly:
    - OPEN: Entry ID not in any proposed_chunks.addresses
    - ADDRESSED: Entry ID in proposed_chunks.addresses where chunk_directory is set
    - RESOLVED: Entry ID addressed by a chunk that has reached COMPLETE status
    """

    OPEN = "OPEN"
    ADDRESSED = "ADDRESSED"
    RESOLVED = "RESOLVED"


@dataclass
class FrictionEntry:
    """Parsed friction entry from the log body."""

    id: str  # e.g., "F001"
    date: str  # e.g., "2026-01-12"
    theme_id: str  # e.g., "code-refs"
    title: str
    content: str  # Full markdown content after the heading


# Chunk: docs/chunks/friction_template_and_cli - Friction log business logic
class Friction:
    """Business logic for friction log management."""

    # Regex to parse entry headings: ### FXXX: YYYY-MM-DD [theme-id] Title
    ENTRY_HEADING_PATTERN = re.compile(
        r"^###\s+(F\d+):\s+(\d{4}-\d{2}-\d{2})\s+\[([^\]]+)\]\s+(.+)$"
    )

    def __init__(self, project_dir: pathlib.Path):
        self.project_dir = project_dir
        self.friction_path = project_dir / "docs" / "trunk" / "FRICTION.md"

    def exists(self) -> bool:
        """Check if the friction log file exists."""
        return self.friction_path.exists()

    def read_content(self) -> str:
        """Read the raw content of the friction log file."""
        return self.friction_path.read_text()

    def write_content(self, content: str) -> None:
        """Write content to the friction log file."""
        self.friction_path.write_text(content)

    def parse_frontmatter(self) -> FrictionFrontmatter | None:
        """Parse and validate FRICTION.md frontmatter.

        Returns:
            Validated FrictionFrontmatter if successful, None if:
            - File doesn't exist
            - Frontmatter is malformed or fails validation
        """
        if not self.exists():
            return None

        content = self.read_content()

        # Extract frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return None

        try:
            frontmatter_data = yaml.safe_load(match.group(1))
            if not isinstance(frontmatter_data, dict):
                return None
            return FrictionFrontmatter.model_validate(frontmatter_data)
        except (yaml.YAMLError, ValidationError):
            return None

    def parse_entries(self) -> list[FrictionEntry]:
        """Extract friction entries from the log body.

        Returns:
            List of FrictionEntry objects parsed from the document.
        """
        if not self.exists():
            return []

        content = self.read_content()

        # Skip frontmatter
        match = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            body = content
        else:
            body = match.group(1)

        entries = []
        current_entry: dict | None = None
        current_content_lines: list[str] = []

        for line in body.split("\n"):
            heading_match = self.ENTRY_HEADING_PATTERN.match(line)
            if heading_match:
                # Save previous entry if exists
                if current_entry is not None:
                    current_entry["content"] = "\n".join(current_content_lines).strip()
                    entries.append(
                        FrictionEntry(
                            id=current_entry["id"],
                            date=current_entry["date"],
                            theme_id=current_entry["theme_id"],
                            title=current_entry["title"],
                            content=current_entry["content"],
                        )
                    )
                # Start new entry
                current_entry = {
                    "id": heading_match.group(1),
                    "date": heading_match.group(2),
                    "theme_id": heading_match.group(3),
                    "title": heading_match.group(4),
                }
                current_content_lines = []
            elif current_entry is not None:
                current_content_lines.append(line)

        # Don't forget the last entry
        if current_entry is not None:
            current_entry["content"] = "\n".join(current_content_lines).strip()
            entries.append(
                FrictionEntry(
                    id=current_entry["id"],
                    date=current_entry["date"],
                    theme_id=current_entry["theme_id"],
                    title=current_entry["title"],
                    content=current_entry["content"],
                )
            )

        return entries

    def get_next_entry_id(self) -> str:
        """Return the next sequential F-number ID.

        Returns:
            Next ID in sequence (e.g., "F001" if no entries, "F004" if F001-F003 exist).
        """
        entries = self.parse_entries()
        if not entries:
            return "F001"

        # Extract numeric parts and find max
        max_num = 0
        for entry in entries:
            # Extract number from "FXXX"
            match = re.match(r"F(\d+)", entry.id)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

        return f"F{max_num + 1:03d}"

    def get_entry_status(
        self, entry_id: str, chunks_module=None
    ) -> FrictionStatus:
        """Compute the derived status of a friction entry.

        Status is derived from proposed_chunks:
        - OPEN: Entry ID not in any proposed_chunks.addresses
        - ADDRESSED: Entry ID in proposed_chunks.addresses where chunk_directory is set
        - RESOLVED: Entry ID addressed by a chunk that has reached COMPLETE status

        Args:
            entry_id: The friction entry ID (e.g., "F001")
            chunks_module: Optional Chunks instance for checking chunk status.
                           If not provided, RESOLVED status cannot be determined.

        Returns:
            The derived FrictionStatus.
        """
        frontmatter = self.parse_frontmatter()
        if frontmatter is None:
            return FrictionStatus.OPEN

        # Check if entry is addressed by any proposed chunk
        for proposed in frontmatter.proposed_chunks:
            if entry_id in proposed.addresses:
                if proposed.chunk_directory:
                    # Check if the chunk has reached COMPLETE (ACTIVE) status
                    if chunks_module is not None:
                        chunk_frontmatter = chunks_module.parse_chunk_frontmatter(
                            proposed.chunk_directory
                        )
                        if chunk_frontmatter and chunk_frontmatter.status.value == "ACTIVE":
                            return FrictionStatus.RESOLVED
                    return FrictionStatus.ADDRESSED

        return FrictionStatus.OPEN

    def list_entries(
        self,
        status_filter: FrictionStatus | None = None,
        theme_filter: str | None = None,
        chunks_module=None,
    ) -> list[tuple[FrictionEntry, FrictionStatus]]:
        """Query entries with optional filters.

        Args:
            status_filter: Only return entries with this status
            theme_filter: Only return entries with this theme ID
            chunks_module: Optional Chunks instance for computing RESOLVED status

        Returns:
            List of (FrictionEntry, FrictionStatus) tuples.
        """
        entries = self.parse_entries()
        result = []

        for entry in entries:
            status = self.get_entry_status(entry.id, chunks_module)

            # Apply filters
            if status_filter is not None and status != status_filter:
                continue
            if theme_filter is not None and entry.theme_id != theme_filter:
                continue

            result.append((entry, status))

        return result

    def append_entry(
        self,
        title: str,
        description: str,
        impact: str,
        theme_id: str,
        theme_name: str | None = None,
        entry_date: str | None = None,
    ) -> str:
        """Append a new friction entry to the log.

        Args:
            title: Brief title for the friction entry
            description: Detailed description of the friction
            impact: Severity level (low, medium, high, blocking)
            theme_id: Theme ID to cluster the entry under
            theme_name: Human-readable theme name (required if theme is new)
            entry_date: Optional date string (defaults to today)

        Returns:
            The ID of the newly created entry (e.g., "F003").

        Raises:
            ValueError: If theme is new but theme_name is not provided.
        """
        if not self.exists():
            raise ValueError("Friction log does not exist. Run 've init' first.")

        content = self.read_content()
        frontmatter = self.parse_frontmatter()

        if frontmatter is None:
            raise ValueError("Could not parse friction log frontmatter.")

        # Check if theme exists
        existing_themes = {t.id for t in frontmatter.themes}
        if theme_id not in existing_themes:
            if not theme_name:
                raise ValueError(
                    f"Theme '{theme_id}' is new. Please provide a theme_name."
                )
            # Add new theme to frontmatter
            frontmatter.themes.append(FrictionTheme(id=theme_id, name=theme_name))

        # Get next entry ID
        entry_id = self.get_next_entry_id()

        # Use today's date if not provided
        if entry_date is None:
            entry_date = date.today().isoformat()

        # Build entry content
        entry_content = f"""
### {entry_id}: {entry_date} [{theme_id}] {title}

{description}

**Impact**: {impact.capitalize()}
"""

        # Update the file
        # Parse frontmatter section and body
        match = re.match(r"^(---\s*\n.*?\n---\s*\n)(.*)$", content, re.DOTALL)
        if not match:
            raise ValueError("Could not parse friction log structure.")

        # Reconstruct frontmatter
        new_frontmatter = yaml.dump(
            frontmatter.model_dump(), default_flow_style=False, sort_keys=False
        )
        new_content = f"---\n{new_frontmatter}---\n{match.group(2).rstrip()}\n{entry_content}"

        self.write_content(new_content)

        return entry_id

    def get_themes(self) -> list[FrictionTheme]:
        """Get all themes defined in the friction log.

        Returns:
            List of FrictionTheme objects.
        """
        frontmatter = self.parse_frontmatter()
        if frontmatter is None:
            return []
        return frontmatter.themes

    # Chunk: docs/chunks/selective_artifact_friction - External friction source support
    def get_external_friction_sources(self) -> list[ExternalFrictionSource]:
        """Get external friction sources referenced by this friction log.

        Returns:
            List of ExternalFrictionSource objects.
        """
        frontmatter = self.parse_frontmatter()
        if frontmatter is None:
            return []
        return frontmatter.external_friction_sources

    def analyze_by_theme(
        self,
        theme_filter: str | None = None,
        chunks_module=None,
    ) -> dict[str, list[tuple[FrictionEntry, FrictionStatus]]]:
        """Group entries by theme for analysis.

        Args:
            theme_filter: Only analyze entries with this theme ID
            chunks_module: Optional Chunks instance for computing RESOLVED status

        Returns:
            Dict mapping theme_id to list of (FrictionEntry, FrictionStatus) tuples.
        """
        entries = self.list_entries(
            theme_filter=theme_filter, chunks_module=chunks_module
        )

        by_theme: dict[str, list[tuple[FrictionEntry, FrictionStatus]]] = {}
        for entry, status in entries:
            if entry.theme_id not in by_theme:
                by_theme[entry.theme_id] = []
            by_theme[entry.theme_id].append((entry, status))

        return by_theme
