"""Backreference scanning and management for VE artifacts.

# Chunk: docs/chunks/chunks_decompose - Extracted from chunks.py for module decomposition

This module provides utilities for scanning source files for backreference
comments (# Chunk:, # Narrative:, # Subsystem:) and updating them during
consolidation operations.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass


@dataclass
class BackreferenceInfo:
    """Information about backreferences in a source file."""

    file_path: pathlib.Path
    chunk_refs: list[str]  # List of chunk IDs referenced
    narrative_refs: list[str]  # List of narrative IDs referenced
    subsystem_refs: list[str]  # List of subsystem IDs referenced

    @property
    def unique_chunk_count(self) -> int:
        """Count of unique chunk references."""
        return len(set(self.chunk_refs))

    @property
    def total_chunk_count(self) -> int:
        """Total count of chunk references (including duplicates)."""
        return len(self.chunk_refs)


CHUNK_BACKREF_PATTERN = re.compile(r"^#\s+Chunk:\s+docs/chunks/([a-z0-9_-]+)", re.MULTILINE)
NARRATIVE_BACKREF_PATTERN = re.compile(r"^#\s+Narrative:\s+docs/narratives/([a-z0-9_-]+)", re.MULTILINE)
SUBSYSTEM_BACKREF_PATTERN = re.compile(r"^#\s+Subsystem:\s+docs/subsystems/([a-z0-9_-]+)", re.MULTILINE)


def count_backreferences(
    project_dir: pathlib.Path,
    source_patterns: list[str] | None = None,
) -> list[BackreferenceInfo]:
    """Scan source files for backreference comments.

    Finds all `# Chunk:`, `# Narrative:`, and `# Subsystem:` comments
    in source files and returns counts per file.

    Args:
        project_dir: Path to the project directory.
        source_patterns: List of glob patterns to search (default: ["src/**/*.py"]).

    Returns:
        List of BackreferenceInfo for files containing backreferences.
    """
    if source_patterns is None:
        source_patterns = ["src/**/*.py"]

    results: list[BackreferenceInfo] = []

    for pattern in source_patterns:
        for file_path in project_dir.glob(pattern):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            # Extract all backreferences
            chunk_refs = CHUNK_BACKREF_PATTERN.findall(content)
            narrative_refs = NARRATIVE_BACKREF_PATTERN.findall(content)
            subsystem_refs = SUBSYSTEM_BACKREF_PATTERN.findall(content)

            # Only include files with at least one chunk reference
            if chunk_refs:
                results.append(BackreferenceInfo(
                    file_path=file_path,
                    chunk_refs=chunk_refs,
                    narrative_refs=narrative_refs,
                    subsystem_refs=subsystem_refs,
                ))

    # Sort by unique chunk count descending
    results.sort(key=lambda r: r.unique_chunk_count, reverse=True)

    return results


def update_backreferences(
    project_dir: pathlib.Path,
    file_path: pathlib.Path,
    chunk_ids_to_replace: list[str],
    narrative_id: str,
    narrative_description: str,
    dry_run: bool = False,
) -> int:
    """Replace chunk backreferences with narrative backreference.

    Finds all `# Chunk: docs/chunks/{id}` comments where id is in
    chunk_ids_to_replace and replaces them with a single
    `# Narrative: docs/narratives/{narrative_id} - {description}` comment.

    Args:
        project_dir: Path to the project directory.
        file_path: Path to the source file to update.
        chunk_ids_to_replace: Chunk IDs whose references should be replaced.
        narrative_id: Narrative directory to reference.
        narrative_description: Description for the narrative backreference.
        dry_run: If True, don't modify the file, just return count.

    Returns:
        Number of backreferences replaced.
    """
    if not file_path.exists():
        return 0

    content = file_path.read_text()
    lines = content.split("\n")
    new_lines: list[str] = []
    replaced_count = 0
    narrative_line_added = False

    # Build pattern to match chunk refs we want to replace
    chunk_ids_set = set(chunk_ids_to_replace)

    for line in lines:
        match = CHUNK_BACKREF_PATTERN.match(line)
        if match:
            chunk_id = match.group(1)
            if chunk_id in chunk_ids_set:
                replaced_count += 1
                # Add narrative reference only once
                if not narrative_line_added:
                    new_lines.append(
                        f"# Narrative: docs/narratives/{narrative_id} - {narrative_description}"
                    )
                    narrative_line_added = True
                # Skip this chunk line (don't add to new_lines)
                continue

        new_lines.append(line)

    if not dry_run and replaced_count > 0:
        file_path.write_text("\n".join(new_lines))

    return replaced_count
