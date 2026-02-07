"""Shared utilities for CLI commands.

Contains validation helpers and common formatting functions used across
multiple command groups.
"""
# Chunk: docs/chunks/cli_modularize - Shared CLI utilities

import pathlib
from typing import Callable

import click

from validation import validate_identifier
from task_utils import TaskProjectContext, is_task_directory


def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


# Chunk: docs/chunks/chunknaming_drop_ticket - Validation simplified to check only short_name length
def validate_combined_chunk_name(short_name: str, ticket_id: str | None) -> list[str]:
    """Validate the chunk directory name length.

    Since ticket_id no longer affects the directory name (it's stored only in
    frontmatter), we only validate the short_name length. The directory name
    is just {short_name} and must not exceed 31 characters to match the
    ExternalArtifactRef.artifact_id limit.

    Args:
        short_name: The short name of the chunk.
        ticket_id: Optional ticket ID (kept for backward compatibility but
                   not used - ticket_id no longer affects directory names).

    Returns:
        List of error messages (empty if valid).
    """
    # ticket_id no longer affects directory name, so only validate short_name
    combined_name = short_name

    if len(combined_name) > 31:
        return [
            f"Chunk name '{combined_name}' is {len(combined_name)} characters, "
            f"exceeds limit of 31 characters"
        ]
    return []


def warn_task_project_context(context: TaskProjectContext | None, artifact_type: str) -> None:
    """Emit a warning if running an artifact command from within a task's project.

    This warning helps prevent the common mistake of creating local artifacts
    when cross-repo artifacts were intended.

    Args:
        context: TaskProjectContext from check_task_project_context(), or None.
        artifact_type: Human-readable name of the artifact type (e.g., "chunk", "narrative").
    """
    if context is None:
        return

    click.echo(
        f"Warning: You are creating a local {artifact_type} in project '{context.project_ref}', "
        f"which is part of a task. To create a cross-repo {artifact_type}, run this command from "
        f"the task directory instead.",
        err=True,
    )


# Chunk: docs/chunks/cli_task_context_dedup - Task-context routing helper
def handle_task_context(
    project_dir: pathlib.Path,
    handler: Callable[[], None],
) -> bool:
    """Execute handler if in task context, return True if handled.

    Use this helper to route CLI commands to task-specific handlers when running
    in a task directory (cross-repo mode). Returns True if the handler was called,
    allowing the caller to return early.

    Args:
        project_dir: The project directory to check.
        handler: Zero-argument callable to execute if in task context.
                 Typically a lambda capturing the task handler with arguments.

    Returns:
        True if handler was called (in task context), False otherwise.

    Usage:
        def list_proposed_chunks_cmd(project_dir):
            if handle_task_context(project_dir, lambda: _list_task_proposed_chunks(project_dir)):
                return
            # Single-repo mode continues here...
    """
    if is_task_directory(project_dir):
        handler()
        return True
    return False
