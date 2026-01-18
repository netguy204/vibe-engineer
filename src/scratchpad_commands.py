"""Scratchpad-based chunk commands - CLI functions for scratchpad storage.

This module provides chunk command implementations that operate on scratchpad
storage (~/.vibe/scratchpad/) instead of in-repo docs/chunks/. These commands
support the workflow where personal work notes live outside git repositories.
"""
# Subsystem: docs/subsystems/workflow_artifacts - User-global scratchpad storage variant

from __future__ import annotations

from pathlib import Path

from models import ScratchpadChunkStatus
from scratchpad import Scratchpad, ScratchpadChunks
from task_utils import is_task_directory


def detect_scratchpad_context(
    project_dir: Path,
) -> tuple[Path | None, str | None]:
    """Detect whether we're in task or project context.

    Checks for task context markers (e.g., .ve-task.yaml) and falls back
    to using the project directory name for project context.

    Args:
        project_dir: The current working directory or project directory.

    Returns:
        Tuple of (project_path, task_name) where exactly one is non-None.
        - If task context: (None, task_name)
        - If project context: (project_path, None)

    Raises:
        ValueError: If context cannot be determined.
    """
    # Check for task directory marker
    if is_task_directory(project_dir):
        # Extract task name from the directory name
        # Task directories are typically named after the task
        task_name = project_dir.resolve().name
        return (None, task_name)

    # Default to project context using the directory path
    return (project_dir, None)


def scratchpad_create_chunk(
    project_path: Path | None,
    task_name: str | None,
    short_name: str,
    ticket: str | None = None,
    scratchpad_root: Path | None = None,
) -> Path:
    """Create a chunk in the scratchpad.

    Args:
        project_path: Path to the project directory (for project context).
        task_name: Task name (for task context).
        short_name: Short name for the chunk.
        ticket: Optional ticket reference (e.g., Linear ID).
        scratchpad_root: Override scratchpad root (for testing).

    Returns:
        Path to the created chunk directory.

    Raises:
        ValueError: If context cannot be determined or chunk already exists.
    """
    scratchpad = Scratchpad(scratchpad_root=scratchpad_root)
    scratchpad.ensure_initialized()

    context_path = scratchpad.resolve_context(
        project_path=project_path,
        task_name=task_name,
    )

    chunks = ScratchpadChunks(scratchpad, context_path)
    return chunks.create_chunk(short_name, ticket=ticket)


def scratchpad_list_chunks(
    project_path: Path | None,
    task_name: str | None,
    latest: bool = False,
    scratchpad_root: Path | None = None,
) -> list[dict] | str | None:
    """List chunks from the scratchpad.

    Args:
        project_path: Path to the project directory (for project context).
        task_name: Task name (for task context).
        latest: If True, return only the current IMPLEMENTING chunk path.
        scratchpad_root: Override scratchpad root (for testing).

    Returns:
        If latest=True: Path string to current IMPLEMENTING chunk, or None if none.
        If latest=False: List of dicts with 'name' and 'status' keys.
    """
    scratchpad = Scratchpad(scratchpad_root=scratchpad_root)

    context_path = scratchpad.resolve_context(
        project_path=project_path,
        task_name=task_name,
    )

    if not context_path.exists():
        return None if latest else []

    chunks = ScratchpadChunks(scratchpad, context_path)
    chunk_list = chunks.list_chunks()

    if latest:
        # Find the current IMPLEMENTING chunk
        for chunk_id in chunk_list:
            fm = chunks.parse_chunk_frontmatter(chunk_id)
            if fm and fm.status == ScratchpadChunkStatus.IMPLEMENTING:
                # Return the full path relative to scratchpad
                chunk_path = chunks.get_chunk_path(chunk_id)
                if chunk_path:
                    return str(chunk_path)
        return None

    # Return list with status information
    result = []
    for chunk_id in chunk_list:
        fm = chunks.parse_chunk_frontmatter(chunk_id)
        status = fm.status.value if fm else "UNKNOWN"
        result.append({
            "name": chunk_id,
            "status": status,
            "path": str(chunks.get_chunk_path(chunk_id)),
        })
    return result


def scratchpad_complete_chunk(
    project_path: Path | None,
    task_name: str | None,
    chunk_id: str | None = None,
    scratchpad_root: Path | None = None,
) -> str:
    """Complete (archive) a chunk in the scratchpad.

    Archives the specified chunk by updating its status to ARCHIVED.
    If no chunk_id is provided, archives the current IMPLEMENTING chunk.

    Args:
        project_path: Path to the project directory (for project context).
        task_name: Task name (for task context).
        chunk_id: Specific chunk to archive. Defaults to current IMPLEMENTING.
        scratchpad_root: Override scratchpad root (for testing).

    Returns:
        The archived chunk's ID.

    Raises:
        ValueError: If chunk not found or no IMPLEMENTING chunk exists.
    """
    scratchpad = Scratchpad(scratchpad_root=scratchpad_root)

    context_path = scratchpad.resolve_context(
        project_path=project_path,
        task_name=task_name,
    )

    if not context_path.exists():
        raise ValueError("No scratchpad context found")

    chunks = ScratchpadChunks(scratchpad, context_path)

    # If no chunk_id provided, find current IMPLEMENTING chunk
    if chunk_id is None:
        chunk_list = chunks.list_chunks()
        for cid in chunk_list:
            fm = chunks.parse_chunk_frontmatter(cid)
            if fm and fm.status == ScratchpadChunkStatus.IMPLEMENTING:
                chunk_id = cid
                break

        if chunk_id is None:
            raise ValueError("No IMPLEMENTING chunk found to complete")

    # Archive the chunk
    chunks.archive_chunk(chunk_id)
    return chunk_id


def get_current_scratchpad_chunk(
    project_path: Path | None,
    task_name: str | None,
    scratchpad_root: Path | None = None,
) -> tuple[str | None, Path | None]:
    """Get the current IMPLEMENTING chunk from scratchpad.

    Args:
        project_path: Path to the project directory (for project context).
        task_name: Task name (for task context).
        scratchpad_root: Override scratchpad root (for testing).

    Returns:
        Tuple of (chunk_id, chunk_path) or (None, None) if no IMPLEMENTING chunk.
    """
    scratchpad = Scratchpad(scratchpad_root=scratchpad_root)

    context_path = scratchpad.resolve_context(
        project_path=project_path,
        task_name=task_name,
    )

    if not context_path.exists():
        return (None, None)

    chunks = ScratchpadChunks(scratchpad, context_path)
    chunk_list = chunks.list_chunks()

    for chunk_id in chunk_list:
        fm = chunks.parse_chunk_frontmatter(chunk_id)
        if fm and fm.status == ScratchpadChunkStatus.IMPLEMENTING:
            chunk_path = chunks.get_chunk_path(chunk_id)
            return (chunk_id, chunk_path)

    return (None, None)
