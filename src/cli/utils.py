"""Shared utilities for CLI commands.

Contains validation helpers and common formatting functions used across
multiple command groups.
"""
# Chunk: docs/chunks/cli_modularize - Shared CLI utilities

import pathlib
from typing import Callable

import click

from validation import validate_identifier
from task import TaskProjectContext, is_task_directory


# Chunk: docs/chunks/implement_chunk_start-ve-001 - Short name validation delegating to validate_identifier()
def validate_short_name(short_name: str) -> list[str]:
    """Validate short_name and return list of error messages."""
    return validate_identifier(short_name, "short_name", max_length=31)


# Chunk: docs/chunks/implement_chunk_start-ve-001 - Ticket ID validation delegating to validate_identifier()
def validate_ticket_id(ticket_id: str) -> list[str]:
    """Validate ticket_id and return list of error messages."""
    return validate_identifier(ticket_id, "ticket_id", max_length=None)


def format_not_found_error(
    artifact_type: str,
    artifact_id: str,
    list_command: str | None = None,
) -> str:
    """Format a 'not found' error with actionable suggestion.

    Args:
        artifact_type: The type of artifact (e.g., "Chunk", "Narrative")
        artifact_id: The ID that wasn't found
        list_command: Optional list command to suggest (e.g., "ve chunk list")

    Returns:
        Formatted error message with suggestion
    """
    msg = f"{artifact_type} '{artifact_id}' not found"
    if list_command:
        msg += f". Run `{list_command}` to see available {artifact_type.lower()}s"
    return msg


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
