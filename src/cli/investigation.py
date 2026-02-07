"""Investigation command group.

Commands for managing investigations - exploratory documents.
"""
# Subsystem: docs/subsystems/workflow_artifacts - Workflow artifact lifecycle
# Chunk: docs/chunks/cli_modularize - Investigation CLI commands
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
# Chunk: docs/chunks/investigation_commands - CLI commands for investigation management

import json
import pathlib

import click

from external_refs import strip_artifact_path_prefix
from investigations import Investigations
from models import InvestigationStatus, ArtifactType
from task_utils import (
    create_task_investigation,
    list_task_artifacts_grouped,
    TaskInvestigationError,
    TaskArtifactListError,
    load_task_config,
    parse_projects_option,
    check_task_project_context,
)
from artifact_ordering import ArtifactIndex, ArtifactType

from cli.utils import validate_short_name, warn_task_project_context, handle_task_context
from cli.formatters import (
    artifact_to_json_dict,
    format_grouped_artifact_list,
    format_grouped_artifact_list_json,
)


@click.group()
def investigation():
    """Manage investigations - exploratory documents for understanding before acting.

    Start an investigation when you need to explore before committing to
    implementation, such as diagnosing issues or validating hypotheses.
    """
    pass


@investigation.command("create")
@click.argument("short_name")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
@click.option("--projects", default=None, help="Comma-separated list of projects to link (default: all)")
def create_investigation(short_name, project_dir, projects):
    """Create a new investigation."""
    errors = validate_short_name(short_name)

    if errors:
        for error in errors:
            click.echo(f"Error: {error}", err=True)
        raise SystemExit(1)

    # Normalize to lowercase
    short_name = short_name.lower()

    # Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
    if handle_task_context(project_dir, lambda: _create_task_investigation(project_dir, short_name, projects)):
        return

    # Single-repo mode - check if we're in a project that's part of a task
    task_context = check_task_project_context(project_dir)
    warn_task_project_context(task_context, "investigation")

    # Single-repo mode
    investigations = Investigations(project_dir)
    investigation_path = investigations.create_investigation(short_name)

    # Show path relative to project_dir
    relative_path = investigation_path.relative_to(project_dir)
    click.echo(f"Created {relative_path}")


def _create_task_investigation(task_dir: pathlib.Path, short_name: str, projects_input: str | None = None):
    """Handle investigation creation in task directory (cross-repo mode)."""
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
        result = create_task_investigation(task_dir, short_name, projects=projects)
    except TaskInvestigationError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Report created paths
    external_path = result["external_investigation_path"]
    click.echo(f"Created investigation in external repo: {external_path.relative_to(task_dir)}/")

    for project_ref, yaml_path in result["project_refs"].items():
        # Show the investigation directory, not the yaml file
        investigation_dir = yaml_path.parent
        click.echo(f"Created reference in {project_ref}: {investigation_dir.relative_to(task_dir)}/")


@investigation.command("list")
@click.option("--state", type=str, default=None, help="Filter by investigation state")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
# Chunk: docs/chunks/cli_exit_codes - Exit code 0 for empty investigation list results
# Chunk: docs/chunks/cli_json_output - JSON output for artifact list commands
def list_investigations(state, json_output, project_dir):
    """List all investigations."""
    from artifact_ordering import ArtifactIndex, ArtifactType

    # Chunk: docs/chunks/cli_task_context_dedup - Using handle_task_context for routing
    if handle_task_context(project_dir, lambda: _list_task_investigations(project_dir, json_output)):
        return

    # Validate state filter if provided
    if state is not None:
        try:
            state_filter = InvestigationStatus(state)
        except ValueError:
            valid_states = ", ".join(s.value for s in InvestigationStatus)
            click.echo(
                f"Error: Invalid state '{state}'. Valid states: {valid_states}",
                err=True
            )
            raise SystemExit(1)
    else:
        state_filter = None

    investigations = Investigations(project_dir)
    artifact_index = ArtifactIndex(project_dir)

    # Get investigations in causal order (oldest first from index) and reverse for newest first
    ordered = artifact_index.get_ordered(ArtifactType.INVESTIGATION)
    investigation_list = list(reversed(ordered))

    # Filter by state if requested
    if state_filter is not None:
        filtered_list = []
        for inv_name in investigation_list:
            frontmatter = investigations.parse_investigation_frontmatter(inv_name)
            if frontmatter and frontmatter.status == state_filter:
                filtered_list.append(inv_name)
        investigation_list = filtered_list

    if not investigation_list:
        if json_output:
            click.echo(json.dumps([]))
            return
        click.echo("No investigations found")
        raise SystemExit(0)

    # Get tips for indicator display
    tips = set(artifact_index.find_tips(ArtifactType.INVESTIGATION))

    if json_output:
        results = []
        for inv_name in investigation_list:
            frontmatter = investigations.parse_investigation_frontmatter(inv_name)
            result = artifact_to_json_dict(inv_name, frontmatter, tips)
            results.append(result)
        click.echo(json.dumps(results, indent=2))
    else:
        for inv_name in investigation_list:
            frontmatter = investigations.parse_investigation_frontmatter(inv_name)
            status = frontmatter.status.value if frontmatter else "UNKNOWN"
            tip_indicator = " *" if inv_name in tips else ""
            click.echo(f"docs/investigations/{inv_name} [{status}]{tip_indicator}")


# Chunk: docs/chunks/cli_json_output - JSON output for task context investigation listing
def _list_task_investigations(task_dir: pathlib.Path, json_output: bool = False):
    """Handle investigation listing in task directory (cross-repo mode)."""
    try:
        grouped_data = list_task_artifacts_grouped(task_dir, ArtifactType.INVESTIGATION)
        if json_output:
            format_grouped_artifact_list_json(grouped_data, "investigations")
        else:
            format_grouped_artifact_list(grouped_data, "investigations")
    except (TaskInvestigationError, TaskArtifactListError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@investigation.command()
@click.argument("investigation_id")
@click.argument("new_status", required=False, default=None)
@click.option("--project-dir", type=click.Path(exists=True, path_type=pathlib.Path), default=".")
def status(investigation_id, new_status, project_dir):
    """Show or update investigation status."""
    from models import extract_short_name

    # Normalize investigation_id to strip path prefixes
    investigation_id = strip_artifact_path_prefix(investigation_id, ArtifactType.INVESTIGATION)

    investigations = Investigations(project_dir)

    # Extract shortname for display
    shortname = extract_short_name(investigation_id)

    # Display mode: just show current status
    if new_status is None:
        frontmatter = investigations.parse_investigation_frontmatter(investigation_id)
        if frontmatter is None:
            from cli.utils import format_not_found_error
            click.echo(f"Error: {format_not_found_error('Investigation', investigation_id, 've investigation list')}", err=True)
            raise SystemExit(1)
        click.echo(f"{shortname}: {frontmatter.status.value}")
        return

    # Transition mode: validate and update status
    # First validate new_status is a valid InvestigationStatus value
    try:
        new_status_enum = InvestigationStatus(new_status)
    except ValueError:
        valid_statuses = ", ".join(s.value for s in InvestigationStatus)
        click.echo(
            f"Error: Invalid status '{new_status}'. Valid statuses: {valid_statuses}",
            err=True
        )
        raise SystemExit(1)

    # Attempt the transition
    try:
        old_status, updated_status = investigations.update_status(investigation_id, new_status_enum)
        click.echo(f"{shortname}: {old_status.value} -> {updated_status.value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
