"""Chunk consolidation workflow for VE artifacts.

# Chunk: docs/chunks/chunks_decompose - Extracted from chunks.py for module decomposition

This module provides utilities for consolidating multiple chunks into a
narrative, including updating chunk frontmatter and tracking code
backreferences that need updating.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

from backreferences import count_backreferences


@dataclass
class ConsolidationResult:
    """Result of chunk consolidation into a narrative."""

    narrative_id: str  # Created narrative directory name
    chunks_updated: list[str]  # Chunk IDs whose frontmatter was updated
    files_to_update: dict[str, tuple[list[str], str]]  # file -> (old_chunk_ids, new_narrative_ref)


def consolidate_chunks(
    project_dir: pathlib.Path,
    chunk_ids: list[str],
    narrative_name: str,
    narrative_description: str,
) -> ConsolidationResult:
    """Consolidate multiple chunks into a narrative.

    Creates a new narrative synthesizing the given chunks, updates chunk
    frontmatter to reference the narrative, and returns information needed
    to update code backreferences.

    Args:
        project_dir: Path to the project directory.
        chunk_ids: List of chunk IDs to consolidate.
        narrative_name: Short name for the narrative (e.g., "chunk_lifecycle").
        narrative_description: Human-readable description for the narrative.

    Returns:
        ConsolidationResult with:
        - narrative_id: Created narrative directory name
        - chunks_updated: List of chunk IDs whose frontmatter was updated
        - files_to_update: Dict mapping file paths to (old_refs, new_ref) tuples

    Raises:
        ValueError: If any chunk doesn't exist or isn't ACTIVE.
    """
    from frontmatter import update_frontmatter_field

    # Import here to avoid circular import
    from chunks import Chunks
    from models import ChunkStatus
    from narratives import Narratives

    chunks_manager = Chunks(project_dir)
    narratives = Narratives(project_dir)

    # Validate all chunks exist and are ACTIVE
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        if resolved is None:
            raise ValueError(f"Chunk '{chunk_id}' not found")

        fm = chunks_manager.parse_chunk_frontmatter(resolved)
        if fm is None:
            raise ValueError(f"Could not parse frontmatter for chunk '{chunk_id}'")

        if fm.status != ChunkStatus.ACTIVE:
            raise ValueError(
                f"Chunk '{chunk_id}' has status '{fm.status.value}', must be ACTIVE to consolidate"
            )

    # Create the narrative
    narrative_path = narratives.create_narrative(narrative_name)

    # Build proposed_chunks entries for the narrative
    # This links the narrative to the consolidated chunks
    proposed_chunks = []
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        proposed_chunks.append({
            "prompt": f"Originally: {chunk_id}",
            "chunk_directory": resolved,
        })

    # Update narrative OVERVIEW.md with consolidated chunks info
    overview_path = narrative_path / "OVERVIEW.md"
    overview_content = overview_path.read_text()

    # Update proposed_chunks in frontmatter
    import yaml as yaml_lib
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", overview_content, re.DOTALL)
    if match:
        frontmatter = yaml_lib.safe_load(match.group(1)) or {}
        frontmatter["proposed_chunks"] = proposed_chunks
        body = match.group(2)
        new_frontmatter = yaml_lib.dump(frontmatter, default_flow_style=False, sort_keys=False)
        overview_path.write_text(f"---\n{new_frontmatter}---\n{body}")

    # Update each chunk's frontmatter with narrative reference
    chunks_updated = []
    for chunk_id in chunk_ids:
        resolved = chunks_manager.resolve_chunk_id(chunk_id)
        goal_path = chunks_manager.get_chunk_goal_path(resolved)
        if goal_path:
            update_frontmatter_field(goal_path, "narrative", narrative_name)
            chunks_updated.append(resolved)

    # Find files that reference these chunks
    files_to_update: dict[str, tuple[list[str], str]] = {}
    backref_results = count_backreferences(project_dir)
    for info in backref_results:
        # Find which chunk refs from this file are being consolidated
        matching_refs = [
            ref for ref in set(info.chunk_refs)
            if ref in chunk_ids or chunks_manager.resolve_chunk_id(ref) in chunks_updated
        ]
        if matching_refs:
            rel_path = str(info.file_path.relative_to(project_dir))
            files_to_update[rel_path] = (
                matching_refs,
                f"# Narrative: docs/narratives/{narrative_name} - {narrative_description}",
            )

    return ConsolidationResult(
        narrative_id=narrative_name,
        chunks_updated=chunks_updated,
        files_to_update=files_to_update,
    )
