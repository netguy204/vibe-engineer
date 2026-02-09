"""Subsystem command group.

Commands for managing subsystems - emergent architectural patterns.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/cli_modularize - Subsystem CLI commands
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands

import json
import pathlib

import click

from chunks import Chunks
from external_refs import strip_artifact_path_prefix
from subsystems import Subsystems
from models import SubsystemStatus, ArtifactType
from task import (
    is_task_directory,
    create_task_subsystem,
    list_task_artifacts_grouped,
    TaskSubsystemError,
    TaskArtifactListError,
    load_task_config,
    parse_projects_option,
    check_task_project_context,
)
from artifact_ordering import ArtifactIndex

from cli.utils import validate_short_name, warn_task_project_context, handle_task_context
from cli.formatters import (
    artifact_to_json_dict,
    format_grouped_artifact_list,
    format_grouped_artifact_list_json,
)


# Chunk: docs/chunks/subsystem_cli_scaffolding - CLI command group for subsystem commands
@click.group()
def subsystem():
    """Manage subsystems - documented architectural patterns.

    Subsystems emerge when you notice recurring patterns across chunks.
    They capture invariants and coordinate related code.
    """
    pass



# Chunk: docs/chunks/subsystem_cli_scaffolding - ve subsystem list command - displays subsystems with status
@subsystem.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
# Chunk: docs/chunks/cli_exit_codes - Exit code 0 for empty subsystem list results
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
def list_subsystems(json_output, project_dir):
    """List all subsystems."""
    from artifact_ordering import ArtifactIndex

    # Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
    if handle_task_context(project_dir, lambda: _list_task_subsystems(project_dir, json_output)):
        return

    # Single-repo mode
    subsystems_mgr = Subsystems(project_dir)
    artifact_index = ArtifactIndex(project_dir)

    # Get subsystems in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.SUBSYSTEM)
    subsystem_list = list(reversed(ordered))

    if not subsystem_list:
        if json_output:
            click.echo(json.dumps([]))
            return
        click.echo("No subsystems found")
        raise SystemExit(0)

    # Get tips for indicator display
    tips = set(artifact_index.find_tips(ArtifactType.SUBSYSTEM))

    if json_output:
        results = []
        for subsystem_name in subsystem_list:
            frontmatter = subsystems_mgr.parse_subsystem_frontmatter(subsystem_name)
            result = artifact_to_json_dict(subsystem_name, frontmatter, tips)
            results.append(result)
        click.echo(json.dumps(results, indent=2))
    else:
        for subsystem_name in subsystem_list:
            frontmatter = subsystems_mgr.parse_subsystem_frontmatter(subsystem_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
            tip_indicator = " *" if subsystem_name in tips else ""
            click.echo(f"docs/subsystems/{subsystem_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/cli_json_output - JSON output for task context subsystem listing
def _list_task_subsystems(task_dir: pathlib.Path, json_output: bool = False):
    """Handle subsystem listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.SUBSYSTEM)
        if json_output:
            format_grouped_artifact_list_json(grouped_data, "subsystems")
        else:
            format_grouped_artifact_list(grouped_data, "subsystems")
    except (TaskSubsystemError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Chunk: docs/chunks/subsystem_cli_scaffolding - ve subsystem discover command - creates new subsystem with validation
@subsystem.command()
@click.argument("shortname")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def discover(shortname, project_dir, projects):
    """Create a new subsystem."""
    errors = validate_short_name(shortname)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    shortname = shortname.lower()

    # Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
    if handle_task_context(project_dir, lambda: _create_task_subsystem(project_dir, shortname, projects)):
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "subsystem")

    # Single-repo mode
    subsystems_mgr = Subsystems(project_dir)

    # Check for duplicates
    existing = subsystems_mgr.find_by_shortname(shortname)
    if existing:
        click.echo(f"Error: Subsystem '{shortname}' already exists at docs/subsystems/{existing}", err=True)
        raise SystemExit(1)

    # Create the subsystem
    subsystem_path = subsystems_mgr.create_subsystem(shortname)

    # Show path relative to project_dir
    relative_path = subsystem_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


def _create_task_subsystem(task_dir: pathlib.Path, short_name: str, projects_input: str | None = None):
    """Handle subsystem creation in task directory (cross-repo mode)."""
    # Parse and validate projects option
    try:
        config = load_task_config(task_dir)
        projects = parse_projects_option(projects_input, config.projects)
    except FileNotFoundError:
        click.echo(f"Error: Task configuration not found in {task_dir}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        result = create_task_subsystem(task_dir, short_name, projects=projects)
    except TaskSubsystemError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_subsystem_path"]
    click.echo(f"Created subsystem in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the subsystem directory, not the yaml file
        subsystem_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {subsystem_dir.relative_to(task_dir)}/")


# Chunk: docs/chunks/bidirectional_refs - Subsystem validate CLI command for chunk ref validation
@subsystem.command()
@click.argument("subsystem_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def validate(subsystem_id, project_dir):
    """Validate subsystem frontmatter and chunk references."""
    # Normalize subsystem_id to strip path prefixes
    subsystem_id = strip_artifact_path_prefix(subsystem_id, ArtifactType.SUBSYSTEM)

    subsystems_mgr = Subsystems(project_dir)

    # Check if subsystem exists
    frontmatter = subsystems_mgr.parse_subsystem_frontmatter(subsystem_id)
    if frontmatter is None:
        from cli.utils import format_not_found_error
        click.echo(f"Error: {format_not_found_error('Subsystem', subsystem_id, 've subsystem list')}", err=True)
        raise SystemExit(1)

    # Validate chunk references
    errors = subsystems_mgr.validate_chunk_refs(subsystem_id)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    click.echo(f"Subsystem {subsystem_id} validation passed")


@subsystem.command()
@click.argument("subsystem_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(subsystem_id, new_status, project_dir):
    """Show or update subsystem status."""
    # Normalize subsystem_id to strip path prefixes
    subsystem_id = strip_artifact_path_prefix(subsystem_id, ArtifactType.SUBSYSTEM)

    subsystems_mgr = Subsystems(project_dir)

    # Resolve subsystem_id (could be shortname or full ID)
    resolved_id = subsystem_id
    if not subsystems_mgr.is_subsystem_dir(subsystem_id):
        # Try to resolve as shortname
        found = subsystems_mgr.find_by_shortname(subsystem_id)
        if found:
            resolved_id = found
        # If not found, keep the original ID for error message

    # Extract shortname for display
    if "-" in resolved_id:
        shortname = resolved_id.split("-", 1)[1]
    else:
        shortname = resolved_id

    # Display mode: just show current status
    if new_status is None:
        try:
            current_status = subsystems_mgr.get_status(resolved_id)
            click.echo(f"{shortname}: {current_status.value}")
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid SubsystemStatus value
    try:
        new_status_enum = SubsystemStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in SubsystemStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = subsystems_mgr.update_status(resolved_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@subsystem.command()
@click.argument("chunk_id")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def overlap(chunk_id, project_dir):
    """Find subsystems with code references overlapping a chunk's changes.

    When run in task context (directory with .ve-task.yaml), searches for
    the chunk across the external repo and all project repos, then checks
    for overlapping subsystems in the same repo where the chunk was found.
    """
    from task import (
        is_task_directory,
        find_task_directory,
        load_task_config,
        resolve_repo_directory,
    )

    # Normalize chunk_id to strip path prefixes
    chunk_id = strip_artifact_path_prefix(chunk_id, ArtifactType.CHUNK)

    # Detect task context
    task_dir = None
    if is_task_directory(project_dir):
        task_dir = project_dir
    else:
        task_dir = find_task_directory(project_dir)

    if task_dir is not None:
        # Task context: resolve chunk across external and project repos
        try:
            config = load_task_config(task_dir)
        except FileNotFoundError:
            click.echo(
                f"Error: Task configuration not found. Expected .ve-task.yaml in {task_dir}",
                err=True
            )
            raise SystemExit(1)

        # Resolve external repo path
        try:
            external_repo_path = resolve_repo_directory(task_dir, config.external_artifact_repo)
        except FileNotFoundError:
            click.echo(
                f"Error: External repository '{config.external_artifact_repo}' not found or not accessible",
                err=True
            )
            raise SystemExit(1)

        # Find the target chunk (could be in external repo or a project)
        target_chunks = None
        target_chunk_name = None
        target_project_path = None

        # First try external repo
        external_chunks = Chunks(external_repo_path)
        resolved = external_chunks.resolve_chunk_id(chunk_id)
        if resolved is not None:
            target_chunks = external_chunks
            target_chunk_name = resolved
            target_project_path = external_repo_path
        else:
            # Try project repos
            for project_ref in config.projects:
                try:
                    project_path = resolve_repo_directory(task_dir, project_ref)
                    project_chunks = Chunks(project_path)
                    resolved = project_chunks.resolve_chunk_id(chunk_id)
                    if resolved is not None:
                        target_chunks = project_chunks
                        target_chunk_name = resolved
                        target_project_path = project_path
                        break
                except FileNotFoundError:
                    continue

        if target_chunks is None:
            click.echo(f"Error: Chunk '{chunk_id}' not found in any task repository", err=True)
            raise SystemExit(1)

        # Create subsystems instance for the same repo where chunk was found
        target_subsystems = Subsystems(target_project_path)

        try:
            overlapping = target_subsystems.find_overlapping_subsystems(target_chunk_name, target_chunks)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        for item in overlapping:
            click.echo(f"docs/subsystems/{item['subsystem_id']} [{item['status']}]")
    else:
        # Single repo context - existing behavior
        subsystems_mgr = Subsystems(project_dir)
        chunks = Chunks(project_dir)

        try:
            overlapping = subsystems_mgr.find_overlapping_subsystems(chunk_id, chunks)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

        for item in overlapping:
            click.echo(f"docs/subsystems/{item['subsystem_id']} [{item['status']}]")
