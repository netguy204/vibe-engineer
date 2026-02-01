"""External command group.

Commands for managing external artifact references.
"""
# Subsystem: docs/subsystems/cross_repo_operations - Cross-repository operations
# Chunk: docs/chunks/cli_modularize - External CLI commands
# Chunk: docs/chunks/external_resolve - ve external resolve command
# Chunk: docs/chunks/external_resolve_all_types - Generic artifact resolution
# Chunk: docs/chunks/external_resolve_enhance - Enhanced resolve output format

import pathlib

import click

from models import ArtifactType
from task_utils import is_task_directory, TaskChunkError
from external_refs import ARTIFACT_MAIN_FILE
from external_resolve import (
    resolve_artifact_task_directory,
    resolve_artifact_single_repo,
    ResolveResult,
)


@click.group()
def external():
    """External artifact reference commands."""
    pass


@external.command()
@click.argument("local_artifact_id")
@click.option("--main-only", is_flag=True, help="Show only main file content (GOAL.md for chunks, OVERVIEW.md for others)")
@click.option("--secondary-only", is_flag=True, help="Show only secondary file content (PLAN.md for chunks only)")
@click.option("--goal-only", is_flag=True, hidden=True, help="Alias for --main-only (backward compatibility)")
@click.option("--plan-only", is_flag=True, hidden=True, help="Alias for --secondary-only (backward compatibility)")
@click.option("--project", type=str, default=None, help="Specify project for disambiguation (task directory only)")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def resolve(local_artifact_id, main_only, secondary_only, goal_only, plan_only, project, project_dir):
    """Display external artifact content.

    Resolves an external artifact reference and displays its content.
    Auto-detects artifact type from the path (chunks, narratives, investigations, subsystems).

    For chunks: displays GOAL.md and PLAN.md
    For other types: displays OVERVIEW.md

    Works in both task directory mode (using local worktrees) and single repo mode
    (using the repo cache). Always resolves to the current HEAD of the external repo.
    """
    # Handle backward-compatible aliases
    if goal_only:
        main_only = True
    if plan_only:
        secondary_only = True

    # Validate mutually exclusive options
    if main_only and secondary_only:
        click.echo("Error: --main-only and --secondary-only are mutually exclusive", err=True)
        raise SystemExit(1)

    # Determine mode and resolve
    if is_task_directory(project_dir):
        _resolve_external_task_directory(
            project_dir, local_artifact_id, main_only, secondary_only, project
        )
    else:
        if project:
            click.echo("Error: --project can only be used in task directory context", err=True)
            raise SystemExit(1)
        _resolve_external_single_repo(
            project_dir, local_artifact_id, main_only, secondary_only
        )


# Chunk: docs/chunks/accept_full_artifact_paths - Artifact type detection using normalize_artifact_path
def _detect_artifact_type_from_id(project_path: pathlib.Path, local_artifact_id: str) -> tuple[ArtifactType, str]:
    """Detect artifact type by searching for the artifact in project directories.

    Also normalizes the artifact ID by stripping path prefixes if present.

    Args:
        project_path: Path to the project directory
        local_artifact_id: Local artifact ID to find (can include path prefixes)

    Returns:
        Tuple of (ArtifactType, normalized_artifact_id)

    Raises:
        TaskChunkError: If artifact is not found in any artifact directory
    """
    from external_refs import ARTIFACT_DIR_NAME, normalize_artifact_path

    # First try to normalize using path-based detection
    try:
        artifact_type, artifact_id = normalize_artifact_path(
            local_artifact_id,
            search_path=project_path,
        )
        # Verify the artifact exists
        artifact_dir = project_path / "docs" / ARTIFACT_DIR_NAME[artifact_type] / artifact_id
        if artifact_dir.exists():
            return (artifact_type, artifact_id)
    except ValueError:
        # Fall through to legacy search
        pass

    # Legacy search: search all artifact directories
    for artifact_type, dir_name in ARTIFACT_DIR_NAME.items():
        artifacts_dir = project_path / "docs" / dir_name
        if not artifacts_dir.exists():
            continue
        for artifact_dir in artifacts_dir.iterdir():
            if artifact_dir.is_dir():
                if artifact_dir.name == local_artifact_id or artifact_dir.name.startswith(f"{local_artifact_id}-"):
                    return (artifact_type, artifact_dir.name)

    raise TaskChunkError(f"Artifact '{local_artifact_id}' not found in any artifact directory")


def _resolve_external_task_directory(
    task_dir: pathlib.Path,
    local_artifact_id: str,
    main_only: bool,
    secondary_only: bool,
    project_filter: str | None,
):
    """Handle resolve in task directory mode."""
    from external_refs import ARTIFACT_DIR_NAME
    from task_utils import load_task_config, resolve_repo_directory

    # Parse project:artifact format if present
    if ":" in local_artifact_id:
        parts = local_artifact_id.split(":", 1)
        project_filter = parts[0]
        local_artifact_id = parts[1]

    config = load_task_config(task_dir)

    # Filter projects to search
    projects_to_search = config.projects
    if project_filter:
        matching = [p for p in config.projects if p == project_filter or p.endswith(f"/{project_filter}")]
        if not matching:
            click.echo(f"Error: Project '{project_filter}' not found in task configuration", err=True)
            raise SystemExit(1)
        projects_to_search = matching

    # Find artifact and detect type
    artifact_type = None
    resolved_artifact_id = local_artifact_id
    for project_ref in projects_to_search:
        try:
            project_path = resolve_repo_directory(task_dir, project_ref)
            artifact_type, resolved_artifact_id = _detect_artifact_type_from_id(project_path, local_artifact_id)
            break
        except (FileNotFoundError, TaskChunkError):
            continue

    if artifact_type is None:
        click.echo(f"Error: Artifact '{local_artifact_id}' not found", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_task_directory(
            task_dir,
            resolved_artifact_id,
            artifact_type,
            project_filter=project_filter,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


def _resolve_external_single_repo(
    repo_path: pathlib.Path,
    local_artifact_id: str,
    main_only: bool,
    secondary_only: bool,
):
    """Handle resolve in single repo mode."""
    # Detect artifact type from the repo
    try:
        artifact_type, resolved_artifact_id = _detect_artifact_type_from_id(repo_path, local_artifact_id)
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = resolve_artifact_single_repo(
            repo_path,
            resolved_artifact_id,
            artifact_type,
        )
    except TaskChunkError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    _display_resolve_result(result, main_only, secondary_only)


def _display_resolve_result(result: ResolveResult, main_only: bool, secondary_only: bool):
    """Display the resolve result to the user."""
    # Determine file names based on artifact type
    main_file = ARTIFACT_MAIN_FILE[result.artifact_type]
    secondary_file = "PLAN.md" if result.artifact_type == ArtifactType.CHUNK else None

    # Header with metadata (new format)
    artifact_type_display = result.artifact_type.value
    click.echo(f"Artifact: {result.artifact_id} ({artifact_type_display})")
    click.echo(f"Context: {result.context_mode}")
    if result.local_path:
        click.echo(f"Path: {result.local_path}")

    # Directory contents
    if result.directory_contents:
        click.echo("Contents:")
        for filename in result.directory_contents:
            click.echo(f"  {filename}")

    click.echo("")

    # Content
    if not secondary_only:
        click.echo(f"--- {main_file} ---")
        if result.main_content:
            click.echo(result.main_content)
        else:
            click.echo("(not found)")

    # Only show secondary file section for chunks
    if secondary_file and not main_only:
        if not secondary_only:
            click.echo("")
        click.echo(f"--- {secondary_file} ---")
        if result.secondary_content:
            click.echo(result.secondary_content)
        else:
            click.echo("(not found)")
